"""
Controlled profiler for Living Paint's real main.py.

Place this file in the same directory as main.py, then run:

    python measure_main_performance.py

The benchmark:
    * uses a fixed random seed;
    * holds the cursor at a fixed position;
    * automatically spawns a fixed number of brush particles;
    * uses a fixed simulated frame time and removes the FPS wait;
    * ignores keyboard and mouse input during the test;
    * warms up before measuring;
    * profiles the actual main.py loop for a fixed number of frames; and
    * prints a short subsystem summary followed by the hottest functions.

It does not edit main.py or any other project file.
"""

from __future__ import annotations

import cProfile
import functools
import os
import pstats
import random
import runpy
import sys
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from typing import Callable


# =====================================================================
# TEST SETTINGS
# =====================================================================

MAIN_FILENAME = "main.py"

# Start with 1,000. Later, change only this value to compare scaling.
TARGET_BRUSH_PARTICLES = 1000

# The cursor remains here while the particles are created.
SPAWN_POSITION = (400, 300)

# These are simulated frames, so the test does not wait in real time.
SIMULATED_FPS = 60

# Warm-up happens after all requested brush particles have been created.
WARMUP_FRAMES = 60
MEASURED_FRAMES = 300

RANDOM_SEED = 12345
NUMBER_OF_HOT_FUNCTIONS = 15


# =====================================================================
# BENCHMARK STATE
# =====================================================================

class BenchmarkState:
    def __init__(self) -> None:
        self.created_particles = 0
        self.warmup_frames = 0
        self.measured_frames = 0

        self.profiling = False
        self.finished = False
        self.closed_early = False

        self.measurement_started_at = 0.0
        self.measurement_finished_at = 0.0

        self.timings: dict[str, float] = defaultdict(float)
        self.calls: dict[str, int] = defaultdict(int)


state = BenchmarkState()
profiler = cProfile.Profile()


def recording_is_active() -> bool:
    return state.profiling


def timed(label: str, function: Callable) -> Callable:
    """Time a relatively coarse function without changing its result."""

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        should_record = recording_is_active()

        if not should_record:
            return function(*args, **kwargs)

        started_at = perf_counter()

        try:
            return function(*args, **kwargs)
        finally:
            state.timings[label] += perf_counter() - started_at
            state.calls[label] += 1

    return wrapper


# =====================================================================
# PATCHING
# =====================================================================

def run_controlled_main(main_path: Path) -> dict:
    """
    Run the real main.py with deterministic input and timing.

    Imports are patched before main.py executes, so statements such as
    ``from simulation import update_particles`` receive the timed version.
    """

    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    project_directory = main_path.parent.resolve()
    sys.path.insert(0, str(project_directory))

    import pygame
    import brushes
    import density_field
    import renderer
    import simulation
    import spatial_grid

    originals: list[tuple[object, str, object]] = []

    def patch(owner: object, attribute: str, replacement: object) -> None:
        originals.append((owner, attribute, getattr(owner, attribute)))
        setattr(owner, attribute, replacement)

    # Time the large, meaningful sections of each frame.
    patch(
        simulation,
        "update_particles",
        timed("Physics: update_particles", simulation.update_particles),
    )
    patch(
        density_field.DensityField,
        "rebuild",
        timed("Density: rebuild", density_field.DensityField.rebuild),
    )

    if hasattr(renderer, "render_density_field"):
        patch(
            renderer,
            "render_density_field",
            timed("Render: density field", renderer.render_density_field),
        )

    if hasattr(renderer, "render_particles"):
        patch(
            renderer,
            "render_particles",
            timed("Render: particles", renderer.render_particles),
        )

    # These nested timings explain the main physics result. They are not
    # included when adding the primary subsystem totals because they overlap.
    patch(
        simulation,
        "_apply_particle_interactions",
        timed(
            "  Physics detail: particle interactions",
            simulation._apply_particle_interactions,
        ),
    )
    patch(
        simulation,
        "_handle_reproduction",
        timed(
            "  Physics detail: reproduction",
            simulation._handle_reproduction,
        ),
    )
    patch(
        spatial_grid.SpatialGrid,
        "rebuild",
        timed(
            "  Physics detail: spatial-grid rebuild",
            spatial_grid.SpatialGrid.rebuild,
        ),
    )

    original_create_brush_particle = brushes.create_brush_particle

    @functools.wraps(original_create_brush_particle)
    def controlled_create_brush_particle(*args, **kwargs):
        particle = original_create_brush_particle(*args, **kwargs)
        state.created_particles += 1
        return particle

    patch(
        brushes,
        "create_brush_particle",
        controlled_create_brush_particle,
    )

    class DeterministicClock:
        """Replacement for pygame.time.Clock which never deliberately waits."""

        def tick(self, _framerate: int = 0) -> float:
            return 1000.0 / SIMULATED_FPS

    patch(pygame.time, "Clock", DeterministicClock)

    original_event_get = pygame.event.get

    def controlled_event_get(*args, **kwargs):
        # Allow the window close button to abort the test, but discard other
        # input so each run receives the same controls.
        real_events = original_event_get(*args, **kwargs)
        quit_events = [
            event
            for event in real_events
            if event.type == pygame.QUIT
        ]

        if quit_events:
            state.closed_early = not state.finished
            return quit_events

        if state.finished:
            return [pygame.event.Event(pygame.QUIT)]

        return []

    patch(
        pygame.event,
        "get",
        timed("Pygame: event collection", controlled_event_get),
    )

    patch(pygame.mouse, "get_pos", lambda: SPAWN_POSITION)

    def controlled_get_pressed(*_args, **_kwargs):
        spawning = state.created_particles < TARGET_BRUSH_PARTICLES
        return spawning, False, False

    patch(pygame.mouse, "get_pressed", controlled_get_pressed)

    original_display_flip = pygame.display.flip

    def controlled_display_flip() -> None:
        should_record = recording_is_active()

        if should_record:
            started_at = perf_counter()

        original_display_flip()

        if should_record:
            state.timings["Pygame: display flip"] += (
                perf_counter() - started_at
            )
            state.calls["Pygame: display flip"] += 1

        if state.created_particles < TARGET_BRUSH_PARTICLES:
            return

        if not state.profiling and not state.finished:
            state.warmup_frames += 1

            if state.warmup_frames >= WARMUP_FRAMES:
                state.measurement_started_at = perf_counter()
                state.profiling = True
                profiler.enable()

            return

        if state.profiling:
            state.measured_frames += 1

            if state.measured_frames >= MEASURED_FRAMES:
                profiler.disable()
                state.profiling = False
                state.measurement_finished_at = perf_counter()
                state.finished = True

    patch(pygame.display, "flip", controlled_display_flip)

    random.seed(RANDOM_SEED)

    try:
        return runpy.run_path(str(main_path), run_name="__main__")
    finally:
        if state.profiling:
            profiler.disable()
            state.profiling = False
            state.measurement_finished_at = perf_counter()

        for owner, attribute, original in reversed(originals):
            setattr(owner, attribute, original)

        if sys.path and sys.path[0] == str(project_directory):
            sys.path.pop(0)


