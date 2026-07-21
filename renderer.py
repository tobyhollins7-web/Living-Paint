# renderer.py
import pygame
from particles import Particle
from vector2 import Vector2
from spatial_grid import SpatialGrid

def render_radius_indicator(screen: pygame.Surface, position: Vector2, radius: float, colour: tuple[int, int, int],
                            line_width: int) -> None:
    position_screen = (round(position.x), round(position.y))
    pygame.draw.circle(screen, colour, position_screen, round(radius), width=line_width)

def _render_particle(screen: pygame.Surface, particle: Particle) -> None:
    position = (round(particle.position.x), round(particle.position.y))
    pygame.draw.circle(
        screen,
        particle.species.colour,
        position,
        round(particle.species.radius),
    )

def render_particles(screen: pygame.Surface, particles: list[Particle]) -> None:
    for particle in particles:
        _render_particle(screen, particle)

def render_grid(screen: pygame.Surface, grid: SpatialGrid, colour: tuple[int, int, int], line_width: int = 1) -> None:
    for column in range(1, grid.number_columns):
        x_position = round(column * grid.cell_size)
        pygame.draw.line(screen, colour, (x_position, 0), (x_position, grid.domain_height), line_width)

    for row in range(1, grid.number_rows):
        y_position = round(row * grid.cell_size)
        pygame.draw.line(screen, colour, (0, y_position), (grid.domain_width, y_position), line_width)