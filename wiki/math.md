# Mathematics in the Spore Engine

This document covers the mathematical concepts powering the Spore Engine, organized by subsystem.

---

## 1. Vector & Matrix Mathematics

### Vec2 (2D Vector) — `spore_engine/core/geom.py`

Used for 2D physics, screen coordinates, ray casting, and flow fields.

| Operation | Formula | Use |
|-----------|---------|-----|
| Addition | $(x_1+x_2,\; y_1+y_2)$ | Position translation |
| Dot product | $x_1x_2 + y_1y_2$ | Projection, lighting, angle between vectors |
| Cross product (2D) | $x_1y_2 - y_1x_2$ | Signed area, winding direction |
| Length | $\sqrt{x^2 + y^2}$ | Distance, normalization |
| Normalization | $v / \|v\|$ | Unit direction vectors |

### Vec3 (3D Vector) — `spore_engine/core/geom.py`

Used for 3D rendering, ray tracing, and camera math.

Key addition over Vec2:

**3D Cross product:**
$$
a \times b = (a_y b_z - a_z b_y,\;
             a_z b_x - a_x b_z,\;
             a_x b_y - a_y b_x)
$$

The cross product produces a vector perpendicular to both inputs (right-hand rule). Used for:
- Computing surface normals for lighting
- Building camera basis vectors (right, up, forward)
- Torque calculations in physics

### Mat4 (4×4 Homogeneous Matrix) — `spore_engine/core/geom.py`

Allows translation, rotation, scale, and perspective projection in a single unified representation.

**Matrix Multiplication:** $(C)_{ij} = \sum_k A_{ik} \cdot B_{kj}$

**Why 4×4 for 3D?** Homogeneous coordinates let us encode translation (which is an affine, not linear, transformation) as matrix multiplication. A 3D point $(x,y,z)$ is represented as $(x,y,z,1)$, and translation becomes:

$$
\begin{bmatrix}
1 & 0 & 0 & t_x \\
0 & 1 & 0 & t_y \\
0 & 0 & 1 & t_z \\
0 & 0 & 0 & 1
\end{bmatrix}
\begin{bmatrix} x \\ y \\ z \\ 1 \end{bmatrix}
=
\begin{bmatrix} x + t_x \\ y + t_y \\ z + t_z \\ 1 \end{bmatrix}
$$

**Perspective Projection Matrix:**
$$
\begin{bmatrix}
f/\text{aspect} & 0 & 0 & 0 \\
0 & f & 0 & 0 \\
0 & 0 & (F+N)/(N-F) & 2FN/(N-F) \\
0 & 0 & -1 & 0
\end{bmatrix}
$$
where $f = 1/\tan(\text{FOV}/2)$. This maps the view frustum to a unit cube (clip space). After the perspective divide $(x/w,\; y/w,\; z/w)$, points are in Normalized Device Coordinates.

**Look-At Matrix (UVN Camera):**
$$
\begin{aligned}
\text{forward} &= \text{normalize}(\text{target} - \text{eye}) \\
\text{side} &= \text{normalize}(\text{forward} \times \text{up}) \\
\text{up}' &= \text{side} \times \text{forward}
\end{aligned}
$$
The resulting matrix transforms world-space coordinates to camera-relative coordinates.

---

## 2. Color Mathematics — `spore_engine/core/color.py`

### Luminance
$$
L = 0.299R + 0.587G + 0.114B
$$
The coefficients approximate human photopic vision — green contributes most to perceived brightness, blue least. Used for converting color to grayscale and for shade character selection.

### HSV → RGB Conversion
The HSV cylinder is sliced into 6 sectors (each 60°). Within each sector, one of the RGB components is constant, one varies linearly, and one is the value:
$$
\begin{aligned}
i &= \lfloor h \times 6 \rfloor,\; f = h \times 6 - i \\
p &= v \times (1 - s) \\
q &= v \times (1 - f \times s) \\
t &= v \times (1 - (1 - f) \times s)
\end{aligned}
$$
Sector 0: $(v, t, p)$, Sector 1: $(q, v, p)$, etc.

### Linear Interpolation (Lerp)
$$
\text{lerp}(a, b, t) = a + (b - a) \times t
$$
Component-wise on RGB channels. $t \in [0, 1]$. Used for color blending, gradients, and transitions.

### ANSI 256-Color Approximation
Quantizes each RGB channel to 6 levels (0, 51, 102, 153, 204, 255), then indexes a $6 \times 6 \times 6$ cube: $16 + r \times 36 + g \times 6 + b$. Grayscales (R = G = B) use a separate ramp: $232 + R / 10.2$.

---

## 3. Drawing Algorithms — `spore_engine/core/canvas.py`

### Bresenham Line Algorithm
Selects pixels closest to the ideal line using integer arithmetic:
$$
\begin{aligned}
dx &= |x_2 - x_1|,\; dy = -|y_2 - y_1| \\
err &= dx + dy \\
&\text{loop:} \\
&\quad \text{plot}(x_1, y_1) \\
&\quad \text{if } e_2 \ge dy:\; err += dy,\; x_1 += s_x \\
&\quad \text{if } e_2 \le dx:\; err += dx,\; y_1 += s_y
\end{aligned}
$$
The error accumulator tracks the distance from the ideal line. $dy$ starts negative so the same error term can test against both $dx$ and $dy$.

