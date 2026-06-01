from arena.simple_arena import Arena
from arena.phases import ExecutionPhase
from environment.config import EnvConfig
from environment.env_grid import GridForestEnv
from analysis.evaluator import BasicEvaluator
from analysis.logger import PrintLogger
from agents.rule_agent import GreedyCollector, GreedyCutter
from agents.llm_agent import LLMAgent
from llm.llmmanager_mistral import LLMManagerMistral


def main() -> None:
    config = EnvConfig()
    env = GridForestEnv(config)

    # Initialize LLM manager (commented out to avoid API calls during testing)
    # llm: LLMManagerMistral = LLMManagerMistral("llama3:8b", True)
    # llm.set_sys_prompt("Your goal is to move around")

    agents = {
        "collector_0": GreedyCollector("collector_0"),
        "cutter_0": GreedyCutter("cutter_0"),
        #"cutter_1": LLMAgent("cutter_1", llm, 0),
    }

    arena = Arena(
        env=env,
        agents=agents,
        logger=PrintLogger(),
        evaluator=BasicEvaluator()
    )

    results = arena.run_phase(ExecutionPhase())
    print("\nEpisode complete!")
    print(f"Final wood: {env.resource_manager.wood}, Final fruits: {env.resource_manager.fruits}")
    print(f"Final trees: {len(env.world.trees)}")
    print(f"Final agents: {env.agents}")
    print(results)

if __name__ == "__main__":
    main()
