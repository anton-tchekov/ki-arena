import os

from agents.llm_agent import LLMAgent
from arena.simple_arena import Arena
from arena.phases import TrainingPhase, ExecutionPhase
from environment.config import EnvConfig
from environment.env_grid import GridForestEnv
from environment.renderer import BackToMenu
from environment.state_history import StateHistory, list_saves, next_save_path
from analysis.evaluator import BasicEvaluator
from analysis.logger import PrintLogger
from analysis.run_logger import RunLogger
from analysis.statistics import SimulationStats
from agents.rl_agent import RLAgent
from agents.rule_agent import GreedyCollector, GreedyCutter
from environment.reward import AliveBonusReward, CompositeRewardFn, CollectorRewardFn, CutterRewardFn, StepPenaltyFn, ExplorerRewardFn  
from llm.llmmanager import LLMManager
from llm.llmmanager_mistral import LLMManagerMistral


def _build_session(renderer=None):
    """
    Build a fresh config + agents + env, ready for a new session. Reuses an
    existing renderer/window when given, instead of opening a second one — used
    to get a full "as if just started" reset without losing the GUI window.
    """
    # Initialize LLM manager (commented out to avoid API calls during testing)/
    llm: LLMManagerMistral = LLMManagerMistral(False)
    llm.set_sys_prompt("Please justify your action choice in one sentence after the action")

    config = EnvConfig()
    # Apply the cutter conservation rule from config (0 = off / greedy).
    GreedyCutter.forest_reserve = config.cutter_forest_reserve
    agents = {
        # --- Default demo: rule-based (Greedy) agents. Need no API/Ollama and
        #     are deterministic with a fixed seed. Matches README + docs/demo.md. ---
        #"collector_0": GreedyCollector("collector_0"),
        #"collector_1": GreedyCollector("collector_1"),
        #"collector_2": GreedyCollector("collector_2"),
        #"cutter_0": GreedyCutter("cutter_0"),
        #"cutter_1": GreedyCutter("cutter_1"),

        # --- Alternative: RL agents (tabular Q-learning). Uncomment these and the
        #     training phase below turns on automatically. ---
        "collector_0": RLAgent("collector_0", debug=False),
        #"collector_1": RLAgent("collector_1", debug=False),
        #"collector_2": RLAgent("collector_2", debug=False),
        #"collector_3": RLAgent("collector_3", debug=False),
        "cutter_0": RLAgent("cutter_0", debug=False),
        #"cutter_1": RLAgent("cutter_1", debug=False),
        #"cutter_2": RLAgent("cutter_2", debug=False),
        #"cutter_3": RLAgent("cutter_3", debug=False),

        # --- Alternative: LLM agents (need Ollama running or MISTRAL_API_KEY). ---
        #"collector_0": LLMAgent("collector_0", llm, 0),
        #"cutter_0": LLMAgent("cutter_0", llm, 0),
        #"collector_1": LLMAgent("collector_1", llm, 0),
        #"cutter_1": LLMAgent("cutter_1", llm, 0),
        #"collector_2": LLMAgent("collector_2", llm, 0),
        #"cutter_2": LLMAgent("cutter_2", llm, 0),
    }
    env = GridForestEnv(config, agents, renderer=renderer)
    return config, agents, env


