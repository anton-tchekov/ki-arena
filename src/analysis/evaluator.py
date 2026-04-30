class Evaluator:
    def evaluate(self, env, agents):
        return {}


class BasicEvaluator(Evaluator):
    def evaluate(self, env, agents):
        return {
            "total_fruit": sum(env.world.trees.values()),
            "num_trees": len(env.world.trees)
        }