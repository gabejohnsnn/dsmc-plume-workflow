#!/usr/bin/env python3
"""
Split the inlet patch into 15 individual patches with spatially varying
properties interpolated from CFD exit plane data.

Run this BEFORE dsmcInitialise+. Delete 0/ first if it exists.
"""

import sys
import os
import csv
import math
import numpy as np
from pathlib import Path

if len(sys.argv) < 3:
    print("Usage: python3 splitInlet.py <case_dir> <csv_file>")
    sys.exit(1)

case_dir = Path(sys.argv[1])
csv_file = sys.argv[2]

kB = 1.381e-23
m_molecule = 3.384e-26  # kg (EqGas)
R_gas = 408.0  # J/kg-K

with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    cfd_rows = list(reader)

cfd_y = np.array([float(r['y-coordinate [m]']) for r in cfd_rows])
cfd_P = np.array([float(r['pressure [Pa]']) for r in cfd_rows])
cfd_T = np.array([float(r['temperature [K]']) for r in cfd_rows])
cfd_rho = np.array([float(r['density [kg/m3]']) for r in cfd_rows])
cfd_Vax = np.array([float(r['axial-velocity [m/s]']) for r in cfd_rows])
cfd_Vrad = np.array([float(r['radial-velocity [m/s]']) for r in cfd_rows])

with open(case_dir / 'constant' / 'polyMesh' / 'points', 'r') as f:
    lines = f.readlines()

points = []
in_block = False
for line in lines:
    s = line.strip()
    if s == '(' and not in_block:
        in_block = True
        continue
    if s == ')' and in_block:
        break
    if in_block:
        coords = s.strip('()').split()
        if len(coords) == 3:
            points.append([float(c) for c in coords])

with open(case_dir / 'constant' / 'polyMesh' / 'faces', 'r') as f:
    lines = f.readlines()

faces = []
in_block = False
for line in lines:
    s = line.strip()
    if s == '(' and not in_block:
        in_block = True
        continue
    if s == ')' and in_block:
        break
    if in_block:
        idx = s.index('(')
        pts = s[idx:].strip('()').split()
        faces.append([int(p) for p in pts])

with open(case_dir / 'constant' / 'polyMesh' / 'boundary', 'r') as f:
    boundary_text = f.read()

inlet_start_face = 117074
n_inlet_faces = 15

face_data = []
for i in range(n_inlet_faces):
    face = faces[inlet_start_face + i]
    ys = [math.sqrt(points[p][1]**2 + points[p][2]**2) for p in face]
    r_center = sum(ys) / len(ys)

    P = float(np.interp(r_center, cfd_y, cfd_P))
    T = float(np.interp(r_center, cfd_y, cfd_T))
    rho = float(np.interp(r_center, cfd_y, cfd_rho))
    Vax = float(np.interp(r_center, cfd_y, cfd_Vax))
    Vrad = float(np.interp(r_center, cfd_y, cfd_Vrad))

    n = P / (kB * T)

    face_data.append({
        'face_index': i,
        'r_mm': r_center * 1000,
        'P': P,
        'T': T,
        'rho': rho,
        'Vax': Vax,
        'Vrad': Vrad,
        'n': n,
    })

    print(f"  inlet_{i:02d}: r={r_center*1000:.2f} mm, "
          f"P={P:.1f} Pa, T={T:.1f} K, n={n:.3e} m-3, "
          f"V=({Vax:.0f}, {Vrad:.0f}, 0) m/s")

# Original patches (minus inlet):
#   wall:   type wall,      nFaces 1,     startFace 117089
#   axis:   type symmetry,  nFaces 300,   startFace 117090
#   outlet: type patch,     nFaces 736,   startFace 117390
#   front:  type wedge,     nFaces 58800, startFace 118126
#   back:   type wedge,     nFaces 58800, startFace 176926
#
# We replace the single "inlet" (15 faces starting at 117074) with
# 15 individual patches of 1 face each.