# =====================================================================
# REPORTING
# =====================================================================

def milliseconds(seconds: float) -> float:
    return seconds * 1000.0


def print_primary_summary(total_seconds: float) -> None:
    print()
    print("Primary frame costs")
    print("=" * 86)
    print(
        f"{'Section':<35}"
        f"{'Calls':>10}"
        f"{'Total':>13}"
        f"{'Per call':>14}"
        f"{'Share':>12}"
    )
    print("-" * 86)

    primary_labels = [
        "Physics: update_particles",
        "Density: rebuild",
        "Render: density field",
        "Render: particles",
        "Pygame: display flip",
        "Pygame: event collection",
    ]

    for label in primary_labels:
        calls = state.calls.get(label, 0)
        seconds = state.timings.get(label, 0.0)
        per_call_ms = milliseconds(seconds / calls) if calls else 0.0
        share = 100.0 * seconds / total_seconds if total_seconds else 0.0

        print(
            f"{label:<35}"
            f"{calls:>10,}"
            f"{milliseconds(seconds):>11.2f} ms"
            f"{per_call_ms:>11.3f} ms"
            f"{share:>10.1f}%"
        )


def print_physics_detail(total_seconds: float) -> None:
    print()
    print("Inside the physics update")
    print("=" * 86)

    detail_labels = [
        "  Physics detail: particle interactions",
        "  Physics detail: spatial-grid rebuild",
        "  Physics detail: reproduction",
    ]

    for label in detail_labels:
        calls = state.calls.get(label, 0)
        seconds = state.timings.get(label, 0.0)
        per_call_ms = milliseconds(seconds / calls) if calls else 0.0
        share = 100.0 * seconds / total_seconds if total_seconds else 0.0

        print(
            f"{label.strip():<43}"
            f"{calls:>8,} calls"
            f"{milliseconds(seconds):>12.2f} ms total"
            f"{per_call_ms:>10.3f} ms/call"
            f"{share:>8.1f}%"
        )

    print()
    print(
        "These detail rows overlap with update_particles and must not be "
        "added to the primary costs."
    )


def project_function_rows(project_directory: Path) -> list[dict]:
    statistics = pstats.Stats(profiler)
    rows = []

    for key, values in statistics.stats.items():
        filename, line_number, function_name = key
        primitive_calls, total_calls, self_time, cumulative_time, _ = values
        resolved_filename = None

        try:
            resolved_filename = Path(filename).resolve()
            is_project_file = (
                resolved_filename == project_directory
                or project_directory in resolved_filename.parents
            )
        except (OSError, RuntimeError):
            is_project_file = False

        if (
            not is_project_file
            or resolved_filename == Path(__file__).resolve()
        ):
            continue

        if function_name in {"<module>", "wrapper"}:
            continue

        rows.append(
            {
                "filename": Path(filename).name,
                "line": line_number,
                "function": function_name,
                "calls": total_calls,
                "primitive_calls": primitive_calls,
                "self_time": self_time,
                "cumulative_time": cumulative_time,
            }
        )

    return rows


