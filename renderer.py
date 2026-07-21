# renderer.py
import pygame
from particles import Particle
from vector2 import Vector2
from spatial_grid import SpatialGrid

def render_radius_indicator(screen: pygame.Surface, position: Vector2, radius: float, colour: tuple[int, int, int],
                            line_width: int) -> None:
    position_screen = (round(position.x), round(position.y))
    pygame.draw.circle(screen, colour, position_screen, round(radius), width=line_width)

def _colour_energy_particle(particle: Particle, background_colour: tuple[int, int, int]) -> tuple[int, int, int]:
    t = max(0.0, min(particle.energy / particle.species.starting_energy, 1.0))
    particle_colour: list[int] = [0, 0, 0]
    # Iterate through the individual primary colours of the particle RGB Tuple (R, G, B)
    for i, colour in enumerate(particle.species.colour):
        particle_colour[i] = int((colour - background_colour[i]) * t + background_colour[i])

    return particle_colour[0], particle_colour[1], particle_colour[2]

def _render_particle(screen: pygame.Surface, particle: Particle, background_colour: tuple[int, int, int]) -> None:
    position = (round(particle.position.x), round(particle.position.y))
    pygame.draw.circle(
        screen,
        _colour_energy_particle(particle, background_colour),  # Blend the colour based on energy level
        position,
        round(particle.species.radius),
    )

def render_particles(screen: pygame.Surface, particles: list[Particle], background_colour: tuple[int, int, int]) -> None:
    for particle in particles:
        _render_particle(screen, particle, background_colour)

def render_grid(screen: pygame.Surface, grid: SpatialGrid, colour: tuple[int, int, int], line_width: int = 1) -> None:
    for column in range(1, grid.number_columns):
        x_position = round(column * grid.cell_size)
        pygame.draw.line(screen, colour, (x_position, 0), (x_position, grid.domain_height), line_width)

    for row in range(1, grid.number_rows):
        y_position = round(row * grid.cell_size)
        pygame.draw.line(screen, colour, (0, y_position), (grid.domain_width, y_position), line_width)