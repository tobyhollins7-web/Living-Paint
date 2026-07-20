# simulation.py
# determines what happens next
from particles import Particle
from vector2 import Vector2
from attractors import Attractor

def _reset_acceleration(particle: Particle) -> None:
    particle.acceleration = Vector2(0.0, 0.0)

def _apply_external_acceleration(particle: Particle, attractor: Attractor | None, drag_coefficient: float) -> None:
    # Attractor contributions
    if attractor is not None:
        # Get the vector from the particle to the target
        particle_to_target = attractor.position.subtract(particle.position)
        distance_to_target = particle_to_target.magnitude()

        # Normalise this vector to get the direction which acceleration acts in
        unit_direction = particle_to_target.normalised()

        # Scale the acceleration to be in the direction of the vector, with magnitude attraction_strength
        attraction_acceleration = unit_direction.scaled_by(attractor.strength_at_distance(distance_to_target))

        # Add the attractor contributions to total acceleration
        particle.acceleration = particle.acceleration.add(attraction_acceleration)

    # Drag contributions to acceleration (Linear drag-velocity model)
    drag_acceleration = particle.velocity.scaled_by(-drag_coefficient)  # Contribution of drag in -ve velocity direction
    particle.acceleration = particle.acceleration.add(drag_acceleration)


def _apply_particle_interactions(particles: list[Particle], repulsion_coefficient: float) -> None:
    for i in range(len(particles)):
        for j in range(i + 1, len(particles)):
            particle_a = particles[i]
            particle_b = particles[j]

            # Get the vector from particle A to B
            vector_ab = particle_b.position.subtract(particle_a.position)
            distance_ab = vector_ab.magnitude()
            particle_overlap = particle_a.species.radius + particle_b.species.radius - distance_ab

            # Case where the particles overlap
            if particle_overlap > 0.0:
                # Get the unit vector from A to B
                unit_vector_ab = vector_ab.normalised()

                # Calculate a simple linear repulsion acceleration magnitude
                repulsion_magnitude = repulsion_coefficient * particle_overlap

                # Add acceleration component due to particle interaction to both particles
                particle_a.acceleration = particle_a.acceleration.add(unit_vector_ab.scaled_by(-repulsion_magnitude))
                particle_b.acceleration = particle_b.acceleration.add(unit_vector_ab.scaled_by(repulsion_magnitude))


def _integrate_particle(particle: Particle, dt: float) -> None:
    # Integrate acceleration to get velocity increment
    velocity_increment = particle.acceleration.scaled_by(dt)
    particle.velocity = particle.velocity.add(velocity_increment)

    # Integrate velocity to get displacement increment
    displacement_increment = particle.velocity.scaled_by(dt)
    particle.position = particle.position.add(displacement_increment)

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
                     attractor: Attractor | None, drag_coefficient: float, repulsion_coefficient: float) -> None:
    for particle in particles:
        _reset_acceleration(particle)
        _apply_external_acceleration(particle, attractor, drag_coefficient)

    _apply_particle_interactions(particles, repulsion_coefficient)

    for particle in particles:
        _integrate_particle(particle, dt)
        _handle_boundary_collision(particle, width, height)
