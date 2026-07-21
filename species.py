# species.py
# defines what each type of paint is
from dataclasses import dataclass

@dataclass(frozen=True)
class FeedingRule:
    rate: float
    efficiency: float

@dataclass(frozen=True)
class Species:
    id: int
    name: str
    colour: tuple[int, int, int]
    radius: float
    starting_energy: float
    metabolism: float

    interaction_strengths: dict[int, float]  # int: id of species interacts with, float: the strength of said interaction
    feeding_rules: dict[int, FeedingRule]