### Midpoint Circle Algorithm
Uses the implicit circle function $f(x,y) = x^2 + y^2 - r^2$:
$$
\begin{aligned}
d &= 1 - r \quad (\text{initial decision parameter at } (1, r-\tfrac12)) \\
\text{if } d &< 0:\; d += 2x + 3 \quad (\text{next pixel is inside}) \\
\text{else} &: \; d += 2(x-y) + 5,\; y -= 1 \quad (\text{next pixel is outside})
\end{aligned}
$$
Only $\frac18$ of the circle is computed; the rest is mirrored using 8-way symmetry.

### Scanline Triangle/Polygon Fill
Triangles are split at the middle vertex into upper and lower trapezoids. Each scanline fills between the left and right edges using linear interpolation:
$$
t = \frac{i_y - y_1}{y_2 - y_1},\quad x = x_1 + t \times (x_2 - x_1)
$$
General polygons use the even-odd rule: find all edge intersections on a scanline, sort by $x$, and fill between pairs.

### Bezier Curves
$$
B(t) = \sum_{j=0}^{n} \binom{n}{j} \cdot t^{\,j} \cdot (1-t)^{\,n-j} \cdot P_j
$$
where $\binom{n}{j} = \frac{n!}{j! \cdot (n-j)!}$. Quadratic ($n=2$) uses 3 control points, cubic ($n=3$) uses 4. Evaluated at $\text{steps}+1$ evenly-spaced $t$ values.

### Catmull-Rom Splines — `spore_engine/gen/splines.py`

A cubic interpolating spline that passes through all control points (no control-point lattice, unlike Bezier). Given points $P_0, P_1, P_2, P_3$, the segment between $P_1$ and $P_2$ is:

$$
C(t) = \frac12 \begin{bmatrix} 1 & t & t^2 & t^3 \end{bmatrix}
\begin{bmatrix}
0 & 2 & 0 & 0 \\
-1 & 0 & 1 & 0 \\
2 & -5 & 4 & -1 \\
-1 & 3 & -3 & 1
\end{bmatrix}
\begin{bmatrix} P_0 \\ P_1 \\ P_2 \\ P_3 \end{bmatrix}
$$

The tangents at interior points are automatically computed from neighboring points, producing smooth interpolation through every control point.

### Half-Block Rendering (HiResCanvas)
Doubles vertical resolution by mapping two physical pixels (top/bottom) to a single terminal cell using Unicode half-blocks:

| Top | Bottom | Char | FG | BG |
|-----|--------|------|----|----|
| empty | empty | `' '` | — | — |
| filled | empty | `▀` | top | — |
| empty | filled | `▄` | bottom | — |
| filled | filled | `▀` | top | bottom |

---

## 4. 3D Rendering Pipeline — `spore_engine/render3d/engine3d.py`

### Vertex Transformation Pipeline
$$
\text{Model} \;\to\; \text{View} \;\to\; \text{Projection} \;\to\; \text{Perspective Divide} \;\to\; \text{Viewport}
$$
1. **Model transform:** Object-local coords $\to$ world space (rotation, translation, scale via Mat4)
2. **View transform:** World $\to$ camera-relative (via `look_at` matrix)
3. **Projection transform:** Camera $\to$ clip space (via `perspective` matrix)
4. **Perspective divide:** $(x/w,\; y/w,\; z/w) \to$ NDC in $[-1, 1]^3$
5. **Viewport transform:** NDC $\to$ pixel coordinates:
   $s_x = \lfloor (x+1) \times 0.5 \times \text{canvas\_width} \rfloor$ and
   $s_y = \lfloor (1-y) \times 0.5 \times \text{canvas\_height} \rfloor$

### Face Normal Calculation
$$
N = (V_1 - V_0) \times (V_2 - V_0),\qquad N = \frac{N}{\|N\|}
$$
The cross product of two edges gives a perpendicular vector. The winding order (clockwise vs counter-clockwise) determines which direction the normal points.

### Back-Face Culling
$$
\text{if } N \cdot \text{view\_direction} \ge 0:\; \text{skip face}
$$
Faces pointing away from the camera are invisible. Since view-space normals point toward the camera for visible faces, the dot product with $(0,0,1)$ is negative for visible faces.

### Lambertian Lighting
$$
\begin{aligned}
\text{brightness} &= \max(0.2,\; N \cdot L) \\
\text{shaded\_color} &= \text{face\_color} \times \text{brightness}
\end{aligned}
$$
Lambert's cosine law: the perceived brightness varies with the cosine of the angle between the surface normal and the light direction. The 0.2 floor provides ambient fill.

### Painter's Algorithm
Faces are sorted by depth (farthest first) and rendered back-to-front. Closer faces overwrite farther ones. Works for non-intersecting convex objects.

---

## 5. Ray Casting (DDA) — in scene demos

A Wolfenstein-style ray caster using Digital Differential Analysis:

### Per-Column Ray
$$
\begin{aligned}
\text{camera\_x} &= \frac{2x}{\text{screen\_width}} - 1 \\
\text{ray\_dir} &= \text{direction} + \text{camera\_plane} \times \text{camera\_x}
\end{aligned}
$$

### DDA Grid Traversal
$$
\text{delta} = \left|\frac{1}{\text{ray\_dir}}\right| \quad (\text{distance to next grid boundary})
$$
At each step, advance to the nearest grid boundary in $x$ or $y$. The perpendicular distance avoids fisheye:
$$
\text{perp\_dist} = \text{side\_dist} - \text{delta}
$$

