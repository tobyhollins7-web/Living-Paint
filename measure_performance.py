# benchmark_density.py
#
# Standalone deterministic benchmark for DensityField.
# Place this file beside density_field.py and run:
#
#     python benchmark_density.py
#
# This deliberately benchmarks density rebuilding separately from
# Pygame's FPS cap, physics and rendering.

from dataclasses import dataclass
from math import ceil, sqrt
from statistics import mean
from time import perf_counter

from density_field import DensityField


# ============================================================
# BENCHMARK SETTINGS
# ============================================================

WIDTH = 800
HEIGHT = 600

PARTICLE_COUNT = 3000
INFLUENCE_RADIUS = 25.0

CELL_SIZES = [8.0, 4.0, 2.0, 1.0]

WARMUP_REBUILDS = 2
MEASURED_REBUILDS = 10

PARTICLE_MARGIN = 30.0


# ============================================================
# MINIMAL PARTICLE-LIKE OBJECTS
#
# DensityField only needs:
#     particle.position.x
#     particle.position.y
#     particle.species.colour
#
# Therefore, the benchmark does not need to construct your full
# simulation Particle objects.
# ============================================================

@dataclass(slots=True)
class BenchmarkPosition:
    x: float
    y: float


@dataclass(slots=True)
class BenchmarkSpecies:
    colour: tuple[int, int, int]


@dataclass(slots=True)
class BenchmarkParticle:
    position: BenchmarkPosition
    species: BenchmarkSpecies


# ============================================================
# PARTICLE CREATION
# ============================================================

def create_fixed_particles(
    particle_count: int,
    width: int,
    height: int,
    margin: float,
) -> list[BenchmarkParticle]:
    """
    Create an evenly spaced and completely deterministic particle layout.

    The same positions and colours are used for every cell-size test,
    making comparisons between tests fair.
    """

    colours = [
        (0, 220, 220),      # Cyan
        (255, 110, 90),     # Coral
        (170, 100, 255),    # Violet
        (245, 190, 50),     # Gold
    ]

    species = [
        BenchmarkSpecies(colour)
        for colour in colours
    ]

    usable_width = width - 2.0 * margin
    usable_height = height - 2.0 * margin

    aspect_ratio = usable_width / usable_height

    columns = ceil(sqrt(particle_count * aspect_ratio))
    rows = ceil(particle_count / columns)

    spacing_x = usable_width / max(columns - 1, 1)
    spacing_y = usable_height / max(rows - 1, 1)

    particles = []

    for index in range(particle_count):
        column = index % columns
        row = index // columns

        x = margin + column * spacing_x
        y = margin + row * spacing_y

        particles.append(
            BenchmarkParticle(
                position=BenchmarkPosition(x, y),
                species=species[index % len(species)],
            )
        )

    return particles


# ============================================================
# TIMING
# ============================================================

def percentile(samples: list[float], proportion: float) -> float:
    ordered = sorted(samples)

    index = round((len(ordered) - 1) * proportion)
    return ordered[index]


def benchmark_cell_size(
    particles: list[BenchmarkParticle],
    cell_size: float,
) -> dict[str, float]:
    density_field = DensityField(
        domain_width=WIDTH,
        domain_height=HEIGHT,
        cell_size=cell_size,
        influence_radius=INFLUENCE_RADIUS,
    )

    # Warm-up allows Python and the operating system to settle before
    # measurements are collected.
    for _ in range(WARMUP_REBUILDS):
        density_field.rebuild(particles)

    rebuild_times = []

    for _ in range(MEASURED_REBUILDS):
        start_time = perf_counter()

        density_field.rebuild(particles)

        elapsed_time = perf_counter() - start_time
        rebuild_times.append(elapsed_time)

    mean_time = mean(rebuild_times)
    p95_time = percentile(rebuild_times, 0.95)
    maximum_time = max(rebuild_times)

    candidate_cells_per_particle = (
        2 * ceil(INFLUENCE_RADIUS / cell_size) + 1
    ) ** 2

    total_candidate_tests = (
        candidate_cells_per_particle * len(particles)
    )

    return {
        "columns": density_field.number_columns,
        "rows": density_field.number_rows,
        "field_cells": (
            density_field.number_columns
            * density_field.number_rows
        ),
        "candidate_cells_per_particle": candidate_cells_per_particle,
        "total_candidate_tests": total_candidate_tests,
        "mean_ms": mean_time * 1000.0,
        "p95_ms": p95_time * 1000.0,
        "maximum_ms": maximum_time * 1000.0,
        "maximum_rebuilds_per_second": 1.0 / mean_time,
    }


# ============================================================
# OUTPUT
# ============================================================

def print_heading() -> None:
    print()
    print("Living Paint density-field benchmark")
    print("=" * 72)
    print(f"Domain:           {WIDTH} x {HEIGHT}")
    print(f"Particles:        {PARTICLE_COUNT}")
    print(f"Influence radius: {INFLUENCE_RADIUS:.1f} px")
    print(f"Warm-up runs:     {WARMUP_REBUILDS}")
    print(f"Measured runs:    {MEASURED_REBUILDS}")
    print()
    print(
        f"{'Cell':>6} "
        f"{'Grid':>12} "
        f"{'Mean':>10} "
        f"{'P95':>10} "
        f"{'Maximum':>10} "
        f"{'Rebuild/s':>11}"
    )
    print("-" * 72)


def print_result(cell_size: float, result: dict[str, float]) -> None:
    grid_description = (
        f"{int(result['columns'])}x{int(result['rows'])}"
    )

    print(
        f"{cell_size:>5.1f} "
        f"{grid_description:>12} "
        f"{result['mean_ms']:>8.2f}ms "
        f"{result['p95_ms']:>8.2f}ms "
        f"{result['maximum_ms']:>8.2f}ms "
        f"{result['maximum_rebuilds_per_second']:>10.1f}"
    )


def print_interpretation(results: dict[float, dict[str, float]]) -> None:
    print()
    print("Interpretation")
    print("=" * 72)

    for cell_size, result in results.items():
        mean_ms = result["mean_ms"]

        if mean_ms <= 16.67:
            display_assessment = "fast enough for rebuilding at 60 Hz"
        elif mean_ms <= 50.0:
            display_assessment = "fast enough for rebuilding at 20 Hz"
        else:
            display_assessment = "too slow even for a 20 Hz rebuild target"

        print(
            f"{cell_size:>4.1f} px: "
            f"{mean_ms:>8.2f} ms, {display_assessment}."
        )

    baseline_size = CELL_SIZES[0]
    baseline_time = results[baseline_size]["mean_ms"]

    print()
    print(f"Cost relative to the {baseline_size:g} px baseline:")

    for cell_size in CELL_SIZES:
        relative_cost = (
            results[cell_size]["mean_ms"] / baseline_time
        )

        print(
            f"  {cell_size:>4.1f} px cells: "
            f"{relative_cost:>6.2f} times the baseline cost"
        )

    print()
    print(
        "These figures measure density rebuilding only. They exclude physics, "
        "density rendering, display updates and Pygame's frame limiter."
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    particles = create_fixed_particles(
        particle_count=PARTICLE_COUNT,
        width=WIDTH,
        height=HEIGHT,
        margin=PARTICLE_MARGIN,
    )

    print_heading()

    results = {}

    for cell_size in CELL_SIZES:
        result = benchmark_cell_size(
            particles=particles,
            cell_size=cell_size,
        )

        results[cell_size] = result
        print_result(cell_size, result)

    print_interpretation(results)


if __name__ == "__main__":
    main()