def print_hot_functions(
    project_directory: Path,
    total_seconds: float,
) -> None:
    rows = project_function_rows(project_directory)

    print()
    print("Hottest project functions by direct work")
    print("=" * 106)
    print(
        f"{'Function':<51}"
        f"{'Calls':>12}"
        f"{'Direct':>14}"
        f"{'Cumulative':>16}"
        f"{'Direct share':>13}"
    )
    print("-" * 106)

    for row in sorted(
        rows,
        key=lambda item: item["self_time"],
        reverse=True,
    )[:NUMBER_OF_HOT_FUNCTIONS]:
        location = (
            f"{row['filename']}:{row['line']} "
            f"{row['function']}"
        )
        share = (
            100.0 * row["self_time"] / total_seconds
            if total_seconds
            else 0.0
        )

        print(
            f"{location:<51}"
            f"{row['calls']:>12,}"
            f"{milliseconds(row['self_time']):>12.2f} ms"
            f"{milliseconds(row['cumulative_time']):>14.2f} ms"
            f"{share:>11.1f}%"
        )


def print_conclusion(total_seconds: float) -> None:
    candidates = {
        label: seconds
        for label, seconds in state.timings.items()
        if not label.startswith("  ")
    }

    if not candidates:
        return

    largest_label, largest_seconds = max(
        candidates.items(),
        key=lambda item: item[1],
    )

    print()
    print("Simple conclusion")
    print("=" * 86)
    print(
        f"The largest measured top-level cost was {largest_label}, taking "
        f"{100.0 * largest_seconds / total_seconds:.1f}% of measured time."
    )

    physics = state.timings.get("Physics: update_particles", 0.0)
    density = (
        state.timings.get("Density: rebuild", 0.0)
        + state.timings.get("Render: density field", 0.0)
    )

    if physics or density:
        if physics > density:
            ratio = physics / density if density else float("inf")
            print(
                f"Physics cost {ratio:.2f} times as much as the complete "
                "density rebuild-and-render path."
            )
        else:
            ratio = density / physics if physics else float("inf")
            print(
                f"The complete density rebuild-and-render path cost "
                f"{ratio:.2f} times as much as physics."
            )

    print(
        "Use the direct-work table to choose the first individual function "
        "to inspect. Cumulative rows include functions called underneath them."
    )
    print(
        "Because cProfile instruments every function call, absolute timings "
        "are slower than normal play. Comparisons between identical runs and "
        "the ranking of costs are the useful results."
    )


def print_report(main_path: Path, main_globals: dict) -> None:
    if state.measurement_finished_at > state.measurement_started_at:
        total_seconds = (
            state.measurement_finished_at
            - state.measurement_started_at
        )
    else:
        total_seconds = 0.0

    particles = main_globals.get("particles")
    final_particle_count = (
        len(particles)
        if isinstance(particles, list)
        else "unknown"
    )

    print()
    print("Living Paint controlled main.py profile")
    print("=" * 86)
    print(f"Main file:             {main_path}")
    print(f"Random seed:           {RANDOM_SEED}")
    print(f"Requested particles:   {TARGET_BRUSH_PARTICLES}")
    print(f"Brush particles made:  {state.created_particles}")
    print(f"Final particle count:  {final_particle_count}")
    print(f"Simulated frame rate:  {SIMULATED_FPS} Hz")
    print(f"Warm-up frames:        {state.warmup_frames}")
    print(f"Measured frames:       {state.measured_frames}")
    print(f"Measured wall time:    {total_seconds:.3f} s")

    if state.closed_early or state.measured_frames < MEASURED_FRAMES:
        print()
        print(
            "WARNING: The test ended before the complete measurement window, "
            "so do not compare this run directly with a completed run."
        )

    if total_seconds <= 0.0:
        print()
        print("No complete measurement data were collected.")
        return

    print(
        f"Profiled throughput:   "
        f"{state.measured_frames / total_seconds:.1f} frames/s"
    )
    print(
        f"Mean profiled frame:   "
        f"{milliseconds(total_seconds / state.measured_frames):.2f} ms"
    )

    print_primary_summary(total_seconds)
    print_physics_detail(total_seconds)
    print_hot_functions(main_path.parent.resolve(), total_seconds)
    print_conclusion(total_seconds)


# =====================================================================
# MAIN
# =====================================================================

def main() -> None:
    if TARGET_BRUSH_PARTICLES <= 0:
        raise ValueError("TARGET_BRUSH_PARTICLES must be positive.")
    if SIMULATED_FPS <= 0:
        raise ValueError("SIMULATED_FPS must be positive.")
    if WARMUP_FRAMES < 0 or MEASURED_FRAMES <= 0:
        raise ValueError(
            "WARMUP_FRAMES must be non-negative and "
            "MEASURED_FRAMES must be positive."
        )

    main_path = Path(__file__).resolve().with_name(MAIN_FILENAME)

    if not main_path.is_file():
        raise FileNotFoundError(
            f"Could not find {MAIN_FILENAME!r} beside this benchmark script."
        )

    main_globals = run_controlled_main(main_path)
    print_report(main_path, main_globals)


if __name__ == "__main__":
    main()
