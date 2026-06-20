import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider

from agents.msg import Message


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

    def __init__(self):
        self.paused = False
        self.view_index = 0
        self.view_changed = False
        self.needs_restore = False
        self.quit = False
        self.tick_delay = 0.05  # seconds the renderer waits between steps

        self.fig = plt.figure("Ki-Arena Control Panel", figsize=(5, 5.5))
        # close_event is a fallback; the WM protocol below is what makes
        # closing detectable *synchronously* while the sim loop is paused.
        self.fig.canvas.mpl_connect("close_event", self._on_close)
        _bind_window_close(self.fig, self._on_close)

        ax_rw = self.fig.add_axes([0.03, 0.90, 0.18, 0.06])
        ax_pp = self.fig.add_axes([0.26, 0.90, 0.48, 0.06])
        ax_fw = self.fig.add_axes([0.79, 0.90, 0.18, 0.06])

        self.btn_rewind  = Button(ax_rw, "< Prev")
        self.btn_pause   = Button(ax_pp, "Pause")
        self.btn_forward = Button(ax_fw, "Next >")

        self.btn_rewind.on_clicked(self._on_rewind)
        self.btn_pause.on_clicked(self._toggle_pause)
        self.btn_forward.on_clicked(self._on_forward)

        self._label = self.fig.text(
            0.5, 0.985, "",
            ha="center", va="top",
            fontsize=9
        )

        # Tick-speed slider. The handle position (0..1) is mapped cubically to
        # the delay, so most of the travel gives fine control in the small-delay
        # range between 0 and the default, while the top still reaches 1.0 s.
        ax_speed = self.fig.add_axes([0.30, 0.855, 0.45, 0.02])
        self.slider_speed = Slider(
            ax_speed, "Delay (s)", 0.0, 1.0,
            valinit=self.tick_delay ** (1 / 3), valstep=0.001
        )
        self.slider_speed.valtext.set_text(f"{self.tick_delay:.3f}")
        self.slider_speed.on_changed(self._on_speed_change)

        # Live graph of resources / population over cycles
        self.ax_graph = self.fig.add_axes([0.12, 0.45, 0.82, 0.37])

        # Blackboard readout: each agent's current announcement, one per line
        self.ax_board = self.fig.add_axes([0.06, 0.04, 0.90, 0.34])
        self.update_blackboard({})

    def _on_close(self, event=None):
        self.quit = True

    def _on_speed_change(self, pos):
        self.tick_delay = float(pos) ** 3
        self.slider_speed.valtext.set_text(f"{self.tick_delay:.3f}")

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
        self.view_index += 1  # clamped to latest_index by renderer
        self.view_changed = True

    # ------------------------------------------------------------------
    def update_graph(self, history, current_index=None) -> None:
        """
        Redraw the wood / fruit / population graph from the rewind snapshots.
        If current_index is given (while paused/browsing), mark that cycle.
        """
        if history is None or len(history) == 0:
            return

        cycles, wood, fruits, population = history.series()

        ax = self.ax_graph
        ax.clear()
        ax.plot(cycles, wood, color="#8d6e63", label="Wood")
        ax.plot(cycles, fruits, color="#fdd835", label="Fruit")
        ax.plot(cycles, population, color="#42a5f5", label="Population")

        if current_index is not None and 0 <= current_index < len(cycles):
            ax.axvline(cycles[current_index], color="#888888",
                       linestyle="--", linewidth=1)

        ax.set_xlabel("Cycle", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.legend(loc="upper left", fontsize=7)

        self.fig.canvas.draw_idle()
        try:
            self.fig.canvas.flush_events()
        except Exception:
            pass

    # ------------------------------------------------------------------
    def update_blackboard(self, notes: dict[str, Message]) -> None:
        """
        Show the current blackboard: one "agent: message" line per agent.
        `notes` is the {agent_name: Message} dict from the shared Blackboard;
        each Message renders itself via str(). Drawn with draw_idle only — the
        flush from update_graph renders it.
        """
        ax = self.ax_board
        ax.clear()
        ax.axis("off")

        ax.text(0.0, 1.0, "Blackboard", transform=ax.transAxes,
                va="top", ha="left", fontsize=9, fontweight="bold")

        if notes:
            y = 0.82
            for name, message in notes.items():
                ax.text(0.0, y, f"{name}: {message}", transform=ax.transAxes,
                        va="top", ha="left", fontsize=8, family="monospace")
                y -= 0.13
        else:
            ax.text(0.0, 0.82, "(no announcements)", transform=ax.transAxes,
                    va="top", ha="left", fontsize=8, color="gray", style="italic")

        self.fig.canvas.draw_idle()

    # ------------------------------------------------------------------
    def set_label(self, text: str) -> None:
        self._label.set_text(text)
        self.fig.canvas.draw_idle()

    # ------------------------------------------------------------------
    def close(self):
        if self.fig is not None:
            plt.close(self.fig)
            self.fig = None
