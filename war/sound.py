import math
import shutil
import struct
import subprocess
import sys
import threading
import time

import numpy as np

# -- constants ------------------------------------------------------------
SR = 44100
CHANNELS = 2
MASTER = 0.75
_CHUNK = 4096

# -- path so the music package is importable ------------------------------
_MUSIC_DIR = '/home/indresh/Desktop/music'
if _MUSIC_DIR not in sys.path:
    sys.path.insert(0, _MUSIC_DIR)

# -- tiny filters used by the synthesis helpers ---------------------------
def _lp(x, fc):
    a = math.exp(-2.0 * math.pi * fc / SR)
    y = np.empty_like(x)
    y[0] = (1.0 - a) * x[0]
    for i in range(1, len(x)):
        y[i] = a * y[i - 1] + (1.0 - a) * x[i]
    return y

def _hp(x, fc):
    a = math.exp(-2.0 * math.pi * fc / SR)
    y = np.empty_like(x)
    y[0] = 0.0
    for i in range(1, len(x)):
        y[i] = a * (y[i - 1] + x[i] - x[i - 1])
    return y

def _pan_coefs(pan):
    """Constant-power stereo pan.  pan in [-1, 1]."""
    th = (max(-1.0, min(1.0, pan)) + 1.0) * math.pi / 4.0
    return math.cos(th), math.sin(th)

# -- vectorised PCG noise (fast, deterministic sequence) ------------------

def _pcg_noise(n, seed=0x9E3779B9):
    """Generate *n* random floats in [-1, 1] using PCG hashing (vectorised)."""
    idx = np.arange(n, dtype=np.uint32)
    s = ((idx * np.uint32(2654435761) + np.uint32(seed)) & np.uint32(0xFFFFFFFF))
    s = ((s * np.uint32(1103515245) + np.uint32(12345)) & np.uint32(0x7FFFFFFF))
    return (s.astype(np.float64) / 0x3FFFFFFF) - 1.0

def _v_iir_1po(x, a):
    """Vectorised 1-pole IIR lowpass: y[i] = a*y[i-1] + (1-a)*x[i].

    Uses a block-based scalar loop (256 samples per block) to stay fast
    while avoiding the numerical instability of the cumsum trick.
    """
    n = len(x)
    if n == 0:
        return x.copy()
    b = 1.0 - a
    y = np.empty(n, dtype=np.float64)
    y[0] = b * x[0]
    y_prev = y[0]
    BLOCK = 256
    for start in range(1, n, BLOCK):
        end = min(start + BLOCK, n)
        for i in range(start, end):
            y_prev = a * y_prev + b * x[i]
            y[i] = y_prev
    return y

# -- synthesis helpers (numpy vectorised) ---------------------------------

def _env(n, attack=0.005, hold=0.0, decay=0.05, sustain=0.7, release=0.1):
    """ADSR envelope for *n* samples at SR."""
    n = max(1, int(n))
    a = max(1, int(attack * SR))
    d = max(1, int(decay * SR))
    r = max(1, int(release * SR))
    h = max(0, int(hold * SR))
    env = np.ones(n, dtype=np.float64)
    if a < n:
        env[:a] = np.linspace(0.0, 1.0, a)
    dd = min(a + d, n)
    if dd > a:
        env[a:dd] = np.linspace(1.0, sustain, dd - a)
    if dd < n:
        env[dd:] = sustain
    rs = max(dd, n - r)
    if rs < n:
        env[rs:] = np.linspace(env[rs] if rs < n else sustain, 0.0, n - rs)
    return env

def _noise(n):
    return np.random.uniform(-1.0, 1.0, max(1, int(n)))

def _brown(n, smoothing=0.003):
    """Brown noise - integrated white noise."""
    w = _noise(n)
    out = np.empty_like(w)
    out[0] = w[0]
    a = math.exp(-2.0 * math.pi * smoothing * SR / SR)
    for i in range(1, len(w)):
        out[i] = a * out[i - 1] + (1.0 - a) * w[i]
    mx = np.max(np.abs(out))
    return out / mx if mx > 0 else out

# -------------------------------------------------------------------------
#  SOUND PRESETS - each returns a mono float64 buffer
# -------------------------------------------------------------------------

