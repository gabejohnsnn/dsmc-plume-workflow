#!/usr/bin/env python3

import sys
import math
import shutil

half_angle_deg = 2.5
half_angle_rad = math.radians(half_angle_deg)
cos_a = math.cos(half_angle_rad)
sin_a = math.sin(half_angle_rad)

if len(sys.argv) < 2:
    print("Usage: python3 rotatePoints.py <path_to_points_file>")
    sys.exit(1)

points_file = sys.argv[1]

# Backup original
shutil.copy2(points_file, points_file + ".bak")
print(f"Backup saved to {points_file}.bak")

with open(points_file, "r") as f:
    lines = f.readlines()

# Find the start of the points list (line with just a number = point count)
# then the opening '(' and closing ')'
header_lines = []
point_count = None
points_start = None
points_end = None

i = 0
# Read past the FoamFile header
while i < len(lines):
    stripped = lines[i].strip()
    # Look for the point count (a line that's just an integer)
    if point_count is None:
        try:
            point_count = int(stripped)
            header_lines.append(lines[i])
            i += 1
            # Next line should be '('
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

# Find closing ')'
points_end = None
for j in range(points_start, len(lines)):
    if lines[j].strip() == ')':
        points_end = j
        break

# Parse and rotate points
new_point_lines = []
for k in range(points_start, points_end):
    line = lines[k].strip()
    # Remove parentheses
    inner = line.strip('()')
    parts = inner.split()
    if len(parts) != 3:
        new_point_lines.append(lines[k])
        continue

    x = float(parts[0])
    y = float(parts[1])  # radial coordinate
    z = float(parts[2])

    if z > 0:
        new_y = y * cos_a
        new_z = y * sin_a
    elif z < 0:
        new_y = y * cos_a
        new_z = -y * sin_a
    else:
        new_y = y
        new_z = 0.0

    new_point_lines.append(f"({x} {new_y} {new_z})\n")

# Write output
with open(points_file, "w") as f:
    # Write header
    for line in header_lines:
        f.write(line)
    # Write rotated points
    for line in new_point_lines:
        f.write(line)
    # Write closing ')' and any footer
    for line in lines[points_end:]:
        f.write(line)

print(f"Rotated {point_count} points by +/-{half_angle_deg} degrees.")
print("Done. Run checkMesh to verify.")
