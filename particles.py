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
    reproduction_cooldown_remaining: float = 0.0

def create_particle(position: Vector2, species: Species, velocity: Vector2, energy: float | None = None,
                    reproduction_cooldown_remaining: float = 0.0) -> Particle:
    if velocity is None:
        velocity = Vector2(0.0, 0.0)

    if energy is None:
        energy = species.starting_energy

    return Particle(
        position=position,
        velocity=velocity,
        acceleration=Vector2(0.0, 0.0),
        species=species,
        energy=energy,
        reproduction_cooldown_remaining=reproduction_cooldown_remaining
    )