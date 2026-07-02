from __future__ import annotations
import math
from typing import Optional, List
from ..core.canvas import Canvas, HiResCanvas
from ..core.color import Color, Gradient, WHITE, BLACK

class VoxelScene:
    """
    Renders a heightmap as a 3D voxel landscape with dynamic shading.
    """
    def __init__(self, width: int, depth: int, heightmap: List[List[float]],
                 colors: Optional[List[Color]] = None):
        self.w = width
        self.d = depth
        self.heightmap = heightmap
        # Smooth altitude colors
        self.colors = colors or [
            Color(10, 20, 100),   # Deep Water
            Color(30, 60, 180),   # Water
            Color(220, 200, 140), # Sand
            Color(40, 120, 30),   # Grass
            Color(80, 80, 80),    # Rock
            Color(240, 240, 255)  # Snow
        ]

    def _get_base_color(self, h: float) -> Color:
        if h < 0.15: return self.colors[0]
        if h < 0.25: return self.colors[1]
        if h < 0.3:  return self.colors[2]
        if h < 0.6:  return self.colors[3]
        if h < 0.85: return self.colors[4]
        return self.colors[5]

    def render(self, canvas: Canvas | HiResCanvas, angle: float = 0, 
               elevation: float = 0.5, distance: float = 120,
               fov: float = 1.0, light_angle: float = 0.0, amb: float = 0.4):
        """
        Renders the landscape with directional shading and atmospheric fog.
        """
        cw, ch = canvas.width, canvas.height
        
        # Camera rotation
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # Light direction vector (simplified)
        lx = math.cos(light_angle)
        lz = math.sin(light_angle)
        
        # Ray casting approach for a classic voxel look (comanche style)
        for i in range(cw):
            # View ray direction
            v_angle = (i / cw - 0.5) * fov
            ray_x = math.cos(angle + v_angle)
            ray_z = math.sin(angle + v_angle)
            
            # Rendering front-to-back
            highest_y = ch
            
            for d in range(2, int(distance)):
                # Step through the world
                wx = (self.w / 2) + ray_x * d
                wz = (self.d / 2) + ray_z * d
                
                if 0 <= wx < self.w - 1 and 0 <= wz < self.d - 1:
                    ix, iz = int(wx), int(wz)
                    h = self.heightmap[iz][ix]
                    
                    # 1. Height-based projection
                    # Using a perspective formula: py = horizon + (height - camera_h) / distance
                    py = int(ch / 2 + (elevation - h) * 120 / (d * 0.08 + 1))
                    
                    if py < highest_y:
                        # 2. Dynamic Shading (Normal approximation)
                        # Calculate gradient for shading
                        h_r = self.heightmap[iz][ix+1]
                        h_d = self.heightmap[iz+1][ix]
                        nx = h - h_r
                        nz = h - h_d
                        
                        # Dot product with light
                        shade = (nx * lx + nz * lz) * 15.0
                        shade = max(0, min(1.0, amb + shade))
                        
                        # 3. Final Color calculation
                        base_col = self._get_base_color(h)
                        final_col = base_col.mul(shade)
                        
                        # 4. Exponential Fog
                        fog_factor = math.exp(-d * 0.02)
                        final_col = final_col.mul(fog_factor).blend(Color(100, 140, 200), 1.0 - fog_factor)
                        
                        # Use different characters for depth
                        char = '█' if d < 40 else '▓' if d < 80 else '▒'
                        
                        for y in range(max(0, py), min(highest_y, ch)):
                            canvas.set_pixel(i, y, char, final_col)
                        
                        highest_y = py
                        
                if highest_y <= 0: break
