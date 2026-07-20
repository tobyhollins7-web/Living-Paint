# species.py
# defines what each type of paint is
from dataclasses import dataclass

@dataclass(frozen=True)
class Species:
    name: str
    colour: tuple[int, int, int]
    radius: float
