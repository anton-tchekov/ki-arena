"""
Headless runner for Ki-Arena — run the simulation with no GUI.

This is the entry point the docs (experiment.md / demo.md / slides.md) refer to
when they say "headless". It exists so experiments are reproducible from the
command line and so the live demo has a fallback when the GUI misbehaves.

It never opens a window (matplotlib is forced to the non-interactive "Agg"
backend) and never waits for input, so it runs on a server / over SSH / in CI.

Examples
--------
  # Default: rule-based (Greedy) agents, one run, seed 1
  python run_headless.py

  # Reproduce the tree_spawn_rate sweep from docs/experiment.md
  python run_headless.py --agents greedy --seeds 1,2,3 --set tree_spawn_rate=0.9

  # Train + run RL agents
  python run_headless.py --agents rl --train-episodes 200 --seeds 1

  # LLM agents over Ollama (needs `ollama serve` running), a short run
  python run_headless.py --agents llm --llm-model qwen2.5:3b-instruct \
      --set max_cycles=40 --collectors 2 --cutters 1 --save --tag llm-demo

  # Save the replay of an interesting run to saves/ (viewable later in the GUI)
  python run_headless.py --agents greedy --seeds 2 --save --tag baseline
"""

import argparse
import os
import random
import signal

# Force a non-interactive backend BEFORE anything imports matplotlib via the
# environment package — this is what makes the run truly headless.
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib
matplotlib.use("Agg")

import numpy as np

from environment.config import EnvConfig
from environment.env_grid import GridForestEnv
from environment.state_history import StateHistory, next_save_path
from environment.termination import MaxCycleTermination
from environment.reward import (
    CompositeRewardFn, CollectorRewardFn, CutterRewardFn,
    ExplorerRewardFn, StepPenaltyFn,
)
from arena.simple_arena import Arena
from arena.phases import TrainingPhase
from arena.runner import EpisodeRunner
from analysis.statistics import SimulationStats
from agents.rule_agent import GreedyCollector, GreedyCutter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Config overrides
# ---------------------------------------------------------------------------
def _coerce(value: str):
    """Turn a CLI string into bool / int / float / str."""
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            pass
    return value


def apply_overrides(config: EnvConfig, overrides: dict) -> None:
    """Set config attributes from --set key=value pairs. Rebuilds the
    termination condition if max_cycles changed (it is baked in at init)."""
    for key, raw in overrides.items():
        if not hasattr(config, key):
            raise SystemExit(f"Unknown config key: {key!r} "
                             f"(see environment/config.py for valid names)")
        setattr(config, key, _coerce(raw))
    if "max_cycles" in overrides:
        config.termination_conditions = [MaxCycleTermination(config.max_cycles)]


# ---------------------------------------------------------------------------
# Agent construction
# ---------------------------------------------------------------------------
def build_agents(kind: str, n_collectors: int, n_cutters: int, args):
    """Create the agent dict for the requested kind: greedy / rl / llm."""
    names = ([f"collector_{i}" for i in range(n_collectors)]
             + [f"cutter_{i}" for i in range(n_cutters)])

    if kind == "greedy":
        agents = {}
        for name in names:
            agents[name] = (GreedyCutter(name) if "cutter" in name
                            else GreedyCollector(name))
        return agents

    if kind == "rl":
        from agents.rl_agent import RLAgent
        agents = {name: RLAgent(name) for name in names}
        # Never clobber the team's committed models/ during a headless run:
        # suppress the auto-save TrainingPhase does at the end of training.
        for a in agents.values():
            a.save = lambda *args, **kwargs: None
        return agents

    if kind == "llm":
        from agents.llm_agent import LLMAgent
        if args.llm_backend == "mistral":
            from llm.llmmanager_mistral import LLMManagerMistral
            llm = LLMManagerMistral(False, model=args.llm_model,
                                     reasoning_effort=args.llm_reasoning_effort)
        else:
            from llm.llmmanager import LLMManager
            llm = LLMManager(args.llm_model, use_experience=False)
        return {name: LLMAgent(name, llm, 0, guidance=not args.llm_no_guidance,
                                force_reasoning=args.llm_force_reasoning) for name in names}

    raise SystemExit(f"Unknown --agents kind: {kind!r}")


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def collect_metrics(env) -> dict:
    rm = env.resource_manager
    cycles = max(1, env.cycle)
    deaths = getattr(env, "stats_deaths_by_cause", {})
    return {
        "cycles": env.cycle,
        "peak_pop": getattr(env, "stats_peak_population", 0),
        "avg_pop": round(getattr(env, "stats_population_sum", 0) / cycles, 2),
        "spawns": getattr(env, "stats_agents_spawned", 0),
        "deaths_age": deaths.get("old age", 0),
        "deaths_wood": deaths.get("starvation_wood", 0),
        "deaths_fruit": deaths.get("starvation_fruit", 0),
        "trees_end": len(env.world.trees),
        "wood_end": round(rm.wood, 1),
        "fruit_end": round(rm.fruits, 1),
        "wood_cut": rm.total_wood_cut,
        "fruit_collected": rm.total_fruit_collected,
    }


