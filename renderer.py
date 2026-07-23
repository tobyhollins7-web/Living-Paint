# renderer.py
import pygame
from math import exp
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

def render_density_field(
    screen: pygame.Surface,
    density_field: DensityField,
    background_colour: tuple[int, int, int],
    density_gain: float,
) -> None:
    field_surface = pygame.Surface(
        (
            density_field.number_columns,
            density_field.number_rows,
        )
    )

    for row in range(density_field.number_rows):
        for column in range(density_field.number_columns):
            density = density_field.values[row][column]

            coverage = 1.0 - exp(-density_gain * density)

            coverage = max(0.0, min(
                (coverage - 0.15) / (0.65 - 0.15),
                1.0,
            ))
            coverage = coverage * coverage * (3.0 - 2.0 * coverage)

            if density > 0.0:
                particle_colour = (
                    density_field.colour_sums[row][column][0] / density,
                    density_field.colour_sums[row][column][1] / density,
                    density_field.colour_sums[row][column][2] / density,
                )
            else:
                particle_colour = background_colour

            colour = (
                round(
                    background_colour[0]
                    + coverage * (particle_colour[0] - background_colour[0])
                ),
                round(
                    background_colour[1]
                    + coverage * (particle_colour[1] - background_colour[1])
                ),
                round(
                    background_colour[2]
                    + coverage * (particle_colour[2] - background_colour[2])
                ),
            )

            field_surface.set_at((column, row), colour)

    continuous_surface = pygame.transform.smoothscale(
        field_surface,
        screen.get_size(),
    )

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