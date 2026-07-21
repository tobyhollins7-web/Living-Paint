# brushes.py
# Defines how the user can add material to the world
from particles import Particle
from vector2 import Vector2
from species import Species
from random import randrange, uniform

def create_particle(brush_radius: int, species: Species, position: Vector2, width: int, height: int) -> Particle:
    found_point = False
    x_try, y_try = position.x, position.y

    # Spawn a particle in a random position within the brush_radius
    while not found_point:
        x_try = uniform(position.x - brush_radius, position.x + brush_radius)
        y_try = uniform(position.y - brush_radius, position.y + brush_radius)
        if (x_try - position.x) ** 2 + (y_try - position.y) ** 2 <= brush_radius ** 2:
            found_point = True

    # Clamps the positions to ensure spawns within the box
    x_position = max(species.radius, min(x_try, width - species.radius))
    y_position = max(species.radius, min(y_try, height - species.radius))

    return Particle(
        position=Vector2(x_position, y_position),
        velocity=Vector2(randrange(-500, 500), randrange(-500, 500)),
        acceleration=Vector2(0.0, 0.0),
        species=species,
        energy=species.starting_energy,
    )
