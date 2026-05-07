from sim.arena.simple_arena import Arena
from sim.arena.phases import ExecutionPhase
from sim.environment.config import EnvConfig
from sim.environment.env_grid import GridForestEnv
from sim.analysis.evaluator import BasicEvaluator
from sim.analysis.logger import PrintLogger
from sim.agents.rule_agent import GreedyCollector



def main() -> None:
    config = EnvConfig()
    env = GridForestEnv(config)

    agents = {
        "collector_0": GreedyCollector("collector_0"),
        "cutter_0": GreedyCollector("cutter_0"),
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
