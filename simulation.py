# simulation.py
# determines what happens next
from math import cos, sin, pi
from random import uniform, shuffle
from particles import Particle, create_particle
from vector2 import Vector2
from attractors import Attractor
from spatial_grid import SpatialGrid

def _apply_feeding(particle_a: Particle, particle_b: Particle, distance_ab: float, contact_distance_ab: float,
                   dt: float) -> None:
    # Check to see if A is a predator of B, if not will be None
    feeding_rule_a_to_b = particle_a.species.feeding_rules.get(particle_b.species.id, None)

    # Check to see if B is a predator of A, if not will be None
    feeding_rule_b_to_a = particle_b.species.feeding_rules.get(particle_a.species.id, None)

    feeding_reach_a = min(particle_a.species.radius * 0.1, 10.0)
    feeding_reach_b = min(particle_b.species.radius * 0.1, 10.0)

    energy_taken_by_a, energy_taken_by_b = 0.0, 0.0

    # If A is a predator of B, take either the max amount A can take from B, or B's total energy if this is lesser
    if feeding_rule_a_to_b is not None and distance_ab <= contact_distance_ab + feeding_reach_a:
        energy_taken_by_a = min(feeding_rule_a_to_b.rate * dt, max(particle_b.energy, 0.0))

    # If B is a predator of A, take either the max amount B can take from A, or A's total energy if this is lesser
    if feeding_rule_b_to_a is not None and distance_ab <= contact_distance_ab + feeding_reach_b:
        energy_taken_by_b = min(feeding_rule_b_to_a.rate * dt, max(particle_a.energy, 0.0))

    # Work out how much energy is gained by either of the particles
    energy_gained_by_a = energy_taken_by_a * feeding_rule_a_to_b.efficiency if feeding_rule_a_to_b is not None else 0.0
    energy_gained_by_b = energy_taken_by_b * feeding_rule_b_to_a.efficiency if feeding_rule_b_to_a is not None else 0.0

    # Add the net gained energy from feeding to particles
    particle_a.energy = min(particle_a.energy + energy_gained_by_a - energy_taken_by_b, particle_a.species.maximum_energy)
    particle_b.energy = min(particle_b.energy + energy_gained_by_b - energy_taken_by_a, particle_b.species.maximum_energy)

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
    species_interaction_radius: float, pair_damping_coefficient: float, dt: float) -> None:
    # Spatial grid logic, no need to sample all particles, just particles in nearby grids
    for i, particle_a in enumerate(particles):
        nearby_indices = spatial_grid.nearby_particle_indices(particle_a.position)
        for j in nearby_indices:
            if j <= i:
                continue
            particle_b = particles[j]

            vector_ab = particle_b.position.subtract(particle_a.position)
            distance_ab = vector_ab.magnitude()
            contact_distance_ab = particle_a.species.radius + particle_b.species.radius

            # This pair cannot affect one another.
            if distance_ab >= max(contact_distance_ab, species_interaction_radius):
                continue

            _apply_feeding(particle_a, particle_b, distance_ab, contact_distance_ab, dt)

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


# Simple function which updates the energy of the particle, minus metabolic rate * time elapsed
def _update_particle_energy(particle: Particle, dt: float) -> None:
    energy_consumed = particle.species.metabolism * dt
    energy_generated = particle.species.energy_generation * dt

    particle.energy = min(particle.energy - energy_consumed + energy_generated, particle.species.maximum_energy)


# Removes any particles with energy <= 0
def _handle_low_energy_particles(particles: list[Particle]) -> list[Particle]:
    energetic_particles = []
    for particle in particles:
        if particle.energy > 0.0:
            energetic_particles.append(particle)
    return energetic_particles

def _find_offspring_position(parent: Particle, particles: list[Particle], pending_offspring: list[Particle],
                             spatial_grid: SpatialGrid, width: int, height: int,
                             num_attempts: int = 8, offspring_clearance_frac: float = 0.05) -> Vector2 | None:
    angle_between_attempts = 2 * pi / num_attempts
    angle = uniform(0.0, angle_between_attempts)

    # Make the distance from the parent (2.0 + offspring_clearance_frac) times the radius
    distance = parent.species.radius * (2.0 + offspring_clearance_frac)

    for _ in range(num_attempts):
        # Get the position for the attempted offspring spawn location
        position = Vector2(
            parent.position.x + distance * cos(angle),
            parent.position.y + distance * sin(angle)
        )

        # Update angle for future attempts (before continuing for any reason this attempt)
        angle += angle_between_attempts

        # Skip cases where child spawns outside the simulation
        if position.x < parent.species.radius or position.x > width - parent.species.radius:
            continue
        elif position.y < parent.species.radius or position.y > height - parent.species.radius:
            continue

        # Get the nearby particles to the proposed offspring position
        nearby_indices = spatial_grid.nearby_particle_indices(position)
        nearby_particles = [particles[index] for index in nearby_indices]

        position_is_blocked = False

        # Loop through these particles to work out if nearby particle is too close for offspring to be born
        for nearby_particle in nearby_particles:

            # Skip particle if the nearby particle is itself the parent
            if nearby_particle is parent:
                continue

            # Work out the distance to the nearby particle
            nearby_distance = nearby_particle.position.subtract(position).magnitude()

            if nearby_distance < (
                parent.species.radius * (1.0 + offspring_clearance_frac) +
                nearby_particle.species.radius
            ):
                position_is_blocked = True
                break

        # if position is blocked by a nearby existing particle, continue to next attempt
        if position_is_blocked:
            continue

        # Loop through all pending offspring, to check if current offspring is too close to be born
        for offspring in pending_offspring:
            offspring_distance = offspring.position.subtract(position).magnitude()

            if offspring_distance < (
                parent.species.radius * (1.0 + offspring_clearance_frac) +
                offspring.species.radius
            ):
                position_is_blocked = True
                break

        # if position is blocked by a pending offspring, continue to next attempt
        if position_is_blocked:
            continue

        # If all checks pass return the current attempt's position as a viable position for offspring
        return position

    # If no positions available from all attempts, then offspring cannot be birthed
    return None

