# spatial_grid.py
from dataclasses import dataclass, field
from math import ceil

from particles import Particle
from vector2 import Vector2

@dataclass
class SpatialGrid:
    domain_width: int
    domain_height: int
    cell_size: float

    number_columns: int = field(init=False)
    number_rows: int = field(init=False)
    cells: list[list[int]] = field(init=False)  # Each cell contains the indices of particles currently inside it

    # __post_init__ to derive the number of columns and rows needed for a given domain
    def __post_init__(self) -> None:
        if self.domain_width <= 0 or self.domain_height <= 0 or self.cell_size <= 0:
            raise ValueError("The domain width, height and cell size must be positive!")

        # Calculate the number of columns and rows needed
        self.number_columns = ceil(self.domain_width / self.cell_size)
        self.number_rows = ceil(self.domain_height / self.cell_size)

        # Initialise the cell lists
        number_of_cells = self.number_rows * self.number_columns
        self.cells = [[] for _ in range(number_of_cells)]

    # Clears all cells
    def clear(self) -> None:
        for cell in self.cells:
            cell.clear()

    # Converts cell indices to flat indices: index = row x n_columns + column (unique 1-to-1 mapping)
    def _flat_index(self, column: int, row: int) -> int:
        return row * self.number_columns + column

    # Converts a continuous (x, y) position vector to cell indices
    def position_to_cell(self, position: Vector2) -> tuple[int, int]:
        # Use floor division to find the corresponding column and row
        column = int(position.x // self.cell_size)
        row = int(position.y // self.cell_size)

        # Clamp to ensure within the grid
        column = max(0, min(column, self.number_columns - 1))
        row = max(0, min(row, self.number_rows - 1))
        return column, row

    # Inserts particle into grid
    def insert(self, particle_index: int, position: Vector2) -> None:
        column, row = self.position_to_cell(position)
        flat_index = self._flat_index(column, row)
        self.cells[flat_index].append(particle_index)

    def rebuild(self, particles: list[Particle]) -> None:
        self.clear()
        for particle_index, particle in enumerate(particles):
            self.insert(particle_index, particle.position)

    # Returns the nearby particle indices in the nearest 8 adjacent cells
    def nearby_particle_indices(self, position: Vector2) -> list[int]:
        centre_column, centre_row = self.position_to_cell(position)
        nearby_indices: list[int] = []

        minimum_column = max(0, centre_column - 1)
        maximum_column = min(self.number_columns - 1, centre_column + 1)
        minimum_row = max(0, centre_row - 1)
        maximum_row = min(self.number_rows - 1, centre_row + 1)

        for row in range(minimum_row, maximum_row + 1):
            for column in range(minimum_column, maximum_column + 1):
                flat_index = self._flat_index(column, row)
                nearby_indices.extend(self.cells[flat_index])

        return nearby_indices