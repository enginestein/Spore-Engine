import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.engine3d import Mesh3D, render_mesh_solid
from spore_engine.render3d.raytracer import Scene, Sphere, Plane

SHADE = ' .:-=+*#%@'

def scene_3d_objects(c, hr, t, pt, dt):
    grad = Gradient(Color(5, 3, 20), Color(12, 8, 35), Color(20, 15, 50))
    for y in range(c.h):
        for x in range(c.w):
            n = (math.sin(x*0.02+t*0.5)+math.cos(y*0.03+t*0.3))*0.5+0.5
            c.set_pixel(x, y, '█', grad.at((y+n*0.3)/c.h), z=-100)
    meshes = [
        Mesh3D.cube(1.5).transform(Mat4.translate(-4,0,0)*Mat4.rotate_y(t*0.7)*Mat4.rotate_x(t*0.5)),
        Mesh3D.sphere(1.2,10,14).transform(Mat4.translate(0,0,0)*Mat4.rotate_y(t*0.3)*Mat4.rotate_x(t*0.4)),
        Mesh3D.torus(1.2,0.5,20,10).transform(Mat4.translate(4,0,0)*Mat4.rotate_x(t*0.5)*Mat4.rotate_z(t*0.3)),
        Mesh3D.pyramid(1.5).transform(Mat4.translate(-3,2.5,0)*Mat4.rotate_y(t*0.6)),
        Mesh3D.icosphere(1,2).transform(Mat4.translate(3,2.5,0)*Mat4.rotate_y(t*0.4)*Mat4.rotate_x(t*0.3)),
    ]
    view = Mat4.look_at(Vec3(0,0,-6), Vec3(0,0,0))
    proj = Mat4.perspective(1.2, hr.w/hr.h, 0.1, 20)
    light = Vec3(math.sin(t*0.3), -0.3, math.cos(t*0.3)).norm()
    for m in meshes:
        render_mesh_solid(hr, m, view, proj, light)
    hr.to_canvas(c)
    c.draw_text(2, 0, "3D Objects", Color.from_hsv(t*0.02%1.0, 0.5, 1.0), z=100)

def scene_donut(c, hr, t, pt, dt):
    t *= 1.5
    A, B = t*0.7, t*0.3
    sinA, cosA = math.sin(A), math.cos(A)
    sinB, cosB = math.sin(B), math.cos(B)
    R1, R2, K2 = 1.0, 2.0, 5.0
    K1 = hr.w * K2 * 3 / (8 * (R1 + R2))
    cx, cy = hr.w // 2, hr.h // 2
    for y in range(hr.h):
        for x in range(hr.w):
            n = (math.sin(x*0.01+t*0.3)+math.cos(y*0.012+t*0.2))*0.5+0.5
            hr.set_pixel_z(x, y, Color.from_hsv(0.65, 0.3, n*0.08), -100)
    for theta in range(0, 200, 1):
        costheta = math.cos(theta*0.04)
        sintheta = math.sin(theta*0.04)
        for phi in range(0, 200, 1):
            cosphi = math.cos(phi*0.04)
            sinphi = math.sin(phi*0.04)
            circlex = R2 + R1 * costheta
            circley = R1 * sintheta
            x = circlex*(cosB*cosphi+sinA*sinB*sinphi) - circley*cosA*sinB
            y = circlex*(sinB*cosphi-sinA*cosB*sinphi) + circley*cosA*cosB
            z = cosA*circlex*sinphi + circley*sinA + K2
            ooz = 1/z
            xp = int(cx + K1*ooz*x)
            yp = int(cy - K1*ooz*y)
            nx = costheta*(cosB*cosphi+sinA*sinB*sinphi)-sintheta*cosA*sinB
            ny = costheta*(sinB*cosphi-sinA*cosB*sinphi)+sintheta*cosA*cosB
            nz = cosA*costheta*sinphi+sintheta*sinA
            l = nx*0.7+ny*0.3+nz*0.7
            l = max(0.2, l)
            hue = (theta*0.02+phi*0.01+t*0.05) % 1.0
            hr.set_pixel_z(xp, yp, Color.from_hsv(hue, 0.9, min(1,l+0.3)), ooz*100)
    hr.to_canvas(c)
    c.draw_text(2, 0, "3D Donut", Color(255, 200, 100), z=100)

