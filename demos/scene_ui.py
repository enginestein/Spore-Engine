import math
import random
from spore_engine.ui.widgets import Label, TextBox, ProgressBar, Button, Menu, Frame, WidgetManager
from spore_engine.core.color import Color, WHITE, DIM, GREEN, RED, BLUE, YELLOW
import demos as _demos

_wm = None
_msg_box = None

def scene_ui(c, hr, t, pt, dt):
    global _wm, _msg_box
    
    if _wm is None:
        _wm = WidgetManager()
        
        # Background Frame
        _wm.add(Frame(2, 2, 76, 20, title='Interactive Spore Dashboard', fg=Color(100, 100, 150)))
        
        # Info Panel
        _msg_box = _wm.add(TextBox(4, 4, 40, 6, fg=Color(200, 255, 200)))
        _msg_box.set_text("Welcome! Move the selection or use buttons to interact. Unlike before, actions only trigger when confirmed.")
        
        # Progress Bars
        _wm.add(Label(48, 4, "System Status", DIM))
        pb1 = _wm.add(ProgressBar(48, 5, 25, fg=GREEN, label='CPU'))
        pb2 = _wm.add(ProgressBar(48, 6, 25, fg=BLUE, label='RAM'))
        pb3 = _wm.add(ProgressBar(48, 7, 25, fg=RED, label='DISK'))
        
        # Interactive Buttons
        def on_click_1():
            _msg_box.set_text("Button 'Primary Action' was clicked! Real TUI feedback received.")
        
        def on_click_2():
            _msg_box.set_text("System Reset sequence initiated... Just kidding, it's just a demo!")
            
        _wm.add(Button(4, 12, 18, text="Primary Action", fg=WHITE, bg=Color(50, 50, 100), callback=on_click_1))
        _wm.add(Button(26, 12, 18, text="System Reset", fg=WHITE, bg=Color(100, 50, 50), callback=on_click_2))
        
        # Interactive Menu
        def on_menu_select(idx, text):
            _msg_box.set_text(f"Menu Item Selected: '{text}' (Index: {idx})")
            
        _wm.add(Label(4, 15, "Navigation Menu", DIM))
        _wm.add(Menu(4, 16, ["Dashboard", "Settings", "Analytics", "Logout"], callback=on_menu_select))

    # --- Interaction Logic ---
    # Since the main demo launcher handles 'up'/'down' for scene switching usually,
    # we'll use 'w'/'s' or just simulate focus/hover for the demo.
    # We'll check the global KEY_PRESSED from the engine.
    
    key = _demos.KEY_PRESSED
    if key:
        if key == 'up' or key == 'w':
            _wm.handle_event('key_down', 'up')
        elif key == 'down' or key == 's':
            _wm.handle_event('key_down', 'down')
        elif key == 'enter' or key == ' ':
            _wm.handle_event('mouse_down', (0, 0)) # Simulate click on focused
            _wm.handle_event('mouse_up', (0, 0))
            _wm.handle_event('key_down', 'enter')

    # Update progress bars with some sinus movement
    for w in _wm.widgets:
        if isinstance(w, ProgressBar):
            if w.label == 'CPU': w.set_progress(0.5 + 0.4 * math.sin(t * 1.5))
            if w.label == 'RAM': w.set_progress(0.3 + 0.2 * math.sin(t * 0.7))
            if w.label == 'DISK': w.set_progress(0.8 + 0.1 * math.sin(t * 0.2))

    for y in range(c.h):
        ty = y / c.h
        for x in range(c.w):
            n = (math.sin(x*0.02+t*0.1)+math.cos(y*0.03+t*0.08))*0.5+0.5
            c.set_pixel(x, y, ' ', bg=Color(int(5+n*6), int(4+n*4), int(10+n*12)))

    _wm.render(c, z=30)

    # Footer
    c.draw_text(2, 0, "TUI Interactive Demo", Color(200, 200, 255), z=100)
    c.draw_text(48, 16, "┌── Controls ────────────┐", DIM)
    c.draw_text(48, 17, "│ Arrows : Navigate Menu │", Color(200, 200, 255))
    c.draw_text(48, 18, "│ Enter  : Click/Select  │", Color(200, 200, 255))
    c.draw_text(48, 19, "└────────────────────────┘", DIM)