def _snd_rifle():
    """Assault rifle - sharp crack + dark tail."""
    n = int(SR * 0.12)
    t = np.arange(n, dtype=np.float64) / SR
    click = _noise(n) * np.exp(-600.0 * t)
    body = _lp(_noise(n), 2500) * np.exp(-18.0 * t)
    sub  = np.sin(2 * np.pi * 55 * t) * np.exp(-25.0 * t) * 0.3
    env  = _env(n, 0.001, 0.0, 0.02, 0.4, 0.08)
    return (click * 0.55 + body * 0.35 + sub) * env

def _snd_heavy():
    """Heavy machine gun - deeper thud + metallic rattle."""
    n = int(SR * 0.15)
    t = np.arange(n, dtype=np.float64) / SR
    thud = np.sin(2 * np.pi * 80 * t) * np.exp(-12.0 * t) * 0.45
    crack = _hp(_noise(n), 3000) * np.exp(-50.0 * t)
    rattle = _lp(_noise(n), 1800) * np.exp(-20.0 * t)
    env = _env(n, 0.001, 0.0, 0.03, 0.3, 0.10)
    return (thud + crack * 0.5 + rattle * 0.35) * env

def _snd_laser():
    """Laser bolt - sine sweep down + filtered noise."""
    n = int(SR * 0.10)
    t = np.arange(n, dtype=np.float64) / SR
    p = np.linspace(0, 1, n)
    f = 2200.0 - 1800.0 * p
    phase = np.cumsum(f / SR) * 2.0 * math.pi
    sweep = np.sin(phase) * np.exp(-8.0 * t) * 0.45
    hiss = _hp(_noise(n), 4000) * np.exp(-30.0 * t) * 0.3
    env = _env(n, 0.001, 0.0, 0.01, 0.5, 0.05)
    return (sweep + hiss) * env

def _snd_sniper():
    """Sniper rifle - long-range crack with reverb tail."""
    n = int(SR * 0.25)
    t = np.arange(n, dtype=np.float64) / SR
    crack = _hp(_noise(n), 5000) * np.exp(-80.0 * t) * 0.6
    body = _lp(_noise(n), 3000) * np.exp(-12.0 * t) * 0.4
    sub = np.sin(2 * np.pi * 45 * t) * np.exp(-10.0 * t) * 0.25
    # distant echo
    echo = np.zeros(n)
    d = int(0.08 * SR)
    if d < n:
        echo[d:] = (crack[:n-d] + body[:n-d]) * 0.2
    env = _env(n, 0.001, 0.0, 0.015, 0.5, 0.18)
    return (crack + body + sub + echo) * env

def _snd_flame():
    """Flamethrower - filtered noise roar."""
    n = int(SR * 0.20)
    t = np.arange(n, dtype=np.float64) / SR
    roar = _lp(_noise(n), 1200) * np.exp(-6.0 * t)
    hiss = _hp(_noise(n), 2000) * np.exp(-10.0 * t) * 0.3
    rumble = np.sin(2 * np.pi * 35 * t) * np.exp(-5.0 * t) * 0.3
    env = _env(n, 0.01, 0.05, 0.04, 0.6, 0.10)
    return (roar * 0.55 + hiss + rumble) * env

def _snd_tank():
    """Tank cannon - massive sub-thud + debris crackle."""
    n = int(SR * 0.35)
    t = np.arange(n, dtype=np.float64) / SR
    boom = np.sin(2 * np.pi * 38 * t) * np.exp(-6.0 * t) * 0.55
    boom2 = np.sin(2 * np.pi * 55 * t) * np.exp(-8.0 * t) * 0.3
    crack = _hp(_noise(n), 3500) * np.exp(-30.0 * t) * 0.4
    debris = _lp(_noise(n), 2000) * np.exp(-8.0 * t) * 0.2
    env = _env(n, 0.001, 0.0, 0.04, 0.5, 0.25)
    return (boom + boom2 + crack + debris) * env

