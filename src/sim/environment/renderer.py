import copy
import time

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

from environment.world_grid import GridWorld
from environment.control_panel import ControlPanel, _bind_window_close, _bind_expose_redraw, _map_ax


def _fmt(x):
    """Show floats with 2 decimals; leave ints (and everything else) untouched."""
    return f"{x:.2f}" if isinstance(x, float) else str(x)


class BackToMenu(Exception):
    """Raised when the user clicks the control panel's Menu button, to unwind
    the current live run or replay back to main()'s replay menu without
    closing the window."""
    pass


class GridWorldRenderer:
    def __init__(self):
        self.default_config = {
            "colors": {
                "empty": "#1e1e1e",
                "tree_low": "#2e7d32",
                "tree_high": "#66bb6a",
                "collector": "#42a5f5",
                "cutter": "#ef5350",
            },
            "show_text": True,
            "show_grid": True,
            "figure_size": (6, 6),  # kept for API compatibility; combined figure ignores this
        }

        # Single combined figure: control panel (left 44%) + grid (right 56%)
        # This avoids two separate OS windows which cannot be positioned on Wayland/GTK4.
        self.fig = plt.figure("Ki-Arena", figsize=(11, 6))
        _bind_window_close(self.fig, self._on_close_shared)
        _bind_expose_redraw(self.fig)
        # One-time: actually realizes/shows the window. Every render loop
        # since only calls draw_idle()/flush_events() (not plt.pause) to avoid
        # re-raising the window on every frame, so this is the only show().
        plt.show(block=False)

        # Grid axes occupy the left portion of the combined figure
        self.ax = self.fig.add_axes([0.02, 0.06, 0.525, 0.87])

        # Control panel widgets live in the right 44% of the same figure
        self.control_panel = ControlPanel(fig=self.fig, region=(0.555, 0.0, 0.44, 1.0))

        # close_event on the shared figure mirrors to the control panel quit flag
        self.fig.canvas.mpl_connect("close_event", lambda e: self.control_panel._on_close())

        # Set by the runner before the first render call
        self.state_history = None
        self.blackboard = None
        # Set by the runner during a live run: called when the user clicks Save,
        # even while paused (the pause loop below polls for the request so a
        # long-running paused session doesn't have to resume just to save).
        self.on_save = None

        # Kept across calls so _wait_if_paused can redraw without extra args
        self._last_world = None
        self._last_config = None

        # Only redraw the graph when a new cycle snapshot has been added
        self._last_graph_len = -1

        # Frame-rate cap for the "max speed" (delay == 0) path
        self._last_draw_time = 0.0
        self._min_frame_interval = 1.0 / 30.0

        # Target cycle while running a single-cycle "Next" step (None = not stepping)
        self._step_target_cycle = None

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def render(self, world: GridWorld, config=None):
        self._last_world = world
        self._last_config = config

        delay = self.control_panel.tick_delay
        now = time.perf_counter()

        # Drawing and pacing are decoupled. A full matplotlib redraw costs far
        # more than the simulation step, so the draw rate is ALWAYS capped to
        # ~30 fps regardless of delay — otherwise a tiny delay would still force
        # a redraw every step and dominate the runtime.
        draw_due = (now - self._last_draw_time) >= self._min_frame_interval

        if draw_due:
            self._draw(world, self._merge_config(config))
            self._refresh_panel()          # label + graph, gated to once per cycle
            # Not plt.pause: it calls the backend's show(block=False) on every
            # invocation, which on Tk re-raises/deiconifies the window each
            # time — at ~30 calls/sec that makes the window visibly pop to the
            # front whenever another window overlaps it. draw + flush_events
            # processes the redraw and pending clicks without that side effect.
            try:
                self.fig.canvas.draw_idle()
                self.fig.canvas.flush_events()
            except Exception:
                pass
            # Record before the delay below, so the delay counts toward the next
            # frame's interval (keeps moderate delays drawing every step).
            self._last_draw_time = time.perf_counter()

        # The delay is the actual speed knob: it paces the simulation. Use a
        # precise sleep (plt.pause has ~30 ms of fixed overhead that would swamp
        # small delays and defeat fine speed control).
        if delay > 0:
            self._sleep_responsive(delay)
        elif not draw_due:
            self._flush_gui()

        if self._should_quit():
            self._quit()
        self._check_back_to_menu()

        self._wait_if_paused()

        if self._should_quit():
            self._quit()
        self._check_back_to_menu()

    def _status_text(self, cycle) -> str:
        """Cycle plus live demographics (death causes + sustainable population),
        read from the world mirror the env keeps up to date each cycle."""
        w = self._last_world
        parts = [f"Cycle: {cycle}"]
        dbc = getattr(w, "deaths_by_cause", None)
        if dbc is not None:
            parts.append(
                f"deaths  age:{dbc.get('old age', 0)}  "
                f"fruit:{dbc.get('starvation_fruit', 0)}  wood:{dbc.get('starvation_wood', 0)}"
            )
        avg = getattr(w, "avg_population", None)
        if avg is not None:
            parts.append(f"sustainable pop: {avg:.1f}")
        return "    |    ".join(parts)

    def _refresh_panel(self):
        """Update the cycle label, graph and blackboard — once per new cycle."""
        notes = self.blackboard.read() if self.blackboard is not None else {}
        hist = self.state_history
        if hist is None or len(hist) == 0:
            self.control_panel.set_label(
                self._status_text(getattr(self._last_world, 'cycle', 0))
            )
            self.control_panel.update_blackboard(notes)
            return
        if len(hist) != self._last_graph_len:
            self.control_panel.set_label(
                self._status_text(hist.cycle_at(hist.latest_index))
            )
            # Blackboard first, then the graph — the graph's flush renders both.
            self.control_panel.update_blackboard(notes)
            self.control_panel.update_graph(hist)
            self._last_graph_len = len(hist)

    def _on_close_shared(self, event=None):
        """Called when the combined figure window is closed."""
        self.control_panel._on_close()

    def _quit(self):
        """Tear down the window and stop the whole program."""
        try:
            plt.close("all")
        except Exception:
            pass
        raise SystemExit

    def _sleep_responsive(self, seconds):
        """
        Sleep for `seconds` to pace the simulation. Short waits are a single
        precise sleep; longer ones are chunked so the GUI keeps processing
        events (pause / slider / close) instead of freezing.
        """
        end = time.perf_counter() + seconds
        while True:
            remaining = end - time.perf_counter()
            if remaining <= 0:
                return
            if remaining > 0.02:
                self._flush_gui()
                if self._should_quit():
                    return
                time.sleep(0.02)
            else:
                time.sleep(remaining)
                return

    def _flush_gui(self):
        """Process pending GUI events without blocking."""
        try:
            self.fig.canvas.flush_events()
        except Exception:
            pass

    def close(self):
        if self.fig:
            plt.close(self.fig)

    def clear_grid(self) -> None:
        """Blank the grid pane (e.g. while the replay menu is showing) so a
        finished run's last frame doesn't linger on screen."""
        self.ax.clear()
        self.ax.set_facecolor(self.default_config["colors"]["empty"])
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_title("")
        self._last_world = None
        self._last_graph_len = -1
        self.fig.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Replay playback (no env stepping — just displays saved snapshots)
    # ------------------------------------------------------------------
    def play_replay(self, history, world) -> None:
        """
        Play back a loaded StateHistory. Starts paused on the first frame; the
        same controls as a live run work: Pause/Resume plays or stops, Prev/Next
        and clicking the graph scrub through cycles (while paused).
        """
        self.state_history = history
        self._last_world = world
        self._last_config = None
        cp = self.control_panel

        if len(history) == 0:
            return

        # The speed slider becomes a cycles/sec control for the replay.
        cp.set_replay_speed_mode(True)

        # Start paused so the user can step through (per the replay UX).
        cp.paused = True
        cp.btn_pause.label.set_text("Resume")
        idx = 0
        cp.view_index = 0
        self._draw_replay_frame(idx)

        acc = 0.0                       # fractional cycles carried between ticks
        last_time = time.perf_counter()
        last_draw = last_time

        while True:
            self._flush_gui()
            if self._should_quit():
                self._quit()
            self._check_back_to_menu()

            now = time.perf_counter()

            # Scrubbing via Prev/Next/graph-click (only fires while paused).
            if cp.view_changed:
                idx = max(0, min(cp.view_index, history.latest_index))
                cp.view_index = idx
                cp.view_changed = False
                self._draw_replay_frame(idx)
                acc, last_time, last_draw = 0.0, now, now

            elif not cp.paused:
                # Advance by cycles/sec * elapsed. Cycle stepping is decoupled
                # from drawing: at high speeds we jump many cycles per frame but
                # still redraw only ~30 fps, so fast replays stay smooth.
                acc += cp.replay_cps * (now - last_time)
                last_time = now
                if acc >= 1.0:
                    step = int(acc)
                    acc -= step
                    idx = min(history.latest_index, idx + step)
                    cp.view_index = idx
                    if idx >= history.latest_index:
                        self._draw_replay_frame(idx)
                        cp.paused = True            # reached the end → pause
                        cp.btn_pause.label.set_text("Resume")
                        self.fig.canvas.draw_idle()
                    elif (now - last_draw) >= self._min_frame_interval:
                        self._draw_replay_frame(idx)
                        last_draw = now
            else:
                # Paused: keep the clock current so resuming doesn't jump ahead.
                acc, last_time = 0.0, now

            time.sleep(0.005)

    def _draw_replay_frame(self, idx: int) -> None:
        hist = self.state_history
        hist.restore_world_only(self._last_world, idx)
        self._draw(self._last_world, self._merge_config(self._last_config))
        cycle = hist.cycle_at(idx)
        latest = hist.cycle_at(hist.latest_index)
        tag = "[paused]" if self.control_panel.paused else "[playing]"
        self.control_panel.set_label(f"Replay — Cycle {cycle} / {latest}  {tag}")
        self.control_panel.update_blackboard(hist.blackboard_at(idx))
        self.control_panel.update_graph(hist, idx)
        self._flush_gui()

    # ------------------------------------------------------------------
    # Pause / browse logic
    # ------------------------------------------------------------------

    def _should_quit(self) -> bool:
        """True if the window was closed."""
        cp = self.control_panel
        if cp.quit:
            return True
        if self.fig is not None and not plt.fignum_exists(self.fig.number):
            cp.quit = True
            return True
        return False

    def _check_back_to_menu(self) -> None:
        """Raise BackToMenu once if the user clicked the panel's Menu button."""
        cp = self.control_panel
        if cp.back_to_menu:
            cp.back_to_menu = False
            raise BackToMenu()

    def _wait_if_paused(self):
        cp = self.control_panel
        if not cp.paused:
            self._step_target_cycle = None
            return

        # Single-cycle step in progress: don't block until the target cycle is
        # reached, so the sim advances exactly one cycle then re-pauses below.
        if self._step_target_cycle is not None:
            if getattr(self._last_world, "cycle", 0) < self._step_target_cycle:
                return
            self._step_target_cycle = None

        # Back up current world state so we can undo display-only changes
        # if the user browses but then resumes from "latest".
        world_backup = self._take_world_backup(self._last_world) if self._last_world else None

        # Initialise view to latest snapshot when entering pause
        if self.state_history is not None and len(self.state_history) > 0:
            cp.view_index = self.state_history.latest_index
            self._update_pause_label(cp.view_index)
            self.control_panel.update_graph(self.state_history, cp.view_index)

        # Make sure the current frame is on screen when we pause — a fast single
        # step (or the very first paused frame) may have skipped render()'s
        # throttled draw.
        if self._last_world is not None:
            self._draw(self._last_world, self._merge_config(self._last_config))
            self._flush_gui()

        browsed = False

        while cp.paused:
            # Pump *both* windows' event queues. plt.pause only services the
            # active figure (the grid), which starves the control panel of its
            # button and window-close events while paused. Flushing each canvas
            # explicitly keeps the panel fully responsive.
            self._flush_gui()
            time.sleep(0.03)

            if self._should_quit():
                self._quit()
            self._check_back_to_menu()

            if cp.save_request:
                cp.save_request = False
                if self.on_save is not None:
                    self.on_save()

            # Step request (Next at the latest cycle): leave the pause loop, run
            # exactly one more cycle, then pause again (handled at the top on the
            # next call). Step from the real latest state, not a browsed frame.
            if cp.step_request:
                cp.step_request = False
                self._step_target_cycle = getattr(self._last_world, "cycle", 0) + 1
                if browsed and world_backup is not None:
                    self._apply_world_backup(self._last_world, world_backup)
                self._last_graph_len = -1
                return

            if not cp.view_changed:
                continue
            if self.state_history is None or len(self.state_history) == 0:
                cp.view_changed = False
                continue

            # Clamp view_index to valid range
            cp.view_index = max(0, min(cp.view_index, self.state_history.latest_index))

            # Restore world for display and redraw
            self.state_history.restore_world_only(self._last_world, cp.view_index)
            self._draw(self._last_world, self._merge_config(self._last_config))
            self._update_pause_label(cp.view_index)
            self.control_panel.update_graph(self.state_history, cp.view_index)
            self._flush_gui()

            cp.view_changed = False
            browsed = True

        # On resume: decide whether runner needs to restore full env state
        if browsed and self.state_history is not None and len(self.state_history) > 0:
            if cp.view_index < self.state_history.latest_index:
                # User resumed from a past snapshot → runner must restore
                cp.needs_restore = True
            else:
                # User navigated back to latest → undo display-only world changes
                if world_backup is not None:
                    self._apply_world_backup(self._last_world, world_backup)

        # Force the graph to refresh on resume so the browse marker is cleared
        self._last_graph_len = -1

    def _update_pause_label(self, view_index: int) -> None:
        if self.state_history is None or len(self.state_history) == 0:
            return
        cycle = self.state_history.cycle_at(view_index)
        latest_cycle = self.state_history.cycle_at(self.state_history.latest_index)
        if view_index == self.state_history.latest_index:
            self.control_panel.set_label(f"Cycle: {cycle}  [paused]")
        else:
            self.control_panel.set_label(f"Cycle: {cycle} / {latest_cycle}  [browsing]")

    # ------------------------------------------------------------------
    # World snapshot helpers (renderer-local, for undo of display-only changes)
    # ------------------------------------------------------------------

    def _take_world_backup(self, world) -> dict:
        return {
            "positions":    copy.deepcopy(world.positions),
            "trees":        copy.deepcopy(world.trees),
            "alive_agents": copy.deepcopy(world.alive_agents),
            "agent_ages":   copy.deepcopy(world.agent_ages),
            "wood":         world.wood,
            "fruits":       world.fruits,
            "cycle":        world.cycle,
        }

    def _apply_world_backup(self, world, backup: dict) -> None:
        world.positions    = copy.deepcopy(backup["positions"])
        world.trees        = copy.deepcopy(backup["trees"])
        world.alive_agents = copy.deepcopy(backup["alive_agents"])
        world.agent_ages   = copy.deepcopy(backup["agent_ages"])
        world.wood         = backup["wood"]
        world.fruits       = backup["fruits"]
        world.cycle        = backup["cycle"]

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw(self, world: GridWorld, merged_config: dict) -> None:
        """Draw one frame into self.ax (no plt.pause call)."""
        grid = self._build_grid(world)

        cmap = ListedColormap([
            merged_config["colors"]["empty"],
            merged_config["colors"]["tree_low"],
            merged_config["colors"]["tree_high"],
            merged_config["colors"]["collector"],
            merged_config["colors"]["cutter"],
        ])

        self.ax.clear()
        self.ax.imshow(grid, cmap=cmap, vmin=0, vmax=4)
        self._draw_grid(world, merged_config)
        self._draw_text(world, merged_config)
        self._draw_title(world)

    def _build_grid(self, world):
        # imshow draws grid[row][col]: row is the vertical axis (y), col is the
        # horizontal axis (x). So index as grid[y][x].
        grid = np.zeros((world.size, world.size))

        for (x, y), fruit in world.trees.items():
            grid[y][x] = 1 if fruit <= 2 else 2

        for agent, pos in world.positions.items():
            x, y = pos
            if "collector" in agent:
                grid[y][x] = 3
            elif "cutter" in agent:
                grid[y][x] = 4

        return grid

    def _draw_grid(self, world: GridWorld, config):
        self.ax.set_xticks(np.arange(-0.5, world.size, 1), minor=True)
        self.ax.set_yticks(np.arange(-0.5, world.size, 1), minor=True)

        if config["show_grid"]:
            self.ax.grid(which="minor", color="white", linestyle="-", linewidth=1)

        self.ax.tick_params(
            which="both", bottom=False, left=False,
            labelbottom=False, labelleft=False
        )

    def _draw_text(self, world: GridWorld, config):
        if not config["show_text"]:
            return

        for (x, y), fruit in world.trees.items():
            # text(horizontal, vertical) = text(x, y).
            self.ax.text(x, y, _fmt(fruit), ha="center", va="center",
                         color="white", fontsize=10)

        if not hasattr(world, "agent_ages"):
            return

        position_agents: dict = {}
        for agent, pos in world.positions.items():
            key = tuple(pos)
            position_agents.setdefault(key, []).append(agent)

        for agent, pos in world.positions.items():
            x, y = pos
            key = (x, y)
            age = world.agent_ages.get(agent, 0)

            if position_agents[key][0] == agent:
                self.ax.text(x, y - 0.3, str(age), ha="center", va="center",
                             color="white", fontsize=8,
                             bbox=dict(facecolor="black", alpha=0.7,
                                       edgecolor="none", pad=1))

            if len(position_agents[key]) > 1 and position_agents[key][0] == agent:
                self.ax.text(x, y + 0.3, str(len(position_agents[key])),
                             ha="center", va="center", color="white", fontsize=8,
                             bbox=dict(facecolor="black", alpha=0.7,
                                       edgecolor="none", pad=1))

    def _draw_title(self, world: GridWorld):
        total_fruit_on_trees = sum(world.trees.values())
        num_trees = len(world.trees)
        wood = getattr(world, "wood", 0)
        fruits = getattr(world, "fruits", 0)
        cycle = getattr(world, "cycle", 0)

        self.ax.set_title(
            f"Cycle: {_fmt(cycle)} | Trees: {_fmt(num_trees)} | "
            f"Tree Fruit: {_fmt(total_fruit_on_trees)} | "
            f"Wood: {_fmt(wood)} | Fruits: {_fmt(fruits)}"
        )

    def _merge_config(self, config):
        if config is None:
            return self.default_config

        merged = {
            k: (v.copy() if isinstance(v, dict) else v)
            for k, v in self.default_config.items()
        }
        for k, v in config.items():
            if isinstance(v, dict):
                merged[k].update(v)
            else:
                merged[k] = v
        return merged