total_patches = 15 + 5  # 15 inlets + wall + axis + outlet + front + back

boundary_out = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v1706                                 |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       polyBoundaryMesh;
    location    "constant/polyMesh";
    object      boundary;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
{total_patches}
(
"""

# Add 15 inlet patches
for i in range(n_inlet_faces):
    boundary_out += f"""    inlet_{i:02d}
    {{
        type            patch;
        nFaces          1;
        startFace       {inlet_start_face + i};
    }}
"""

# Add remaining patches (unchanged)
boundary_out += """    wall
    {
        type            wall;
        inGroups        1(wall);
        nFaces          1;
        startFace       117089;
    }
    axis
    {
        type            symmetry;
        inGroups        1(symmetry);
        nFaces          300;
        startFace       117090;
    }
    outlet
    {
        type            patch;
        nFaces          736;
        startFace       117390;
    }
    front
    {
        type            wedge;
        nFaces          58800;
        startFace       118126;
    }
    back
    {
        type            wedge;
        nFaces          58800;
        startFace       176926;
    }
)
// ************************************************************************* //
"""

# Backup and write
import shutil
boundary_path = case_dir / 'constant' / 'polyMesh' / 'boundary'
shutil.copy2(boundary_path, str(boundary_path) + '.bak_pre_split')
with open(boundary_path, 'w') as f:
    f.write(boundary_out)
print(f"\nWrote {boundary_path}")

# === Generate boundariesDict ===
boundaries_dict = """/*---------------------------------------------------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v1706                                 |
|   \\\\  /    A nd           | Web:      http://www.openfoam.org               |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      boundariesDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
dsmcPatchBoundaries
(
"""

# Wall
boundaries_dict += """    boundary
    {
        patchBoundaryProperties
        {
            patchName   wall;
        }
        boundaryModel   dsmcDiffuseWallPatch;
        dsmcDiffuseWallPatchProperties
        {
            temperature       300;
            velocity          (0 0 0);
        }
    }
"""

# Outlet
boundaries_dict += """    boundary
    {
        patchBoundaryProperties
        {
            patchName   outlet;
        }
        boundaryModel   dsmcDeletionPatch;
        dsmcDeletionPatchProperties
        {
            allSpecies  yes;
        }
    }
"""

# 15 inlet deletion patches (needed for patch count matching)
for i in range(n_inlet_faces):
    boundaries_dict += f"""    boundary
    {{
        patchBoundaryProperties
        {{
            patchName   inlet_{i:02d};
        }}
        boundaryModel   dsmcDeletionPatch;
        dsmcDeletionPatchProperties
        {{
            allSpecies  yes;
        }}
    }}
"""

boundaries_dict += """);
dsmcCyclicBoundaries
(
);
dsmcGeneralBoundaries
(
"""

# 15 inlet freestream inflow patches
for i in range(n_inlet_faces):
    fd = face_data[i]
    boundaries_dict += f"""    boundary
    {{
        generalBoundaryProperties
        {{
            patchName   inlet_{i:02d};
        }}
        boundaryModel   dsmcFreeStreamInflowPatch;
        dsmcFreeStreamInflowPatchProperties
        {{
            typeIds                     (EqGas);
            translationalTemperature    {fd['T']:.1f};
            velocity                    ({fd['Vax']:.1f} {fd['Vrad']:.1f} 0);
            numberDensities
            {{
                EqGas   {fd['n']:.4e};
            }}
        }}
    }}
"""

boundaries_dict += """);
// ************************************************************************* //
"""

boundaries_path = case_dir / 'system' / 'boundariesDict'
shutil.copy2(boundaries_path, str(boundaries_path) + '.bak_pre_split')
with open(boundaries_path, 'w') as f:
    f.write(boundaries_dict)
print(f"Wrote {boundaries_path}")

print(f"\nDone! Now run:")
print(f"  rm -rf 0/")
print(f"  dsmcInitialise+")
print(f"  dsmcFoam+ > log.dsmcFoam 2>&1 &")
