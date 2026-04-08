#!/usr/bin/env python3
"""
Fix degenerate axis cells in a wedge mesh.

Restores from the .bak file (pre-wedge-rotation flat slab), offsets
any Y=0 points to a small positive value, then re-applies the wedge
rotation to ALL points.

Usage:
    python3 fixAxisPoints2.py <path_to_points_file>

Expects points.bak to exist (created by rotatePoints.py).
"""

import sys
import math
import shutil

half_angle_deg = 2.5
half_angle_rad = math.radians(half_angle_deg)
cos_a = math.cos(half_angle_rad)
sin_a = math.sin(half_angle_rad)

Y_THRESHOLD = 1e-10   # anything below this absolute Y is "on the axis"
Y_OFFSET = 1e-6       # offset to apply (1 micron)

if len(sys.argv) < 2:
    print("Usage: python3 fixAxisPoints2.py <path_to_points_file>")
    sys.exit(1)

points_file = sys.argv[1]
bak_file = points_file + ".bak"

# Read from the ORIGINAL pre-rotation backup
try:
    with open(bak_file, "r") as f:
        lines = f.readlines()
    print(f"Reading from backup: {bak_file}")
except FileNotFoundError:
    print(f"ERROR: {bak_file} not found.")
    print("This script needs the pre-rotation backup created by rotatePoints.py")
    sys.exit(1)

# Save current file as another backup
shutil.copy2(points_file, points_file + ".bak3")

# Find the points block
header_lines = []
point_count = None
points_start = None
points_end = None

i = 0
while i < len(lines):
    stripped = lines[i].strip()
    if point_count is None:
        try:
            point_count = int(stripped)
            header_lines.append(lines[i])
            i += 1
            if lines[i].strip() == '(':
                header_lines.append(lines[i])
                i += 1
                points_start = i
            break
        except ValueError:
            header_lines.append(lines[i])
            i += 1
    else:
        i += 1

for j in range(points_start, len(lines)):
    if lines[j].strip() == ')':
        points_end = j
        break

# Process: offset axis points in the FLAT slab, then rotate everything
fixed_count = 0
new_point_lines = []

for k in range(points_start, points_end):
    line = lines[k].strip()
    inner = line.strip('()')
    parts = inner.split()
    if len(parts) != 3:
        new_point_lines.append(lines[k])
        continue

    x = float(parts[0])
    y = float(parts[1])  # radial coordinate in flat slab
    z = float(parts[2])  # thin direction in flat slab

    # Fix axis points: offset Y (radial) from 0 to small value
    if abs(y) < Y_THRESHOLD:
        y = Y_OFFSET
        fixed_count += 1

    # Now apply wedge rotation (same logic as rotatePoints.py)
    if z > 0:
        new_y = y * cos_a
        new_z = y * sin_a
    elif z < 0:
        new_y = y * cos_a
        new_z = -y * sin_a
    else:
        # z == 0 shouldn't happen in the slab, but handle it
        new_y = y
        new_z = 0.0

    new_point_lines.append(f"({x} {new_y} {new_z})\n")

# Write output
with open(points_file, "w") as f:
    for line in header_lines:
        f.write(line)
    for line in new_point_lines:
        f.write(line)
    for line in lines[points_end:]:
        f.write(line)

print(f"Fixed {fixed_count} axis points (offset Y from 0 to {Y_OFFSET} m)")
print(f"Re-applied wedge rotation (+/-{half_angle_deg} deg) to all {point_count} points")
print("Run checkMesh to verify, then rm -rf 0/ && dsmcInitialise+")
