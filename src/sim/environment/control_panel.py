import os
import time

import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider
from typing import Optional


def _map_ax(pos, region):
    """Map axis [l, b, w, h] from local [0,1]² to figure coords within region [rl, rb, rw, rh]."""
    rl, rb, rw, rh = region
    l, b, w, h = pos
    return [rl + l * rw, rb + b * rh, w * rw, h * rh]


def _bind_window_close(fig, callback) -> None:
    """
    Bind a synchronous window-close handler on the figure's GUI window.

    matplotlib's own ``close_event`` for a TkAgg window is dispatched through a
    deferred ``after_idle`` callback on *that window's* event loop. While the
    simulation is paused we are spinning another figure's event loop, so that
    deferred callback never runs and the close goes undetected. Hooking the
    native ``WM_DELETE_WINDOW`` protocol fires immediately instead, the same way
    the panel's buttons do. Best-effort: silently skipped on non-Tk backends.
    """
    try:
        window = fig.canvas.manager.window
        window.protocol("WM_DELETE_WINDOW", lambda: callback())
    except Exception:
        pass


def _pump_gui(fig, interval: float) -> None:
    """
    Process pending GUI events and wait ~interval seconds, without using
    ``plt.pause``.

    ``plt.pause`` calls the backend's ``show(block=False)`` on every
    invocation, which on Tk re-raises/deiconifies the window each time — in a
    blocking loop that runs 10-20x/second, that makes the window visibly pop
    to the front and back whenever another window overlaps it. Driving the
    event loop with ``draw_idle`` + ``flush_events`` (what ``pause`` does
    internally besides the ``show`` call) processes clicks and redraws just
    the same, without repeatedly re-showing the window.
    """
    try:
        if fig.stale:
            fig.canvas.draw_idle()
        fig.canvas.flush_events()
    except Exception:
        pass
    time.sleep(interval)


def _bind_expose_redraw(fig) -> None:
    """
    Force a full canvas redraw when the window is uncovered.

    Our render loops only request a redraw (``draw_idle``) when the simulation
    data actually changes; while paused, or between ticks, nothing re-triggers
    a draw at all. Tk repaints an exposed canvas region from its own
    back-buffer, but if that buffer was never (re)drawn while the window sat
    behind another one — e.g. covering just part of it, or a compositor
    dropping the buffer — the newly exposed area can show stale or garbled
    pixels until the next real draw(). Binding <Expose> forces that repaint
    immediately. Best-effort: silently skipped on non-Tk backends.
    """
    try:
        widget = fig.canvas.get_tk_widget()
        widget.bind("<Expose>", lambda e: fig.canvas.draw())
    except Exception:
        pass