def _snd_mech():
    """Mech cannon - even heavier than tank."""
    n = int(SR * 0.40)
    t = np.arange(n, dtype=np.float64) / SR
    boom = np.sin(2 * np.pi * 30 * t) * np.exp(-5.0 * t) * 0.6
    body = np.sin(2 * np.pi * 65 * t) * np.exp(-7.0 * t) * 0.25
    crack = _hp(_noise(n), 2800) * np.exp(-25.0 * t) * 0.35
    env = _env(n, 0.001, 0.0, 0.05, 0.45, 0.30)
    return (boom + body + crack) * env

def _snd_boom_small():
    """Small explosion - grenade / drone strike."""
    n = int(SR * 0.50)
    t = np.arange(n, dtype=np.float64) / SR
    f0 = 90.0
    f = f0 * (1.0 - 0.55 * np.minimum(t / 0.15, 1.0))
    phase = np.cumsum(f / SR) * 2.0 * math.pi
    tone = np.sin(phase) * 0.5
    rumble = (np.sin(2 * np.pi * 12 * t) * 0.35
              + np.sin(2 * np.pi * 20 * t) * 0.25
              + np.sin(2 * np.pi * 32 * t) * 0.15)
    debris = _lp(_noise(n), 2500) * np.exp(-5.0 * t) * 0.3
    env = np.exp(-3.0 * t)
    return (tone + rumble + debris) * env

def _snd_boom_large():
    """Large explosion - artillery shell / building collapse."""
    n = int(SR * 0.80)
    t = np.arange(n, dtype=np.float64) / SR
    f0 = 65.0
    f = f0 * (1.0 - 0.60 * np.minimum(t / 0.20, 1.0))
    phase = np.cumsum(f / SR) * 2.0 * math.pi
    tone = np.sin(phase) * 0.55
    rumble = (np.sin(2 * np.pi * 8.0 * t) * 0.40
              + np.sin(2 * np.pi * 15.0 * t) * 0.30
              + np.sin(2 * np.pi * 24.0 * t) * 0.20)
    debris = _lp(_noise(n), 2000) * np.exp(-4.0 * t) * 0.35
    crack = _hp(_noise(n), 4000) * np.exp(-20.0 * t) * 0.25
    env = np.exp(-2.2 * t)
    return (tone + rumble + debris + crack) * env

def _snd_boom_massive():
    """Massive explosion - zeppelin, mothership, driller strike."""
    n = int(SR * 1.20)
    t = np.arange(n, dtype=np.float64) / SR
    f0 = 45.0
    f = f0 * (1.0 - 0.50 * np.minimum(t / 0.30, 1.0))
    phase = np.cumsum(f / SR) * 2.0 * math.pi
    tone = np.sin(phase) * 0.6
    rumble = (np.sin(2 * np.pi * 6.0 * t) * 0.45
              + np.sin(2 * np.pi * 11.0 * t) * 0.35
              + np.sin(2 * np.pi * 19.0 * t) * 0.25)
    debris = _lp(_noise(n), 1800) * np.exp(-3.0 * t) * 0.4
    crack = _hp(_noise(n), 3500) * np.exp(-15.0 * t) * 0.3
    env = np.exp(-1.6 * t)
    return (tone + rumble + debris + crack) * env

def _snd_flak():
    """Anti-aircraft flak burst - sharp pop + descending tone."""
    n = int(SR * 0.20)
    t = np.arange(n, dtype=np.float64) / SR
    f = 500.0 - 350.0 * np.minimum(t / 0.06, 1.0)
    phase = np.cumsum(f / SR) * 2.0 * math.pi
    tone = np.sin(phase) * 0.35
    pop = _hp(_noise(n), 2000) * np.exp(-40.0 * t) * 0.55
    env = _env(n, 0.001, 0.0, 0.03, 0.4, 0.12)
    return (tone + pop) * env

def _snd_blip():
    """Electronic blip - target acquisition / hack confirm."""
    n = int(SR * 0.12)
    t = np.arange(n, dtype=np.float64) / SR
    f = 600.0 - 200.0 * np.minimum(t / 0.04, 1.0)
    phase = np.cumsum(f / SR) * 2.0 * math.pi
    tone = np.sin(phase) * 0.4
    env = np.exp(-12.0 * t)
    return tone * env

