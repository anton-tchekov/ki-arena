from agents.llm_agent import LLMAgent
from arena.simple_arena import Arena
from arena.phases import TrainingPhase, ExecutionPhase
from environment.config import EnvConfig
from environment.env_grid import GridForestEnv
from analysis.evaluator import BasicEvaluator
from analysis.logger import PrintLogger
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
    agents = {
        "collector_0": LLMAgent("collector_0", llm, 0),
        "collector_1": LLMAgent("collector_1", llm, 0),
        #"collector_2": GreedyCollector("collector_2"),
        #"cutter_0": GreedyCutter("cutter_0"),
        #"cutter_1": LLMAgent("cutter_1", llm, 0),
        #"collector_0": RLAgent("collector_0"),
        #"cutter_0": RLAgent("cutter_0"),
    }
    env = GridForestEnv(config, agents)

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
        print("\nEpisode complete!")
        print(SimulationStats.summary(env))

if __name__ == "__main__":
    main()
