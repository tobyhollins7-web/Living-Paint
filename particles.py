# particles.py
# Defines the state of an individual particle
from dataclasses import dataclass
from vector2 import Vector2
from species import Species

@dataclass
class Particle:
    position: Vector2
    velocity: Vector2
    acceleration: Vector2
    species: Species
    energy: float