def _snd_whistle():
    """Incoming projectile - descending whistle."""
    n = int(SR * 0.60)
    t = np.arange(n, dtype=np.float64) / SR
    f = 1100.0 - 800.0 * np.minimum(t / 0.4, 1.0)
    wob = 1.0 + 0.008 * np.sin(2 * np.pi * 9.0 * t)
    phase = np.cumsum(f * wob / SR) * 2.0 * math.pi
    tone = np.sin(phase) * 0.35
    breath = _lp(_noise(n), 3000) * 0.06
    env = _env(n, 0.02, 0.1, 0.1, 0.7, 0.35)
    return (tone + breath) * env

def _snd_zap():
    """Laser / energy weapon - fast sweep."""
    n = int(SR * 0.08)
    t = np.arange(n, dtype=np.float64) / SR
    f = 1800.0 - 1200.0 * np.minimum(t / 0.03, 1.0)
    phase = np.cumsum(f / SR) * 2.0 * math.pi
    tone = np.sin(phase) * 0.35
    hiss = _hp(_noise(n), 5000) * np.exp(-30.0 * t) * 0.25
    env = np.exp(-15.0 * t)
    return (tone + hiss) * env

def _snd_horn():
    """War horn - brass + harmonics."""
    n = int(SR * 1.00)
    t = np.arange(n, dtype=np.float64) / SR
    tone = (np.sin(2 * np.pi * 147 * t) * 0.50
            + np.sin(2 * np.pi * 294 * t) * 0.30
            + np.sin(2 * np.pi * 441 * t) * 0.15
            + np.sin(2 * np.pi * 588 * t) * 0.08)
    trem = 1.0 + 0.12 * np.sin(2 * np.pi * 0.8 * t)
    env = _env(n, 0.04, 0.15, 0.15, 0.85, 0.50)
    return tone * trem * env * 0.25

def _snd_cry():
    """Battle shout - ragged rising voice."""
    n = int(SR * 0.55)
    t = np.arange(n, dtype=np.float64) / SR
    f = 320.0 + 100.0 * np.sin(2 * np.pi * 5.5 * t) + 200.0 * np.minimum(t / 0.3, 1.0)
    wob = 1.0 + 0.05 * np.sin(2 * np.pi * 20.0 * t)
    body = np.sin(2 * np.pi * f * wob * t) * 0.45
    h2 = np.sin(2 * np.pi * f * 0.5 * wob * t) * 0.25
    rasp = _lp(_noise(n), 3500) * 0.20
    env = np.sin(np.pi * np.minimum(t / 0.35, 1.0)) * np.exp(-2.5 * t)
    return (body + h2 + rasp) * env * 0.20

def _snd_swarm():
    """Drone swarm buzz - insectoid."""
    n = int(SR * 0.40)
    t = np.arange(n, dtype=np.float64) / SR
    f = 210.0 + 20.0 * np.sin(2 * np.pi * 14.0 * t)
    tone = np.sin(2 * np.pi * f * t) * 0.35
    buzz = np.sin(2 * np.pi * f * 2.01 * t) * 0.15
    chit = _hp(_noise(n), 5000) * np.exp(-8.0 * t) * 0.25
    env = _env(n, 0.01, 0.05, 0.08, 0.6, 0.20)
    return (tone + buzz + chit) * env * 0.18

def _snd_missile_launch():
    """Missile / artillery launch - whoosh + crack."""
    n = int(SR * 0.30)
    t = np.arange(n, dtype=np.float64) / SR
    f = 300.0 + 600.0 * np.minimum(t / 0.08, 1.0)
    phase = np.cumsum(f / SR) * 2.0 * math.pi
    whoosh = np.sin(phase) * 0.30
    roar = _lp(_noise(n), 2000) * np.exp(-5.0 * t) * 0.4
    crack = _hp(_noise(n), 4000) * np.exp(-30.0 * t) * 0.3
    env = _env(n, 0.005, 0.05, 0.05, 0.7, 0.15)
    return (whoosh + roar + crack) * env

def _snd_ricochet():
    """Bullet ricochet - quick ping."""
    n = int(SR * 0.08)
    t = np.arange(n, dtype=np.float64) / SR
    f = 3000.0 + 2000.0 * np.minimum(t / 0.02, 1.0)
    phase = np.cumsum(f / SR) * 2.0 * math.pi
    ping = np.sin(phase) * 0.4
    env = np.exp(-20.0 * t)
    return ping * env

