# density_field.py
from dataclasses import dataclass, field
from math import ceil

import numpy as np

from numba_kernels import deposit_particle, rebuild_density
from particles import Particle

@dataclass
class DensityField:
    domain_width: int
    domain_height: int
    cell_size: float
    influence_radius: float

    number_columns: int = field(init=False)
    number_rows: int = field(init=False)

    values: np.ndarray = field(init=False)
    colour_sums: np.ndarray = field(init=False)
    cell_centres_x: np.ndarray = field(init=False)
    cell_centres_y: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        if self.domain_width <= 0 or self.domain_height <= 0 or self.cell_size <= 0 or self.influence_radius <= 0.0:
            raise ValueError("The domain width, height, cell size and influence radius must be positive!")

        self.number_columns = ceil(self.domain_width / self.cell_size)
        self.number_rows = ceil(self.domain_height / self.cell_size)

        self.values = np.zeros((self.number_rows, self.number_columns), dtype=np.float64)
        self.colour_sums = np.zeros((self.number_rows, self.number_columns, 3), dtype=np.float64)
        self.cell_centres_x = (np.arange(self.number_columns, dtype=np.float64) + 0.5) * self.cell_size
        self.cell_centres_y = (np.arange(self.number_rows, dtype=np.float64) + 0.5) * self.cell_size

    def clear(self) -> None:
        self.values.fill(0.0)
        self.colour_sums.fill(0.0)

    def deposit_particle(self, particle: Particle) -> None:
        particle_x = particle.position.x
        particle_y = particle.position.y
        red, green, blue = particle.species.colour
        deposit_particle(self.values, self.colour_sums, self.cell_centres_x, self.cell_centres_y, particle_x,
                         particle_y, red, green, blue, self.cell_size, self.influence_radius)

    def rebuild(self, particles: list[Particle]) -> None:
        positions = np.empty((len(particles), 2), dtype=np.float64)
        colours = np.empty((len(particles), 3), dtype=np.float64)

        for particle_index, particle in enumerate(particles):
            positions[particle_index, 0] = particle.position.x
            positions[particle_index, 1] = particle.position.y
            colours[particle_index] = particle.species.colour

        rebuild_density(self.values, self.colour_sums, self.cell_centres_x, self.cell_centres_y, positions,
                        colours, self.cell_size, self.influence_radius)