### Wall Height
$$
\text{line\_height} = \frac{\text{screen\_height}}{\text{perp\_dist}}
$$

---

## 6. Ray Tracing — `spore_engine/render3d/raytracer.py`

### Sphere Intersection
Solve $|P + tD - C|^2 = r^2$ via quadratic formula:
$$
a = D \cdot D,\quad b = 2D\cdot(P-C),\quad c = |P-C|^2 - r^2
$$
$$
t = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$
The smallest positive $t$ is the visible hit.

### Plane Intersection
$$
t = -\frac{N \cdot P + d}{N \cdot D}
$$
For plane defined by $N \cdot X + d = 0$.

### Phong Lighting
$$
\begin{aligned}
\text{diffuse} &= \max(0,\; N \cdot \hat L) \times \text{power} \times 0.6 \\
\text{specular} &= \max(0,\; N \cdot \hat H)^{32} \times \text{power} \times 0.5 \quad (\text{Blinn-Phong})
\end{aligned}
$$
Where $H = (\hat L + \hat V) / |\hat L + \hat V|$ is the half-vector.

### Reflection
$$
\hat R = \hat D - 2(\hat N \cdot \hat D)\hat N
$$
Recursive with max depth 3. Result blended with surface color by reflectivity.

---

## 7. SDF (Signed Distance Fields) — `spore_engine/render3d/sdf.py`

### Primitive SDFs
$$
\begin{aligned}
\text{Sphere:} &\quad f(p) = |p - c| - r \\
\text{Box:} &\quad f(p) = \max(|p_x| - d_x,\; |p_y| - d_y,\; |p_z| - d_z) \\
\text{Torus:} &\quad f(p) = \big|(\sqrt{p_x^2 + p_z^2} - R,\; p_y)\big| - r \\
\text{Cylinder:} &\quad f(p) = \max(|p_{xz}| - r,\; |p_y| - h) \\
\text{Plane:} &\quad f(p) = p \cdot \hat n - d
\end{aligned}
$$

### CSG Operations
$$
\begin{aligned}
\text{Union:} &\quad \min(a, b) \\
\text{Subtract:} &\quad \max(a, -b) \\
\text{Intersect:} &\quad \max(a, b) \\
\text{Smooth Union:} &\quad \min(a, b) - \text{smoothmin}(a, b, k)
\end{aligned}
$$
Smooth union uses a polynomial blend for rounded transitions between shapes.

### Ray Marching
For each pixel, march a ray from the camera origin:
$$
\begin{aligned}
t &= 0.01 \\
&\text{for step in range(max\_steps):} \\
&\qquad d = \text{scene\_sdf}(\text{origin} + \text{direction} \cdot t) \\
&\qquad \text{if } d < \epsilon:\; \text{hit surface} \\
&\qquad t += d \\
&\qquad \text{if } t > \text{max\_dist}:\; \text{miss}
\end{aligned}
$$

### Normal Estimation
$$
\nabla f(p) = \frac{(f(p+\epsilon\hat x) - f(p-\epsilon\hat x),\; f(p+\epsilon\hat y) - f(p-\epsilon\hat y),\; f(p+\epsilon\hat z) - f(p-\epsilon\hat z))}{2\epsilon}
$$
Numerical gradient via central differences. Used for lighting and reflection.

---

## 8. Procedural Noise — `spore_engine/sim/noise.py`

### Perlin Noise
1. **Permutation table:** 512 shuffled integers for pseudo-random gradient selection
2. **Lattice:** For input $(x,y)$, find containing unit square corners
3. **Fade curve:** $6t^5 - 15t^4 + 10t^3$ — $C^2$ continuous smoothstep
4. **Gradient vectors:** 12 edge-center directions for isotropic noise
5. **Interpolation:** Bilinear of dot products at four corners

### Fractal Brownian Motion (fBm)
$$
\begin{aligned}
&\text{for each octave:} \\
&\qquad \text{value += amplitude} \times \text{noise}(x \times \text{frequency},\; y \times \text{frequency}) \\
&\qquad \text{amplitude} \times= \text{gain } (0.5),\; \text{frequency} \times= \text{lacunarity } (2.0)
\end{aligned}
$$
Layers multiple octaves for natural-looking textures.

### Ridge Noise
$$
n = 1 - |\text{noise}()|,\; \text{then } n^2
$$
Creates sharp valley features for mountain generation.

### Worley Noise (Cellular)
For each point, find distance to nearest random feature point in a $3 \times 3$ cell neighborhood. Produces Voronoi-like cell patterns for organic textures, stone, and water.

---

## 9. Hydraulic Erosion — `spore_engine/gen/erosion.py`

### Droplet Simulation
Each droplet carries water volume $w$ and sediment $s$, moving along the terrain gradient:
$$
\text{gradient} = (h[\text{left}] - h[\text{right}],\; h[\text{up}] - h[\text{down}])
$$

### Sediment Capacity
$$
C = k_c \cdot |\nabla h| \cdot |v|
$$
Where $k_c$ = sediment capacity constant, $\nabla h$ = terrain slope, $v$ = droplet velocity.

