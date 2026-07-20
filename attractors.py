# attractors.py
# Defines attraction fields and their distance falloff
from dataclasses import dataclass
from vector2 import Vector2

@dataclass
class Attractor:
    position: Vector2
    strength: float
    radius: float

    def strength_at_distance(self, distance: float) -> float:
        if self.radius <= 0.0:
            return 0.0
        if distance > self.radius:
            return 0.0
        return self.strength * (1.0 - distance / self.radius)
