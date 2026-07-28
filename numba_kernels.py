# numba_kernels.py
# Contains numerical kernels compiled by Numba
from math import floor, sqrt

import numpy as np
from numba import njit


@njit(cache=True)
def apply_particle_interactions(positions: np.ndarray, velocities: np.ndarray, accelerations: np.ndarray,
                                energies: np.ndarray, species_ids: np.ndarray, radii: np.ndarray,
                                maximum_energies: np.ndarray, interaction_strengths: np.ndarray,
                                feeding_rates: np.ndarray, feeding_efficiencies: np.ndarray, cell_size: float,
                                number_columns: int, number_rows: int, repulsion_coefficient: float,
                                species_interaction_radius: float, pair_damping_coefficient: float,
                                dt: float) -> None:
    number_particles = len(positions)
    number_cells = number_columns * number_rows
    cell_counts = np.zeros(number_cells, dtype=np.int32)
    particle_cells = np.empty(number_particles, dtype=np.int32)

    # Count particles in every cell.
    for particle_index in range(number_particles):
        column = int(floor(positions[particle_index, 0] / cell_size))
        row = int(floor(positions[particle_index, 1] / cell_size))
        column = max(0, min(column, number_columns - 1))
        row = max(0, min(row, number_rows - 1))
        cell_index = row * number_columns + column
        particle_cells[particle_index] = cell_index
        cell_counts[cell_index] += 1

    # Build stable contiguous cell contents, preserving particle index order.
    cell_starts = np.empty(number_cells + 1, dtype=np.int32)
    cell_starts[0] = 0

    for cell_index in range(number_cells):
        cell_starts[cell_index + 1] = cell_starts[cell_index] + cell_counts[cell_index]

    cell_write_positions = cell_starts[:-1].copy()
    ordered_particle_indices = np.empty(number_particles, dtype=np.int32)

    for particle_index in range(number_particles):
        cell_index = particle_cells[particle_index]
        ordered_particle_indices[cell_write_positions[cell_index]] = particle_index
        cell_write_positions[cell_index] += 1

    for particle_a_index in range(number_particles):
        centre_cell = particle_cells[particle_a_index]
        centre_column = centre_cell % number_columns
        centre_row = centre_cell // number_columns

        minimum_column = max(0, centre_column - 1)
        maximum_column = min(number_columns - 1, centre_column + 1)
        minimum_row = max(0, centre_row - 1)
        maximum_row = min(number_rows - 1, centre_row + 1)

        for row in range(minimum_row, maximum_row + 1):
            for column in range(minimum_column, maximum_column + 1):
                cell_index = row * number_columns + column

                for ordered_index in range(cell_starts[cell_index], cell_starts[cell_index + 1]):
                    particle_b_index = ordered_particle_indices[ordered_index]

                    if particle_b_index <= particle_a_index:
                        continue

                    dx = positions[particle_b_index, 0] - positions[particle_a_index, 0]
                    dy = positions[particle_b_index, 1] - positions[particle_a_index, 1]
                    distance_squared = dx * dx + dy * dy

                    species_a = species_ids[particle_a_index]
                    species_b = species_ids[particle_b_index]
                    contact_distance = radii[species_a] + radii[species_b]
                    maximum_distance = max(contact_distance, species_interaction_radius)

                    if distance_squared >= maximum_distance * maximum_distance:
                        continue

                    distance = sqrt(distance_squared)
                    feeding_rate_a = feeding_rates[species_a, species_b]
                    feeding_rate_b = feeding_rates[species_b, species_a]
                    energy_taken_by_a = 0.0
                    energy_taken_by_b = 0.0

                    if feeding_rate_a > 0.0:
                        feeding_reach_a = min(radii[species_a] * 0.1, 10.0)
                        if distance <= contact_distance + feeding_reach_a:
                            energy_taken_by_a = min(feeding_rate_a * dt, max(energies[particle_b_index], 0.0))

                    if feeding_rate_b > 0.0:
                        feeding_reach_b = min(radii[species_b] * 0.1, 10.0)
                        if distance <= contact_distance + feeding_reach_b:
                            energy_taken_by_b = min(feeding_rate_b * dt, max(energies[particle_a_index], 0.0))

                    energy_gained_by_a = energy_taken_by_a * feeding_efficiencies[species_a, species_b]
                    energy_gained_by_b = energy_taken_by_b * feeding_efficiencies[species_b, species_a]
                    energies[particle_a_index] = min(energies[particle_a_index] + energy_gained_by_a - energy_taken_by_b,
                                                       maximum_energies[species_a])
                    energies[particle_b_index] = min(energies[particle_b_index] + energy_gained_by_b - energy_taken_by_a,
                                                       maximum_energies[species_b])

                    if distance == 0.0:
                        unit_x = 1.0
                        unit_y = 0.0
                    else:
                        inverse_distance = 1.0 / distance
                        unit_x = dx * inverse_distance
                        unit_y = dy * inverse_distance

                    particle_overlap = contact_distance - distance

                    if particle_overlap > 0.0:
                        repulsion_magnitude = repulsion_coefficient * particle_overlap
                        accelerations[particle_a_index, 0] -= unit_x * repulsion_magnitude
                        accelerations[particle_a_index, 1] -= unit_y * repulsion_magnitude
                        accelerations[particle_b_index, 0] += unit_x * repulsion_magnitude
                        accelerations[particle_b_index, 1] += unit_y * repulsion_magnitude
                        damping_weight = 1.0
                    else:
                        if species_interaction_radius <= contact_distance:
                            continue

                        t = (distance - contact_distance) / (species_interaction_radius - contact_distance)
                        falloff = 4.0 * t * (1.0 - t)
                        strength_a_to_b = interaction_strengths[species_a, species_b]
                        strength_b_to_a = interaction_strengths[species_b, species_a]
                        accelerations[particle_a_index, 0] += unit_x * strength_a_to_b * falloff
                        accelerations[particle_a_index, 1] += unit_y * strength_a_to_b * falloff
                        accelerations[particle_b_index, 0] -= unit_x * strength_b_to_a * falloff
                        accelerations[particle_b_index, 1] -= unit_y * strength_b_to_a * falloff

                        if strength_a_to_b == 0.0 and strength_b_to_a == 0.0:
                            continue

                        damping_weight = 1.0 - t

                    relative_velocity_x = velocities[particle_b_index, 0] - velocities[particle_a_index, 0]
                    relative_velocity_y = velocities[particle_b_index, 1] - velocities[particle_a_index, 1]
                    radial_relative_speed = relative_velocity_x * unit_x + relative_velocity_y * unit_y
                    damping_magnitude = pair_damping_coefficient * damping_weight * radial_relative_speed
                    damping_x = unit_x * damping_magnitude
                    damping_y = unit_y * damping_magnitude
                    accelerations[particle_a_index, 0] += damping_x
                    accelerations[particle_a_index, 1] += damping_y
                    accelerations[particle_b_index, 0] -= damping_x
                    accelerations[particle_b_index, 1] -= damping_y


