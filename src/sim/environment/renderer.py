import copy
import time

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

from environment.world_grid import GridWorld
from environment.control_panel import ControlPanel, _bind_window_close


def _fmt(x):
    """Show floats with 2 decimals; leave ints (and everything else) untouched."""
    return f"{x:.2f}" if isinstance(x, float) else str(x)


class GridWorldRenderer:
    def __init__(self):
        self.control_panel = ControlPanel()

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
            "figure_size": (6, 6),
        }

        self.fig = None
        self.ax = None

        # Set by the runner before the first render call
        self.state_history = None
        self.blackboard = None

        # Kept across calls so _wait_if_paused can redraw without extra args
        self._last_world = None
        self._last_config = None

        # Only redraw the graph when a new cycle snapshot has been added
        self._last_graph_len = -1

        # Frame-rate cap for the "max speed" (delay == 0) path
        self._last_draw_time = 0.0
        self._min_frame_interval = 1.0 / 30.0

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
            try:
                plt.pause(0.001)
            except Exception:
                plt.draw()
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

        self._wait_if_paused()

        if self._should_quit():
            self._quit()

    def _refresh_panel(self):
        """Update the cycle label, graph and blackboard — once per new cycle."""
        notes = self.blackboard.read() if self.blackboard is not None else {}
        hist = self.state_history
        if hist is None or len(hist) == 0:
            self.control_panel.set_label(
                f"Cycle: {getattr(self._last_world, 'cycle', 0)}"
            )
            self.control_panel.update_blackboard(notes)
            return
        if len(hist) != self._last_graph_len:
            self.control_panel.set_label(
                f"Cycle: {hist.cycle_at(hist.latest_index)}"
            )
            # Blackboard first, then the graph — the graph's flush renders both.
            self.control_panel.update_blackboard(notes)
            self.control_panel.update_graph(hist)
            self._last_graph_len = len(hist)

    def _quit(self):
        """Tear down both windows and stop the whole program."""
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
        """Process pending GUI events for both windows without blocking."""
        for fig in (self.control_panel.fig, self.fig):
            if fig is None:
                continue
            try:
                fig.canvas.flush_events()
            except Exception:
                pass

    def close(self):
        if self.fig:
            plt.close(self.fig)
        self.control_panel.close()

    # ------------------------------------------------------------------
    # Pause / browse logic
    # ------------------------------------------------------------------

    def _should_quit(self) -> bool:
        """
        True if either window was closed. The WM_DELETE_WINDOW hook set up in
        the control panel sets cp.quit synchronously; the fignum_exists polling
        below is a backend-agnostic fallback.
        """
        cp = self.control_panel
        if cp.quit:
            return True
        if cp.fig is not None and not plt.fignum_exists(cp.fig.number):
            cp.quit = True
            return True
        if self.fig is not None and not plt.fignum_exists(self.fig.number):
            cp.quit = True
            return True
        return False

    def _wait_if_paused(self):
        cp = self.control_panel
        if not cp.paused:
            return

        # Back up current world state so we can undo display-only changes
        # if the user browses but then resumes from "latest".
        world_backup = self._take_world_backup(self._last_world) if self._last_world else None

        # Initialise view to latest snapshot when entering pause
        if self.state_history is not None and len(self.state_history) > 0:
            cp.view_index = self.state_history.latest_index
            self._update_pause_label(cp.view_index)
            self.control_panel.update_graph(self.state_history, cp.view_index)

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
        """Draw one frame into self.fig / self.ax (no plt.pause call)."""
        grid = self._build_grid(world)

        cmap = ListedColormap([
            merged_config["colors"]["empty"],
            merged_config["colors"]["tree_low"],
            merged_config["colors"]["tree_high"],
            merged_config["colors"]["collector"],
            merged_config["colors"]["cutter"],
        ])

        if self.fig is None:
            self.fig, self.ax = plt.subplots(figsize=merged_config["figure_size"])
            self.fig.canvas.mpl_connect(
                "close_event", lambda e: self.control_panel._on_close()
            )
            _bind_window_close(self.fig, self.control_panel._on_close)

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