def dominant_death_cause(m: dict) -> str:
    order = [("Alter", m["deaths_age"]), ("Holzmangel", m["deaths_wood"]),
             ("Fruchtmangel", m["deaths_fruit"])]
    order.sort(key=lambda kv: kv[1], reverse=True)
    return order[0][0] if order[0][1] > 0 else "keine Tode"


# ---------------------------------------------------------------------------
# One run
# ---------------------------------------------------------------------------
def run_once(args, seed: int) -> dict:
    random.seed(seed)
    np.random.seed(seed)

    config = EnvConfig()
    apply_overrides(config, args.set_overrides)
    # Wire the cutter conservation rule the same way main.py does.
    GreedyCutter.forest_reserve = config.cutter_forest_reserve

    # RL needs the shaped reward (cut/collect/explore) — and it must be set on the
    # config BEFORE the env is built, because GridForestEnv caches reward_fn at
    # construction. Setting it afterwards would silently train on BasicReward
    # (which gives cutters 0 for cutting → they never learn to cut).
    if args.agents == "rl":
        config.reward_fn = CompositeRewardFn(
            (1.0, CollectorRewardFn()),
            (1.0, CutterRewardFn()),
            (0.5, ExplorerRewardFn()),
            (1.0, StepPenaltyFn(-0.05)),
        )

    agents = build_agents(args.agents, args.collectors, args.cutters, args)
    env = GridForestEnv(config, agents)
    runner = EpisodeRunner(env, agents, logger=None)

    # Optional human-readable run log (also surfaces LLM blackboard plans).
    if args.log:
        from analysis.run_logger import RunLogger
        env.run_logger = RunLogger(os.path.join(BASE_DIR, args.log))
        env.run_logger.log_run_start(config, agents)

    if args.agents == "rl":
        # Reward already set on the config above (before env construction).
        arena = Arena(env=env, agents=agents)
        arena.run_phase(TrainingPhase(episodes=args.train_episodes))

    # Execution episode (no rendering). We wire a StateHistory so the run can be
    # saved as a replay if requested.
    history = StateHistory()
    saves_dir = os.path.join(BASE_DIR, "saves")
    interrupted = {"saved_path": None}

    def _save_on_interrupt(signum, frame):
        # Ctrl-C / kill mid-run (e.g. an open-ended experiment stopped by hand):
        # save whatever the history has so far instead of losing the whole run.
        if args.save and len(history) > 0 and interrupted["saved_path"] is None:
            path = next_save_path(saves_dir)
            history.save_to_file(path, config)
            interrupted["saved_path"] = path
            print(f"\nInterrupted (signal {signum}) — saved partial replay to {path} "
                  f"({len(history)} cycles)")
        raise SystemExit(1)

    prev_sigterm = signal.signal(signal.SIGTERM, _save_on_interrupt)
    prev_sigint = signal.signal(signal.SIGINT, _save_on_interrupt)
    try:
        for ep in range(args.episodes):
            env.reset()
            from agents.blackboard import shared_blackboard
            shared_blackboard.clear()
            _run_episode_headless(runner, env, history if args.save else None,
                                   progress_every=0 if args.quiet else 10)
    finally:
        signal.signal(signal.SIGTERM, prev_sigterm)
        signal.signal(signal.SIGINT, prev_sigint)

    metrics = collect_metrics(env)

    if getattr(env, "run_logger", None):
        env.run_logger.log_summary(SimulationStats.summary(env))
        env.run_logger.close()

    if args.save and len(history) > 0 and interrupted["saved_path"] is None:
        path = next_save_path(saves_dir)
        history.save_to_file(path, config)
        metrics["saved"] = path
        _write_save_note(path, args, seed, metrics)

    if not args.quiet:
        print(SimulationStats.summary(env))

    return metrics