class ControlPanel:
    """
    A separate matplotlib window with Pause/Resume, Rewind, and Forward buttons.

    Flags read by the renderer / runner:
        paused        – simulation is halted
        view_changed  – user clicked ◀ or ▶; renderer should redraw from history
        view_index    – which history snapshot to display (set/clamped by renderer)
        needs_restore – set by renderer when user resumes from a past snapshot;
                        runner restores full env state then clears this flag
    """

    def __init__(self, fig=None, region=(0.0, 0.0, 1.0, 1.0)):
        self.paused = False
        self.view_index = 0
        self.view_changed = False
        self.needs_restore = False
        self.quit = False
        self.back_to_menu = False  # set when the user clicks "Menu"
        self.tick_delay = 0.05  # seconds the renderer waits between steps

        # Replay menu state: set to a file path or the string "LIVE" once chosen.
        self.replay_choice = None
        self._menu_axes = []
        self._menu_buttons = []

        # Step mode: set when the user presses Next at the latest cycle while
        # paused, asking a live run to advance exactly one cycle then re-pause.
        self.step_request = False

        # Replay playback speed. During a replay the speed slider is reused as a
        # "cycles per second" control (instead of the live "delay" meaning).
        self.replay_mode = False
        self.replay_cps = 20.0
        self._cps_max = 240.0  # cycles/sec at the slider's far right

        # Store history data for graph click mapping
        self._graph_cycles = []
        self._graph_history = None

        if fig is None:
            self.fig = plt.figure("Ki-Arena Control Panel", figsize=(5, 5.5))
            self.fig.canvas.mpl_connect("close_event", self._on_close)
            _bind_window_close(self.fig, self._on_close)
            _bind_expose_redraw(self.fig)
            plt.show(block=False)  # one-time: see renderer.py for why not plt.pause
        else:
            # Shared figure provided by the renderer; close events bound there.
            self.fig = fig

        rl, rb, rw, rh = region
        self._region = region

        ax_menu = self.fig.add_axes(_map_ax([0.03, 0.90, 0.16, 0.06], region))
        ax_rw   = self.fig.add_axes(_map_ax([0.21, 0.90, 0.14, 0.06], region))
        ax_pp   = self.fig.add_axes(_map_ax([0.37, 0.90, 0.26, 0.06], region))
        ax_fw   = self.fig.add_axes(_map_ax([0.65, 0.90, 0.32, 0.06], region))

        self.btn_menu    = Button(ax_menu, "☰ Menu")
        self.btn_rewind  = Button(ax_rw, "< Prev")
        self.btn_pause   = Button(ax_pp, "Pause")
        self.btn_forward = Button(ax_fw, "Next >")

        self.btn_menu.on_clicked(self._on_menu)
        self.btn_rewind.on_clicked(self._on_rewind)
        self.btn_pause.on_clicked(self._toggle_pause)
        self.btn_forward.on_clicked(self._on_forward)

        self._label = self.fig.text(
            rl + 0.5 * rw, rb + 0.985 * rh, "",
            ha="center", va="top",
            fontsize=9
        )

        # Tick-speed slider. The handle position (0..1) is mapped cubically to
        # the delay, so most of the travel gives fine control in the small-delay
        # range between 0 and the default, while the top still reaches 1.0 s.
        ax_speed = self.fig.add_axes(_map_ax([0.30, 0.855, 0.45, 0.02], region))
        self.slider_speed = Slider(
            ax_speed, "Delay (s)", 0.0, 1.0,
            valinit=self.tick_delay ** (1 / 3), valstep=0.001
        )
        self.slider_speed.valtext.set_text(f"{self.tick_delay:.3f}")
        self.slider_speed.on_changed(self._on_speed_change)

        # Three stacked graphs over cycles, each on its own scale so nothing gets
        # squashed: resources (wood/fruit) on top, then population head-counts,
        # then average age of the living agents at the bottom.
        self.ax_graph = self.fig.add_axes(_map_ax([0.12, 0.70, 0.82, 0.13], region))       # resources
        self.ax_graph_pop = self.fig.add_axes(_map_ax([0.12, 0.555, 0.82, 0.12], region))  # population
        self.ax_graph_age = self.fig.add_axes(_map_ax([0.12, 0.41, 0.82, 0.12], region))   # average age
        # Enable click events on all graphs (for rewind-by-click)
        self.ax_graph.set_picker(True)
        self.ax_graph_pop.set_picker(True)
        self.ax_graph_age.set_picker(True)
        self.fig.canvas.mpl_connect('button_press_event', self._on_graph_click)

        # Blackboard readout: each agent's current announcement, one per line
        self.ax_board = self.fig.add_axes(_map_ax([0.06, 0.04, 0.90, 0.30], region))
        self.update_blackboard({})

    def _on_close(self, event=None):
        self.quit = True

    def _on_menu(self, event):
        self.back_to_menu = True

    def _on_speed_change(self, pos):
        pos = float(pos)
        # Live runs: cubic map to a small per-step delay (fine control near 0).
        self.tick_delay = pos ** 3
        # Replays: exponential map to cycles/sec (1 at far left .. _cps_max right).
        self.replay_cps = self._cps_max ** pos
        if self.replay_mode:
            self.slider_speed.valtext.set_text(f"{self.replay_cps:.0f}")
        else:
            self.slider_speed.valtext.set_text(f"{self.tick_delay:.3f}")

    def set_replay_speed_mode(self, on: bool) -> None:
        """Relabel the speed slider as cycles/sec (replay) or delay (live)."""
        import math
        self.replay_mode = on
        if on:
            self.slider_speed.label.set_text("Cycles/s")
            # Default ~20 cycles/sec: find the handle position that maps to it.
            default_pos = math.log(20.0) / math.log(self._cps_max)
            self.slider_speed.set_val(default_pos)  # fires _on_speed_change
        else:
            self.slider_speed.label.set_text("Delay (s)")
            self.slider_speed.valtext.set_text(f"{self.tick_delay:.3f}")
        self.fig.canvas.draw_idle()

    # ------------------------------------------------------------------
    def _toggle_pause(self, event):
        self.paused = not self.paused
        self.btn_pause.label.set_text("Resume" if self.paused else "Pause")
        self.fig.canvas.draw_idle()

    def _on_rewind(self, event):
        if not self.paused:
            return
        self.view_index -= 1  # clamped to 0 by renderer
        self.view_changed = True

    def _on_forward(self, event):
        if not self.paused:
            return
        # Up to the latest recorded cycle, Next just browses forward through the
        # history. At (or past) the latest cycle it asks the live sim to advance
        # one more cycle — that gives step-by-step iteration while paused.
        latest = len(self._graph_cycles) - 1
        if self.view_index >= latest:
            self.step_request = True
        else:
            self.view_index += 1
            self.view_changed = True

    def _on_graph_click(self, event):
        """
        Handle click events on the graph to allow rewinding to specific points.
        Only works when paused (browsing mode).
        """
        if not self.paused:
            return
        
        # Check if click was on any of the three stacked graphs.
        if event.inaxes not in (self.ax_graph, self.ax_graph_pop, self.ax_graph_age):
            return
        
        # Only handle left mouse button clicks
        if event.button != 1:  # 1 = left mouse button
            return
        
        # Need history data to map click to cycle
        if not self._graph_cycles or len(self._graph_cycles) == 0:
            return
            
        # Get the x-coordinate (cycle) from the click position
        x_data = event.xdata
        if x_data is None:
            return
        
        # Find the nearest cycle index
        nearest_index = self._find_nearest_cycle_index(x_data)
        if nearest_index is not None:
            self.view_index = nearest_index
            self.view_changed = True

    def _find_nearest_cycle_index(self, target_cycle: float) -> Optional[int]:
        """
        Find the index of the cycle in _graph_cycles that is closest to target_cycle.
        Returns None if no cycles are available.
        """
        if not self._graph_cycles or len(self._graph_cycles) == 0:
            return None
        
        # Find the closest cycle using linear search (cycles are already sorted)
        closest_index = 0
        closest_distance = abs(self._graph_cycles[0] - target_cycle)
        
        for i, cycle in enumerate(self._graph_cycles):
            distance = abs(cycle - target_cycle)
            if distance < closest_distance:
                closest_distance = distance
                closest_index = i
        
        return closest_index

    # ------------------------------------------------------------------
    def update_graph(self, history, current_index=None) -> None:
        """
        Redraw the wood / fruit / population graph from the rewind snapshots.
        If current_index is given (while paused/browsing), mark that cycle.
        """
        if history is None or len(history) == 0:
            return

        cycles, wood, fruits, population, collectors, cutters, avg_age = history.series()

        # Store cycles and history for click handling
        self._graph_cycles = cycles
        self._graph_history = history

        # --- Top graph: resources (wood / fruit) ---
        ax = self.ax_graph
        ax.clear()
        ax.plot(cycles, wood, color="#8d6e63", label="Wood")
        ax.plot(cycles, fruits, color="#fdd835", label="Fruit")
        ax.set_ylabel("Wood / Fruit", fontsize=8)
        # X labels only on the bottom graph; all three share the same cycle axis.
        ax.tick_params(labelsize=7, labelbottom=False)
        ax.set_ylim(bottom=0)
        ax.legend(loc="upper left", fontsize=7)

        # --- Middle graph: population (colours match the grid) ---
        axp = self.ax_graph_pop
        axp.clear()
        axp.plot(cycles, population, color="#cfcfcf", label="Population")
        axp.plot(cycles, collectors, color="#42a5f5", linestyle="--", linewidth=0.9, label="Collectors")
        axp.plot(cycles, cutters, color="#ef5350", linestyle="--", linewidth=0.9, label="Cutters")
        axp.set_ylabel("Population", fontsize=8)
        axp.tick_params(labelsize=7, labelbottom=False)
        axp.set_ylim(bottom=0)  # head-counts never go negative; keep baseline at 0
        axp.legend(loc="upper left", fontsize=7)

        # --- Bottom graph: average age of the living population ---
        axa = self.ax_graph_age
        axa.clear()
        axa.plot(cycles, avg_age, color="#ab47bc", label="Avg age")
        axa.set_xlabel("Cycle", fontsize=8)
        axa.set_ylabel("Avg age", fontsize=8)
        axa.tick_params(labelsize=7)
        axa.set_ylim(bottom=0)

        # Browse marker on all graphs.
        if current_index is not None and 0 <= current_index < len(cycles):
            for a in (ax, axp, axa):
                a.axvline(cycles[current_index], color="#888888",
                          linestyle="--", linewidth=1)

        self.fig.canvas.draw_idle()
        try:
            self.fig.canvas.flush_events()
        except Exception:
            pass

    # ------------------------------------------------------------------
    def update_blackboard(self, notes: dict[str, str]) -> None:
        """
        Show the current blackboard: one "agent: plan" line per agent.
        `notes` is the {agent_name: plan_text} dict from the shared Blackboard,
        where each plan is the natural-language sentence the LLM wrote. Drawn
        with draw_idle only — the flush from update_graph renders it.
        """
        ax = self.ax_board
        ax.clear()
        ax.axis("off")

        ax.text(0.0, 1.0, "Blackboard", transform=ax.transAxes,
                va="top", ha="left", fontsize=9, fontweight="bold")

        if notes:
            y = 0.82
            for name, plan in notes.items():
                # Truncate long plans so they fit the panel.
                text = plan if len(plan) <= 48 else plan[:45] + "..."
                ax.text(0.0, y, f"{name}: {text}", transform=ax.transAxes,
                        va="top", ha="left", fontsize=8, family="monospace")
                y -= 0.13
        else:
            ax.text(0.0, 0.82, "(no announcements)", transform=ax.transAxes,
                    va="top", ha="left", fontsize=8, color="gray", style="italic")

        self.fig.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Replay menu (shown at startup when saved runs exist)
    # ------------------------------------------------------------------
    def show_replay_menu(self, save_paths: list[str]) -> None:
        """
        Show a clickable list of saved runs in the right panel, plus a button to
        start a fresh live run. Sets ``self.replay_choice`` to the picked path or
        the string "LIVE" when the user clicks. The big graph/blackboard frames
        are hidden so the menu stands alone.
        """
        self.replay_choice = None
        self.back_to_menu = False
        self._menu_axes = []
        self._menu_buttons = []

        # Hide the normal panel widgets so the menu stands alone.
        self._hidden_for_menu = [
            self.ax_graph, self.ax_graph_pop, self.ax_graph_age, self.ax_board,
            self.btn_menu.ax, self.btn_rewind.ax, self.btn_pause.ax, self.btn_forward.ax,
            self.slider_speed.ax,
        ]
        for ax in self._hidden_for_menu:
            ax.set_visible(False)

        if save_paths:
            self.set_label("Pick a replay to watch, or start a new run")
        else:
            self.set_label("No replays yet — start a new run")

        # New live run on top.
        ax_live = self.fig.add_axes(_map_ax([0.12, 0.80, 0.76, 0.06], self._region))
        btn_live = Button(ax_live, "▶  New live run")
        btn_live.on_clicked(lambda _e: self._choose_replay("LIVE"))
        self._menu_axes.append(ax_live)
        self._menu_buttons.append(btn_live)

        if save_paths:
            # One button per saved run (newest first); cap so they fit the panel.
            y = 0.71
            for path in save_paths[:11]:
                name = os.path.basename(path)
                ax = self.fig.add_axes(_map_ax([0.12, y, 0.76, 0.045], self._region))
                btn = Button(ax, name)
                btn.on_clicked(lambda _e, p=path: self._choose_replay(p))
                self._menu_axes.append(ax)
                self._menu_buttons.append(btn)
                y -= 0.058
        else:
            # No saved runs: show a message where the list would be.
            ax_msg = self.fig.add_axes(_map_ax([0.12, 0.66, 0.76, 0.08], self._region))
            ax_msg.axis("off")
            ax_msg.text(0.5, 0.5, "(no saved runs found)", ha="center", va="center",
                        fontsize=9, color="gray", style="italic")
            self._menu_axes.append(ax_msg)

        self.fig.canvas.draw_idle()

    def _choose_replay(self, choice: str) -> None:
        self.replay_choice = choice

    def wait_for_replay_choice(self) -> Optional[str]:
        """Block until a menu button is clicked or the window is closed.
        Pumps the GUI event loop (without plt.pause — see _pump_gui) so
        clicks are processed. Returns the choice, or None if the window was
        closed."""
        while self.replay_choice is None and not self.quit:
            _pump_gui(self.fig, 0.05)
            if self.fig is not None and not plt.fignum_exists(self.fig.number):
                self.quit = True
        return None if self.quit else self.replay_choice

    def hide_replay_menu(self) -> None:
        """Remove the menu buttons and restore the normal panel widgets."""
        for ax in self._menu_axes:
            try:
                self.fig.delaxes(ax)
            except Exception:
                pass
        self._menu_axes = []
        self._menu_buttons = []
        for ax in getattr(self, "_hidden_for_menu", []):
            ax.set_visible(True)
        # The caller decides the paused state afterwards (live and replay both
        # start paused), so this only restores the widgets.
        self.fig.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Blocking Yes/No popup (e.g. "save this replay?")
    # ------------------------------------------------------------------
    def ask_yes_no(self, question: str, yes_label: str = "Yes", no_label: str = "No") -> bool:
        """
        Show a blocking Yes/No popup over the panel and return the choice.
        Returns False (== No) if the window is closed while asking.
        """
        self._popup_choice = None
        self._popup_axes = []
        self._popup_buttons = []

        ax_msg = self.fig.add_axes(_map_ax([0.06, 0.60, 0.88, 0.10], self._region))
        ax_msg.axis("off")
        ax_msg.text(0.5, 0.5, question, ha="center", va="center",
                    fontsize=10, wrap=True)
        self._popup_axes.append(ax_msg)

        ax_yes = self.fig.add_axes(_map_ax([0.12, 0.50, 0.34, 0.07], self._region))
        ax_no  = self.fig.add_axes(_map_ax([0.54, 0.50, 0.34, 0.07], self._region))
        btn_yes = Button(ax_yes, yes_label)
        btn_no  = Button(ax_no, no_label)
        btn_yes.on_clicked(lambda _e: self._set_popup_choice(True))
        btn_no.on_clicked(lambda _e: self._set_popup_choice(False))
        self._popup_axes += [ax_yes, ax_no]
        self._popup_buttons += [btn_yes, btn_no]

        self.fig.canvas.draw_idle()

        while self._popup_choice is None and not self.quit:
            _pump_gui(self.fig, 0.05)
            if self.fig is not None and not plt.fignum_exists(self.fig.number):
                self.quit = True

        for ax in self._popup_axes:
            try:
                self.fig.delaxes(ax)
            except Exception:
                pass
        self._popup_axes = []
        self._popup_buttons = []
        self.fig.canvas.draw_idle()

        return bool(self._popup_choice)

    def _set_popup_choice(self, choice: bool) -> None:
        self._popup_choice = choice

    # ------------------------------------------------------------------
    def set_label(self, text: str) -> None:
        self._label.set_text(text)
        self.fig.canvas.draw_idle()

    # ------------------------------------------------------------------
    def close(self):
        # When the figure is shared with the renderer, the renderer owns closing it.
        # Only close here when ControlPanel owns its own standalone figure.
        if self.fig is not None and not plt.fignum_exists(self.fig.number):
            return
        if self.fig is not None:
            try:
                plt.close(self.fig)
            except Exception:
                pass
            self.fig = None
