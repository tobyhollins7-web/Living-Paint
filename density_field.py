# density_field.py
from dataclasses import dataclass, field
from math import ceil, floor, sqrt
from particles import Particle

@dataclass
class DensityField:
    domain_width: int
    domain_height: int
    cell_size: float
    influence_radius: float

    number_columns: int = field(init=False)
    number_rows: int = field(init=False)

    values: list[list[float]] = field(init=False)
    colour_sums: list[list[list[float]]] = field(init=False)

    def __post_init__(self) -> None:
        if self.domain_width <= 0 or self.domain_height <= 0 or self.cell_size <= 0 or self.influence_radius <= 0.0:
            raise ValueError("The domain width, height and cell size must be positive!")

        self.number_columns = ceil(self.domain_width / self.cell_size)
        self.number_rows = ceil(self.domain_height / self.cell_size)

        self.values = [
            [0.0 for columns in range(self.number_columns)]
            for row in range(self.number_rows)
        ]

        self.colour_sums = [
            [[0.0, 0.0, 0.0] for column in range(self.number_columns)]
            for row in range(self.number_rows)
        ]

    def clear(self) -> None:
        self.values = [
            [0.0 for columns in range(self.number_columns)]
            for row in range(self.number_rows)
        ]
        self.colour_sums = [
            [[0.0, 0.0, 0.0] for column in range(self.number_columns)]
            for row in range(self.number_rows)
        ]

    def deposit_particle(self, particle: Particle) -> None:
        minimum_column = max(0, floor((particle.position.x - self.influence_radius) / self.cell_size))
        maximum_column = min(self.number_columns - 1, floor((particle.position.x + self.influence_radius) / self.cell_size))

        minimum_row = max(0, floor((particle.position.y - self.influence_radius) / self.cell_size))
        maximum_row = min(self.number_rows - 1, floor((particle.position.y + self.influence_radius) / self.cell_size))

        for row in range(minimum_row, maximum_row + 1):
            for column in range(minimum_column, maximum_column + 1):
                cell_centre_x = (column + 0.5) * self.cell_size
                cell_centre_y = (row + 0.5) * self.cell_size
                distance_squared = (cell_centre_x - particle.position.x) ** 2 + (cell_centre_y - particle.position.y) ** 2
                if distance_squared < self.influence_radius ** 2:
                    distance = sqrt(distance_squared)
                    weight = (1 - distance / self.influence_radius) ** 2
                    self.values[row][column] += weight

                    for channel in range(3):
                        self.colour_sums[row][column][channel] += (
                                particle.species.colour[channel] * weight
                        )

    def rebuild(self, particles: list[Particle]) -> None:
        self.clear()
        for particle in particles:
            self.deposit_particle(particle)