def _run_episode_headless(runner: EpisodeRunner, env, history, progress_every: int = 0) -> None:
    """Step one episode with no renderer. Mirrors EpisodeRunner.run_episode but
    without any GUI / pause logic, and records a snapshot per cycle if a history
    is given (so --save can write a replay). If progress_every > 0, prints the
    current cycle every that many cycles (useful for slow LLM runs)."""
    from agents.blackboard import shared_blackboard
    last_rewards = {a: 0 for a in env.agents}
    max_cycles = getattr(env.config, "max_cycles", 100)
    max_steps = max_cycles * max(1, len(env.possible_agents)) * 2
    prev_cycle = env.cycle

    for agent_name in env.agent_iter(max_iter=max_steps):
        agent = runner._resolve_agent(agent_name)
        obs = env.observe(agent_name)
        info = env.infos[agent_name]
        is_done = env.terminations[agent_name] or env.truncations[agent_name]
        agent.observe(obs, last_rewards.get(agent_name, 0), is_done, info)

        if is_done:
            shared_blackboard.remove(agent_name)
            env.step(None)
            continue

        action = agent.act(obs, info)
        env.step(action)

        post_done = (env.terminations.get(agent_name, True)
                     or env.truncations.get(agent_name, True))
        next_obs = None if post_done else env.observe(agent_name)
        reward = env.rewards.get(agent_name, 0)
        last_rewards[agent_name] = reward
        if hasattr(agent, "after_action"):
            agent.after_action(obs, action, reward, next_obs, post_done, info)

        if env.cycle != prev_cycle:
            if history is not None:
                history.save(env)
            prev_cycle = env.cycle
            if progress_every and env.cycle % progress_every == 0:
                print(f"  ... cycle {env.cycle}/{max_cycles}", flush=True)

    for agent in runner.agents.values():
        agent.on_episode_end()
    for agent in runner._dynamic_agents.values():
        agent.on_episode_end()
    runner._dynamic_agents.clear()


