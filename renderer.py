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
    t = max(0.0, min(particle.energy / particle.species.maximum_energy, 1.0))
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

def render_paint_trails(surface: pygame.Surface, particles: list[Particle],
                       previous_positions: dict[int, Vector2], background_colour: tuple[int, int, int]) -> None:
    for particle in particles:
        previous_position = previous_positions.get(id(particle))

        # This will be the case if the particle has expired
        if previous_position is None:
            continue

        # Match particle colour to its energy level
        particle_colour = _colour_energy_particle(particle, background_colour)

        # Draws a trail
        pygame.draw.circle(
            surface,
            particle_colour,
            (round(previous_position.x), round(previous_position.y)),
            particle.species.paint_trail.width,
        )

        current_position = particle.position

        # This checks to see if the particle is stationary (i.e. has not moved between frames)
        if previous_position.x == current_position.x and previous_position.y == current_position.y:
            continue

        # Connects previous position to current position with a line, prevents feathered trail
        pygame.draw.line(
            surface,
            particle_colour,
            (round(previous_position.x), round(previous_position.y)),
            (round(current_position.x), round(current_position.y)),
            width=particle.species.paint_trail.width
        )