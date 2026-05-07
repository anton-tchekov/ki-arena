from sim.environment.env_grid import GridForestEnv

class Evaluator:
    def evaluate(self, env, agents):
        return {}


class BasicEvaluator(Evaluator):
    def evaluate(self, env: GridForestEnv, agents):
        return {
            "total_fruit": sum(env.world.trees.values()),
            "num_trees": len(env.world.trees)
        }