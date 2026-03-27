# 2D Palletization Benchmark App

This repository contains a desktop application for the AI tooling benchmark focused on 2D single-bin palletization. The application is implemented in Python 3.10+ with a PyQt5 GUI, a modular solver layer, JSON import/export support, automated tests, and environment verification scripts.

## Problem Context

The goal is to place as many rectangular item instances as possible inside a single pallet of size `W x H` while:

- preventing item overlap,
- enforcing a minimum inter-item gap `g`,
- keeping all placed items inside the pallet,
- maximizing pallet usage.

The optimization objective is lexicographic:

1. maximize the number of placed items,
2. among equally sized feasible solutions, minimize unused pallet area.

The implemented approach uses a deterministic bottom-left style heuristic with candidate generation from already placed rectangles. It is designed to be robust, understandable, and fast enough for interactive use in the GUI.

## Features

- PyQt5 desktop GUI with pallet input, item table, controls, visualization, and logger
- Validation of invalid geometry, negative values, and impossible item definitions
- Support for multiple item types and optional 90-degree rotation
- JSON import for input data and JSON export for computed layouts
- Visualization of placed items with orientation labels
- System logger panel with timestamps and severity levels
- Modular solver architecture separated from the GUI
- Unit tests for validation and solver behavior

## Project Structure

- `App/` application entry point
- `src/` application logic and algorithms
- `Data/` sample input data
- `Example/` benchmark helper scripts
- `images/` README assets
- `Tests/` automated tests

## JSON Input Format

```json
{
  "bin": {
    "width": 1200,
    "height": 800,
    "gap": 20
  },
  "items": [
    {
      "name": "Box A",
      "width": 300,
      "height": 200,
      "quantity": 4,
      "can_rotate": true
    }
  ]
}
```

## Installation

### Windows

```bat
install.bat
```

### Linux / macOS

```bash
bash install.sh
```

The installation scripts now:

- check whether Python is installed and whether its version is at least 3.10,
- check whether Conda / Anaconda is installed,
- attempt to install Miniconda automatically when Conda is missing,
- create a dedicated Conda environment with Python 3.11,
- install all required project dependencies,
- prepare the project for immediate execution.

## Run

If you used the provided installation scripts:

```bat
conda run -n palletizer-benchmark python App/main.py
```

If you already manage your own environment:

```bat
python -m pip install PyQt5 pytest
python App/main.py
```

## Verification

Run:

```bat
python verify.py
```

The script checks:

- Python version,
- required dependencies,
- importability of the main application modules.

## Tests

Run:

```bat
python -m pytest Tests
```

## Implemented Algorithm

The solver expands the input item types into requested item instances, sorts item types by descending footprint area, and attempts to place each instance using a deterministic candidate search:

1. candidate positions are generated from the origin and from the right/top edges of already placed rectangles,
2. every allowed orientation is tested,
3. only placements that stay inside the pallet and respect the minimum gap are accepted,
4. among feasible positions, the solver picks the lowest and then left-most placement.

This heuristic naturally favors dense packing while remaining simple to inspect and debug.

## Known Limitations

- The solver is heuristic and does not guarantee a global optimum.
- The current visualization highlights placed items; unplaced items are reported numerically and in logs instead of being drawn outside the pallet.
- GUI execution requires PyQt5 to be installed in the active Python environment.

## Screenshot

Add a GUI screenshot to `images/` and reference it here after the application is launched in the prepared environment.