### Erosion / Deposition
$$
\begin{aligned}
\text{if sediment} &< C:\; \text{terrain.height} -= \text{erosion\_rate} \cdot \text{speed} \cdot dh \cdot \text{water\_vol} \quad (\text{erode}) \\
\text{else} &: \; \text{terrain.height} += (\text{sediment} - C) \cdot \text{deposit\_rate} \qquad (\text{deposit})
\end{aligned}
$$
Erosion removes material from the current cell; deposition adds it back when the droplet is oversaturated.

### Evaporation
$$
\begin{aligned}
\text{water\_vol} &\times= (1 - \text{evap\_rate}) \\
\text{speed} &= \sqrt{\text{speed}^2 + \text{gravity} \cdot dh}
\end{aligned}
$$
Water volume decreases each step. Droplets with insufficient volume are terminated.

---

## 10. Physics Simulation — `spore_engine/sim/physics.py`

### Semi-Implicit Euler Integration
$$
\begin{aligned}
\text{vel}.y &+= \text{gravity} \times dt \quad (\text{update velocity first}) \\
\text{vel}.x &\times= (1 - \text{friction}) \\
\text{pos} &+= \text{vel} \times dt \quad (\text{then update position})
\end{aligned}
$$
More stable than explicit Euler.

### Impulse-Based Collision
For two overlapping circles:
$$
\begin{aligned}
\text{normal} &= \text{normalize}(B.\text{pos} - A.\text{pos}) \\
\text{overlap} &= A.\text{radius} + B.\text{radius} - \text{dist} \\
j &= -\frac{(1 + e) \times \text{vel\_along\_normal}}{\text{total\_inv\_mass}} \quad (\text{impulse magnitude})
\end{aligned}
$$
Derived from conservation of momentum and coefficient of restitution $e$.

### Hooke's Law (Springs)
$$
F = -k \times x - d \times v
$$
Where $k$ = stiffness, $d$ = damping, $x$ = displacement from rest length, $v$ = relative velocity along spring axis.

### Separating Axis Theorem (SAT)
For convex polygon collision: project both polygons onto each edge normal. If a separating axis exists (zero overlap), no collision. Return minimum overlap axis for resolution.

---

## 11. Soft Body Physics — `spore_engine/sim/softbody.py`

### Pressure Force
$$
P = k_{\text{pressure}} \cdot \left(\frac{A}{A_{\text{rest}}} - 1\right)
$$
Per pressure cell (closed polygon of nodes). The volume (area in 2D) is computed via the shoelace formula. Pressure pushes outward when compressed, inward when expanded, using gradient-based force distribution.

### Link Spring Force
$$
F = -k \cdot (|x| - \text{rest}) - d \cdot (v \cdot \hat x)
$$
Per edge connecting two nodes. $k$ = stiffness, $\text{rest}$ = rest length, $d$ = damping, $v$ = relative velocity. Multiple constraint iterations per frame (typically 3 substeps) maintain stability.

### Node Updates
Semi-implicit Euler with velocity damping:
$$
\begin{aligned}
v &+= \text{gravity} \cdot dt \\
v &\times= (1 - \text{damping} \cdot dt) \\
\text{pos} &+= v \cdot dt
\end{aligned}
$$
Links are resolved via position-based correction ($\alpha = \min(\text{stiffness} \cdot dt,\; 0.25)$) per iteration.

---

## 12. 3D Physics — `spore_engine/sim/physics3d.py`

### Rigid Body Rotation
$$
\begin{aligned}
\text{angular velocity: } &\omega \\
\text{torque: } &\tau = r \times F \\
\text{inertia: } &I = \tfrac12 m r^2 \quad (\text{disc})
\end{aligned}
$$

### Integration
$$
\begin{aligned}
\omega &+= \frac{\tau}{I} \cdot dt \\
\text{angle} &+= \omega \cdot dt
\end{aligned}
$$
Torque is accumulated per frame, then applied. Angular velocity is damped by friction.

### 3D Collision Detection
- **Sphere-Sphere:** $\text{distance} < r_1 + r_2$
- **Box-Box (SAT):** project axes onto each face normal; overlap on all axes = collision
- **Sphere-Box:** closest point on box to sphere center; distance $<$ sphere radius

### Polygon Physics
Convex polygon bodies use SAT for collision, with impulse-based resolution. The moment of inertia is computed from vertex geometry:
$$
I = \sum (x_1^2 + x_1 x_2 + x_2^2 + y_1^2 + y_1 y_2 + y_2^2) \cdot \text{cross}
$$

---

## 13. Steering Behaviors — `spore_engine/sim/steering.py`

### Seek
$$
\begin{aligned}
\text{desired} &= \text{normalize}(\text{target} - \text{pos}) \cdot \text{max\_speed} \\
\text{steer} &= \text{desired} - \text{velocity}
\end{aligned}
$$
Accelerate toward a target at maximum speed.

### Flee
Same as seek but $\text{steer} = \text{velocity} - \text{desired}$ (repulsion from target).

### Arrive
Slow down within a braking radius:
$$
\begin{aligned}
\text{if dist} &< \text{braking\_radius:} \\
&\qquad \text{speed} = \text{max\_speed} \cdot \frac{\text{dist}}{\text{braking\_radius}} \\
&\qquad \text{desired} = \text{normalize}(\text{target} - \text{pos}) \cdot \text{speed}
\end{aligned}
$$

### Separate
Repulsion from nearby agents within a separation radius:
$$
\text{steer} -= \frac{\text{normalize}(\text{other} - \text{self}) \cdot \text{weight}}{\text{distance}}
$$

