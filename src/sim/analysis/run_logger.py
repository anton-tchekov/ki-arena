from datetime import datetime

# The blackboard holds the natural-language plans LLM agents announce. Import is
# best-effort so logging never depends on the (optional) LLM stack being present.
try:
    from agents.blackboard import shared_blackboard
except Exception:  # pragma: no cover
    shared_blackboard = None


def _fmt(x) -> str:
    """Floats with 2 decimals, everything else untouched."""
    return f"{x:.2f}" if isinstance(x, float) else str(x)


class RunLogger:
    """
    Writes a concise, human-readable log of ONE simulation run to a file.

    The file is opened in overwrite mode, so it always reflects only the most
    recent run. The goal is observability without clutter: instead of one line
    per agent per step (thousands of near-identical lines for greedy agents),
    it records the things that actually explain how a run went —

      - the full configuration the run started with (so the event lines below
        can stay terse: spawn cost, thresholds, yields etc. are all stated
        once here and never repeated per-event),
      - the agents it started with,
      - terse population events (an agent spawning or dying) — just who, why,
        and the new population; no resource figures glued on,
      - resource amounts on their OWN periodic "state" line, never appended
        behind an event,
      - any plans LLM agents announce (shown under the state line; empty for
        rule agents, so this costs nothing when unused),
      - the end-of-run summary.

    Attach an instance to the environment as ``env.run_logger`` and the env
    reports its own events; everything is guarded so logging is entirely
    optional.
    """

    def __init__(self, path: str, digest_every: int = 20):
        self.path = path
        self.digest_every = max(1, digest_every)
        self._f = open(path, "w", encoding="utf-8")
        self._closed = False

    def _write(self, line: str = "") -> None:
        if self._closed:
            return
        self._f.write(line + "\n")
        self._f.flush()  # flush so the file is readable mid-run / after a crash

    # ------------------------------------------------------------------
    # Run header
    # ------------------------------------------------------------------
    def log_run_start(self, config, agents: dict) -> None:
        c = config
        self._write("================ KI-Arena Run Log ================")
        self._write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._write("")
        self._write("--- Configuration (all event lines below can be read against this) ---")
        self._write(f"Grid            : {c.size}x{c.size}  (max cycles {c.max_cycles})")
        self._write(f"Start resources : wood={_fmt(c.starting_wood)}, fruit={_fmt(c.starting_fruit)}")
        self._write(
            f"Trees           : start {c.n_trees}, max {c.max_trees}; "
            f"new-tree spawn p={c.tree_spawn_rate}; fruit-grow p={c.fruit_spawn_rate} (+{c.fruit_growth_amount}/grow)"
        )
        self._write(
            f"Harvest         : cutter +{c.wood_per_tree} wood per tree; collector +1 fruit per pick"
        )
        if c.use_per_agent_consumption:
            mode, wood_amt, fruit_amt = "per agent / cycle", c.wood_consumption_per_agent, c.fruit_consumption_per_agent
        else:
            mode, wood_amt, fruit_amt = "global / cycle", c.wood_consumption_rate, c.fruit_consumption_rate
        wood_c = f"wood={wood_amt}" if c.enable_wood_consumption else "wood=off"
        fruit_c = f"fruit={fruit_amt}" if c.enable_fruit_consumption else "fruit=off"
        self._write(f"Consumption     : {mode}  {wood_c}, {fruit_c}")
        self._write(
            f"Spawning        : new agent when wood AND fruit >= {c.spawn_threshold}; "
            f"costs wood={c.spawn_wood_cost}, fruit={c.spawn_fruit_cost}; type={c.spawn_type}"
        )
        reasons = []
        if c.enable_aging:
            reasons.append(f"old age at {c.max_age} cycles")
        if c.enable_resource_starvation:
            reasons.append(f"starvation when fruit<{c.collector_min_fruits} or wood<{c.cutter_min_wood}")
        self._write(f"Death           : {'; '.join(reasons) if reasons else 'disabled'}")
        self._write(f"Reward          : {type(c.reward_fn).__name__}")
        self._write(f"Observation     : {type(c.observation_builder).__name__}")
        term_names = ", ".join(type(t).__name__ for t in c.termination_conditions) or "none"
        self._write(f"Termination     : {term_names}")
        self._write(f"Digest          : state line every {self.digest_every} cycles")
        self._write("")
        self._write("--- Agents at start ---")
        for name, agent in agents.items():
            self._write(f"  {name}  ({type(agent).__name__})")
        self._write("")
        self._write("--- Run (SPAWN/DEATH events; 'state' lines carry the resource amounts) ---")

    # ------------------------------------------------------------------
    # Population events (the env's decisions)
    # ------------------------------------------------------------------
    def log_spawn(self, cycle, name, pop_before, pop_after) -> None:
        # Why (threshold) and cost are fixed by config; only who + new pop here.
        self._write(f"[cycle {cycle:>5}] SPAWN  {name:<13} population {pop_before} -> {pop_after}")

    def log_death(self, cycle, name, reason, age, pop_before, pop_after) -> None:
        # Thresholds behind the reason live in the config header, not here.
        self._write(
            f"[cycle {cycle:>5}] DEATH  {name:<13} {reason}, lived {age} cycles"
            f"   (population {pop_before} -> {pop_after})"
        )

    # ------------------------------------------------------------------
    # Periodic state line — the ONE place resource amounts are reported
    # ------------------------------------------------------------------
    def log_cycle(self, env) -> None:
        cycle = env.cycle
        # Always log the very first cycle, then one line every `digest_every`.
        if cycle != 1 and cycle % self.digest_every != 0:
            return
        rm = env.resource_manager
        self._write(
            f"[cycle {cycle:>5}] state  wood={_fmt(rm.wood)}  fruit={_fmt(rm.fruits)}  "
            f"trees={len(env.world.trees)}  population={len(env.agents)}"
        )
        # Surface LLM plans if any are posted (rule agents post nothing).
        if shared_blackboard is not None:
            for who, plan in shared_blackboard.read().items():
                self._write(f"              · {who}: {plan}")

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    def log_summary(self, summary_text: str) -> None:
        self._write("")
        self._write(summary_text)

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._f.close()
        finally:
            self._closed = True
