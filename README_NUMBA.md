# Living Paint Numba rewrite

This version keeps the existing particle, species, brush and reproduction interfaces while moving the expensive numerical work into compiled array kernels.

## Install

From the project directory:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

```powershell
.\.venv\Scripts\python.exe main.py
```

The first run takes longer when each Numba kernel is compiled. Later runs reuse the on-disk cache.

## Benchmark

Run the controlled whole-application profile:

```powershell
.\.venv\Scripts\python.exe measure_main_performance.py
```

Run it twice after installing the rewrite. Treat the first run as compilation and cache warm-up, then compare the second run with the previous baseline:

| Measurement | Previous baseline |
|---|---:|
| Mean profiled frame | 19.60 ms |
| Profiled throughput | 51.0 frames/s |
| Physics update | 14.139 ms |
| Particle interactions | 8.793 ms |
| Density rebuild | 13.370 ms |
| Density rendering | 12.065 ms |

The top-level timings remain meaningful. Compiled work appears as time inside the Python wrapper rather than as many individual Python function calls in the direct-work table.

## Architecture

- `numba_kernels.py` contains the compiled interaction and density kernels.
- `simulation.py` converts the current particle state to typed arrays, runs the interaction kernel, then copies acceleration and energy back to the particle objects.
- The compiled interaction kernel builds a compact contiguous spatial grid internally.
- `spatial_grid.py` remains responsible for reproduction queries and debugging overlays.
- `density_field.py` stores density and colour data in NumPy arrays and rebuilds them with one compiled kernel call.
- `renderer.py` creates the complete RGB grid with NumPy and transfers it to Pygame in bulk.

This is a CPU Numba implementation. It deliberately does not use CUDA because the current 1,000-particle workload is small enough that GPU transfer and launch overhead could outweigh the calculation.
