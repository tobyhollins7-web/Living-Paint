# simulation.py
# determines what happens next
from math import cos, sin, pi, sqrt
from random import uniform, shuffle

import numpy as np

from numba_kernels import apply_particle_interactions
from particles import Particle, create_particle
from vector2 import Vector2
from species import FeedingRule
from attractors import Attractor
from spatial_grid import SpatialGrid

_species_array_cache: dict[tuple[int, ...], tuple[np.ndarray, ...]] = {}

def _apply_feeding(particle_a: Particle, particle_b: Particle, distance_ab: float, contact_distance_ab: float,
                   dt: float, feeding_rule_a_to_b: FeedingRule | None, feeding_rule_b_to_a: FeedingRule | None) -> None:
    energy_taken_by_a = 0.0
    energy_taken_by_b = 0.0

    # A feeds on B
    if feeding_rule_a_to_b is not None:
        feeding_reach_a = min(particle_a.species.radius * 0.1, 10.0)
        if distance_ab <= contact_distance_ab + feeding_reach_a:
            energy_taken_by_a = min(
                feeding_rule_a_to_b.rate * dt,
                max(particle_b.energy, 0.0),
            )

    # B feeds on A
    if feeding_rule_b_to_a is not None:
        feeding_reach_b = min(particle_b.species.radius * 0.1, 10.0)
        if distance_ab <= contact_distance_ab + feeding_reach_b:
            energy_taken_by_b = min(
                feeding_rule_b_to_a.rate * dt,
                max(particle_a.energy, 0.0),
            )

    energy_gained_by_a = (
        energy_taken_by_a * feeding_rule_a_to_b.efficiency
        if feeding_rule_a_to_b is not None
        else 0.0
    )

    energy_gained_by_b = (
        energy_taken_by_b * feeding_rule_b_to_a.efficiency
        if feeding_rule_b_to_a is not None
        else 0.0
    )

    particle_a.energy = min(
        particle_a.energy
        + energy_gained_by_a
        - energy_taken_by_b,
        particle_a.species.maximum_energy,
    )

    particle_b.energy = min(
        particle_b.energy
        + energy_gained_by_b
        - energy_taken_by_a,
        particle_b.species.maximum_energy,
    )


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

def _apply_pair_damping(particle_a: Particle, particle_b: Particle, unit_x: float, unit_y: float,
                        damping_coefficient: float, damping_weight: float) -> None:
    # Calculate relative velocity of particles
    relative_velocity_x = particle_b.velocity.x - particle_a.velocity.x
    relative_velocity_y = particle_b.velocity.y - particle_a.velocity.y

    # Calculate the signed relative speed along the line connecting the particles
    radial_relative_speed = relative_velocity_x * unit_x + relative_velocity_y * unit_y

    # Equate magnitude of damping from a linear model of speed
    damping_magnitude = damping_coefficient * damping_weight * radial_relative_speed

    # Work out the increment in acceleration due to damping acting on both particles along AB vector
    damping_x = unit_x * damping_magnitude
    damping_y = unit_y * damping_magnitude

    # Add damping acceleration to both particles' accelerations
    particle_a.acceleration.x += damping_x
    particle_a.acceleration.y += damping_y

    particle_b.acceleration.x -= damping_x
    particle_b.acceleration.y -= damping_y


def _get_species_arrays(particles: list[Particle]) -> tuple[np.ndarray, ...]:
    species_by_id = {particle.species.id: particle.species for particle in particles}
    cache_key = tuple(id(species_by_id[species_id]) for species_id in sorted(species_by_id))
    cached_arrays = _species_array_cache.get(cache_key)

    if cached_arrays is not None:
        return cached_arrays

    maximum_species_id = max(
        max([current_species.id, *current_species.interaction_strengths, *current_species.feeding_rules])
        for current_species in species_by_id.values()
    )
    number_species = maximum_species_id + 1
    radii = np.zeros(number_species, dtype=np.float64)
    maximum_energies = np.zeros(number_species, dtype=np.float64)
    interaction_strengths = np.zeros((number_species, number_species), dtype=np.float64)
    feeding_rates = np.zeros((number_species, number_species), dtype=np.float64)
    feeding_efficiencies = np.zeros((number_species, number_species), dtype=np.float64)

    for current_species in species_by_id.values():
        species_id = current_species.id
        radii[species_id] = current_species.radius
        maximum_energies[species_id] = current_species.maximum_energy

        for other_species_id, strength in current_species.interaction_strengths.items():
            interaction_strengths[species_id, other_species_id] = strength

        for other_species_id, feeding_rule in current_species.feeding_rules.items():
            feeding_rates[species_id, other_species_id] = feeding_rule.rate
            feeding_efficiencies[species_id, other_species_id] = feeding_rule.efficiency

    species_arrays = radii, maximum_energies, interaction_strengths, feeding_rates, feeding_efficiencies
    _species_array_cache[cache_key] = species_arrays
    return species_arrays


def _apply_particle_interactions(particles: list[Particle], spatial_grid: SpatialGrid, repulsion_coefficient: float,
                                 species_interaction_radius: float, pair_damping_coefficient: float,
                                 dt: float) -> None:
    if not particles:
        return

    number_particles = len(particles)
    positions = np.empty((number_particles, 2), dtype=np.float64)
    velocities = np.empty((number_particles, 2), dtype=np.float64)
    accelerations = np.empty((number_particles, 2), dtype=np.float64)
    energies = np.empty(number_particles, dtype=np.float64)
    species_ids = np.empty(number_particles, dtype=np.int32)

    for particle_index, particle in enumerate(particles):
        positions[particle_index] = particle.position.x, particle.position.y
        velocities[particle_index] = particle.velocity.x, particle.velocity.y
        accelerations[particle_index] = particle.acceleration.x, particle.acceleration.y
        energies[particle_index] = particle.energy
        species_ids[particle_index] = particle.species.id

    radii, maximum_energies, interaction_strengths, feeding_rates, feeding_efficiencies = _get_species_arrays(particles)
    apply_particle_interactions(positions, velocities, accelerations, energies, species_ids, radii, maximum_energies,
                                interaction_strengths, feeding_rates, feeding_efficiencies, spatial_grid.cell_size,
                                spatial_grid.number_columns, spatial_grid.number_rows, repulsion_coefficient,
                                species_interaction_radius, pair_damping_coefficient, dt)

    for particle_index, particle in enumerate(particles):
        particle.acceleration.x = accelerations[particle_index, 0]
        particle.acceleration.y = accelerations[particle_index, 1]
        particle.energy = energies[particle_index]

def _integrate_particle(particle: Particle, dt: float) -> None:
    # Integrate acceleration to get velocity increment
    particle.velocity.x += particle.acceleration.x * dt
    particle.velocity.y += particle.acceleration.y * dt

    # Integrate velocity to get displacement increment
    particle.position.x += particle.velocity.x * dt
    particle.position.y += particle.velocity.y * dt


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
    first_offspring_index = len(particles)
    particles.extend(pending_offspring)
    spatial_grid.append_particles(first_particle_index=first_offspring_index, new_particles=pending_offspring)
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

