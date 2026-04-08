#!/bin/bash
#SBATCH --partition="general" 
#SBATCH --constraint="ib"
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=24:00:00
#SBATCH --mem-per-cpu=32G
#SBATCH --job-name=dsmcPlume
#SBATCH --output=output.dat
#SBATCH --error=log.err
#SBATCH --mail-type=ALL
#SBATCH --mail-user=gjohns17@uvm.edu

# 1. Load modules
module purge
module load gcc/13.3.0-xp3epyt
module load apptainer
module load openmpi/5.0.5-ib

# 2. Path Definitions
SIF_IMG="/users/g/j/gjohns17/dsmc_v3.sif"
CASE_DIR="/users/g/j/gjohns17/OpenFOAM_Runs/benchmarkPlumeCase1"
CUSTOM_BIN_DIR="/opt/openfoam_custom/platforms/linux64GccDPInt32Opt/bin"
CUSTOM_LIB_DIR="/opt/openfoam_custom/platforms/linux64GccDPInt32Opt/lib"

# Environment Setup
SETUP_ENV="source /opt/OpenFOAM/setImage_v1706.sh && export LD_LIBRARY_PATH=$CUSTOM_LIB_DIR:\$LD_LIBRARY_PATH"

# Apptainer Command Prefix
APPT="apptainer exec --bind $PWD:/home/openfoam $SIF_IMG bash -c"

cd $CASE_DIR

# 3. Clean previous results
echo "Cleaning case..."
rm -rf processor*
rm -rf postProcessing
rm -f log.*
rm -rf 0/
find . -maxdepth 1 -type d -regextype posix-egrep -regex './[0-9]+(\.[0-9]+)?' -exec rm -rf {} +
find . -maxdepth 1 -type d -name '*e-*' -exec rm -rf {} +

# 4. Initialize particles
echo "Running dsmcInitialise+..."
$APPT "$SETUP_ENV && $CUSTOM_BIN_DIR/dsmcInitialise+" > log.dsmcInitialise 2>&1

# 5. Run solver (serial)
echo "Running dsmcFoam+ (serial)..."
$APPT "$SETUP_ENV && $CUSTOM_BIN_DIR/dsmcFoam+" > log.dsmcFoam 2>&1

echo "Job Finished."
