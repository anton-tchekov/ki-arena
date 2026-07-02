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

        cycles = max(1, env.cycle)  # guard against divide-by-zero on empty runs

        # Sustainable population: average head-count across all cycles, so it is
        # comparable between runs of different length (unlike peak/final counts).
        sustainable_pop = getattr(env, "stats_population_sum", 0) / cycles

        # Average age of the population, meaned over all cycles of the run.
        avg_pop_age = getattr(env, "stats_age_sum", 0) / cycles

        # Deaths split by cause.
        deaths = getattr(env, "stats_deaths_by_cause", {})
        d_age = deaths.get("old age", 0)
        d_fruit = deaths.get("starvation_fruit", 0)
        d_wood = deaths.get("starvation_wood", 0)

        # Everyone who ever existed (possible_agents keeps spawned agents even
        # after they die), split by role — the run's full demographic make-up.
        ever = list(getattr(env, "possible_agents", alive))
        ever_collectors = sum(1 for a in ever if "collector" in a)
        ever_cutters = sum(1 for a in ever if "cutter" in a)

        # Demographic metric: collector-to-cutter ratio of everyone who lived,
        # plus vital rates (births = spawns, deaths) per cycle = turnover.
        if ever_cutters > 0:
            ratio = f"{ever_collectors / ever_cutters:.2f} : 1"
        else:
            ratio = f"{ever_collectors} : 0"
        births = getattr(env, "stats_agents_spawned", 0)
        died = getattr(env, "stats_agents_died", 0)
        births_per = births / cycles
        deaths_per = died / cycles

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
            f"   Sustainable (avg/cycle)  : {f(round(sustainable_pop, 2))}",
            f"   Average age (over run)   : {f(round(avg_pop_age, 2))}",
            "",
            " Deaths by cause:",
            f"   Old age                  : {d_age}",
            f"   Starvation (no fruit)    : {d_fruit}",
            f"   Starvation (no wood)     : {d_wood}",
            "",
            " Demographics (everyone who ever lived):",
            f"   Collectors               : {ever_collectors}",
            f"   Cutters                  : {ever_cutters}",
            f"   Collector : Cutter ratio : {ratio}",
            f"   Births / Deaths per cycle: {births_per:.2f} / {deaths_per:.2f}",
            "",
            " Agent lifespans (cycles):",
            f"   Average                  : {f(avg_life)}",
            f"   Longest                  : {longest_life} ({longest_name})",
            "====================================================",
        ]
        return "\n".join(lines)