def _create_offspring(parent: Particle, offspring_position: Vector2) -> Particle:
    rule = parent.species.reproduction_rule
    return create_particle(
        position=offspring_position,
        species=parent.species,
        velocity=Vector2(
            parent.velocity.x + uniform(-10.0, 10.0),
            parent.velocity.y + uniform(-10.0, 10.0)
        ),
        energy=rule.offspring_energy,
        reproduction_cooldown_remaining=rule.reproduction_cooldown,
    )

def _handle_reproduction(particles: list[Particle], dt: float, width: int, height: int, maximum_particles: int,
                         spatial_grid: SpatialGrid, retry_cooldown: float = 0.25) -> list[Particle]:

    pending_offspring: list[Particle] = []

    for particle in particles:
        particle.reproduction_cooldown_remaining = max(0.0, particle.reproduction_cooldown_remaining - dt)

    # Treat all particles as potential parents initially
    parents = particles.copy()

    # Shuffle the order of the parents to prevent bias towards early parents in particles
    shuffle(parents)

    for parent in parents:
        # If we have reached the maximum number of particles, stop reproduction
        if len(particles) + len(pending_offspring) >= maximum_particles:
            break

        # If parent cannot reproduce yet, skip it
        if parent.reproduction_cooldown_remaining > 0.0:
            continue

        # Get the reproduction rule
        reproduction_rule = parent.species.reproduction_rule

        # If parent does not have enough energy to reproduce, skip it
        if parent.energy < reproduction_rule.reproduction_threshold:
            continue

        # If passes all eligibility checks then can potentially birth a child
        offspring_position = _find_offspring_position(
            parent=parent,
            particles=particles,
            pending_offspring=pending_offspring,
            spatial_grid=spatial_grid,
            width=width,
            height=height,
        )

        # If offspring position is None, then there is no space for an offspring
        if offspring_position is None:
            # Give a small reproduction cooldown for parent
            parent.reproduction_cooldown_remaining = retry_cooldown
            continue

        # Create offspring
        offspring = _create_offspring(
            parent=parent,
            offspring_position=offspring_position,
        )

        # Apply parenting costs to the parent for creating an offspring
        parent.energy -= reproduction_rule.reproduction_cost
        parent.reproduction_cooldown_remaining = reproduction_rule.reproduction_cooldown

        # Append offspring to the pending offspring
        pending_offspring.append(offspring)

    # Extend the particles to now include all the offspring this timestep
    particles.extend(pending_offspring)
    return particles


def update_particles(particles: list[Particle], dt: float, width: int, height: int,
                     attractor: Attractor | None, drag_coefficient: float, repulsion_coefficient: float,
                     species_interaction_radius: float, maximum_particles: int, pair_damping_coefficient: float,
                     spatial_grid: SpatialGrid) -> list[Particle]:

    # Reset initial acceleration + Work out external accelerations acting on particles
    for particle in particles:
        _reset_acceleration(particle)
        _apply_external_acceleration(particle, attractor, drag_coefficient)

    # Apply metabolism and energy generation updates
    for particle in particles:
        _update_particle_energy(particle, dt)

    # Bin the particles into the spatial grid
    spatial_grid.rebuild(particles)

    # Apply particle-particle interactions
    _apply_particle_interactions(particles, spatial_grid, repulsion_coefficient, species_interaction_radius,
                                 pair_damping_coefficient, dt)

    for particle in particles:
        # Integrate acceleration twice to get displacement
        _integrate_particle(particle, dt)

        # If any particles collide with a boundary, bounce them off it
        _handle_boundary_collision(particle, width, height)

    # Remove any low-energy particles
    updated_particles = _handle_low_energy_particles(particles)

    # Particle positions and indices may have changed.
    spatial_grid.rebuild(updated_particles)

    updated_particles = _handle_reproduction(
        particles=updated_particles,
        dt=dt,
        width=width,
        height=height,
        maximum_particles=maximum_particles,
        spatial_grid=spatial_grid,
    )

    return updated_particles

