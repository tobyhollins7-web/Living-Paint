# brushes.py
# Defines how the user can add material to the world
from math import cos, sin, pi, sqrt

from particles import Particle, create_particle
from vector2 import Vector2
from species import Species
from random import randrange, uniform

def create_brush_particle(brush_radius: float, species: Species, cursor_position: Vector2, width: int,
                          height: int) -> Particle:

    # Work out a random angle and distance
    angle = uniform(0, 2 * pi)
    distance = brush_radius * sqrt(uniform(0.0, 1.0))

    # Work out the position of this randomly placed particle in pixel coordinates
    position = Vector2(
        cursor_position.x + distance * cos(angle),
        cursor_position.y + distance * sin(angle)
    )

    # Clamp the position of the newly generated particle to be within the extents of the window
    position.x = max(species.radius, min(position.x, width - species.radius))
    position.y = max(species.radius, min(position.y, height - species.radius))

    return create_particle(
        position=position,
        species=species,
        velocity=Vector2(
            uniform(-50.0, 50.0),
            uniform(-50.0, 50.0)
        ),
    )
