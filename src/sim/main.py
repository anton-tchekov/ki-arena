from arena.simple_arena import Arena
from arena.phases import ExecutionPhase
from environment.config import EnvConfig
from environment.env_grid import GridForestEnv
from analysis.evaluator import BasicEvaluator
from analysis.logger import PrintLogger
from agents.rule_agent import GreedyCollector
from agents.llm_agent import LLMAgent
from llm.llmmanager import LLMManager



def main() -> None:
    config = EnvConfig()
    env = GridForestEnv(config)

    llm: LLMManager = LLMManager("ministral-3:3b", False)
    llm.set_sys_prompt("Your goal is to move around")

    agents = {
        "collector_0": GreedyCollector("collector_0"),
        "cutter_0": GreedyCollector("cutter_0"),
        "cutter_1": LLMAgent("cutter_1", llm, 0),
    }

    arena = Arena(
        env=env,
        agents=agents,
        logger=PrintLogger(),
        evaluator=BasicEvaluator()
    )

    results = arena.run_phase(ExecutionPhase())
    print(results)

if __name__ == "__main__":
    main()