def _snd_impact():
    """Bullet impact - thud + debris."""
    n = int(SR * 0.06)
    t = np.arange(n, dtype=np.float64) / SR
    thud = np.sin(2 * np.pi * 120 * t) * np.exp(-30.0 * t) * 0.5
    debris = _hp(_noise(n), 2000) * np.exp(-50.0 * t) * 0.4
    env = np.exp(-25.0 * t)
    return (thud + debris) * env

# -- ambient generators --------------------------------------------------

def _amb_wind(n, phase_offset=0.0):
    """Wind gusts - slow brown noise with sine modulation."""
    t = np.arange(n, dtype=np.float64) / SR
    brown = _brown(n, 0.002)
    gust = 0.55 + 0.45 * np.sin(2 * np.pi * 0.08 * t + phase_offset)
    return brown * gust * 0.06

def _amb_battle(n, phase_offset=0.0):
    """Distant battle drone - low rumble + filtered noise."""
    t = np.arange(n, dtype=np.float64) / SR
    rumble = (np.sin(2 * np.pi * 35 * t + phase_offset) * 0.3
              + np.sin(2 * math.pi * 52 * t + phase_offset * 1.3) * 0.2)
    noise = _lp(_brown(n, 0.001), 200) * 0.15
    pulse = 0.6 + 0.4 * np.sin(2 * np.pi * 0.12 * t + phase_offset)
    return (rumble + noise) * pulse * 0.08

# -------------------------------------------------------------------------
#  SOUND ENGINE
# -------------------------------------------------------------------------

