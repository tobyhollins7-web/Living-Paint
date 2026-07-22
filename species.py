# species.py
# defines what each type of paint is
from dataclasses import dataclass

@dataclass(frozen=True)
class FeedingRule:
    rate: float
    efficiency: float

@dataclass(frozen=True)
class ReproductionRule:
    reproduction_threshold: float  # How much energy required before reproduction
    reproduction_cost: float  # How much energy reproduction costs
    offspring_energy: float  # How much energy offspring has
    reproduction_cooldown: float  # How long it takes before reproducing again

@dataclass(frozen=True)
class PaintTrail:
    width: int

@dataclass(frozen=True)
class Species:
    id: int
    name: str
    colour: tuple[int, int, int]
    radius: float

    starting_energy: float  # Initial amount of energy
    maximum_energy: float  # Maximum amount of energy
    metabolism: float  # Amount of energy consumed per second
    energy_generation: float  # Amount of energy generated per second

    reproduction_rule: ReproductionRule

    paint_trail: PaintTrail

    interaction_strengths: dict[int, float]  # int: id of species interacts with, float: the strength of said interaction
    feeding_rules: dict[int, FeedingRule]