### Flock (Reynolds Boids)
$$
\text{velocity} += \text{steer\_separate} + \text{steer\_align} + \text{steer\_cohesion}
$$
- **Alignment:** steer toward average velocity of neighbors
- **Cohesion:** steer toward average position of neighbors

Forces are weighted and clamped to $\text{max\_force}$; velocity is clamped to $\text{max\_speed}$.

---

## 14. Inverse Kinematics (FABRIK) — `spore_engine/anim/ik.py`

### Forward Pass
Starting from root, extend each bone toward the target:
$$
\text{positions}[i] = \text{positions}[i-1] + \frac{\text{positions}[i] - \text{positions}[i-1]}{|\text{positions}[i] - \text{positions}[i-1]|} \cdot \text{length}[i-1]
$$

### Backward Pass
Starting from end effector, pull each bone back toward root:
$$
\text{positions}[i-1] = \text{positions}[i] + \frac{\text{positions}[i-1] - \text{positions}[i]}{|\text{positions}[i-1] - \text{positions}[i]|} \cdot \text{length}[i-1]
$$
After the backward pass, re-anchor root at original position and repeat forward pass.

### Convergence
Stop when $|\text{end\_effector} - \text{target}| < \text{tolerance}$ (typically 0.5 pixels). Handles both reachable and unreachable targets: if target is beyond total chain length, all bones align toward target.

### CCD Alternative
Cyclic Coordinate Descent rotates each bone (from tip to root) to minimize the angle between the bone-to-end-effector and bone-to-target vectors.

---

## 15. Fluid Simulation — `spore_engine/sim/fluid.py`

Based on Jos Stam's "Stable Fluids" (2003) — an unconditionally stable Navier-Stokes solver.

### Navier-Stokes Equations
$$
\begin{aligned}
\frac{\partial u}{\partial t} &= -(u \cdot \nabla)u + \nu \nabla^2 u - \nabla p + f \quad (\text{momentum conservation}) \\
\nabla \cdot u &= 0 \quad (\text{incompressibility})
\end{aligned}
$$

### Solver Steps per Frame
1. **Diffusion:** $\frac{\partial q}{\partial t} = \nu \nabla^2 q$ — implicit Gauss-Seidel iteration
2. **Projection:** Enforce incompressibility by solving Poisson equation $\nabla^2 p = \nabla \cdot u$
3. **Advection:** $\frac{\partial q}{\partial t} + u \cdot \nabla q = 0$ — semi-Lagrangian backward trace (unconditionally stable)
4. Repeat projection
5. **Dye transport:** same diffusion + advection for visualization

### Wave Equation
$$
\frac{\partial^2 h}{\partial t^2} = c^2 \nabla^2 h - \text{damping} \cdot \frac{\partial h}{\partial t}
$$
Discretized as: $\text{new} = (\text{neighbor\_sum} \times 0.5 - \text{current}) \times \text{damping}$. A Verlet-like finite-difference scheme. Each cell's new value is the average of its four neighbors minus the previous value, scaled by damping.

---

## 16. Volumetric Rendering — `spore_engine/fx/volumetric.py`

### Density Accumulation
$$
\text{density} += \text{density\_step} \cdot \sigma
$$
Where $\sigma$ is the scattering coefficient. Density values decay over time (exponential decay per frame).

### Light Scattering (Beer's Law)
$$
I = I_0 \cdot \exp\!\big(-\Sigma\; \text{density}\big)
$$
Light intensity attenuates exponentially as it passes through the volume. Each step accumulates the density along the ray.

### Cone Light Projection
$$
\text{attenuation} = \max\!\big(0,\; 1 - \tfrac{r}{\text{length}}\big) \cdot \text{intensity}
$$
A cone is swept from the light origin with a given angular width. Each ray within the cone accumulates attenuation based on distance and angular falloff. Flicker is simulated via sinusoidal modulation of intensity.

---

## 17. Cellular Automata

### Conway's Game of Life
- Alive with $<2$ neighbors: dies (underpopulation)
- Alive with $>3$ neighbors: dies (overpopulation)
- Dead with exactly 3 neighbors: becomes alive (reproduction)

### Gray-Scott Reaction-Diffusion
$$
\begin{aligned}
\frac{\partial U}{\partial t} &= D_U \nabla^2 U - UV^2 + F(1-U) \\
\frac{\partial V}{\partial t} &= D_V \nabla^2 V + UV^2 - (F+K)V
\end{aligned}
$$
Where $F$ = feed rate, $K$ = kill rate, $D_U > D_V$ for pattern formation.

---

## 18. A* Pathfinding — `spore_engine/gen/pathfinding.py`

### Cost Function
$$
F = G + H
$$
- $G$ = path cost from start to current node
- $H$ = heuristic estimated cost to goal (Euclidean or Manhattan distance)

### Algorithm
1. Push start node onto open set (priority queue ordered by $F$)
2. Pop node with lowest $F$; if it's the goal, reconstruct path
3. For each neighbor, compute tentative $G = \text{current}.G + \text{edge cost}$
4. If tentative $G$ is smaller than a neighbor's currently recorded $G$, update the neighbor's parent and push it to the open set
5. Repeat until goal reached or open set empty

The heuristic guides search toward the goal; with an admissible heuristic (never overestimates), A* is guaranteed optimal.

---

