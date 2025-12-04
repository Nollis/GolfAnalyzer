import numpy as np
from scipy.spatial.transform import Rotation as R

matrix = np.array([
  [-0.12681294977664948, -0.03936590254306793, 0.9911454319953918], 
  [-0.15554757416248322, -0.9860610961914062, -0.05906570702791214], 
  [0.9796549081802368, -0.16166073083877563, 0.11892211437225342]
])

r = R.from_matrix(matrix)
euler = r.as_euler('xyz', degrees=True)
print(f"Euler XYZ: {euler}")

# Try to find a correction
# Goal: Y axis (col 1) should be pointing UP (0, 1, 0)
# Currently: (-0.04, -0.98, -0.16) -> Pointing DOWN

# If we rotate 180 around X?
# R_x_180 = [[1,0,0],[0,-1,0],[0,0,-1]]
# M_new = R_x_180 @ M
# Col 1 of M_new = R_x_180 @ Col 1_old = [1,0,0; 0,-1,0; 0,0,-1] @ [-0.04, -0.98, -0.16] = [-0.04, 0.98, 0.16] -> UP!

print("Applying 180 deg rotation around X (Global):")
rx_180 = R.from_euler('x', 180, degrees=True).as_matrix()
m_new = rx_180 @ matrix
print(m_new)
print(f"New Euler: {R.from_matrix(m_new).as_euler('xyz', degrees=True)}")

# Check other axes
# Col 0 (Right) was [-0.12, -0.15, 0.98] -> Z
# New Col 0 = [-0.12, 0.15, -0.98] -> -Z
# Col 2 (Forward) was [0.99, -0.06, 0.12] -> X
# New Col 2 = [0.99, 0.06, -0.12] -> X

# So character faces X, Right is -Z, Up is Y.
# This seems plausible for a "side view" golf swing?