class SoundEngine:
    """Real-time warfare sound engine.

    API is identical to the previous engine so the rest of the game needs
    no changes.
    """

    def __init__(self, sr=SR):
        self.sr = sr
        self.enabled = False
        self.muted = False
        self.proc = None
        self.lock = threading.Lock()
        self.running = False

        # listener
        self.listener_x = 0.0
        self.view_w = 100.0

        # one-shot voice pool
        self.voices = []

        # gunfire energy accumulator
        self.gun = 0.0
        self.gun_pan = 0.0
        self.gun_w = 0.0

        # rumble overflow
        self.rumble = 0.0

        # ambient levels
        self.amb = {}

        # persistent filter / phase state
        self._gi = 0
        self._wind_ph = 0.0
        self._battle_ph = 0.0
        self._gun_f = 0.0
        self._crack = 0.0

        # pre-rendered sound buffers
        self._cache = {}
        self._build_cache()

        self._start()

    # -- pre-render all sounds -------------------------------------------

    def _build_cache(self):
        """Synthesise every one-shot sound at startup."""
        defs = {
            'shot':            _snd_rifle,
            'shot_heavy':      _snd_heavy,
            'shot_laser':      _snd_laser,
            'shot_sniper':     _snd_sniper,
            'flame':           _snd_flame,
            'shot_tank':       _snd_tank,
            'shot_mech':       _snd_mech,
            'boom_small':      _snd_boom_small,
            'boom_large':      _snd_boom_large,
            'boom_massive':    _snd_boom_massive,
            'flak':            _snd_flak,
            'blip':            _snd_blip,
            'whistle':         _snd_whistle,
            'zap':             _snd_zap,
            'horn':            _snd_horn,
            'cry':             _snd_cry,
            'swarm':           _snd_swarm,
            'missile_launch':  _snd_missile_launch,
            'ricochet':        _snd_ricochet,
            'impact':          _snd_impact,
        }
        for name, fn in defs.items():
            self._cache[name] = np.ascontiguousarray(fn(), dtype=np.float64)

    # -- boot aplay ------------------------------------------------------

    def _start(self):
        if not shutil.which('aplay'):
            return
        try:
            self.proc = subprocess.Popen(
                ['aplay', '-q', '-r', str(self.sr), '-c', '2',
                 '-f', 'S16_LE', '-t', 'raw', '-'],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
        except Exception:
            self.proc = None
        if self.proc is None:
            return
        self.enabled = True
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()

    def close(self):
        self.running = False
        proc = self.proc
        self.proc = None
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=0.5)
            except Exception:
                pass
            try:
                proc.stdin.close()
            except Exception:
                pass

    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted

    # -- game-facing API (unchanged) -------------------------------------

    def set_listener(self, x, view_w):
        self.listener_x = x
        self.view_w = max(20.0, view_w)

    def ambient(self, kind, level):
        with self.lock:
            self.amb[kind] = max(0.0, min(1.0, level))

    def event(self, kind, x=None, vol=1.0, pitch=1.0):
        if not self.enabled or self.muted:
            return
        pan = 0.0
        if x is not None:
            pan, vol = self._geo(x, vol)
        try:
            with self.lock:
                self._dispatch(kind, vol, pan, pitch, x)
        except Exception:
            pass

    # -- event dispatch --------------------------------------------------

    def _dispatch(self, kind, vol, pan, pitch, x):
        if kind == 'shot':
            self.gun = min(1.0, self.gun + 0.06 * vol)
            self.gun_pan += pan * vol
            self.gun_w += vol
        elif kind == 'boom':
            self._spawn_boom(vol, pan, pitch, x)
        elif kind == 'flak':
            self._spawn('flak', vol, pan)
        elif kind == 'blip':
            self._spawn('blip', vol, pan)
        elif kind == 'horn':
            self._spawn('horn', vol, pan)
        elif kind == 'whistle':
            self._spawn('whistle', vol, pan)
        elif kind == 'zap':
            self._spawn('zap', vol, pan)
        elif kind == 'swarm':
            self._spawn('swarm', vol, pan)
        elif kind == 'cry':
            self._spawn('cry', vol, pan)
        elif kind == 'flame':
            self._spawn('flame', vol, pan)

    def _spawn_boom(self, vol, pan, strength, x):
        active = sum(1 for v in self.voices if v['kind'].startswith('boom'))
        if active >= 4:
            self.rumble = min(1.0, self.rumble + 0.12 * vol)
            return
        st = max(0.3, min(3.0, strength))
        if st < 1.0:
            buf = self._cache['boom_small']
        elif st < 2.0:
            buf = self._cache['boom_large']
        else:
            buf = self._cache['boom_massive']
        gl, gr = _pan_coefs(pan)
        self.voices.append({
            'kind': 'boom', 'buf': buf, 'pos': 0,
            'g': vol * min(1.0, 0.6 + 0.15 * st),
            'gl': gl, 'gr': gr,
        })

    def _spawn(self, kind, vol, pan):
        buf = self._cache.get(kind)
        if buf is None:
            return
        gl, gr = _pan_coefs(pan)
        self.voices.append({
            'kind': kind, 'buf': buf, 'pos': 0,
            'g': min(1.0, vol), 'gl': gl, 'gr': gr,
        })

    # -- spatialisation --------------------------------------------------

    def _geo(self, x, vol):
        half = max(1.0, self.view_w * 0.5)
        frac = (x - self.listener_x) / half
        if abs(frac) <= 1.0:
            out = 1.0
        else:
            out = max(0.0, 1.0 - (abs(frac) - 1.0) / 3.0)
        return max(-1.0, min(1.0, frac)), vol * (0.35 + 0.65 * out)

    # -- mixer thread ----------------------------------------------------

    def _run(self):
        try:
            while self.running:
                if not self.enabled or self.muted:
                    time.sleep(0.02)
                    continue
                data = self._render(_CHUNK)
                try:
                    self.proc.stdin.write(data)
                    self.proc.stdin.flush()
                except (BrokenPipeError, OSError, ValueError):
                    self.enabled = False
                    return
        except Exception:
            self.enabled = False

    def _render(self, n):
        with self.lock:
            voices = list(self.voices)
            amb = dict(self.amb)
            gun = self.gun
            gp = self.gun_pan
            gw = self.gun_w
            rumble = self.rumble
            self.gun = 0.0
            self.gun_pan = 0.0
            self.gun_w = 0.0
            self.rumble = rumble * 0.50

        gpan = (gp / gw) if gw > 0 else 0.0
        ggl, ggr = _pan_coefs(gpan)
        gdec = math.exp(-1.0 / (0.12 * self.sr))
        crack_dec = math.exp(-1.0 / (0.015 * self.sr))
        wind_lvl = amb.get('wind', 0.0)
        battle_lvl = amb.get('drone', 0.0)

        out_l = np.zeros(n, dtype=np.float64)
        out_r = np.zeros(n, dtype=np.float64)

        # -- wind ambience -----------------------------------------------
        if wind_lvl > 0.01:
            t = np.arange(n, dtype=np.float64) / self.sr
            brown = _brown(n, 0.002)
            gust = 0.55 + 0.45 * np.sin(2 * np.pi * 0.08 * t + self._wind_ph)
            wv = brown * gust * 0.06 * wind_lvl
            out_l += wv
            out_r += wv
            self._wind_ph += 2 * np.pi * 0.08 * n / self.sr

        # -- distant battle drone ----------------------------------------
        if battle_lvl > 0.01:
            t = np.arange(n, dtype=np.float64) / self.sr
            rum = (np.sin(2 * np.pi * 35 * t + self._battle_ph) * 0.30
                   + np.sin(2 * np.pi * 52 * t + self._battle_ph * 1.3) * 0.20)
            bnoise = _lp(_brown(n, 0.001), 200) * 0.15
            pulse = 0.6 + 0.4 * np.sin(2 * np.pi * 0.12 * t + self._battle_ph)
            bv = (rum + bnoise) * pulse * 0.08 * battle_lvl
            out_l += bv
            out_r += bv
            self._battle_ph += 2 * np.pi * 0.12 * n / self.sr

        # -- gunfire bus (vectorised) ------------------------------------
        if gun > 0.003:
            gn = _pcg_noise(n, 0x9E3779B9 + (self._gi & 0xFFFFFFFF))
            a_gun = math.exp(-2.0 * math.pi * 800.0 / self.sr)
            gfiltered = _v_iir_1po(gn, a_gun)
            # crack pops: when raw noise peaks above 0.93, set crack flag
            if np.any(gn > 0.93):
                self._crack = 1.0
            crack = self._crack
            self._crack *= crack_dec
            gs = (gfiltered * 0.40 + crack * gn * 0.55) * gun
            out_l += gs * ggl
            out_r += gs * ggr

        # -- distant rumble overflow (vectorised) ------------------------
        if rumble > 0.01:
            rn = _pcg_noise(n, 0x1234567 + (self._gi & 0xFFFFFFFF))
            a_rum = math.exp(-2.0 * math.pi * 30.0 / self.sr)
            rfiltered = _v_iir_1po(rn, a_rum)
            rv = rfiltered * 0.9 * rumble
            out_l += rv
            out_r += rv

        # -- one-shots ---------------------------------------------------
        alive = []
        for v in voices:
            buf = v['buf']
            pos = v['pos']
            remaining = len(buf) - pos
            if remaining <= 0:
                continue
            take = min(n, remaining)
            chunk = buf[pos:pos + take] * v['g']
            out_l[:take] += chunk * v['gl']
            out_r[:take] += chunk * v['gr']
            v['pos'] = pos + take
            if v['pos'] < len(buf):
                alive.append(v)

        self._gi += n
        with self.lock:
            self.voices = alive

        # -- master soft-clip + stereo interleave ------------------------
        sl = np.tanh(out_l * MASTER)
        sr2 = np.tanh(out_r * MASTER)
        peak = max(np.max(np.abs(sl)), np.max(np.abs(sr2)))
        if peak > 0.95:
            scale = 0.95 / peak
            sl *= scale
            sr2 *= scale
        left = np.clip(sl * 32767, -32767, 32767).astype(np.int16)
        right = np.clip(sr2 * 32767, -32767, 32767).astype(np.int16)
        # interleave L R L R ... for aplay's S16_LE stereo
        stereo = np.empty(n * 2, dtype=np.int16)
        stereo[0::2] = left
        stereo[1::2] = right
        return stereo.tobytes()

    @staticmethod
    def _noise_pcg(i):
        """Fallback single-sample PCG noise (kept for API compat)."""
        s = (i * 2654435761 + 0x9E3779B9) & 0xFFFFFFFF
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        return (s / 0x3FFFFFFF) - 1.0
