import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import time
import math
import ctypes
import os

# 글꼴 구성
GAME_FONT = "GeekbleMalang2"


def load_custom_font(font_path):
    if not os.path.exists(font_path):
        print(f"Font file not found: {font_path}")
        return False

    res = ctypes.windll.gdi32.AddFontResourceExW(font_path, 0x10, 0)
    if res > 0:
        print(f"Successfully loaded font: {font_path}")
        return True
    else:
        print(f"Failed to load font: {font_path}")
        return False


class InputHandler:
    def __init__(self, root, canvas):
        self.keys = {}
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_pressed = False

        root.bind("<KeyPress>", self.on_key_press)
        root.bind("<KeyRelease>", self.on_key_release)
        canvas.bind("<Motion>", self.on_mouse_move)
        canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    def on_key_press(self, event):
        self.keys[event.keysym.lower()] = True

    def on_key_release(self, event):
        self.keys[event.keysym.lower()] = False

    def on_mouse_move(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y

    def on_mouse_down(self, event):
        self.mouse_pressed = True

    def on_mouse_up(self, event):
        self.mouse_pressed = False

    def is_key_pressed(self, key):
        return self.keys.get(key, False)


class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.x = 0
        self.y = 0
        self.target = None

        # 화면 흔들림
        self.shake_duration = 0
        self.shake_intensity = 0

    def follow(self, target):
        self.target = target

    def shake(self, duration, intensity):
        self.shake_duration = duration
        self.shake_intensity = intensity

    def update(self):
        if self.target:
            # 부드러운 따라가기
            target_x = self.target.x - self.width / 2
            target_y = self.target.y - self.height / 2
            self.x += (target_x - self.x) * 0.1
            self.y += (target_y - self.y) * 0.1

        # 흔들림 적용
        if self.shake_duration > 0:
            self.shake_duration -= 0.016
            import random

            offset_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            offset_y = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.x += offset_x
            self.y += offset_y

            if self.shake_duration <= 0:
                self.shake_duration = 0


class Renderer:
    def __init__(self, canvas, camera):
        self.canvas = canvas
        self.camera = camera
        self.width = int(canvas["width"])
        self.height = int(canvas["height"])

        self.buffer = Image.new("RGBA", (self.width, self.height), (32, 32, 32, 255))
        self.draw_ctx = ImageDraw.Draw(self.buffer)
        self.photo_image = None
        self.canvas_image_id = None

        self.font_cache = {}
        self.default_font_path = "assets/fonts/GeekbleMalang2TTF.ttf"  # 기본 대체

    def clear(self):
        self.draw_ctx.rectangle((0, 0, self.width, self.height), fill=(32, 32, 32, 255))

    def present(self):
        self.photo_image = ImageTk.PhotoImage(self.buffer)

        if self.canvas_image_id is None:
            self.canvas_image_id = self.canvas.create_image(
                0, 0, image=self.photo_image, anchor="nw"
            )
        else:
            self.canvas.itemconfig(self.canvas_image_id, image=self.photo_image)

    def _get_pil_color(self, color_str, alpha=255):
        if color_str.startswith("#"):
            r = int(color_str[1:3], 16)
            g = int(color_str[3:5], 16)
            b = int(color_str[5:7], 16)
            return (r, g, b, int(alpha))
        else:
            colors = {
                "white": (255, 255, 255),
                "black": (0, 0, 0),
                "red": (255, 0, 0),
                "green": (0, 255, 0),
                "blue": (0, 0, 255),
                "yellow": (255, 255, 0),
            }
            c = colors.get(color_str.lower(), (255, 255, 255))
            return (c[0], c[1], c[2], int(alpha))

    def _get_font(self, font_tuple):
        # font_tuple: (폰트체, 크기, 두께/스타일)
        family = font_tuple[0]
        size = font_tuple[1]

        key = (family, size)
        if key not in self.font_cache:
            try:
                path = "assets/fonts/GeekbleMalang2TTF.ttf"
                if not os.path.exists(path):
                    if os.path.exists("assets/fonts/GeekbleMalang2TTF.ttf"):
                        path = "assets/fonts/GeekbleMalang2TTF.ttf"
                    else:
                        self.font_cache[key] = ImageFont.load_default()
                        return self.font_cache[key]

                self.font_cache[key] = ImageFont.truetype(path, size)
            except Exception as e:
                print(f"Font load error: {e}")
                self.font_cache[key] = ImageFont.load_default()

        return self.font_cache[key]

    def draw_rect(self, x, y, w, h, color, tags=None, outline=None, width=1):
        screen_x = x - self.camera.x
        screen_y = y - self.camera.y
        fill_color = self._get_pil_color(color) if color else None
        outline_color = self._get_pil_color(outline) if outline else None
        self.draw_ctx.rectangle(
            (screen_x, screen_y, screen_x + w, screen_y + h),
            fill=fill_color,
            outline=outline_color,
            width=width,
        )

    def draw_oval(self, x, y, w, h, color, tags=None, outline=None, width=1):
        screen_x = x - self.camera.x
        screen_y = y - self.camera.y
        fill_color = self._get_pil_color(color) if color else None
        outline_color = self._get_pil_color(outline) if outline else None
        self.draw_ctx.ellipse(
            (screen_x, screen_y, screen_x + w, screen_y + h),
            fill=fill_color,
            outline=outline_color,
            width=width,
        )

    def draw_line(self, x1, y1, x2, y2, color, width=1):
        screen_x1 = x1 - self.camera.x
        screen_y1 = y1 - self.camera.y
        screen_x2 = x2 - self.camera.x
        screen_y2 = y2 - self.camera.y
        fill_color = self._get_pil_color(color)
        self.draw_ctx.line(
            (screen_x1, screen_y1, screen_x2, screen_y2), fill=fill_color, width=width
        )

    def draw_text(self, x, y, text, color="white", font=(GAME_FONT, 18)):
        screen_x = x - self.camera.x
        screen_y = y - self.camera.y
        pil_font = self._get_font(font)
        fill_color = self._get_pil_color(color)

        bbox = self.draw_ctx.textbbox((0, 0), text, font=pil_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        self.draw_ctx.text(
            (screen_x - text_w / 2, screen_y - text_h / 2),
            text,
            font=pil_font,
            fill=fill_color,
        )

    def draw_ui_text(
        self, x, y, text, color="white", font=(GAME_FONT, 24), anchor="nw"
    ):
        pil_font = self._get_font(font)
        fill_color = self._get_pil_color(color)

        bbox = self.draw_ctx.textbbox((0, 0), text, font=pil_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        draw_x, draw_y = x, y

        if anchor == "n":
            draw_x -= text_w / 2
        elif anchor == "ne":
            draw_x -= text_w
        elif anchor == "center":
            draw_x -= text_w / 2
            draw_y -= text_h / 2
        elif anchor == "e":
            draw_x -= text_w
            draw_y -= text_h / 2
        elif anchor == "w":
            draw_y -= text_h / 2
        elif anchor == "sw":
            draw_y -= text_h
        elif anchor == "s":
            draw_x -= text_w / 2
            draw_y -= text_h
        elif anchor == "se":
            draw_x -= text_w
            draw_y -= text_h

        self.draw_ctx.text((draw_x, draw_y), text, font=pil_font, fill=fill_color)

    def draw_ui_rect(self, x, y, w, h, color, outline=None, width=1):
        fill_color = self._get_pil_color(color) if color else None
        outline_color = self._get_pil_color(outline) if outline else None
        self.draw_ctx.rectangle(
            (x, y, x + w, y + h), fill=fill_color, outline=outline_color, width=width
        )

    def load_image(self, path, size=None):
        try:
            pil_image = Image.open(path).convert("RGBA")
            if size:
                pil_image = pil_image.resize(size, Image.NEAREST)
            return pil_image
        except Exception as e:
            print(f"Failed to load image {path}: {e}")
            return None

    def draw_image(self, image, x, y, anchor="center"):
        if not image:
            return

        screen_x = x - self.camera.x
        screen_y = y - self.camera.y

        iw = image.width
        ih = image.height

        draw_x = screen_x
        draw_y = screen_y

        if anchor == "center":
            draw_x -= iw / 2
            draw_y -= ih / 2

        # 경계 확인
        if (
            draw_x + iw < 0
            or draw_x > self.width
            or draw_y + ih < 0
            or draw_y > self.height
        ):
            return

        self.buffer.paste(image, (int(draw_x), int(draw_y)), image)

    def draw_image_tiled(self, image, x, y, w, h):
        if not image:
            return

        screen_x = int(x - self.camera.x)
        screen_y = int(y - self.camera.y)

        screen_w = self.width
        screen_h = self.height

        if (
            screen_x + w < 0
            or screen_x > screen_w
            or screen_y + h < 0
            or screen_y > screen_h
        ):
            return

        iw = image.width
        ih = image.height

        start_col = max(0, int((-screen_x) // iw))
        end_col = min(math.ceil(w / iw), int((screen_w - screen_x) // iw) + 1)
        start_row = max(0, int((-screen_y) // ih))
        end_row = min(math.ceil(h / ih), int((screen_h - screen_y) // ih) + 1)

        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                tx = screen_x + c * iw
                ty = screen_y + r * ih
                self.buffer.paste(image, (tx, ty), image)

    def draw_shadow(self, x, y, w, h, alpha=0.3):
        key = (w, h, alpha)
        if not hasattr(self, "shadow_cache"):
            self.shadow_cache = {}

        if key not in self.shadow_cache:
            img = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            alpha_int = int(255 * alpha)
            d.ellipse((0, 0, w, h), fill=(0, 0, 0, alpha_int))
            self.shadow_cache[key] = img

        shadow_img = self.shadow_cache[key]
        screen_x = int(x - self.camera.x)
        screen_y = int(y - self.camera.y)
        self.buffer.paste(shadow_img, (screen_x, screen_y), shadow_img)

    def draw_overlay(self, x, y, w, h, color="#000000", alpha=0.5):
        key = (w, h, color, alpha)
        if not hasattr(self, "overlay_cache"):
            self.overlay_cache = {}

        if key not in self.overlay_cache:
            c = self._get_pil_color(color, alpha * 255)
            img = Image.new("RGBA", (int(w), int(h)), c)
            self.overlay_cache[key] = img

        overlay_img = self.overlay_cache[key]
        self.buffer.paste(overlay_img, (int(x), int(y)), overlay_img)

    def draw_ui_line(self, x1, y1, x2, y2, color, width=1):
        fill_color = self._get_pil_color(color)
        self.draw_ctx.line((x1, y1, x2, y2), fill=fill_color, width=width)

    def draw_ui_oval(self, x, y, w, h, color, outline=None, width=1):
        fill_color = self._get_pil_color(color) if color else None
        outline_color = self._get_pil_color(outline) if outline else None
        self.draw_ctx.ellipse(
            (x, y, x + w, y + h), fill=fill_color, outline=outline_color, width=width
        )

    def draw_arc(self, x, y, w, h, start, extent, color, outline=None, width=1):
        screen_x = x - self.camera.x
        screen_y = y - self.camera.y
        fill_color = self._get_pil_color(color) if color else None
        outline_color = self._get_pil_color(outline) if outline else None
        end = start + extent
        self.draw_ctx.pieslice(
            (screen_x, screen_y, screen_x + w, screen_y + h),
            start=start,
            end=end,
            fill=fill_color,
            outline=outline_color,
            width=width,
        )

    def measure_text(self, text, font):
        pil_font = self._get_font(font)
        bbox = self.draw_ctx.textbbox((0, 0), text, font=pil_font)
        return bbox[2] - bbox[0]


class Game:
    def __init__(self, width=1280, height=720):
        self.root = tk.Tk()
        self.root.title("Enter the Dungeon")
        self.root.geometry(f"{width}x{height}")
        self.root.resizable(False, False)

        self.width = width
        self.height = height

        self.canvas = tk.Canvas(
            self.root, width=width, height=height, bg="#202020", highlightthickness=0
        )
        self.canvas.pack()

        self.input = InputHandler(self.root, self.canvas)
        self.camera = Camera(width, height)
        self.renderer = Renderer(self.canvas, self.camera)

        self.running = True
        self.last_time = time.time()
        self.dt = 0

        # 커서 제어
        self.cursor_locked = True
        self.root.bind("<FocusIn>", self.on_focus_in)
        self.root.bind("<FocusOut>", self.on_focus_out)

        self.entities = []
        self.bullets = []
        self.particles = []

        self.player = None
        self.dungeon = None

        self.target_fps = 60
        self.fixed_dt = 1.0 / self.target_fps
        self.accumulator = 0.0

    def start(self):
        self.last_time = time.time()
        self.game_loop()
        self.root.mainloop()

    def game_loop(self):
        if not self.running:
            return

        current_time = time.time()
        frame_time = current_time - self.last_time
        self.last_time = current_time

        if frame_time > 0.25:
            frame_time = 0.25

        self.accumulator += frame_time

        self.update_cursor()

        # 프레임 건너뛰기 로직
        while self.accumulator >= self.fixed_dt:
            self.update(self.fixed_dt)
            self.accumulator -= self.fixed_dt

        self.draw()
        self.renderer.present()

        elapsed = time.time() - current_time
        delay = max(1, int((self.fixed_dt - elapsed) * 1000))

        self.root.after(delay, self.game_loop)

    def update(self, dt):
        pass

    def draw(self):
        self.renderer.clear()
        # 그리기 로직

    def on_focus_in(self, event):
        if self.cursor_locked:
            self.lock_cursor()

    def on_focus_out(self, event):
        # 사용자가 다른 앱을 사용할 수 있도록 포커스 아웃 시 항상 잠금 해제
        self.unlock_cursor(force_visible=True)

    def lock_cursor(self):
        try:
            self.root.config(cursor="none")
            rect = RECT()
            rect.left = self.root.winfo_rootx()
            rect.top = self.root.winfo_rooty()
            rect.right = rect.left + self.width
            rect.bottom = rect.top + self.height
            ctypes.windll.user32.ClipCursor(ctypes.byref(rect))
        except Exception as e:
            print(f"Cursor lock failed: {e}")

    def unlock_cursor(self, force_visible=False):
        try:
            if force_visible or not self.cursor_locked:
                self.root.config(cursor="arrow")
            ctypes.windll.user32.ClipCursor(None)
        except Exception as e:
            print(f"Cursor unlock failed: {e}")

    def update_cursor(self):
        # Alt 키 확인
        is_alt = self.input.is_key_pressed("alt_l") or self.input.is_key_pressed(
            "alt_r"
        )

        if is_alt:
            if self.cursor_locked:
                self.cursor_locked = False
                self.unlock_cursor()
        else:
            if not self.cursor_locked:
                self.cursor_locked = True
                self.lock_cursor()
            else:
                self.lock_cursor()


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class Animation:
    def __init__(self, frames, duration=1.0, loop=True):
        self.frames = frames  # PhotoImage 목록
        self.duration = duration
        self.loop = loop
        self.timer = 0
        self.current_frame_index = 0
        self.finished = False

    def update(self, dt):
        if self.finished:
            return

        self.timer += dt
        if self.timer >= self.duration:
            if self.loop:
                self.timer %= self.duration
            else:
                self.finished = True
                self.timer = self.duration

        # 프레임 계산
        if self.frames:
            pct = self.timer / self.duration
            idx = int(pct * len(self.frames))
            if idx >= len(self.frames):
                idx = len(self.frames) - 1
            self.current_frame_index = idx

    def get_frame(self):
        if not self.frames:
            return None
        return self.frames[self.current_frame_index]
