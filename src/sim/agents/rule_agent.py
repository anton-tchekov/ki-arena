from agents.base import BaseAgent
from environment.actions import Action
import random

# A collector ignores trees with fewer fruit than this and seeks a richer one.
MIN_FRUIT_TO_COLLECT = 10


def _adjacent_tree(pos, trees):
    """The tree this position is right next to (Manhattan distance 1), or None.
    An agent adjacent to a tree is 'committed' to it (it will interact next)."""
    px, py = pos
    for t in trees:
        if abs(t[0] - px) + abs(t[1] - py) == 1:
            return t
    return None


def _pick_uncontested_tree(name, x, y, trees, others):
    """
    Walk the trees from nearest to farthest and return the first one for which
    no other agent is closer (so agents spread out instead of all squatting the
    same tree). Returns the tree (tx, ty), or None if every tree has a closer
    competitor — in which case the caller should wander.

    `others` is a list of (other_name, (ox, oy)). An agent already adjacent to a
    tree is committed to THAT tree and is ignored when judging any other tree, so
    a free tree never looks "taken" just because a busy agent happens to be near
    it. Ties are broken by name so two equally-close agents never both claim one.
    """
    tree_list = list(trees.keys())
    # The tree each other agent is committed to (adjacent to), or None if free.
    committed = {oname: _adjacent_tree(pos, tree_list) for oname, pos in others}

    def my_dist(t):
        return abs(t[0] - x) + abs(t[1] - y)

    for t in sorted(tree_list, key=my_dist):
        d = my_dist(t)
        contested = False
        for oname, (ox, oy) in others:
            # Committed to a different tree -> won't pursue this one.
            if committed[oname] is not None and committed[oname] != t:
                continue
            od = abs(ox - t[0]) + abs(oy - t[1])
            if od < d or (od == d and oname < name):
                contested = True
                break
        if not contested:
            return t
    return None


def _step_toward(x, y, tx, ty) -> Action:
    """Move one step toward (tx, ty), or INTERACT if already adjacent."""
    dx = tx - x
    dy = ty - y

    if abs(dx) + abs(dy) == 1:
        return Action.INTERACT

    # x via UP/DOWN, y via LEFT/RIGHT
    if abs(dx) > abs(dy):
        return Action.UP if dx < 0 else Action.DOWN
    else:
        return Action.LEFT if dy < 0 else Action.RIGHT


class GreedyCollector(BaseAgent):
    """
    A simple collector agent that moves toward the nearest tree that no other
    agent is closer to. When adjacent to a tree, it INTERACTs to collect fruits.
    """
    def act(self, obs, info) -> Action:
        x = obs['x']
        y = obs['y']
        trees = obs['trees']

        # Only consider trees that still have enough fruit to be worth it; if a
        # tree drops below the threshold, head to a richer one instead.
        ripe_trees = {t: f for t, f in trees.items() if f >= MIN_FRUIT_TO_COLLECT}
        if not ripe_trees:
            return random.choice(list(Action))  # nothing worth collecting -> wander

        others = [(n, p) for n, p in obs.get('agents', {}).items() if n != self.name]
        target = _pick_uncontested_tree(self.name, x, y, ripe_trees, others)
        if target is None:
            return random.choice(list(Action))  # every ripe tree contested -> wander

        return _step_toward(x, y, target[0], target[1])


class GreedyCutter(BaseAgent):
    """
    A simple cutter agent that moves toward the nearest tree that no other agent
    is closer to. When adjacent to a tree, it INTERACTs to cut it down.
    """
    def act(self, obs, info) -> Action:
        x = obs['x']
        y = obs['y']
        trees = obs['trees']

        if not trees:
            return random.choice(list(Action))

        others = [(n, p) for n, p in obs.get('agents', {}).items() if n != self.name]
        target = _pick_uncontested_tree(self.name, x, y, trees, others)
        if target is None:
            return random.choice(list(Action))  # every tree contested -> wander

        return _step_toward(x, y, target[0], target[1])