## 19. WFC (Wave Function Collapse) — `spore_engine/gen/wfc.py`

### Entropy
$$
S = -\sum_i p_i \cdot \log(p_i)
$$
Where $p_i$ = probability of tile $i$ among remaining candidates. Cells with fewer valid tiles have lower entropy.

### Algorithm Steps
1. **Collapse:** Pick the cell with lowest entropy, assign a tile weighted by probability
2. **Propagation:** For each neighbor, remove tiles incompatible with the newly collapsed cell's edge patterns; recurse on any neighbor reduced to one possibility
3. Repeat until all cells are collapsed or a contradiction occurs

Edge patterns are directional strings ($n$, $e$, $s$, $w$). Two tiles are compatible if their adjacent edges match.

---

## 20. Delaunay Triangulation — `spore_engine/gen/delaunay.py`

### Bowyer-Watson Algorithm
1. Create a super-triangle enclosing all input points
2. For each point:
   - Find all triangles whose circumcircle contains the point (bad triangles)
   - Remove bad triangles, forming a polygonal cavity
   - Triangulate the cavity by connecting the point to each boundary edge
3. Remove any triangle containing a super-triangle vertex

### Circumcircle Test
$$
\begin{aligned}
d &= 2 \cdot (a.x \cdot (b.y - c.y) + b.x \cdot (c.y - a.y) + c.x \cdot (a.y - b.y)) \\
\text{circum}(a,b,c) &= ((a_x^2 + a_y^2) \cdot (b.y - c.y) + \dots) / d \\
\text{in\_circle} &= |p - \text{circum}|^2 \le r^2
\end{aligned}
$$

### Voronoi Diagram
The dual graph: connect circumcenters of adjacent Delaunay triangles. Each Voronoi cell contains all points closer to its seed point than any other.

---

## 21. Marching Cubes — `spore_engine/gen/marching_cubes.py`

### Algorithm
For each cube in a 3D scalar grid:
1. Evaluate the density at all 8 corners; classify each as above or below the isovalue
2. Build an 8-bit index (one bit per corner) — 256 possible configurations
3. Use the edge table to determine which edges the isosurface crosses
4. Use the triangle table to generate triangles connecting interpolated edge vertices

### Edge Vertex Interpolation
$$
p = p_1 + \frac{\text{iso} - v_1}{v_2 - v_1} \cdot (p_2 - p_1)
$$

### Lookup Tables
- `EDGE_TABLE[256]`: bitmask of intersected edges per configuration
- `TRI_TABLE[256]`: variable-length triangle vertex indices (referencing 12 cube edges)

### Marching Squares — `spore_engine/gen/terrain.py`

The 2D analogue of marching cubes, used for contour-line extraction from heightmaps (`marching_squares()`). For each cell in a scalar grid:
1. Evaluate the value at all 4 corners; classify each as above or below the contour level.
2. Build a 4-bit index (one bit per corner) — 16 possible configurations.
3. Look up which cell edges the contour crosses and interpolate the crossing points linearly.
4. Connect interpolated points into line segments along the edges.

The 16 lookup cases are symmetric: 1 fully-inside, 1 fully-outside, and 14 boundary cases (4 with a single crossing edge pair, 2 ambiguous saddle cases handled by a tie-break rule).

---

## 22. Isometric Projection
$$
\begin{aligned}
\text{screen\_x} &= (\text{world\_x} - \text{world\_y}) \times \frac{\text{tile\_w}}{2} \\
\text{screen\_y} &= (\text{world\_x} + \text{world\_y}) \times \frac{\text{tile\_h}}{2} - \text{elevation} \times h_{\text{scale}}
\end{aligned}
$$
A 2.5D projection where $x$ and $y$ axes are foreshortened equally at $30^\circ$ from horizontal.

---

## 23. Fractals

### Mandelbrot Set
Iterate $z = z^2 + c$ until $|z|^2 > 4$. The set is $c$ values for which $z$ remains bounded. Iteration count maps to color.

### Julia Set
Same iteration, but $c$ is fixed and $z$ starts from the pixel coordinate. The shape depends on the $c$ parameter.

### Burning Ship — `spore_engine/gen/fractals.py`
$$
z = (|\text{Re}(z)| + i|\text{Im}(z)|)^2 + c
$$
Same iteration as Mandelbrot, but taking absolute values of real and imaginary parts before squaring. Produces a ship-shaped fractal with fiery colors.

