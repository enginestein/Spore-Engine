from __future__ import annotations
from typing import Optional, Dict
from ..core.canvas import Canvas, HiResCanvas
from ..core.color import Color, Gradient, WHITE

class Font:
    """
    Bitmap font engine for rendering large text.
    Each character is represented by a bitmap of bits.
    """
    def __init__(self, width: int, height: int, bitmap_data: Dict[str, list[int]]):
        self.width = width
        self.height = height
        self.data = bitmap_data

    def render_text(self, canvas: Canvas | HiResCanvas, text: str, x: int, y: int, 
                    scale: int = 1, fg: Optional[Color] = None, bg: Optional[Color] = None):
        """
        Renders large bitmap text.
        """
        color = fg or WHITE
        cursor_x = x
        for char in text:
            if char in self.data:
                bitmap = self.data[char]
                for col in range(self.width):
                    col_data = bitmap[col]
                    for row in range(self.height):
                        if (col_data >> row) & 1:
                            # Draw a block of scale x scale pixels
                            for dx in range(scale):
                                for dy in range(scale):
                                    canvas.set_pixel(cursor_x + col * scale + dx, 
                                                     y + row * scale + dy, 
                                                     '█', color, bg)
            cursor_x += (self.width + 1) * scale

    def render_text_gradient(self, canvas: Canvas | HiResCanvas, text: str, x: int, y: int,
                             scale: int = 1, gradient: Optional[Gradient] = None, bg: Optional[Color] = None):
        """
        Renders bitmap text filled with a gradient.
        """
        if not gradient:
            gradient = Gradient(Color(255, 0, 0), Color(255, 255, 0))
            
        cursor_x = x
        for i, char in enumerate(text):
            if char in self.data:
                bitmap = self.data[char]
                char_t = i / max(1, len(text) - 1)
                color = gradient.at(char_t)
                for col in range(self.width):
                    col_data = bitmap[col]
                    for row in range(self.height):
                        if (col_data >> row) & 1:
                            for dx in range(scale):
                                for dy in range(scale):
                                    canvas.set_pixel(cursor_x + col * scale + dx, 
                                                     y + row * scale + dy, 
                                                     '█', color, bg)
            cursor_x += (self.width + 1) * scale

    @staticmethod
    def default_5x7() -> Font:
        # 5x7 font data (columns)
        # Each int is 7 bits
        data = {
            'A': [0x7E, 0x11, 0x11, 0x11, 0x7E],
            'B': [0x7F, 0x49, 0x49, 0x49, 0x36],
            'C': [0x3E, 0x41, 0x41, 0x41, 0x22],
            'D': [0x7F, 0x41, 0x41, 0x22, 0x1C],
            'E': [0x7F, 0x49, 0x49, 0x49, 0x41],
            'F': [0x7F, 0x09, 0x09, 0x09, 0x01],
            'G': [0x3E, 0x41, 0x49, 0x49, 0x7A],
            'H': [0x7F, 0x08, 0x08, 0x08, 0x7F],
            'I': [0x00, 0x41, 0x7F, 0x41, 0x00],
            'J': [0x20, 0x40, 0x41, 0x3F, 0x01],
            'K': [0x7F, 0x08, 0x14, 0x22, 0x41],
            'L': [0x7F, 0x40, 0x40, 0x40, 0x40],
            'M': [0x7F, 0x02, 0x0C, 0x02, 0x7F],
            'N': [0x7F, 0x04, 0x08, 0x10, 0x7F],
            'O': [0x3E, 0x41, 0x41, 0x41, 0x3E],
            'P': [0x7F, 0x09, 0x09, 0x09, 0x06],
            'Q': [0x3E, 0x41, 0x51, 0x21, 0x5E],
            'R': [0x7F, 0x09, 0x19, 0x29, 0x46],
            'S': [0x46, 0x49, 0x49, 0x49, 0x31],
            'T': [0x01, 0x01, 0x7F, 0x01, 0x01],
            'U': [0x3F, 0x40, 0x40, 0x40, 0x3F],
            'V': [0x1F, 0x20, 0x40, 0x20, 0x1F],
            'W': [0x3F, 0x40, 0x38, 0x40, 0x3F],
            'X': [0x63, 0x14, 0x08, 0x14, 0x63],
            'Y': [0x07, 0x08, 0x70, 0x08, 0x07],
            'Z': [0x61, 0x51, 0x49, 0x45, 0x43],
            ' ': [0x00, 0x00, 0x00, 0x00, 0x00],
            '0': [0x3E, 0x51, 0x49, 0x45, 0x3E],
            '1': [0x00, 0x42, 0x7F, 0x40, 0x00],
            '2': [0x42, 0x61, 0x51, 0x49, 0x46],
            '3': [0x21, 0x41, 0x45, 0x4B, 0x31],
            '4': [0x18, 0x14, 0x12, 0x7F, 0x10],
            '5': [0x27, 0x45, 0x45, 0x45, 0x39],
            '6': [0x3C, 0x4A, 0x49, 0x49, 0x30],
            '7': [0x01, 0x71, 0x09, 0x05, 0x03],
            '8': [0x36, 0x49, 0x49, 0x49, 0x36],
            '9': [0x06, 0x49, 0x49, 0x29, 0x1E],
            '!': [0x00, 0x00, 0x5F, 0x00, 0x00],
            '.': [0x00, 0x60, 0x60, 0x00, 0x00],
            ',': [0x00, 0x50, 0x30, 0x00, 0x00],
            ':': [0x00, 0x36, 0x36, 0x00, 0x00],
            '?': [0x02, 0x01, 0x51, 0x09, 0x06],
            '-': [0x08, 0x08, 0x08, 0x08, 0x08],
            '+': [0x08, 0x08, 0x3E, 0x08, 0x08],
            '*': [0x14, 0x08, 0x3E, 0x08, 0x14],
        }
        return Font(5, 7, data)
