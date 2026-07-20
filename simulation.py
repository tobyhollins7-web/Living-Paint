# simulation.py
# determines what happens next
from particles import Particle
from vector2 import Vector2
from attractors import Attractor

def _update_particle(particle: Particle, dt: float, attractor: Attractor | None, drag_coefficient: float) -> None:
    particle.acceleration = Vector2(0.0, 0.0)

    if attractor is not None:
        # Get the vector from the particle to the target
        particle_to_target = attractor.position.subtract(particle.position)
        distance_to_target = particle_to_target.magnitude()

        # Normalise this vector to get the direction which acceleration acts in
        unit_direction = particle_to_target.normalised()

        # Scale the acceleration to be in the direction of the vector, with magnitude attraction_strength
        attraction_acceleration = unit_direction.scaled_by(attractor.strength_at_distance(distance_to_target))

        # Update particle acceleration
        particle.acceleration = particle.acceleration.add(attraction_acceleration)

    # Drag contributions to acceleration (Linear drag-velocity model)
    drag_acceleration = particle.velocity.scaled_by(-drag_coefficient)  # Contribution of drag in -ve velocity direction
    particle.acceleration = particle.acceleration.add(drag_acceleration)

    # Work out change in velocity as a result in change in acceleration
    velocity_increment = particle.acceleration.scaled_by(dt)
    particle.velocity = particle.velocity.add(velocity_increment)

    # Work out change in displacement as a result in change of velocity
    displacement = particle.velocity.scaled_by(dt)
    particle.position = particle.position.add(displacement)

def _handle_boundary_collision(particle: Particle, width: int, height: int) -> None:
    left = particle.position.x - particle.species.radius
    right = particle.position.x + particle.species.radius
    top = particle.position.y - particle.species.radius
    bottom = particle.position.y + particle.species.radius

    # Case of collision with left wall
    if left <= 0.0 and particle.velocity.x < 0.0:
        particle.velocity.x = -particle.velocity.x
        particle.position.x = particle.species.radius

    # Case of collision with right wall
    elif right >= width and particle.velocity.x > 0.0:
        particle.velocity.x = -particle.velocity.x
        particle.position.x = width - particle.species.radius

    # Case of collision with top wall
    if top <= 0.0 and particle.velocity.y < 0.0:
        particle.velocity.y = -particle.velocity.y
        particle.position.y = particle.species.radius

    # Case of collision with bottom wall
    elif bottom >= height and particle.velocity.y > 0.0:
        particle.velocity.y = -particle.velocity.y
        particle.position.y = height - particle.species.radius


def update_particles(particles: list[Particle], dt: float, width: int, height: int,
                     attractor: Attractor | None, drag_coefficient: float) -> None:
    for particle in particles:
        _update_particle(particle, dt, attractor, drag_coefficient)
        _handle_boundary_collision(particle, width, height)