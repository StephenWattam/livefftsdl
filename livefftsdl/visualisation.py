
import sdl2
import sdl2.ext
import colorsys
import math
from datetime import datetime

import numpy as np

DEFAULT_DELAY = 10
DEFAULT_FFT_RANGE = (-120, 0)

BAR_COLOUR = sdl2.ext.Color(100, 100, 100)
BLACK      = sdl2.ext.Color(0, 0, 0)

MIN_DELAY = 1
MAX_DELAY = 100

TEXT_MARGIN = 5
CLOCK_FORMAT = "%d/%m/%y %H:%M"

class FFTVisualisation:

    def __init__(self, surface, fft_source):

        self.surface = surface
        self.fft_src = fft_source
        self.font_manager = sdl2.ext.FontManager(sdl2.ext.Resources(__file__, "fonts").get_path("tuffy.ttf"))

        # Scan vertically
        self.scan_y             = surface.h - 1
        self._delay             = DEFAULT_DELAY
        self.fft_range          = DEFAULT_FFT_RANGE
        self.leading_line_width = 2
        self.pause              = False
        self.party_mode         = False
        self.clock              = False
        self.fft_freq_range     = 1

        # Colour settings (0-1)
        self.colour_offset = 0.94
        self.colour_range = 0.4

    def delay(self):
        sdl2.SDL_Delay(self._delay)

    def alter_delay(self, delta):
        self._delay = max(min(self._delay + delta, MAX_DELAY), MIN_DELAY)
        self._status_text(f"Delay: {self._delay}")

    def alter_colour_offset(self, delta):
        self.colour_offset = (self.colour_offset + delta) % 1
        self._status_text(f"Colour offset: {self.colour_offset:.2f}")

    def alter_colour_range(self, delta):
        self.colour_range = (self.colour_range + delta) % 2
        self._status_text(f"Colour range: {self.colour_range:.2f}")

    def toggle_pause(self):
        self.pause = not self.pause
        self._status_text(f"Pause: {self.pause}")

    def toggle_clock(self):
        self.clock = not self.clock
        self._status_text(f"Clock: {self.clock}")

    def toggle_party_mode(self):
        self.party_mode = not self.party_mode
        self._status_text(f"Party mode: {self.party_mode}")

    def alter_fft_range(self, delta):
        self.fft_freq_range = max(min(self.fft_freq_range + delta, 1), 0.1)
        self._status_text(f"FFT range: {self.fft_freq_range:.2f}")

    def set_surface(self, new_surface):
        """Called on resize event"""
        self.surface = new_surface

        sdl2.ext.fill(self.surface, BLACK)
        self.scan_y = self.surface.h - 1

    def update(self):

        # Delay and update
        # raw_buf = RAW_SOURCE.get_buffer()
        fft_buf = self.fft_src.get_buffer()
        if self.fft_freq_range < 1:
            fft_buf = fft_buf[:int(len(fft_buf) * self.fft_freq_range)]

        # Draw
        # sdl2.ext.fill(surface, BLACK)
        # render_line(surface, WHITE, raw_buf, y_zoom=10)
        # render_line(surface, WHITE, fft_buf, y_range=FFT_RANGE, y_zoom=-100)
        self._render_leading_line()
        self._render_fft_colour_line(fft_buf)


        if not self.pause:
            self.scan_y -= 1
            if self.scan_y < 0:
                self.scan_y = self.surface.h - 1
                if self.clock:
                    self._render_clock()

        if self.party_mode:
            self.colour_offset += self.colour_range * 0.001

    def _render_leading_line(self):
        """Render the black leading FFT line"""

        for i in range(max(0, self.scan_y - self.leading_line_width), self.scan_y):
            sdl2.ext.line(self.surface, BAR_COLOUR, (0, i, self.surface.w, i))


    def _render_fft_colour_line(self, buf, downsample=1):
        """Render the FFT walking colour line"""

        points = FFTVisualisation.downsample_to_fixed_length(buf, (0, self.surface.w), downsample, y_range=self.fft_range)
        pixels = sdl2.ext.pixels2d(self.surface)

        for p in points:
            pixels[p[0]][self.scan_y] = self.colour_simple(p[1])



    @staticmethod
    def downsample_to_fixed_length(buf, x_range, resolution=1, y_range=None):
        """Takes a buffer of length n and rescales it to length x,
        returning a list of (x, y) values where y is taken from the buffer
        and x represents a point in the range given"""

        skip_index = (len(buf)-1) / x_range[1] - x_range[0]
        x_samples  = range(x_range[0], x_range[1], resolution)
        indices    = [min(len(buf-1), round(skip_index * (i - x_range[0]))) for i in x_samples]
        y_values   = np.take(buf, indices)

        # Normalise if a range is given
        if y_range is not None:
            y_values   = np.clip(y_values, y_range[0], y_range[1])
            y_values   -= y_range[0]
            y_values   *= 1.0/(y_range[1] - y_range[0])

        return list(zip(x_samples, y_values))



    def _status_text(self, text):

        text_surface = self.font_manager.render(text)
        text_rect = text_surface.clip_rect

        # FIXME: draw a box instead of tons of lines.  Sheesh.
        for i in range(0, min(self.surface.h, text_rect.h + 2*TEXT_MARGIN)):
            sdl2.ext.line(self.surface, BLACK, (0, i, self.surface.w, i))
        sdl2.SDL_BlitSurface(text_surface, None, self.surface, sdl2.SDL_Rect(TEXT_MARGIN, TEXT_MARGIN))

        # # Compute position
        # if below_line:
        #     dst_y = min(self.scan_y + TEXT_MARGIN, self.surface.h - text_surface.h - TEXT_MARGIN)
        # else:
        #     dst_y = max(self.scan_y - text_surface.h - TEXT_MARGIN, 0)
        # if right_align:
        #     dst_x = max(self.surface.w - text_surface.w - TEXT_MARGIN, 0)
        # else:
        #     dst_x = TEXT_MARGIN

        # sdl2.SDL_BlitSurface(text_surface, None, self.surface, sdl2.SDL_Rect(dst_x, dst_y))

    def _render_clock(self):
        """Draw a clock in the top-right corner of the screen."""

        now = datetime.now().strftime(CLOCK_FORMAT)
        text_surface = self.font_manager.render(now)
        text_rect = text_surface.clip_rect


        dst_x = max(self.surface.w - text_surface.w - TEXT_MARGIN, 0)
        dst_y = min(TEXT_MARGIN, self.surface.h)
        sdl2.SDL_BlitSurface(text_surface, None, self.surface, sdl2.SDL_Rect(dst_x, dst_y))


    # def render_line(surface, colour, buf, y_range=None, y_pos=None, downsample=5, y_zoom=1):

    #     width      = surface.w
    #     height     = surface.h
    #     y_pos      = y_pos or int(height / 2)
    #     points = FFTVisualisation.downsample_to_fixed_length(buf, (0, width), downsample, y_range=y_range)

    #     for pa, pb in zip(points[:-1], points[1:]):
    #         sdl2.ext.line(surface, WHITE, (pa[0], int(y_pos + y_zoom * pa[1]),
    #                                        pb[0], int(y_pos + y_zoom * pb[1])))


    def colour_simple(self, x):
        """Return an SDL-compatible raw pixel value given a value from 0-1"""

        r, g, b = colorsys.hsv_to_rgb((self.colour_offset + (x ** 2) * self.colour_range) % 1,
                                      0.8,
                                      x ** 2)

        r *= 255
        g *= 255
        b *= 255

        return (int(g) << 8) + (int(b) << 16) + int(r)



