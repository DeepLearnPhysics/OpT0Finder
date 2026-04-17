# Changelog

## v1.0.0 - 2026-04-17

First tagged release of OpT0Finder for current ICARUS/SBND SPINE workflows.

### Fixed

- Avoided ROOT teardown crashes when OpT0Finder and LArCV are loaded in the same Python process.
- Restored ROOT dictionary autoloading by registering the OpT0Finder include paths at Python package import time.
- Removed Python use of the old `CreatePSetFromFile` entry point in favor of `CreateFMParamsFromFile`.
- Fixed configured `make clean` so it removes generated build artifacts without requiring stale targets.
- Made missing or malformed photon-library files fail with a Python/C++ exception instead of dereferencing a null ROOT `TTree`.
- Updated the suggested ICARUS photon-library CVMFS path to the `v10_06_03` product area.

### Added

- Added configurable QLL chi2 scoring through `Chi2Mode`.
- Added `ChiErrorMin` denominator flooring across chi2 modes, with defaults chosen to preserve existing ICARUS and SBND behavior for current configs.
- Exposed `flashmatch.__version__`.
