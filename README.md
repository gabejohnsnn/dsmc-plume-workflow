# dsmcFoam+ Axisymmetric Plume Simulation Workflow

This is a complete workflow for running DSMC plume simulations using **dsmcFoam+** (hyStrath framework, OpenFOAM v1706) on Windows via Docker. It includes tools for converting 2D ANSYS meshes to OpenFOAM axisymmetric wedge format and configuring dsmcFoam+ case files.

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
# Pull the hyStrath Docker image
docker pull gabejohnsnn/dsmc-hystrath:v1706

# Clone this repo
git clone https://github.com/gabejohnsnn/dsmc-plume-workflow.git

# Start a container with the repo mounted
docker run -it --name dsmc_work \
  -v /path/to/dsmc-plume-workflow:/home/openfoam/cases \
  gabejohnsnn/dsmc-hystrath:v1706

# Source OpenFOAM
source /opt/OpenFOAM/setImage_v1706.sh

# Check the container has been mounted
# These should return file paths like: /root/OpenFOAM/-v1706/platforms/linux64GccDPInt32Opt/bin/dsmcFoam+
which dsmcFoam+
which dsmcInitialise+

# Inside the container
cd /home/openfoam/cases
```

---

### Re-entering an existing container
 
`docker run` with `--name dsmc_work` is a one-time command. After the first session, use the commands below to get back into the same container (which preserves your shell history, sourced environment, any files you created outside the mount, and any background `dsmcFoam+` processes).
 
**Check container state first:**
 
```bash
# Lists ALL containers (running + stopped). Look for dsmc_work and check STATUS.
docker ps -a
```
 
**If the container is running** (`STATUS` shows `Up X minutes`):
 
```bash
docker exec -it dsmc_work bash
 
source /opt/OpenFOAM/setImage_v1706.sh
cd /home/openfoam/cases
```
 
**If the container is stopped** (`STATUS` shows `Exited (...)`):
 
```bash
docker start dsmc_work
docker exec -it dsmc_work bash
source /opt/OpenFOAM/setImage_v1706.sh
cd /home/openfoam/cases
```

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
```

For the next two scripts, create a new terminal and enter the case directory
```bash
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

Create `case.foam` (empty file) and open in ParaView.
```bash
touch case.foam
```

---

## Spatially Varying Inlet Conditions

The `splitInlet.py` script can split your inlet patch into per-face zones with interpolated properties:

```bash
python3 ../scripts/splitInlet.py . /path/to/CFD-output.csv
rm -rf 0/
dsmcInitialise+
dsmcFoam+
```

The CSV should have columns: `y-coordinate [m]`, `pressure [Pa]`, `temperature [K]`, `density [kg/m3]`, `axial-velocity [m/s]`, `radial-velocity [m/s]`.

---


## References

- White et al. (2018), "dsmcFoam+: An OpenFOAM based direct simulation Monte Carlo solver," *Computer Physics Communications*, 224, 22-43.
- Bird, G.A. (1994), *Molecular Gas Dynamics and the Direct Simulation of Gas Flows*, Clarendon Press.
- hyStrath documentation: https://hystrath.github.io/
