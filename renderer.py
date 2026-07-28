# renderer.py
import pygame
import numpy as np
from particles import Particle
from vector2 import Vector2
from spatial_grid import SpatialGrid
from density_field import DensityField

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

def render_density_field(screen: pygame.Surface, density_field: DensityField,
                         background_colour: tuple[int, int, int], density_gain: float) -> None:
    density = density_field.values
    coverage = 1.0 - np.exp(-density_gain * density)
    coverage = np.clip((coverage - 0.15) / (0.65 - 0.15), 0.0, 1.0)
    coverage = coverage * coverage * (3.0 - 2.0 * coverage)

    background = np.asarray(background_colour, dtype=np.float64)
    particle_colours = np.empty_like(density_field.colour_sums)
    particle_colours[:] = background
    np.divide(density_field.colour_sums, density[:, :, None], out=particle_colours,
              where=density[:, :, None] > 0.0)

    colours = background + coverage[:, :, None] * (particle_colours - background)
    colours = np.rint(colours).astype(np.uint8)
    field_surface = pygame.surfarray.make_surface(np.transpose(colours, (1, 0, 2)))
    continuous_surface = pygame.transform.smoothscale(field_surface, screen.get_size())

    screen.blit(continuous_surface, (0, 0))


def render_density_grid_overlay(
    screen: pygame.Surface,
    density_field: DensityField,
    colour: tuple[int, int, int],
    line_width: int = 1,
) -> None:
    for column in range(1, density_field.number_columns):
        x_position = round(column * density_field.cell_size)

        pygame.draw.line(
            screen,
            colour,
            (x_position, 0),
            (x_position, density_field.domain_height),
            line_width,
        )

    for row in range(1, density_field.number_rows):
        y_position = round(row * density_field.cell_size)

        pygame.draw.line(
            screen,
            colour,
            (0, y_position),
            (density_field.domain_width, y_position),
            line_width,
        )
