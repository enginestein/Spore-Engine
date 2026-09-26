from __future__ import annotations
import math
import random
from ..core.canvas import Canvas, HiResCanvas
from ..core.color import Color, BLACK
from ..core.glyphs import SHADE_CHARS

#: Re-exported from core.glyphs so the ramp is defined once.
SHADE = SHADE_CHARS

class Mandelbrot:
    def __init__(self, width: int, height: int, max_iter: int = 100):
        self.w = width
        self.h = height
        self.max_iter = max_iter

    def render(self, canvas: Canvas | HiResCanvas, center: tuple[float, float], zoom: float, t: float = 0):
        cx, cy = center
        for py in range(canvas.height):
            for px in range(canvas.width):
                x0 = (px / canvas.width - 0.5) * zoom + cx
                y0 = (py / canvas.height - 0.5) * zoom + cy
                x, y = 0.0, 0.0
                it = 0
                while x*x + y*y < 4 and it < self.max_iter:
                    xt = x*x - y*y + x0
                    y = 2*x*y + y0
                    x = xt
                    it += 1
                
                if it == self.max_iter:
                    canvas.set_pixel(px, py, '@', BLACK)
                else:
                    n = it / self.max_iter
                    hue = (n * 2 + t * 0.02) % 1.0
                    canvas.set_pixel(px, py, SHADE[int(n * (len(SHADE) - 1))],
                                     Color.from_hsv(hue, 0.8, 0.5 + 0.5 * n))

class BurningShip:
    def __init__(self, width: int, height: int, max_iter: int = 100):
        self.w = width
        self.h = height
        self.max_iter = max_iter

    def render(self, canvas: Canvas | HiResCanvas, center: tuple[float, float], zoom: float, t: float = 0):
        """Render the Burning Ship fractal.

        z_next = (|Re z| + i|Im z|)^2 + c, which is why the real and imaginary
        parts are both passed through ``abs`` each iteration. The absolute
        values are what give the shape its characteristic downward "flames".

        This previously contained two complete escape loops: a broken first one
        that discarded its iteration count and then a correct one, so every
        pixel paid for the work twice.
        """
        cx, cy = center
        for py in range(canvas.height):
            for px in range(canvas.width):
                x0 = (px / canvas.width - 0.5) * zoom + cx
                y0 = (py / canvas.height - 0.5) * zoom + cy
                zx, zy = 0.0, 0.0
                it = 0
                while zx * zx + zy * zy < 4 and it < self.max_iter:
                    tmp = zx * zx - zy * zy + x0
                    zy = abs(2 * zx * zy) + y0
                    zx = abs(tmp)
                    it += 1

                if it == self.max_iter:
                    canvas.set_pixel(px, py, '#', BLACK)
                else:
                    n = it / self.max_iter
                    # Fire colors
                    r = int(255 * n)
                    g = int(100 * n * n)
                    b = int(50 * n * n * n)
                    canvas.set_pixel(px, py, SHADE[int(n * (len(SHADE) - 1))],
                                     Color(r, g, b))

class NewtonFractal:
    def __init__(self, width: int, height: int, roots: list[tuple[float, float]] | None = None):
        self.w = width
        self.h = height
        self.roots = roots or [(1, 0), (-0.5, 0.866), (-0.5, -0.866)] # roots of z^3 - 1 = 0

    def render(self, canvas: Canvas | HiResCanvas, zoom: float = 2.0, t: float = 0):
        # f(z) = z^3 - 1
        # f'(z) = 3z^2
        # z_next = z - f(z)/f'(z)
        
        # Animate roots slightly
        animated_roots = []
        for i, (rx, ry) in enumerate(self.roots):
            animated_roots.append((rx + math.sin(t + i) * 0.1, ry + math.cos(t * 0.7 + i) * 0.1))
            
        colors = [Color(255, 0, 0), Color(0, 255, 0), Color(0, 0, 255), Color(255, 255, 0)]
        
        for py in range(canvas.height):
            for px in range(canvas.width):
                zx = (px / canvas.width - 0.5) * zoom
                zy = (py / canvas.height - 0.5) * zoom
                
                it = 0
                closest_root = -1
                for _ in range(20):
                    # Complex division: (a+bi)/(c+di) = (ac+bd)/(c^2+d^2) + i(bc-ad)/(c^2+d^2)
                    # For z^3 - 1:
                    # z^3 = (zx+zyi)^3 = zx^3 + 3zx^2*zyi - 3zx*zy^2 - zy^3*i = (zx^3 - 3zx*zy^2) + i(3zx^2*zy - zy^3)
                    # f(z) = (zx^3 - 3zx*zy^2 - 1) + i(3zx^2*zy - zy^3)
                    # f'(z) = 3z^2 = 3(zx^2 - zy^2) + i(6zx*zy)
                    
                    fz_r = zx**3 - 3*zx*zy**2 - 1
                    fz_i = 3*zx**2*zy - zy**3
                    
                    dfz_r = 3*(zx**2 - zy**2)
                    dfz_i = 6*zx*zy
                    
                    denom = dfz_r**2 + dfz_i**2
                    if denom == 0: break
                    
                    # z = z - f(z)/df(z)
                    zx -= (fz_r * dfz_r + fz_i * dfz_i) / denom
                    zy -= (fz_i * dfz_r - fz_r * dfz_i) / denom
                    
                    it += 1
                    
                    # Check convergence to any root
                    for i, (rx, ry) in enumerate(animated_roots):
                        if (zx - rx)**2 + (zy - ry)**2 < 0.001:
                            closest_root = i
                            break
                    if closest_root != -1: break
                
                if closest_root != -1:
                    color = colors[closest_root % len(colors)].mul(1.0 - it / 30.0)
                    canvas.set_pixel(px, py, '█', color)
                else:
                    canvas.set_pixel(px, py, ' ', BLACK)

class BarnsleyFern:
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.points = [(0.0, 0.0)]
        self.x, self.y = 0.0, 0.0

    def step(self, canvas: Canvas | HiResCanvas, n: int = 100, color: Color | None = None):
        col = color or Color(0, 255, 0)
        for _ in range(n):
            r = random.random()
            if r < 0.01:
                self.x, self.y = 0.0, 0.16 * self.y
            elif r < 0.86:
                nx = 0.85 * self.x + 0.04 * self.y
                ny = -0.04 * self.x + 0.85 * self.y + 1.6
                self.x, self.y = nx, ny
            elif r < 0.93:
                nx = 0.2 * self.x - 0.26 * self.y
                ny = 0.23 * self.x + 0.22 * self.y + 1.6
                self.x, self.y = nx, ny
            else:
                nx = -0.15 * self.x + 0.28 * self.y
                ny = 0.26 * self.x + 0.24 * self.y + 0.44
                self.x, self.y = nx, ny
            
            # Map to canvas
            px = int(canvas.width / 2 + self.x * canvas.width / 11)
            py = int(canvas.height - self.y * canvas.height / 11)
            
            if 0 <= px < canvas.width and 0 <= py < canvas.height:
                canvas.set_pixel(px, py, '*', col)