_RC_MAP = [
    "11111111111111111111111111111111",
    "10000000010000000000100000000001",
    "10000000010000000000100000000001",
    "10000000010000000000100000000001",
    "10000000000011111000100111100001",
    "10000000000000001000100100000001",
    "10001111111100001000100100011101",
    "10001000000100001000000100010101",
    "10001000000100001111100100010101",
    "10001000000100000000000100010001",
    "10001111111100000000000111110001",
    "10000000000000011111110000000001",
    "10000000000000010000010000000001",
    "10000000000000010000010000000001",
    "10000000000000010000010000000001",
    "11111111111111110000011111111111",
    "10000000000000000000000000000001",
    "10000000001110000000011100000001",
    "10000000001000000000010000000001",
    "10000000001000000000010000000001",
    "10000000001110011111011100000001",
    "10000000000000000000000000000001",
    "10000000000000000000000000000001",
    "11111111111111111111111111111111",
]

# player auto-wander state
_pcw = None
def scene_raycaster(c, hr, t, pt, dt):
    global _pcw
    m = _RC_MAP
    mw, mh = len(m[0]), len(m)

    # init player
    if _pcw is None:
        _pcw = {
            'px': 3.5, 'py': 2.5,
            'angle': 0.0,
            'turn_cooldown': 0,
            'speed': 2.5,
        }

    p = _pcw
    move_speed = p['speed'] * dt
    turn_speed = 1.8 * dt

    # auto-wander: move forward, turn when near walls
    if p['turn_cooldown'] > 0:
        p['turn_cooldown'] -= dt

    # try moving forward
    new_px = p['px'] + math.cos(p['angle']) * move_speed
    new_py = p['py'] + math.sin(p['angle']) * move_speed

    # wall collision check
    map_x, map_y = int(new_px), int(new_py)
    hit_wall = (map_x < 1 or map_x >= mw-1 or map_y < 1 or map_y >= mh-1 or
                m[map_y][map_x] == '1' or m[map_y][int(p['py'])] == '1' or m[int(p['py'])][map_x] == '1')

    if hit_wall:
        if p['turn_cooldown'] <= 0:
            p['angle'] += random.choice([-1, 1]) * 1.5 + random.uniform(-0.3, 0.3)
            p['turn_cooldown'] = random.uniform(0.3, 1.0)
    else:
        p['px'] = new_px
        p['py'] = new_py

    # occasional random turns while walking
    if random.random() < dt * 0.8 and p['turn_cooldown'] <= 0:
        p['angle'] += random.uniform(-0.3, 0.3)

    # speed variation
    p['speed'] = 2.0 + 0.5 * math.sin(t * 0.7)

    px, py = p['px'], p['py']
    pdx, pdy = math.cos(p['angle']), math.sin(p['angle'])
    plane_x, plane_y = -pdy * 0.66, pdx * 0.66

    wall_grad = Gradient.from_palette('fire')
    ceil_grad = Gradient(Color(3, 3, 15), Color(8, 5, 30), Color(15, 10, 50))
    floor_grad = Gradient(Color(8, 6, 18), Color(25, 18, 35), Color(45, 28, 48))

    for x in range(c.w):
        camera_x = 2*x/c.w - 1
        rdx = pdx + plane_x*camera_x
        rdy = pdy + plane_y*camera_x
        map_x, map_y = int(px), int(py)
        delta_dist_x = abs(1/rdx) if rdx != 0 else 1e30
        delta_dist_y = abs(1/rdy) if rdy != 0 else 1e30
        step_x = -1 if rdx < 0 else 1
        step_y = -1 if rdy < 0 else 1
        side_dist_x = (px - map_x)*delta_dist_x if rdx < 0 else (map_x+1.0-px)*delta_dist_x
        side_dist_y = (py - map_y)*delta_dist_y if rdy < 0 else (map_y+1.0-py)*delta_dist_y
        hit, side = False, 0
        while not hit:
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x; map_x += step_x; side = 0
            else:
                side_dist_y += delta_dist_y; map_y += step_y; side = 1
            if map_x < 0 or map_x >= mw or map_y < 0 or map_y >= mh:
                break
            if m[map_y][map_x] == '1':
                hit = True
        if not hit:
            for y in range(c.h):
                c.set_pixel(x, y, ' ')
            continue
        perp_dist = (side_dist_x - delta_dist_x) if side == 0 else (side_dist_y - delta_dist_y)
        perp_dist = max(0.01, perp_dist)
        lh = int(c.h / perp_dist)
        ds = max(0, -lh//2 + c.h//2)
        de = min(c.h-1, lh//2 + c.h//2)
        shade = min(1, 2.0/(perp_dist+0.5))
        if side == 1: shade *= 0.6
        wcolor = wall_grad.at(shade)
        for y in range(ds, de+1):
            c.set_pixel(x, y, '█', wcolor)
        for y in range(de+1, c.h):
            d_ = (y - c.h/2) / (c.h/2)
            c.set_pixel(x, y, '▒', floor_grad.at(min(1, d_)))
        for y in range(0, ds):
            d_ = (c.h/2 - y) / (c.h/2)
            c.set_pixel(x, y, '░', ceil_grad.at(min(1, d_)))

    # minimap
    s = min(c.w//(mw*2+2), c.h//(mh*2+2), 1)
    if s >= 1:
        ox, oy = c.w-mw*s-2, 2
        for my in range(mh):
            for mx in range(mw):
                ch = '█' if m[my][mx] == '1' else '·'
                col = Color(100, 80, 60) if m[my][mx] == '1' else DIM
                for dy in range(s):
                    for dx in range(s):
                        c.set_pixel(ox+mx*s+dx, oy+my*s+dy, ch, col)
        c.set_pixel(ox+int(px*s), oy+int(py*s), '@', Color(0,255,255))
        c.set_pixel(ox+int(px*s+pdx*s), oy+int(py*s+pdy*s), '♦', YELLOW)

    c.draw_text(2, 0, f"Raycaster — ({int(px)},{int(py)}) dir:{int(p['angle']*57)%360}°", Color(100, 200, 255), z=100)

_rt_scene = None
def scene_raytracer(c, hr, t, pt, dt):
    global _rt_scene
    if _rt_scene is None:
        _rt_scene = Scene()
        _rt_scene.objects.append(Sphere(-1.5,-0.3,4,1.0,Color(255,80,80),reflect=0.3))
        _rt_scene.objects.append(Sphere(1.5,0.2,4.5,0.8,Color(80,80,255),reflect=0.5))
        _rt_scene.objects.append(Sphere(0,-0.8,3,0.5,Color(80,255,80)))
        _rt_scene.objects.append(Sphere(0.5,0.5,5,0.6,Color(255,255,80)))
        _rt_scene.objects.append(Sphere(-0.8,-0.5,6,0.7,Color(255,128,0),reflect=0.4))
        _rt_scene.objects.append(Plane(0,1,0,-2.0,Color(60,60,100),reflect=0.1))
        _rt_scene.lights.append((3,4,2,Color(255,255,255),1.5))
        _rt_scene.lights.append((-3,3,1,Color(255,200,200),0.8))
    cam = (math.sin(t*0.2)*2, 1+math.sin(t*0.3)*0.3, -2)
    _rt_scene.render(hr, cam, (0,0,5), 50)
    hr.to_canvas(c)
    c.draw_text(2, 0, "Spore Raytracer", Color(255, 180, 100), z=100)
