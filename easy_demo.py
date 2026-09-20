#!/usr/bin/env python3
"""Demo: the new simple API for the Spore Engine.

Shows how easy it is to make graphics & animations with the easy module.
"""
from spore_engine.easy import App
from spore_engine.core.color import Color, WHITE, RED, GREEN, CYAN, YELLOW

app = App(title="Easy Spore Demo — q=quit n=new spin")

# -- Create sprites from ASCII art ------------------------------
player = app.sprite("""
  @  
 /@\\ 
 / \\
""", x=5, y=10, fg=Color(255, 200, 100), z=5)

# -- Animate with simple method chaining ------------------------
player.move_to(70, 10).over(3).ease('bounce_out')

# -- More sprites with different animations ---------------------
player2 = app.sprite("""
 .d8b. 
 8I d8 
 `8bd8' 
""", x=20, y=3, fg=GREEN, z=5)
player2.move_to(60, 12).over(4).ease('elastic_out')
player2.scale_to(2.0).over(2).ease('back_out')

# -- Spin forever -----------------------------------------------
spinner = app.sprite("""
 /-\\ 
 |-| 
 \\-/ 
""", x=40, y=5, fg=CYAN, z=5)
spinner.spin(speed=0.5)

# -- Pulse in size ----------------------------------------------
pulser = app.sprite("""
 **** 
 *  * 
 *  * 
 **** 
""", x=10, y=5, fg=RED, z=5)
pulser.pulse(min_scale=0.6, max_scale=1.4, period=0.8)

# -- Bouncing ball (looping) -----------------------------------
ball = app.sprite(" ● ", x=30, y=2, fg=YELLOW, z=5)
ball.move_to(30, 18).over(1.0).ease('bounce_out').loop()

# -- Build programmatic sprites ---------------------------------
house = app.sprite("", x=50, y=15, fg=Color(200, 150, 100), z=3)
house.set_pixel(0, 0, '┌')
house.set_pixel(8, 0, '┐')
house.set_pixel(0, 5, '└')
house.set_pixel(8, 5, '┘')
for i in range(1, 8):
    house.set_pixel(i, 0, '─')
    house.set_pixel(i, 5, '─')
for i in range(1, 5):
    house.set_pixel(0, i, '│')
    house.set_pixel(8, i, '│')
house.set_pixel(4, 1, '┴')
house.set_pixel(4, 2, '│')
house.set_pixel(4, 3, '│')

# -- Text --------------------------------------------------------
app.text("Hello Spore!", 2, 1, WHITE, z=10)
app.text("Art Sprites + Simple Animations", 2, 2, Color(180, 180, 200), z=10)

# -- Keyboard input ----------------------------------------------
@app.on_key('n')
def on_n(app):
    spinner.spin(speed=2.0)

@app.on_key('q')
def on_q(app):
    app.running = False

if __name__ == '__main__':
    app.run()
