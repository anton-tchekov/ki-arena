import os

from agents.llm_agent import LLMAgent
from arena.simple_arena import Arena
from arena.phases import TrainingPhase, ExecutionPhase
from environment.config import EnvConfig
from environment.env_grid import GridForestEnv
from environment.state_history import StateHistory, list_saves, next_save_path
from analysis.evaluator import BasicEvaluator
from analysis.logger import PrintLogger
from analysis.run_logger import RunLogger
from analysis.statistics import SimulationStats
from agents.rl_agent import RLAgent
from agents.rule_agent import GreedyCollector, GreedyCutter
from environment.reward import CollectorRewardFn, CutterRewardFn
from llm.llmmanager import LLMManager
from llm.llmmanager_mistral import LLMManagerMistral


def main() -> None:

    # Initialize LLM manager (commented out to avoid API calls during testing)
    llm: LLMManagerMistral = LLMManagerMistral(False)
    llm.set_sys_prompt("Please justify your action choice in one sentence after the action")

    config = EnvConfig()
    # Apply the cutter conservation rule from config (0 = off / greedy).
    GreedyCutter.forest_reserve = config.cutter_forest_reserve
    agents = {
        #"collector_0": LLMAgent("collector_0", llm, 0),
        #"collector_1": LLMAgent("collector_1", llm, 0),

        "collector_0": GreedyCollector("collector_0"),
        "collector_1": GreedyCollector("collector_1"),
        "collector_2": GreedyCollector("collector_2"),
        "cutter_0": GreedyCutter("cutter_0"),
        "cutter_1": GreedyCutter("cutter_1"),

        #"cutter_1": LLMAgent("cutter_1", llm, 0),
        #"collector_0": RLAgent("collector_0"),
        #"cutter_0": RLAgent("cutter_0"),
    }
    env = GridForestEnv(config, agents)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    saves_dir = os.path.join(base_dir, "saves")

    # Startup: always show the (paused) menu so the user can pick a replay or
    # start a new run. The replay list shows a message when there are no saves yet.
    cp = env.renderer.control_panel
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
        env.renderer.play_replay(history, env.world)
        return

    # Live run starts paused: use the control panel to play (Resume) or to step
    # one cycle at a time (Next while paused).
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
        evaluator=BasicEvaluator()
    )

    # ToDo: Separate training cycle
    # load pre-trained agents if available (e.g. from previous training runs)
    load_rl_agents = False
    if(load_rl_agents):
        for agent in agents.values():
            if hasattr(agent, "load"):
                agent.load()

    learning = False  # set to False to skip training and run execution directly
    if learning:
        # ToDo: Separate training cycle
        # swap config to use CutterRewardFn for training the RL agent
        config.reward_fn = CutterRewardFn()

        # ToDo: Separate training cycle
        arena.run_phase(TrainingPhase(episodes=300))
        print("Training finished. Running learned execution phase...")

    # Print the end-of-run statistics even if the window is closed mid-run
    # (closing a window raises SystemExit, which still runs this finally block).
    try:
        arena.run_phase(ExecutionPhase())
    finally:
        summary = SimulationStats.summary(env)
        print("\nEpisode complete!")
        print(summary)
        run_logger.log_summary(summary)
        run_logger.close()
        # Save this run as a replay (runs even if the window was closed mid-run).
        hist = getattr(env.renderer, "state_history", None)
        if hist is not None and len(hist) > 0:
            try:
                path = next_save_path(saves_dir)
                hist.save_to_file(path, config)
                print(f"Saved replay to {path}")
            except Exception as e:
                print(f"Could not save replay: {e}")

if __name__ == "__main__":
    main()
