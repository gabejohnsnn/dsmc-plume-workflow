# dsmcFoam+ Axisymmetric Plume Simulation Workflow

Complete workflow for running DSMC plume simulations using **dsmcFoam+** (hyStrath framework, OpenFOAM v1706) on Windows via Docker.

Includes tools for converting 2D ANSYS meshes to OpenFOAM axisymmetric wedge format, configuring dsmcFoam+ case files, and running on the UVM VACC cluster.

Developed at the University of Vermont, Department of Mechanical Engineering.

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac)
- [ParaView](https://www.paraview.org/download/) (for visualization)
- Python 3 (for mesh conversion scripts)
- A 2D mesh exported from ANSYS as a Fluent `.msh` file

> **Why Docker?** dsmcFoam+ lives in the hyStrath repository and must be compiled on top of OpenFOAM v1706. The native Windows OpenFOAM installer doesn't support code compilation, so a pre-built Docker/Apptainer image is the simplest path.

### Setup

```bash
# 1. Pull the hyStrath Docker image
docker pull hystrath/hystrath-1706:latest

# 2. Clone this repo
git clone https://github.com/YOUR_USERNAME/dsmc-plume-workflow.git

# 3. Start a container with the repo mounted
docker run -it --name dsmc_work \
  -v /path/to/dsmc-plume-workflow:/home/openfoam/cases \
  hystrath/hystrath-1706:latest

# 4. Inside the container
cd /home/openfoam/cases
```

---

## Workflow

### Step 1: Import ANSYS Mesh

```bash
cd your-case-directory
fluentMeshToFoam your_mesh.msh
checkMesh
```

### Step 2: Convert to Axisymmetric Wedge

```bash
# Split front/back faces by normal direction
cp ../case-template/system/topoSetDict system/
cp ../case-template/system/createPatchDict system/
topoSet
createPatch -overwrite

# Rotate points to ±2.5° wedge
python3 ../scripts/rotatePoints.py constant/polyMesh/points

# Fix degenerate axis cells
python3 ../scripts/fixAxisPoints2.py constant/polyMesh/points
```

Then edit `constant/polyMesh/boundary`:
- `front` and `back` → type `wedge`
- `axis` → type `symmetry`
- `inlet` → type `patch`
- `outlet` → type `patch`
- `wall` → type `wall`

```bash
checkMesh
```

### Step 3: Configure Case Files

Copy the template case files and edit for your conditions:

```bash
cp ../case-template/constant/dsmcProperties constant/
cp ../case-template/constant/dynamicMeshDict constant/
cp ../case-template/system/controlDict system/
cp ../case-template/system/boundariesDict system/
cp ../case-template/system/dsmcInitialiseDict system/
cp ../case-template/system/fieldPropertiesDict system/
cp ../case-template/system/fvSchemes system/
cp ../case-template/system/fvSolution system/
cp ../case-template/system/controllersDict system/
```

Key files to edit:
- **`constant/dsmcProperties`** — species properties (mass, diameter, omega), `nEquivalentParticles`
- **`system/boundariesDict`** — inlet conditions (number density, temperature, velocity), wall temperature
- **`system/dsmcInitialiseDict`** — background initialization conditions
- **`system/controlDict`** — time step (`deltaT`), end time, write interval

### Step 4: Run

```bash
dsmcInitialise+
dsmcFoam+ > log.dsmcFoam 2>&1 &
tail -f log.dsmcFoam
```

### Step 5: Visualize

Create `case.foam` (empty file) and open in ParaView. Recommended fields:
- `rhoN_EqGas` (number density) — use log scale
- `Ttra_EqGas` (translational temperature)
- `Ma_EqGas` (Mach number)
- `U_EqGas` (velocity)

---

## Spatially Varying Inlet Conditions

If you have CFD exit plane data (e.g., from a nozzle simulation), the `splitInlet.py` script can split your inlet patch into per-face zones with interpolated properties:

```bash
python3 ../scripts/splitInlet.py . /path/to/CFD-output.csv
rm -rf 0/
dsmcInitialise+
dsmcFoam+
```

The CSV should have columns: `y-coordinate [m]`, `pressure [Pa]`, `temperature [K]`, `density [kg/m3]`, `axial-velocity [m/s]`, `radial-velocity [m/s]`.

---

## Running on UVM VACC

See `scripts/run_dsmc_vacc.sh` for a SLURM submission script using Apptainer.

```bash
scp -r your-case/ netid@vacc-user2.uvm.edu:~/OpenFOAM_Runs/
ssh netid@vacc-user2.uvm.edu
cd ~/OpenFOAM_Runs/your-case
sbatch ../scripts/run_dsmc_vacc.sh
```

---

## Repository Structure

```
dsmc-plume-workflow/
├── README.md
├── case-template/
│   ├── constant/
│   │   ├── dsmcProperties          # Species and collision model
│   │   └── dynamicMeshDict         # AMR settings (static by default)
│   └── system/
│       ├── controlDict             # Time stepping and output
│       ├── boundariesDict          # DSMC boundary conditions
│       ├── dsmcInitialiseDict      # Initial particle distribution
│       ├── fieldPropertiesDict     # Macroscopic field sampling
│       ├── fvSchemes               # All "none" for DSMC
│       ├── fvSolution              # Empty for DSMC
│       ├── controllersDict         # Empty (no controllers)
│       ├── topoSetDict             # Face set splitting by normal
│       └── createPatchDict         # Patch creation from face sets
├── scripts/
│   ├── rotatePoints.py             # Rotate slab mesh to ±2.5° wedge
│   ├── fixAxisPoints2.py           # Fix degenerate axis cells
│   ├── splitInlet.py               # Split inlet for spatially varying BCs
│   └── run_dsmc_vacc.sh            # SLURM script for UVM VACC
└── docs/
    └── dsmcFoam_Windows_Guide.docx # Comprehensive setup guide
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| Wedge patch is not planar | Wedge type set before rotating points | Set patches as `patch` first, rotate, then change to `wedge` |
| Poly-patch count mismatch | `dsmcPatchBoundaries` count ≠ non-empty/non-wedge/non-symmetry patches | Count patches with `grep type constant/polyMesh/boundary` and match |
| Cannot find patchField entry | Stale `0/` directory from previous mesh | `rm -rf 0/` then `dsmcInitialise+` |
| Segfault during particle tracking | Degenerate axis cells or missing patch handler | Run `fixAxisPoints2.py`; ensure all patches have boundary models |
| No particles created | `nEquivalentParticles` too large for background density | Decrease `nEquivalentParticles` or increase initialization density |
| Stuck on "Starting time loop" | Zero particles or very slow timestep | Check `0/lagrangian/dsmcCloud/` exists; check CPU usage with `top` |

---

## References

- White et al. (2018), "dsmcFoam+: An OpenFOAM based direct simulation Monte Carlo solver," *Computer Physics Communications*, 224, 22-43.
- Bird, G.A. (1994), *Molecular Gas Dynamics and the Direct Simulation of Gas Flows*, Clarendon Press.
- hyStrath documentation: https://hystrath.github.io/