@njit(cache=True)
def deposit_particle(values: np.ndarray, colour_sums: np.ndarray, cell_centres_x: np.ndarray,
                     cell_centres_y: np.ndarray, particle_x: float, particle_y: float, red: float,
                     green: float, blue: float, cell_size: float, influence_radius: float) -> None:
    influence_radius_squared = influence_radius * influence_radius
    inverse_influence_radius = 1.0 / influence_radius
    number_rows, number_columns = values.shape

    minimum_column = max(0, int(floor((particle_x - influence_radius) / cell_size)))
    maximum_column = min(number_columns - 1, int(floor((particle_x + influence_radius) / cell_size)))
    minimum_row = max(0, int(floor((particle_y - influence_radius) / cell_size)))
    maximum_row = min(number_rows - 1, int(floor((particle_y + influence_radius) / cell_size)))

    for row in range(minimum_row, maximum_row + 1):
        dy = cell_centres_y[row] - particle_y
        dy_squared = dy * dy

        for column in range(minimum_column, maximum_column + 1):
            dx = cell_centres_x[column] - particle_x
            distance_squared = dx * dx + dy_squared

            if distance_squared >= influence_radius_squared:
                continue

            distance = sqrt(distance_squared)
            falloff = 1.0 - distance * inverse_influence_radius
            weight = falloff * falloff
            values[row, column] += weight
            colour_sums[row, column, 0] += red * weight
            colour_sums[row, column, 1] += green * weight
            colour_sums[row, column, 2] += blue * weight


@njit(cache=True)
def rebuild_density(values: np.ndarray, colour_sums: np.ndarray, cell_centres_x: np.ndarray,
                    cell_centres_y: np.ndarray, positions: np.ndarray, colours: np.ndarray, cell_size: float,
                    influence_radius: float) -> None:
    values.fill(0.0)
    colour_sums.fill(0.0)

    for particle_index in range(len(positions)):
        deposit_particle(values, colour_sums, cell_centres_x, cell_centres_y, positions[particle_index, 0],
                         positions[particle_index, 1], colours[particle_index, 0], colours[particle_index, 1],
                         colours[particle_index, 2], cell_size, influence_radius)