def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    saves_dir = os.path.join(base_dir, "saves")

    config, agents, env = _build_session()

    # Outer loop: back to this menu after a replay ends, a live run ends, or
    # the user clicks the control panel's Menu button. Every time we land back
    # here, config/agents/env are rebuilt from scratch (same GUI window) so the
    # menu always represents a true "just started the program" state. Only a
    # closed window (choice is None) leaves the loop.
    while True:
        cp = env.renderer.control_panel
        env.renderer.clear_grid()  # blank grid pane, not the last run's frame
        cp.show_replay_menu(list_saves(saves_dir))
        choice = cp.wait_for_replay_choice()
        cp.hide_replay_menu()

        if choice is None:
            # Window closed while in the menu.
            env.renderer.close()
            return

        if choice != "LIVE":
            # Replay mode: load the saved run and play it back, no simulation.
            history = StateHistory.load_from_file(choice)
            try:
                env.renderer.play_replay(history, env.world)
            except BackToMenu:
                pass
            # Full reset before the menu reappears, same window.
            config, agents, env = _build_session(renderer=env.renderer)
            continue

        # Live run starts paused: use the control panel to play (Resume) or to
        # step one cycle at a time (Next while paused).
        cp.paused = True
        cp.btn_pause.label.set_text("Resume")

        # Per-run log file: overwritten each run, so it only holds the last run.
        # Lives next to main.py regardless of the working directory.
        run_logger = RunLogger(os.path.join(base_dir, "logfile.txt"))
        env.run_logger = run_logger
        run_logger.log_run_start(config, agents)

        arena = Arena(
            env=env,
            agents=agents,
            logger=PrintLogger(),
            evaluator=BasicEvaluator(),
            saves_dir=saves_dir
        )

        # ToDo: Separate training cycle
        # load pre-trained agents if available (e.g. from previous training runs)
        load_rl_agents = False
        if(load_rl_agents):
            for agent in agents.values():
                if hasattr(agent, "load"):
                    agent.load()

        # Train only when RL agents are present; rule/LLM agents need no training.
        learning = any(isinstance(a, RLAgent) for a in agents.values())
        learning = learning and cp.ask_yes_no("Run a training phase before execution?", "Train", "Skip")
        if learning:
            # RL reward shaping — only meaningful while training the Q-tables.
            config.reward_fn = CompositeRewardFn(
                (1.0, CollectorRewardFn()),   # +5 on collect
                (1.0, CutterRewardFn()),      # +5 on cut, +0.3 near trees
                (1.0, ExplorerRewardFn()),    # +0.5 for new cells, -0.05 revisit
                (1.0, StepPenaltyFn(-0.5)),  # -0.5 every movement step to encourage shorter paths
                (1.0, AliveBonusReward(0.5)), # +0.5 every episode step
            )
            # The env caches reward_fn at construction, so update it too — otherwise
            # training would silently run on the default BasicReward.
            env.reward_fn = config.reward_fn

            try:
                arena.run_phase(TrainingPhase(episodes=5000))
            except BackToMenu:
                # Full reset before the menu reappears, same window.
                config, agents, env = _build_session(renderer=env.renderer)
                continue
            print("Training finished. Running learned execution phase...")

        # Run a single execution episode. Print the end-of-run statistics even if
        # the window is closed mid-run (closing a window raises SystemExit, which
        # still runs this finally block) or the user clicks Menu (BackToMenu).
        try:
            arena.run_phase(ExecutionPhase())
        except BackToMenu:
            pass
        finally:
            summary = SimulationStats.summary(env)
            print("\nEpisode complete!")
            print(summary)
            run_logger.log_summary(summary)
            run_logger.close()

        # Ask before saving (runs even if the run was cut short via Menu). Not
        # asked if the window itself was closed — SystemExit skips past here.
        hist = getattr(env.renderer, "state_history", None)
        if hist is not None and len(hist) > 0:
            cycles = hist.cycle_at(hist.latest_index)
            if cp.ask_yes_no(f"Save this run as a replay? ({cycles} cycles)", "Save", "Discard"):
                try:
                    path = next_save_path(saves_dir)
                    hist.save_to_file(path, config)
                    print(f"Saved replay to {path}")
                except Exception as e:
                    print(f"Could not save replay: {e}")
            else:
                print("Replay discarded.")

        # Full reset before the menu reappears, same window — whether the run
        # ended naturally or via the Menu button.
        config, agents, env = _build_session(renderer=env.renderer)

if __name__ == "__main__":
    main()
