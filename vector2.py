# vector2.py
from __future__ import annotations

from dataclasses import dataclass
import math

@dataclass
class Vector2:
    x: float
    y: float

    def add(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def subtract(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def distance_squared(self, other: Vector2) -> float:
        dx = other.x - self.x
        dy = other.y - self.y
        return dx * dx + dy * dy

    def scaled_by(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def magnitude(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalised(self) -> Vector2:
        mag = self.magnitude()
        if mag == 0.0:
            return Vector2(0.0, 0.0)
        return Vector2(self.x / mag, self.y / mag)

    def dot(self, other: Vector2) -> float:
        return self.x * other.x + self.y * other.y
