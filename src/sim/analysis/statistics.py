class SimulationStats:
    """
    Collects and formats end-of-run statistics from the environment.

    Use SimulationStats.summary(env) to get a printable multi-line report of
    how the run went: resources gathered, how long the simulation survived,
    and how the population fared.
    """

    @staticmethod
    def _fmt(x) -> str:
        """Show floats with 2 decimals; leave ints as-is."""
        return f"{x:.2f}" if isinstance(x, float) else str(x)

    @staticmethod
    def summary(env) -> str:
        f = SimulationStats._fmt
        rm = env.resource_manager

        # Per-agent survival: dead agents were recorded at death; survivors take
        # their current age. Merge both into one {agent: cycles_lived} mapping.
        alive = list(getattr(env, "agents", []))
        lifespans = dict(getattr(env, "agent_lifespans", {}))
        ages = getattr(env.world, "agent_ages", {})
        for a in alive:
            lifespans[a] = ages.get(a, 0)

        if lifespans:
            avg_life = sum(lifespans.values()) / len(lifespans)
            longest_name, longest_life = max(lifespans.items(), key=lambda kv: kv[1])
        else:
            avg_life, longest_name, longest_life = 0, "-", 0

        collectors = [a for a in alive if "collector" in a]
        cutters = [a for a in alive if "cutter" in a]

        lines = [
            "================ Simulation Summary ================",
            f" Cycles survived            : {env.cycle}",
            "",
            " Resources gathered (total over the run):",
            f"   Wood cut                 : {f(rm.total_wood_cut)}  ({rm.trees_cut} trees cut)",
            f"   Fruit collected          : {f(rm.total_fruit_collected)}  ({rm.fruit_collect_count} collect actions)",
            "",
            " Resources remaining at end:",
            f"   Wood                     : {f(rm.wood)}",
            f"   Fruit                    : {f(rm.fruits)}",
            f"   Trees on map             : {len(env.world.trees)}",
            "",
            " Population:",
            f"   Started with             : {getattr(env, 'stats_agents_started', len(alive))}",
            f"   Spawned during run       : {getattr(env, 'stats_agents_spawned', 0)}",
            f"   Died                     : {getattr(env, 'stats_agents_died', 0)}",
            f"   Survived to end          : {len(alive)} "
            f"({len(collectors)} collectors, {len(cutters)} cutters)",
            f"   Peak population          : {getattr(env, 'stats_peak_population', len(alive))}",
            "",
            " Agent lifespans (cycles):",
            f"   Average                  : {f(avg_life)}",
            f"   Longest                  : {longest_life} ({longest_name})",
            "====================================================",
        ]
        return "\n".join(lines)