### Newton Fractal — `spore_engine/gen/fractals.py`
$$
z_{n+1} = z_n - \frac{f(z_n)}{f'(z_n)}
$$
For $f(z) = z^3 - 1$, iterate Newton's method from each pixel. Color by which root (of the three cube roots of unity) the iteration converges to. Shade by iteration count.

### Barnsley Fern IFS — `spore_engine/gen/fractals.py`

Four affine transforms with probabilities:
$$
\begin{aligned}
f_1(x,y) &= (0,\; 0.16y) && p = 0.01 \quad (\text{stem}) \\
f_2(x,y) &= (0.85x + 0.04y,\; -0.04x + 0.85y + 1.6) && p = 0.85 \quad (\text{leaves}) \\
f_3(x,y) &= (0.20x - 0.26y,\; 0.23x + 0.22y + 1.6) && p = 0.08 \quad (\text{left leaflets}) \\
f_4(x,y) &= (-0.15x + 0.28y,\; 0.26x + 0.24y + 0.44) && p = 0.06 \quad (\text{right leaflets})
\end{aligned}
$$
Start at $(0,0)$, randomly apply a transform weighted by probability. Each point maps to a pixel on the canvas, accumulating to form a fern shape.

---

## 24. Vector Fields — `spore_engine/fx/field.py`

### Field Source Types

**Radial (source/sink):**
$$
F(x,y) = \text{strength} \cdot \frac{(x - x_0,\; y - y_0)}{\|(x - x_0,\; y - y_0)\|}
$$

**Vortex:**
$$
F(x,y) = \text{strength} \cdot \frac{(y_0 - y,\; x - x_0)}{\|(x - x_0,\; y - y_0)\|}
$$

**Swirl:** Combines radial attraction with tangential rotation.

### Particle Advection
$$
p_{t+1} = p_t + F(p_t) \cdot dt
$$

Particles trace streamlines through the vector field. Trails are rendered by leaving fading marks at each position.

---

## 25. 2D Lighting — `spore_engine/fx/lighting.py`

### Ray-Scene Intersection

For a ray $R(t) = O + t \cdot D$, find the smallest positive $t$ intersecting any line segment $S(u) = A + u \cdot (B - A)$:

$$
t = \frac{(A - O) \times (B - A)}{D \times (B - A)},\quad
u = \frac{(A - O) \times D}{D \times (B - A)}
$$

Intersection valid when $t > 0$ and $0 \le u \le 1$.

### Visibility Polygon (FOV)

Sort all obstacle endpoints by angle from the light source. Cast rays at each angle $\pm \epsilon$ to determine visible segments. The polygon connecting visible ray hits forms the visibility region.

### DDA Grid Shadows

For tile maps, DDA traversal accumulates opacity along each ray. If cumulative opacity exceeds a threshold, cells beyond are shadowed:

$$
\text{brightness} = \max(0,\; 1 - \Sigma\;\text{tile\_opacity})
$$

Light intensity falls off with distance:
$$
\text{intensity} = \max(0,\; \text{power} \cdot (1 - \frac{d}{\text{radius}}))
$$

---

## 26. Particle System Dynamics — `spore_engine/fx/effects.py`

### Particle Update
$$
\begin{aligned}
v &\mathrel{+}= g \cdot dt \quad (\text{gravity}) \\
v &\mathrel{+}= \text{random\_jitter} \quad (\text{turbulence}) \\
p &\mathrel{+}= v \cdot dt \\
\text{life} &\mathrel{-}= dt
\end{aligned}
$$

### Burst Emission
A burst spawns $n$ particles at position $(x,y)$ with:
- Velocity: random direction $\times$ speed
- Lifetime: uniform random in $[\text{min\_life}, \text{max\_life}]$
- Color: random from palette, interpolated over lifetime

Trail particles are spawned each frame with reduced lifetime and opacity.

---

## 27. Scene Transitions — `spore_engine/fx/transitions.py`

### Fade
$$
\text{out}(x,y) = \text{lerp}(\text{src}(x,y),\; \text{dst}(x,y),\; t),\quad t \in [0,1]
$$

### Wipe
A sweeping edge moves across the screen:
$$
\text{edge} = t \cdot w \quad (\text{right wipe})
$$
Pixels on the wiped side use the destination frame; pixels on the other side use the source frame.

### Checkerboard
$$
\text{choice} = \begin{cases}
\text{dst} & \text{if } (\lfloor x/s \rfloor + \lfloor y/s \rfloor) \bmod 2 < t \cdot 2 \\
\text{src} & \text{otherwise}
\end{cases}
$$
Where $s = \text{tile size}$. As $t$ increases, more checker cells flip from source to destination.

### PixelDissolve
Each pixel flips from source to destination when its random threshold is exceeded:
$$
\text{if } \text{rand}(x,y) < t:\; \text{dst},\; \text{else } \text{src}
$$
The random map is pre-computed per transition instance.

---

## 28. Animation Easing Functions — `spore_engine/anim/anim.py`

31 easing curves transform a normalized input $t \in [0,1]$ into an eased output. Each family has `_in` (accelerating), `_out` (decelerating), and `_in_out` (S-curve) variants:

- **quad** — $t^2$, $(1-t)^2$
- **cubic** — $t^3$
- **quart** — $t^4$
- **quint** — $t^5$
- **sine** — $\sin(t \cdot \pi/2)$
- **expo** — $2^{10(t-1)}$ style exponential
- **circ** — $\sqrt{1 - (t-1)^2}$ circular arc
- **back** — overshoots past the target ($s$-offset), then settles
- **bounce** — ball-like bouncing decay, $\text{out}$ ends with $4$ decreasing bounce heights
- **elastic** — damped oscillation with a base-2 exponential envelope
- **linear** — identity, for tweening without easing

The `_out` forms are typically composed as $1 - f(1-t)$, and `_in_out` as $f(2t)/2$ for $t < 0.5$ and $1 - f(2-2t)/2$ otherwise. All are exposed through the `EASING` name dict for string lookup.

---

## 29. Post-Processing Filters — `spore_engine/fx/postfx.py` & `spore_engine/fx/shaders.py`

### Convolution (box blur, glow, edge detection, Kuwahara)

Most filters are separable or local-window operations over each cell. A 2D convolution computes each output pixel as a weighted sum of its neighbors:

$$
\text{out}(x,y) = \sum_{dx=-r}^{r} \sum_{dy=-r}^{r} w(dx,dy) \cdot \text{in}(x+dx, y+dy)
$$

- **box_blur** — uniform kernel $w = 1/(2r+1)^2$ (low-pass).
- **glow (bloom)** — pixels above a luminance threshold are extracted, blurred, and additively blended back.
- **edge_detect** — Sobel gradient magnitude: $G = \sqrt{G_x^2 + G_y^2}$ with $G_x, G_y$ computed via the $3\times3$ Sobel kernels, then inverted (strong gradient ⇒ outline).
- **KuwaharaFilter** — divides the neighborhood into 4 quadrants, outputs the quadrant with the lowest variance, producing a flat, painterly (edge-preserving) result.

### Floyd-Steinberg Error Diffusion Dithering

Converts an image to a limited palette by diffusing quantization error to neighboring pixels with the weights:

$$
\text{error} \cdot \begin{bmatrix} & \frac{7}{16} & \\ \frac{3}{16} & \frac{5}{16} & \frac{1}{16} \end{bmatrix}
$$

The current pixel's quantization error is spread right, down-left, down, and down-right, so the average color is preserved over the whole image.

### Other Effects

- **pixelate** — block-average of $b \times b$ neighborhoods (box filter then downsample).
- **chromatic_aberration** — per-channel horizontal offset, simulating lens dispersion.
- **palette_remap** — map each pixel's luminance $L$ through a gradient: $\text{color} = \text{grad}(L)$.
- **posterize/solarize/cel-shade** — quantize channels to $N$ levels: $\lfloor c \cdot N \rfloor / N$ (or clamp at a threshold).
- **scanlines/vignette** — geometric attenuation: multiply brightness by $\sin$-based row factor, or radial falloff from the screen center.

---

## 30. Biome Classification — `spore_engine/gen/biome_terrain.py`

Three noise channels ($\text{elevation}$, $\text{moisture}$, $\text{temperature}$) are classified into one of 12 biomes by threshold ranges:

$$
\text{biome} = f(\text{elevation},\; \text{moisture},\; \text{temperature})
$$

- Low elevation (below sea level) ⇒ **ocean**.
- Near sea level with **beach** transition band ⇒ **beach**.
- Temperature is modulated by elevation via a lapse rate: $\text{temp} = \text{temp} - k \cdot \text{elevation}$.
- Arid regions (low moisture) ⇒ **desert**; cold high-elevation ⇒ **snow**/**mountain**; intermediate bands yield **grassland**, **forest**, **rainforest**, **tundra**, **taiga**, **swamp**, and **river**.

Final colors are sampled from the `BIOMES` gradient based on position within the biome's elevation range.

---

## 31. Core Utility Math — `spore_engine/core/util.py`

Small numerical helpers shared by scene-authoring code, camera smoothing, and `fx/screenfx.py`. All are pure functions; colors are downsampled via `Color(r, g, b)` integers.

| Function | Definition | Use |
|----------|-----------|-----|
| `clamp(v, lo, hi)` | $\max(lo,\; \min(hi, v))$ | Bound a value |
| `lerp(a, b, t)` | $a + (b - a)t$ | Linear interpolation |
| `ir(x)` | $\lfloor x + 0.5 \rfloor$ (Python `round`) | Float → int |
| `ramp(v, chars)` | $c_{\lfloor v \cdot (n-1)\rfloor}$ over ` .:-=+*#%@` | `0..1` → shade glyph |
| `phase(t, speed, offset)` | $((v)\bmod 1)$ where $v = t\cdot s + o$ | Saw wave `0..1` |
| `wave(t, speed, offset, lo, hi)` | $lo + \frac{hi-lo}{2}(1 + \sin(v))$ | Smooth sine between `lo`/`hi` |
| `osc(t, period, offset, lo, hi)` | same as `wave` with $speed = \frac{2\pi}{period}$ | Sine by period (s) |
| `bounce(t, period, offset, lo, hi)` | $lo + (hi{-}lo)\big(1 - \|2\cdot\text{frac}{\frac{t}{p}} - 1\|\big)$ | Triangle wave |
| `approach(v, t, step)` | step toward `t` without overshoot | Eased setpoint |
| `move_toward(v, t, step)` | alias of `approach` | Same |
| `in_bounds(x, y, w, h)` | $0 \le x < w$ and $0 \le y < h$ | Cell bounds check |
| `dist(ax, ay, bx, by)` | $\sqrt{(ax-bx)^2 + (ay-by)^2}$ | Euclidean distance |
| `lerp_color(c1, c2, t)` | per-channel `int(lerp)`; `None` propagates the other color | Channel-blend colors |
| `smoothstep(t)` | $t^2(3 - 2t)$ | Hermite easing `0→1` |
| `ramp_color(t, *colors)` | sample across $n$ stops: $i = \lfloor t(n-1)\rfloor$, blend `colors[i]→colors[i+1]` | Multi-stop color gradient |

`wave`/`osc`/`bounce`/`phase` default to `lo=0, hi=1` (except `phase`, which is
a pure `0..1` repeat). `lerp_color` treats a `None` endpoint as "keep the other
side", so it is safe to pass placeholder colors.

Related simple-color helpers live in `core/color.py` (`Color.lerp`, `Color.mul`,
`Gradient.at`); `ramp_color` is the t-parameterized multi-stop variant used when
a single `Gradient` object is overkill.
