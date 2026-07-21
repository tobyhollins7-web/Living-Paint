# simulation.py
# determines what happens next
from particles import Particle
from vector2 import Vector2
from attractors import Attractor
from spatial_grid import SpatialGrid

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

def _apply_pair_damping(particle_a: Particle, particle_b: Particle, unit_vector_ab: Vector2,
                        damping_coefficient: float, damping_weight: float) -> None:
    # Calculate relative velocity of particles
    relative_velocity_ab = particle_b.velocity.subtract(particle_a.velocity)

    # Calculate the signed relative speed along the line connecting the particles
    radial_relative_speed = relative_velocity_ab.dot(unit_vector_ab)

    # Equate magnitude of damping from a linear model of speed
    damping_magnitude = damping_coefficient * damping_weight * radial_relative_speed

    # Work out the increment in acceleration due to damping acting on both particles along AB vector
    damping_acceleration = unit_vector_ab.scaled_by(damping_magnitude)

    # Add damping acceleration to both particles' accelerations
    particle_a.acceleration = particle_a.acceleration.add(damping_acceleration)
    particle_b.acceleration = particle_b.acceleration.add(damping_acceleration.scaled_by(-1.0))


def _apply_particle_interactions(particles: list[Particle], spatial_grid: SpatialGrid, repulsion_coefficient: float,
    species_interaction_radius: float, pair_damping_coefficient: float) -> None:

    # Spatial grid logic, no need to sample all particles, just particles in nearby grids
    for i, particle_a in enumerate(particles):
        nearby_indices = spatial_grid.nearby_particle_indices(particle_a.position)
        for j in nearby_indices:
            if j <= 1:
                continue
            particle_b = particles[j]

            vector_ab = particle_b.position.subtract(particle_a.position)
            distance_ab = vector_ab.magnitude()
            contact_distance_ab = particle_a.species.radius + particle_b.species.radius

            # This pair cannot affect one another.
            if distance_ab >= max(contact_distance_ab, species_interaction_radius):
                continue

            # A coincident pair has no naturally defined direction.
            if distance_ab == 0.0:
                unit_vector_ab = Vector2(1.0, 0.0)
            else:
                unit_vector_ab = vector_ab.scaled_by(1.0 / distance_ab)

            particle_overlap = contact_distance_ab - distance_ab

            # Universal short-range overlap repulsion.
            if particle_overlap > 0.0:
                repulsion_magnitude = repulsion_coefficient * particle_overlap
                repulsion_ab = unit_vector_ab.scaled_by(repulsion_magnitude)

                particle_a.acceleration = particle_a.acceleration.add(repulsion_ab.scaled_by(-1.0))
                particle_b.acceleration = particle_b.acceleration.add(repulsion_ab)

                # add damping to the particles to prevent vibration of nearby particles
                _apply_pair_damping(particle_a, particle_b, unit_vector_ab, pair_damping_coefficient,
                                    damping_weight=1.0)
                continue

            # No valid outer interaction region exists.
            if species_interaction_radius <= contact_distance_ab:
                continue

            # Zero at contact and outer radius, with maximum strength midway.
            t = (distance_ab - contact_distance_ab) / (species_interaction_radius - contact_distance_ab)
            falloff = 4.0 * t * (1.0 - t)

            strength_a_to_b = particle_a.species.interaction_strengths.get(particle_b.species.id, 0.0)
            strength_b_to_a = particle_b.species.interaction_strengths.get(particle_a.species.id, 0.0)

            acceleration_a = unit_vector_ab.scaled_by(strength_a_to_b * falloff)
            acceleration_b = unit_vector_ab.scaled_by(-strength_b_to_a * falloff)

            particle_a.acceleration = particle_a.acceleration.add(acceleration_a)
            particle_b.acceleration = particle_b.acceleration.add(acceleration_b)

            if strength_a_to_b != 0.0 or strength_b_to_a != 0.0:
                _apply_pair_damping(particle_a, particle_b, unit_vector_ab, pair_damping_coefficient, 1.0 - t)

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
                     attractor: Attractor | None, drag_coefficient: float, repulsion_coefficient: float,
                     species_interaction_radius: float, pair_damping_coefficient: float,
                     spatial_grid: SpatialGrid) -> None:

    for particle in particles:
        _reset_acceleration(particle)
        _apply_external_acceleration(particle, attractor, drag_coefficient)

    spatial_grid.rebuild(particles)
    _apply_particle_interactions(particles, spatial_grid, repulsion_coefficient, species_interaction_radius,
                                 pair_damping_coefficient,)

    for particle in particles:
        _integrate_particle(particle, dt)
        _handle_boundary_collision(particle, width, height)
