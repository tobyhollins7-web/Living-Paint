# renderer.py
import pygame
from particles import Particle
from vector2 import Vector2

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