def _write_save_note(path: str, args, seed: int, m: dict) -> None:
    """Drop a .txt next to a saved replay explaining what it is."""
    note = os.path.splitext(path)[0] + ".txt"
    overrides = ", ".join(f"{k}={v}" for k, v in args.set_overrides.items()) or "Standard-Konfig"
    with open(note, "w", encoding="utf-8") as f:
        f.write(f"Run: {os.path.basename(path)}\n")
        f.write(f"Tag: {args.tag or '-'}\n")
        f.write(f"Agenten: {args.agents} "
                f"({args.collectors} collector, {args.cutters} cutter)\n")
        f.write(f"Seed: {seed}\n")
        f.write(f"Overrides: {overrides}\n\n")
        f.write(f"Ergebnis: {m['cycles']} Zyklen, Peak-Pop {m['peak_pop']}, "
                f"Schnitt-Pop {m['avg_pop']}, Spawns {m['spawns']}.\n")
        f.write(f"Tode -> Alter {m['deaths_age']}, Holz {m['deaths_wood']}, "
                f"Frucht {m['deaths_fruit']} (dominant: {dominant_death_cause(m)}).\n")
        f.write(f"Ende: {m['trees_end']} Bäume, Holz {m['wood_end']}, "
                f"Frucht {m['fruit_end']}.\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_seeds(spec: str) -> list[int]:
    """Parse a seed spec: "1,2,3" -> [1,2,3], "1-3" -> [1,2,3], "2" -> [2]."""
    spec = spec.strip()
    if "," in spec:
        return [int(s) for s in spec.split(",") if s.strip()]
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        return list(range(int(lo), int(hi) + 1))
    return [int(spec)]


def main():
    p = argparse.ArgumentParser(description="Headless Ki-Arena runner")
    p.add_argument("--agents", choices=["greedy", "rl", "llm"], default="greedy")
    p.add_argument("--collectors", type=int, default=3)
    p.add_argument("--cutters", type=int, default=2)
    p.add_argument("--seeds", default="1",
                   help='"1,2,3" for a list, or "3" for seeds 1..3')
    p.add_argument("--episodes", type=int, default=1,
                   help="execution episodes per seed")
    p.add_argument("--train-episodes", type=int, default=100,
                   help="RL training episodes (only for --agents rl)")
    p.add_argument("--set", dest="sets", action="append", default=[],
                   metavar="key=value",
                   help="override a config value, e.g. --set tree_spawn_rate=0.9")
    p.add_argument("--save", action="store_true",
                   help="save each run as a replay in saves/ (+ a .txt note)")
    p.add_argument("--tag", default="", help="label written into the save note")
    p.add_argument("--log", default="",
                   help="write a human-readable run log to this file "
                        "(relative to src/sim); also captures LLM blackboard plans")
    p.add_argument("--llm-backend", choices=["ollama", "mistral"], default="ollama")
    p.add_argument("--llm-model", default="qwen2.5:3b-instruct")
    p.add_argument("--llm-reasoning-effort", default=None,
                   choices=[None, "none", "minimal", "low", "medium", "high", "xhigh"],
                   help="Mistral-only: reasoning_effort for models with configurable thinking")
    p.add_argument("--llm-no-guidance", action="store_true",
                   help="disable the rule-based navigation hint/claim-filtering and let "
                        "the LLM navigate and coordinate purely on its own")
    p.add_argument("--llm-force-reasoning", action="store_true",
                   help="only with --llm-no-guidance: force the model to write out its "
                        "dx/dy arithmetic as a REASONING line before answering")
    p.add_argument("--quiet", action="store_true",
                   help="don't print each run's full summary block")
    args = p.parse_args()

    args.set_overrides = {}
    for item in args.sets:
        if "=" not in item:
            raise SystemExit(f"--set expects key=value, got {item!r}")
        k, v = item.split("=", 1)
        args.set_overrides[k.strip()] = v.strip()

    seeds = parse_seeds(args.seeds)
    ov = ", ".join(f"{k}={v}" for k, v in args.set_overrides.items()) or "Standard-Konfig"
    print(f"== Ki-Arena headless == agents={args.agents}  seeds={seeds}  {ov}")

    rows = []
    for seed in seeds:
        m = run_once(args, seed)
        m["seed"] = seed
        rows.append(m)
        print(f"[seed {seed}] cycles={m['cycles']:>5}  peak={m['peak_pop']:>3}  "
              f"avg_pop={m['avg_pop']:>5}  spawns={m['spawns']:>3}  "
              f"deaths(age/wood/fruit)={m['deaths_age']}/{m['deaths_wood']}/{m['deaths_fruit']}  "
              f"trees_end={m['trees_end']:>3}  death={dominant_death_cause(m)}"
              + (f"  saved={os.path.basename(m['saved'])}" if m.get("saved") else ""))

    if len(rows) > 1:
        def mean(key):
            return sum(r[key] for r in rows) / len(rows)
        print("-" * 70)
        print(f"[mean n={len(rows)}] cycles={mean('cycles'):.0f}  "
              f"peak={mean('peak_pop'):.1f}  avg_pop={mean('avg_pop'):.1f}  "
              f"spawns={mean('spawns'):.1f}  "
              f"deaths(age/wood/fruit)={mean('deaths_age'):.1f}/"
              f"{mean('deaths_wood'):.1f}/{mean('deaths_fruit'):.1f}  "
              f"trees_end={mean('trees_end'):.1f}")


if __name__ == "__main__":
    main()
