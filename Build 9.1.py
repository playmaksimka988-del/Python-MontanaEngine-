"""
╔══════════════════════════════════════════════════════════════════╗
║  VOXEL ENGINE — Build 9.1 (branch 8.1)                           ║
║                                                                  ║
║  НОВОЕ в 9.1:                                                    ║
║  • FontManager, Theme, UIManager, Widgets                        ║
║  • Draw2D+ (text_wrap, text_shadow, rect_rounded, etc.)          ║
║  • ★ PA-анкоры — точки в GLTF-моделях (кубики с именем PA_*)     ║
║      entity.get_anchor("PA_fire") → мировая позиция              ║
║      entity.get_anchor_matrix("PA_fire") → мировая матрица       ║
║      entity.set_part_visible("mesh_name", True/False)            ║
║      entity.set_part_color("mesh_name", (r,g,b))                 ║
║  • ★ ABB-Col — авто-коллизия по частям моделей                   ║
║      В Main.py: ABB_COL = True, ABB_COL_CONFIG = {...}           ║
║      Движок сканирует части модели, создаёт AABB-коллайдеры      ║
║      Названия: Colision1, Colision2, ...                         ║
║      Настраивается include/exclude по частям                     ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys, io, os
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                                       errors='replace', line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8',
                                       errors='replace', line_buffering=True)
    except Exception:
        pass

import math, time, ctypes, random, json, struct, base64
import importlib, importlib.util, traceback
from collections import deque

import glfw
import numpy as np
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader


class Con:
    @staticmethod
    def _t(): return time.strftime("%H:%M:%S")
    @staticmethod
    def info(m):   print(f"\033[36m[{Con._t()}] [INFO]\033[0m {m}", flush=True)
    @staticmethod
    def ok(m):     print(f"\033[32m[{Con._t()}] [ OK ]\033[0m {m}", flush=True)
    @staticmethod
    def warn(m):   print(f"\033[33m[{Con._t()}] [WARN]\033[0m {m}", flush=True)
    @staticmethod
    def err(m):    print(f"\033[31m[{Con._t()}] [FAIL]\033[0m {m}", flush=True)
    @staticmethod
    def step(m):   print(f"\033[35m[{Con._t()}] [STEP]\033[0m {m}", flush=True)
    @staticmethod
    def shader(m): print(f"\033[95m[{Con._t()}] [SHADER]\033[0m {m}", flush=True)
    @staticmethod
    def plugin(m): print(f"\033[94m[{Con._t()}] [PLUGIN]\033[0m {m}", flush=True)
    @staticmethod
    def sound(m):  print(f"\033[93m[{Con._t()}] [SOUND]\033[0m {m}", flush=True)
    @staticmethod
    def mod(m):    print(f"\033[92m[{Con._t()}] [MOD]\033[0m {m}", flush=True)
    @staticmethod
    def model(m):  print(f"\033[96m[{Con._t()}] [MODEL]\033[0m {m}", flush=True)
    @staticmethod
    def anim(m):   print(f"\033[95m[{Con._t()}] [ANIM]\033[0m {m}", flush=True)
    @staticmethod
    def font(m):   print(f"\033[95m[{Con._t()}] [FONT]\033[0m {m}", flush=True)
    @staticmethod
    def ui(m):     print(f"\033[94m[{Con._t()}] [UI]\033[0m {m}", flush=True)
    @staticmethod
    def abb(m):    print(f"\033[92m[{Con._t()}] [ABB]\033[0m {m}", flush=True)
    @staticmethod
    def anchor(m): print(f"\033[96m[{Con._t()}] [ANCHOR]\033[0m {m}", flush=True)
    @staticmethod
    def sep():     print("\033[90m" + "─" * 64 + "\033[0m", flush=True)
    @staticmethod
    def banner(t):
        print()
        print("\033[96m" + "═" * 64 + "\033[0m")
        print(f"\033[96m  {t}\033[0m")
        print("\033[96m" + "═" * 64 + "\033[0m")
        print()

try:
    k = ctypes.windll.kernel32
    k.SetConsoleMode(k.GetStdHandle(-11), 7)
except Exception:
    pass


DEFAULT_CONFIG = {
    "window": {"width": 1280, "height": 720, "title": "Voxel Engine"},
    "render": {"fov": 75.0, "near": 0.1, "far": 400.0, "vsync": False,
               "frustum_culling": True, "sky_top": [0.35, 0.55, 0.85],
               "sky_bottom": [0.75, 0.85, 0.95]},
    "player": {"sensitivity": 0.003, "height": 1.7, "width": 0.6,
               "start_pos": [0.0, 40.0, 0.0]},
    "lighting": {"sun_dir": [0.55, 0.85, 0.35], "sun_color": [1.0, 0.95, 0.85],
                 "ambient": 0.35},
    "audio": {"enabled": True, "master_volume": 0.8},
    "font": {"path": "", "sizes": [16, 20, 24, 32, 48, 64]},
}

FOLDERS = ["System", "Mods", "Shaders", "Worlds", "Assets",
           "Assets/Textures", "Assets/Models", "Assets/Sounds"]

MAX_BONES = 128
ANCHOR_PREFIXES = ("PA_", "PA")


class Config:
    def __init__(self, path="config.json"):
        self.path = path
        self.data = json.loads(json.dumps(DEFAULT_CONFIG))
        self.load()
    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._merge(self.data, json.load(f))
            except Exception as e:
                Con.warn(f"Конфиг битый: {e}")
        else:
            self.save()
    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception: pass
    def _merge(self, base, over):
        for k, v in over.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._merge(base[k], v)
            else: base[k] = v
    def get(self, *keys, default=None):
        cur = self.data
        for k in keys:
            if not isinstance(cur, dict) or k not in cur: return default
            cur = cur[k]
        return cur


def clamp(v, a, b): return max(a, min(b, v))


class SoundManager:
    def __init__(self, config):
        self.enabled = config.get("audio", "enabled", default=True)
        self.master_volume = config.get("audio", "master_volume", default=0.8)
        self.backend = None; self.cache = {}
        self._init_backend()
    def _init_backend(self):
        if not self.enabled: return
        try:
            import pygame
            pygame.mixer.pre_init(44100, -16, 2, 512); pygame.mixer.init()
            self.backend = ("pygame", pygame); Con.sound("pygame.mixer"); return
        except Exception: pass
        try:
            import winsound
            self.backend = ("winsound", winsound); Con.sound("winsound"); return
        except Exception: pass
        Con.sound("Звук отключён")
    def load(self, name):
        if not self.backend: return None
        if name in self.cache: return self.cache[name]
        path = None
        for ext in (".wav", ".ogg", ".mp3", ".flac"):
            c = f"Assets/Sounds/{name}{ext}"
            if os.path.exists(c): path = c; break
        if not path: return None
        try:
            if self.backend[0] == "pygame":
                snd = self.backend[1].mixer.Sound(path)
                self.cache[name] = snd; return snd
            elif self.backend[0] == "winsound":
                self.cache[name] = path; return path
        except Exception: pass
        return None
    def play(self, name, volume=1.0, loop=False):
        if not self.backend: return
        snd = self.load(name)
        if snd is None: return
        v = clamp(self.master_volume * volume, 0.0, 1.0)
        try:
            if self.backend[0] == "pygame":
                snd.set_volume(v); snd.play(loops=-1 if loop else 0)
            elif self.backend[0] == "winsound":
                flags = self.backend[1].SND_FILENAME | self.backend[1].SND_ASYNC
                if loop: flags |= self.backend[1].SND_LOOP
                self.backend[1].PlaySound(snd, flags)
        except Exception: pass
    def play_at(self, name, src, listener, max_dist=32.0, volume=1.0):
        if not self.backend: return
        d = math.sqrt(sum((a-b)**2 for a, b in zip(src, listener)))
        if d > max_dist: return
        self.play(name, volume=volume * (1.0 - d / max_dist) ** 2)
    def stop_all(self):
        try:
            if self.backend and self.backend[0] == "pygame":
                self.backend[1].mixer.stop()
        except Exception: pass


def perspective(fovy_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2.0)
    m = np.zeros((4, 4), np.float32)
    m[0, 0] = f / aspect; m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m


def look_at(eye, center, up):
    eye = np.asarray(eye, np.float32); center = np.asarray(center, np.float32)
    up = np.asarray(up, np.float32)
    f = center - eye; f = f / (np.linalg.norm(f) + 1e-9)
    s = np.cross(f, up); s = s / (np.linalg.norm(s) + 1e-9)
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[0, 0:3] = s; m[1, 0:3] = u; m[2, 0:3] = -f
    m[0, 3] = -np.dot(s, eye); m[1, 3] = -np.dot(u, eye)
    m[2, 3] = np.dot(f, eye)
    return m


def trs_matrix(t, r, s):
    t = np.array(t, np.float32); s = np.array(s, np.float32)
    x, y, z, w = r
    xx, yy, zz = x*x, y*y, z*z
    xy, xz, yz = x*y, x*z, y*z
    wx, wy, wz = w*x, w*y, w*z
    R = np.array([
        [1 - 2*(yy+zz), 2*(xy-wz),     2*(xz+wy)],
        [2*(xy+wz),     1 - 2*(xx+zz), 2*(yz-wx)],
        [2*(xz-wy),     2*(yz+wx),     1 - 2*(xx+yy)],
    ], np.float32)
    R = R * s[None, :]
    m = np.eye(4, dtype=np.float32)
    m[0:3, 0:3] = R; m[0:3, 3] = t
    return m


def quat_slerp(a, b, t):
    a = np.array(a, np.float32); b = np.array(b, np.float32)
    dot = np.dot(a, b)
    if dot < 0.0: b = -b; dot = -dot
    if dot > 0.9995:
        r = a + t * (b - a); return r / (np.linalg.norm(r) + 1e-9)
    theta0 = math.acos(clamp(dot, -1.0, 1.0))
    theta = theta0 * t
    s0 = math.sin(theta0 - theta); s1 = math.sin(theta)
    st = math.sin(theta0)
    return (a * s0 + b * s1) / st


def model_matrix(pos, scale, rot_y=0.0, rot_x=0.0, rot_z=0.0):
    m = np.eye(4, dtype=np.float32)
    cy, sy = math.cos(rot_y), math.sin(rot_y)
    cx, sx = math.cos(rot_x), math.sin(rot_x)
    cz, sz = math.cos(rot_z), math.sin(rot_z)
    m[0, 0] = (cy*cz + sy*sx*sz) * scale
    m[0, 1] = (-cy*sz + sy*sx*cz) * scale
    m[0, 2] = (sy*cx) * scale
    m[1, 0] = (cx*sz) * scale
    m[1, 1] = (cx*cz) * scale
    m[1, 2] = -sx * scale
    m[2, 0] = (-sy*cz + cy*sx*sz) * scale
    m[2, 1] = (sy*sz + cy*sx*cz) * scale
    m[2, 2] = (cy*cx) * scale
    m[0, 3] = pos[0]; m[1, 3] = pos[1]; m[2, 3] = pos[2]
    return m


class Frustum:
    def __init__(self): self.planes = np.zeros((6, 4), np.float32)
    def from_matrix(self, m):
        self.planes[0] = m[3, :] + m[0, :]; self.planes[1] = m[3, :] - m[0, :]
        self.planes[2] = m[3, :] + m[1, :]; self.planes[3] = m[3, :] - m[1, :]
        self.planes[4] = m[3, :] + m[2, :]; self.planes[5] = m[3, :] - m[2, :]
        for i in range(6):
            n = np.linalg.norm(self.planes[i, :3])
            if n > 1e-9: self.planes[i] /= n
    def sphere_visible(self, center, radius):
        for i in range(6):
            p = self.planes[i]
            d = p[0]*center[0] + p[1]*center[1] + p[2]*center[2] + p[3]
            if d < -radius: return False
        return True


class CollisionWorld:
    def __init__(self):
        self.boxes = []; self.floors = []; self.tags = []
    def add_box(self, mnx, mny, mnz, mxx, mxy, mxz, tag=None):
        self.boxes.append((mnx, mny, mnz, mxx, mxy, mxz))
        self.tags.append(tag)
    def add_floor(self, mnx, mnz, mxx, mxz, y_top):
        self.floors.append((mnx, mnz, mxx, mxz, y_top))
    def remove_by_tag(self, tag):
        keep_b = []; keep_t = []
        for b, t in zip(self.boxes, self.tags):
            if t != tag:
                keep_b.append(b); keep_t.append(t)
        self.boxes = keep_b; self.tags = keep_t
    def clear(self):
        self.boxes.clear(); self.floors.clear(); self.tags.clear()
    def collide_aabb(self, pos, radius, height):
        px, py, pz = float(pos[0]), float(pos[1]), float(pos[2])
        pminx, pmaxx = px - radius, px + radius
        pminy, pmaxy = py, py + height
        pminz, pmaxz = pz - radius, pz + radius
        for (mnx, mny, mnz, mxx, mxy, mxz) in self.boxes:
            if (pmaxx > mnx and pminx < mxx and
                pmaxy > mny and pminy < mxy and
                pmaxz > mnz and pminz < mxz):
                return True
        return False
    def floor_below(self, pos):
        px, pz = float(pos[0]), float(pos[2]); py = float(pos[1])
        best_y = None
        for (mnx, mnz, mxx, mxz, y_top) in self.floors:
            if mnx <= px <= mxx and mnz <= pz <= mxz:
                if y_top <= py + 0.1:
                    if best_y is None or y_top > best_y: best_y = y_top
        return best_y


class Texture:
    def __init__(self, gl_id, width, height):
        self.id = gl_id; self.width = width; self.height = height
    def bind(self, unit=0):
        glActiveTexture(GL_TEXTURE0 + unit); glBindTexture(GL_TEXTURE_2D, self.id)
    def free(self):
        try: glDeleteTextures(1, [self.id])
        except Exception: pass

_texture_cache = {}

def _load_image_via_pillow(path):
    try:
        from PIL import Image
        img = Image.open(path).convert("RGBA")
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        return np.array(img, dtype=np.uint8)
    except Exception as e:
        Con.warn(f"Pillow: {e}"); return None

def load_texture(path, wrap_repeat=True, nearest=False):
    if path in _texture_cache: return _texture_cache[path]
    if not os.path.exists(path):
        Con.warn(f"Нет файла: {path}"); return None
    data = _load_image_via_pillow(path)
    if data is None:
        data = np.full((4, 4, 4), 128, dtype=np.uint8); data[:, :, 3] = 255
    h, w = data.shape[:2]
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
                    GL_NEAREST_MIPMAP_NEAREST if nearest else GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,
                    GL_NEAREST if nearest else GL_LINEAR)
    wrap = GL_REPEAT if wrap_repeat else GL_CLAMP_TO_EDGE
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap)
    try: glGenerateMipmap(GL_TEXTURE_2D)
    except Exception: pass
    glBindTexture(GL_TEXTURE_2D, 0)
    tex = Texture(tex_id, w, h); _texture_cache[path] = tex
    return tex

def _tex_from_array(data):
    h, w = data.shape[:2]
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    try: glGenerateMipmap(GL_TEXTURE_2D)
    except Exception: pass
    glBindTexture(GL_TEXTURE_2D, 0)
    return Texture(tex_id, w, h)


class Font:
    def __init__(self, path="", size=24, cell=None):
        self.size = size
        self.cell = cell if cell else size + 8
        self.charset = self._build_charset()
        self.char_map = {}; self.atlas_tex = None
        self.cols = 16
        self.rows = (len(self.charset) + self.cols - 1) // self.cols
        self._build_atlas(path, size)
    def _build_charset(self):
        chars = "".join(chr(c) for c in range(32, 127))
        chars += "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
        chars += "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        return chars
    def _build_atlas(self, font_path, size):
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            Con.warn("Pillow не установлен"); return
        candidates = []
        if font_path: candidates.append(font_path)
        candidates += ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf",
                       "C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/calibri.ttf",
                       "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        font = None
        for p in candidates:
            if os.path.exists(p):
                try:
                    font = ImageFont.truetype(p, size); break
                except Exception: continue
        if font is None:
            try: font = ImageFont.load_default()
            except Exception: return
        cell = self.cell
        aw = self.cols * cell; ah = self.rows * cell
        img = Image.new("RGBA", (aw, ah), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for i, ch in enumerate(self.charset):
            col = i % self.cols; row = i // self.cols
            x = col * cell; y = row * cell
            try:
                bbox = draw.textbbox((0, 0), ch, font=font)
                tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
                tx = x + (cell - tw)//2 - bbox[0]
                ty = y + (cell - th)//2 - bbox[1]
                draw.text((tx, ty), ch, fill=(255,255,255,255), font=font)
            except Exception: pass
            self.char_map[ch] = (col, row)
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        data = np.array(img, dtype=np.uint8)
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, aw, ah, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glBindTexture(GL_TEXTURE_2D, 0)
        self.atlas_tex = tex_id
        self.atlas_w = aw; self.atlas_h = ah
    def char_uv(self, ch):
        if ch not in self.char_map: ch = "?"
        col, row = self.char_map[ch]
        cw = 1.0 / self.cols; chh = 1.0 / self.rows
        return (col*cw, 1.0-(row+1)*chh, (col+1)*cw, 1.0-row*chh)


class FontManager:
    def __init__(self, path="", sizes=None):
        self.path = path
        self.sizes = sizes or [16, 20, 24, 32, 48, 64]
        self.fonts = {}
        for s in self.sizes:
            try: self.fonts[s] = Font(path, s)
            except Exception as e: Con.err(f"Шрифт {s}: {e}")
        Con.ok(f"FontManager: {len(self.fonts)} размеров")
    def get(self, size):
        size = int(size)
        if size in self.fonts: return self.fonts[size]
        best = min(self.fonts.keys(), key=lambda s: abs(s - size))
        return self.fonts[best]
    def text_width(self, text, size):
        return len(text) * size * 0.55


VERTEX_STRIDE = 19 * 4

class Mesh:
    def __init__(self, verts, indices, has_skin=False):
        self.verts = np.asarray(verts, np.float32)
        self.indices = np.asarray(indices, np.uint32)
        self.has_skin = has_skin
        self.vao = glGenVertexArrays(1); self.vbo = glGenBuffers(1); self.ebo = glGenBuffers(1)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.verts.nbytes, self.verts, GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.indices.nbytes, self.indices, GL_STATIC_DRAW)
        s = VERTEX_STRIDE
        glEnableVertexAttribArray(0); glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, s, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1); glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, s, ctypes.c_void_p(12))
        glEnableVertexAttribArray(2); glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, s, ctypes.c_void_p(24))
        glEnableVertexAttribArray(3); glVertexAttribPointer(3, 2, GL_FLOAT, GL_FALSE, s, ctypes.c_void_p(36))
        glEnableVertexAttribArray(4); glVertexAttribPointer(4, 4, GL_FLOAT, GL_FALSE, s, ctypes.c_void_p(44))
        glEnableVertexAttribArray(5); glVertexAttribPointer(5, 4, GL_FLOAT, GL_FALSE, s, ctypes.c_void_p(60))
        glBindVertexArray(0)
    def draw(self):
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, len(self.indices), GL_UNSIGNED_INT, None)
    def free(self):
        try:
            glDeleteBuffers(1, [self.vbo]); glDeleteBuffers(1, [self.ebo])
            glDeleteVertexArrays(1, [self.vao])
        except Exception: pass


def _vr(pos, normal, color, uv, joints=(0,0,0,0), weights=(0,0,0,0)):
    return [pos[0], pos[1], pos[2], normal[0], normal[1], normal[2],
            color[0], color[1], color[2], uv[0], uv[1],
            joints[0], joints[1], joints[2], joints[3],
            weights[0], weights[1], weights[2], weights[3]]


def make_sphere(radius=1.0, rings=16, sectors=24, color=(1,1,1)):
    verts = []; indices = []
    for r in range(rings + 1):
        phi = math.pi * r / rings
        for s in range(sectors + 1):
            theta = 2 * math.pi * s / sectors
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.cos(phi)
            z = radius * math.sin(phi) * math.sin(theta)
            inv = 1.0 / radius if radius > 0 else 0
            verts.append(_vr((x, y, z), (x*inv, y*inv, z*inv), color, (0, 0)))
    for r in range(rings):
        for s in range(sectors):
            a = r * (sectors + 1) + s; b = a + sectors + 1
            indices.extend([a, b, a+1, a+1, b, b+1])
    return Mesh(np.array(verts, np.float32), np.array(indices, np.uint32))


def make_box(size=(1.0, 1.0, 1.0), color=(1, 1, 1)):
    w, h, d = size
    hw, hh, hd = w/2, h/2, d/2
    faces = [
        ((0,0,1),  [(-hw,-hh, hd),(hw,-hh, hd),(hw,hh, hd),(-hw,hh, hd)]),
        ((0,0,-1), [(hw,-hh,-hd),(-hw,-hh,-hd),(-hw,hh,-hd),(hw,hh,-hd)]),
        ((1,0,0),  [(hw,-hh, hd),(hw,-hh,-hd),(hw,hh,-hd),(hw,hh, hd)]),
        ((-1,0,0), [(-hw,-hh,-hd),(-hw,-hh, hd),(-hw,hh, hd),(-hw,hh,-hd)]),
        ((0,1,0),  [(-hw,hh, hd),(hw,hh, hd),(hw,hh,-hd),(-hw,hh,-hd)]),
        ((0,-1,0), [(-hw,-hh,-hd),(hw,-hh,-hd),(hw,-hh, hd),(-hw,-hh, hd)]),
    ]
    verts = []; indices = []
    uvs = [(0,1),(1,1),(1,0),(0,0)]
    for n, pts in faces:
        base = len(verts)
        for i, p in enumerate(pts):
            verts.append(_vr(p, n, color, uvs[i]))
        indices.extend([base, base+1, base+2, base, base+2, base+3])
    return Mesh(np.array(verts, np.float32), np.array(indices, np.uint32))


def make_cube(size=1.0, color=(1,1,1)): return make_box((size, size, size), color)


def make_billboard(size=1.0, color=(1,1,1)):
    s = size / 2
    pts = [(-s,-s,0),(s,-s,0),(s,s,0),(-s,s,0)]
    uvs = [(0,0),(1,0),(1,1),(0,1)]
    verts = []
    for p, uv in zip(pts, uvs):
        verts.append(_vr(p, (0,0,1), color, uv))
    return Mesh(np.array(verts, np.float32), np.array([0,1,2,0,2,3], np.uint32))


def make_cylinder(radius=1.0, height=2.0, segments=24, color=(1,1,1)):
    verts = []; indices = []
    hh = height / 2
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        x = radius * math.cos(a); z = radius * math.sin(a)
        nx, nz = math.cos(a), math.sin(a)
        verts.append(_vr((x, -hh, z), (nx, 0, nz), color, (0, 0)))
        verts.append(_vr((x, hh, z), (nx, 0, nz), color, (0, 1)))
    for i in range(segments):
        a = i * 2
        indices.extend([a, a+2, a+1, a+1, a+2, a+3])
    top_c = len(verts)
    verts.append(_vr((0, hh, 0), (0, 1, 0), color, (0.5, 0.5)))
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        verts.append(_vr((radius*math.cos(a), hh, radius*math.sin(a)), (0,1,0), color, (0,0)))
    for i in range(segments):
        indices.extend([top_c, top_c+i+1, top_c+i+2])
    bot_c = len(verts)
    verts.append(_vr((0, -hh, 0), (0, -1, 0), color, (0.5, 0.5)))
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        verts.append(_vr((radius*math.cos(a), -hh, radius*math.sin(a)), (0,-1,0), color, (0,0)))
    for i in range(segments):
        indices.extend([bot_c, bot_c+i+2, bot_c+i+1])
    return Mesh(np.array(verts, np.float32), np.array(indices, np.uint32))


class Material:
    def __init__(self, color=(1,1,1), texture=None, alpha=1.0, emissive=0.0, double_sided=False):
        self.color = tuple(color); self.texture = texture
        self.alpha = alpha; self.emissive = emissive; self.double_sided = double_sided
    def bind(self):
        if self.texture: self.texture.bind(0); return 1
        return 0


class ModelMesh:
    def __init__(self, mesh, material, local_matrix=None, node_index=-1, mesh_name=""):
        self.mesh = mesh; self.material = material
        self.local_matrix = local_matrix if local_matrix is not None else np.eye(4, dtype=np.float32)
        self.node_index = node_index
        self.mesh_name = mesh_name


class AnimationChannel:
    def __init__(self, target_node, path, times, values, interpolation="LINEAR"):
        self.target_node = target_node; self.path = path
        self.times = times; self.values = values
        self.interpolation = interpolation
        self.duration = float(times[-1]) if len(times) > 0 else 0.0
    def sample(self, t):
        n = len(self.times)
        if n == 0: return None
        if t <= self.times[0]: return self.values[0]
        if t >= self.times[-1]: return self.values[-1]
        lo, hi = 0, n - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if self.times[mid] <= t: lo = mid
            else: hi = mid
        t0, t1 = self.times[lo], self.times[hi]
        span = t1 - t0
        if span < 1e-6: return self.values[hi]
        a = (t - t0) / span
        v0, v1 = self.values[lo], self.values[hi]
        if self.interpolation == "STEP": return v0
        if self.path == "rotation" and len(v0) == 4: return quat_slerp(v0, v1, a)
        return v0 * (1 - a) + v1 * a


class Animation:
    def __init__(self, name="anim"):
        self.name = name; self.channels = []; self.duration = 0.0
    def add_channel(self, ch):
        self.channels.append(ch); self.duration = max(self.duration, ch.duration)


class Model:
    def __init__(self, name="model"):
        self.name = name
        self.meshes = []
        self.animations = {}
        self.anchors = {}       # {anchor_name: local_matrix}
        self.bbox_min = np.array([1e9]*3, np.float32)
        self.bbox_max = np.array([-1e9]*3, np.float32)
    def add(self, mesh, material, local_matrix=None, node_index=-1, mesh_name=""):
        self.meshes.append(ModelMesh(mesh, material, local_matrix, node_index, mesh_name))
        v = mesh.verts[:, :3]
        if len(v) == 0: return
        if local_matrix is not None:
            hom = np.concatenate([v, np.ones((len(v), 1), np.float32)], axis=1)
            world = (local_matrix @ hom.T).T[:, :3]
        else: world = v
        self.bbox_min = np.minimum(self.bbox_min, world.min(axis=0))
        self.bbox_max = np.maximum(self.bbox_max, world.max(axis=0))
    def free(self):
        for mm in self.meshes: mm.mesh.free()


class Animator:
    def __init__(self, model):
        self.model = model; self.current = None
        self.time = 0.0; self.loop = True; self.speed = 1.0; self.playing = False
        self._default_trs = {}; self._node_children = {}; self._node_parent = {}
        self._skin_joints = []; self._skin_ibm = None
    def setup_nodes(self, children, parents):
        self._node_children = children; self._node_parent = parents
    def setup_default_trs(self, nodes):
        for i, node in enumerate(nodes):
            t = node.get("translation", [0,0,0])
            r = node.get("rotation", [0,0,0,1])
            s = node.get("scale", [1,1,1])
            self._default_trs[i] = (np.array(t, np.float32), np.array(r, np.float32), np.array(s, np.float32))
    def setup_skin(self, joints, ibm):
        self._skin_joints = joints; self._skin_ibm = ibm
    def play(self, name, loop=True, speed=1.0):
        anim = self.model.animations.get(name)
        if anim is None: return False
        self.current = anim; self.time = 0.0
        self.loop = loop; self.speed = speed; self.playing = True
        return True
    def stop(self): self.playing = False
    def update(self, dt):
        if not self.playing or self.current is None: return
        self.time += dt * self.speed
        if self.time >= self.current.duration:
            if self.loop: self.time = self.time % self.current.duration
            else: self.time = self.current.duration; self.playing = False
    def get_bone_matrices(self):
        if not self._skin_joints or self._skin_ibm is None: return None
        local_trs = {}
        for i, (t, r, s) in self._default_trs.items(): local_trs[i] = (t.copy(), r.copy(), s.copy())
        if self.current is not None:
            for ch in self.current.channels:
                val = ch.sample(self.time)
                if val is None: continue
                n = ch.target_node
                if n not in local_trs: continue
                t, r, s = local_trs[n]
                if ch.path == "translation": t = np.array(val, np.float32)
                elif ch.path == "rotation": r = np.array(val, np.float32)
                elif ch.path == "scale": s = np.array(val, np.float32)
                local_trs[n] = (t, r, s)
        world = {}
        def cw(idx, pm):
            if idx in world: return
            t, r, s = local_trs.get(idx, (np.zeros(3, np.float32),
                                          np.array([0,0,0,1], np.float32),
                                          np.ones(3, np.float32)))
            local = trs_matrix(t, r, s)
            world[idx] = pm @ local
            for c in self._node_children.get(idx, []): cw(c, world[idx])
        I = np.eye(4, dtype=np.float32)
        for i in self._default_trs.keys():
            if self._node_parent.get(i, -1) == -1: cw(i, I)
        for i in self._default_trs.keys():
            if i not in world: cw(i, I)
        result = np.zeros((MAX_BONES, 4, 4), np.float32)
        for k, j in enumerate(self._skin_joints):
            if k >= MAX_BONES: break
            w = world.get(j, I)
            ibm = self._skin_ibm[k] if k < len(self._skin_ibm) else I
            result[k] = w @ ibm
        return result


# ═══════════════════════════════════════════════════════════════════
#                       GLTF / OBJ
# ═══════════════════════════════════════════════════════════════════
_GLTF_CS = {5120:1, 5121:1, 5122:2, 5123:2, 5125:4, 5126:4}
_GLTF_DT = {5120:np.int8, 5121:np.uint8, 5122:np.int16, 5123:np.uint16, 5125:np.uint32, 5126:np.float32}
_GLTF_NC = {"SCALAR":1, "VEC2":2, "VEC3":3, "VEC4":4, "MAT2":4, "MAT3":9, "MAT4":16}


def _gacc(gltf, i, buffers):
    if i is None: return None
    acc = gltf["accessors"][i]
    if "bufferView" not in acc: return None
    bv = gltf["bufferViews"][acc["bufferView"]]
    buf = buffers[bv["buffer"]]
    cs = _GLTF_CS[acc["componentType"]]; nc = _GLTF_NC[acc["type"]]
    ne = acc["count"]; dt = _GLTF_DT[acc["componentType"]]
    bo = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    bs = bv.get("byteStride", cs * nc)
    if bs == cs * nc:
        d = np.frombuffer(buf, dtype=dt, count=ne*nc, offset=bo).reshape(ne, nc).copy()
    else:
        d = np.zeros((ne, nc), dtype=dt)
        for j in range(ne):
            d[j] = np.frombuffer(buf, dtype=dt, count=nc, offset=bo + j*bs)
    if acc.get("normalized", False) and dt != np.float32:
        if dt == np.uint8: d = d.astype(np.float32) / 255.0
        elif dt == np.uint16: d = d.astype(np.float32) / 65535.0
        elif dt == np.int8: d = np.maximum(d.astype(np.float32) / 127.0, -1.0)
        elif dt == np.int16: d = np.maximum(d.astype(np.float32) / 32767.0, -1.0)
    return d


def _guri(uri):
    if uri.startswith("data:"):
        h, d = uri.split(",", 1)
        if ";base64" in h: return base64.b64decode(d)
        return d.encode("utf-8")
    return None


def _gbu(gltf, bd, gb=None):
    bufs = []
    for b in gltf.get("buffers", []):
        if "uri" in b:
            u = b["uri"]; dec = _guri(u)
            if dec is not None: bufs.append(dec)
            else:
                p = os.path.join(bd, u)
                with open(p, "rb") as f: bufs.append(f.read())
        else: bufs.append(gb if gb is not None else b"")
    return bufs


def _gtx(gltf, ti, bd, bufs):
    if ti is None: return None
    t = gltf["textures"][ti]
    si = t.get("source")
    if si is None: return None
    img = gltf["images"][si]
    if "uri" in img:
        dec = _guri(img["uri"])
        if dec is not None:
            try:
                from PIL import Image
                import io as _io
                im = Image.open(_io.BytesIO(dec)).convert("RGBA")
                im = im.transpose(Image.FLIP_TOP_BOTTOM)
                return _tex_from_array(np.array(im, dtype=np.uint8))
            except Exception: return None
        else: return load_texture(os.path.join(bd, img["uri"]))
    elif "bufferView" in img:
        bv = gltf["bufferViews"][img["bufferView"]]
        buf = bufs[bv["buffer"]]
        off = bv.get("byteOffset", 0); ln = bv["byteLength"]
        raw = buf[off:off+ln]
        try:
            from PIL import Image
            import io as _io
            im = Image.open(_io.BytesIO(raw)).convert("RGBA")
            im = im.transpose(Image.FLIP_TOP_BOTTOM)
            return _tex_from_array(np.array(im, dtype=np.uint8))
        except Exception: return None
    return None


def _is_anchor_name(name):
    if not name: return False
    for pfx in ANCHOR_PREFIXES:
        if name == pfx or name.startswith(pfx + "_"): return True
    return False


def _gfn(gltf):
    """Возвращает список (node_idx, mesh_idx, world_matrix)."""
    res = []
    if "nodes" not in gltf: return res
    def walk(idx, p):
        n = gltf["nodes"][idx]
        if "matrix" in n:
            local = np.array(n["matrix"], np.float32).reshape(4, 4).T
        else:
            t = n.get("translation", [0,0,0])
            r = n.get("rotation", [0,0,0,1])
            s = n.get("scale", [1,1,1])
            local = trs_matrix(t, r, s)
        w = p @ local
        name = n.get("name", "")
        # Пропускаем PA-анкоры как меши (они только для анкоров)
        if "mesh" in n and not _is_anchor_name(name):
            res.append((idx, n["mesh"], w))
        for c in n.get("children", []): walk(c, w)
    sc = gltf.get("scenes", [{}])[gltf.get("scene", 0)]
    I = np.eye(4, dtype=np.float32)
    for r in sc.get("nodes", []): walk(r, I)
    return res


def _gfa(gltf):
    """Собирает PA-анкоры: {name: local_matrix}."""
    anchors = {}
    if "nodes" not in gltf: return anchors
    def walk(idx, parent):
        n = gltf["nodes"][idx]
        if "matrix" in n:
            local = np.array(n["matrix"], np.float32).reshape(4, 4).T
        else:
            t = n.get("translation", [0,0,0])
            r = n.get("rotation", [0,0,0,1])
            s = n.get("scale", [1,1,1])
            local = trs_matrix(t, r, s)
        world = parent @ local
        name = n.get("name", "")
        if _is_anchor_name(name):
            anchors[name] = world.copy()
        for child in n.get("children", []):
            walk(child, world)
    sc = gltf.get("scenes", [{}])[gltf.get("scene", 0)]
    I = np.eye(4, dtype=np.float32)
    for r in sc.get("nodes", []): walk(r, I)
    return anchors


def _gmat(gltf, mi, bd, bufs):
    if mi is None: return Material()
    m = gltf["materials"][mi]
    pbr = m.get("pbrMetallicRoughness", {})
    c = pbr.get("baseColorFactor", [1,1,1,1])
    a = c[3] if len(c) == 4 else 1.0
    if m.get("alphaMode", "OPAQUE") == "BLEND": a = min(a, 1.0)
    tex = None
    if "baseColorTexture" in pbr:
        tex = _gtx(gltf, pbr["baseColorTexture"].get("index"), bd, bufs)
    em = m.get("emissiveFactor", [0,0,0])
    emf = max(em) if isinstance(em, (list, tuple)) else 0.0
    return Material(color=(c[0], c[1], c[2]), texture=tex, alpha=a,
                    emissive=emf, double_sided=m.get("doubleSided", False))


def _gmesh(gltf, mi, bufs, bd, sd, mesh_name=""):
    gm = gltf["meshes"][mi]
    res = []
    for pi, prim in enumerate(gm.get("primitives", [])):
        if prim.get("mode", 4) != 4: continue
        at = prim.get("attributes", {})
        pos = _gacc(gltf, at.get("POSITION"), bufs)
        if pos is None: continue
        nv = len(pos)
        no = _gacc(gltf, at["NORMAL"], bufs) if "NORMAL" in at else np.zeros((nv, 3), np.float32)
        if "TEXCOORD_0" in at:
            uv = _gacc(gltf, at["TEXCOORD_0"], bufs).copy(); uv[:, 1] = 1.0 - uv[:, 1]
        else: uv = np.zeros((nv, 2), np.float32)
        if "COLOR_0" in at:
            col = _gacc(gltf, at["COLOR_0"], bufs)
            if col.shape[1] == 3:
                col = np.concatenate([col, np.ones((nv, 1), col.dtype)], axis=1)
        else: col = np.ones((nv, 4), np.float32)
        if "indices" in prim:
            idx = _gacc(gltf, prim["indices"], bufs).flatten()
        else: idx = np.arange(nv, dtype=np.uint32)
        hs = False; ja = np.zeros((nv, 4), np.float32); wa = np.zeros((nv, 4), np.float32)
        if sd is not None and "JOINTS_0" in at and "WEIGHTS_0" in at:
            ja = _gacc(gltf, at["JOINTS_0"], bufs).astype(np.float32)
            wa = _gacc(gltf, at["WEIGHTS_0"], bufs).astype(np.float32)
            hs = True
        v = np.zeros((nv, 19), np.float32)
        v[:, 0:3] = pos; v[:, 3:6] = no; v[:, 6:9] = col[:, :3]
        v[:, 9:11] = uv; v[:, 11:15] = ja; v[:, 15:19] = wa
        mesh = Mesh(v, idx.astype(np.uint32), has_skin=hs)
        mat = _gmat(gltf, prim.get("material"), bd, bufs)
        # Название части: если несколько primitive, добавляем индекс
        part_name = mesh_name if len(gm.get("primitives", [])) == 1 else f"{mesh_name}_prim{pi}"
        res.append((mesh, mat, part_name))
    return res


def load_gltf(path):
    if not os.path.exists(path):
        Con.err(f"Нет файла: {path}"); return None
    bd = os.path.dirname(os.path.abspath(path))
    with open(path, "rb") as f:
        head = f.read(4); f.seek(0)
        if head[:4] == b"glTF":
            data = f.read()
            magic, ver, ln = struct.unpack_from("<III", data, 0)
            off = 12; gj = None; gb = None
            while off < ln:
                cl, ct = struct.unpack_from("<II", data, off); off += 8
                cd = data[off:off+cl]; off += cl
                if ct == 0x4E4F534A: gj = json.loads(cd.decode("utf-8"))
                elif ct == 0x004E4942: gb = cd
            if gj is None: Con.err("GLB: нет JSON"); return None
            bufs = _gbu(gj, bd, gb)
        else:
            gj = json.load(f); bufs = _gbu(gj, bd)
    model = Model(name=os.path.basename(path))
    sd = None; nc = {}; np_ = {}
    if "nodes" in gj:
        for i, n in enumerate(gj["nodes"]):
            for c in n.get("children", []):
                nc.setdefault(i, []).append(c); np_[c] = i
    if gj.get("skins"):
        s = gj["skins"][0]
        jl = s.get("joints", []); ii = s.get("inverseBindMatrices")
        ibm = None
        if ii is not None:
            r = _gacc(gj, ii, bufs)
            if r is not None: ibm = r.reshape(-1, 4, 4).transpose(0, 2, 1).copy()
        sd = (jl, ibm)
    nodes = _gfn(gj)
    if not nodes:
        for mi in range(len(gj.get("meshes", []))):
            nodes.append((-1, mi, np.eye(4, dtype=np.float32)))
    tt = 0; tb = len(sd[0]) if sd else 0
    for ni, mi, wm in nodes:
        node_name = gj["nodes"][ni].get("name", "") if ni >= 0 else f"mesh{mi}"
        try: parts = _gmesh(gj, mi, bufs, bd, sd, node_name)
        except Exception as e:
            Con.err(f"GLTF mesh {mi}: {e}"); continue
        for m, mat, pname in parts:
            model.add(m, mat, wm, ni, pname)
            tt += len(m.indices) // 3
    for ad in gj.get("animations", []):
        anim = Animation(ad.get("name", "anim"))
        for ch in ad.get("channels", []):
            tgt = ch["target"]; ni = tgt.get("node", -1); p = tgt.get("path", "")
            if ni < 0 or p not in ("translation", "rotation", "scale"): continue
            s = ad["samplers"][ch["sampler"]]
            ts = _gacc(gj, s["input"], bufs); vs = _gacc(gj, s["output"], bufs)
            if ts is None or vs is None: continue
            anim.add_channel(AnimationChannel(ni, p, ts.flatten().astype(np.float32),
                                              vs.astype(np.float32), s.get("interpolation", "LINEAR")))
        if anim.channels: model.animations[anim.name] = anim
    # PA-анкоры
    model.anchors = _gfa(gj)
    model._nodes_data = {"nodes": gj.get("nodes", []), "children": nc, "parents": np_, "skin": sd}
    Con.model(f"GLTF: {os.path.basename(path)} — {len(model.meshes)} мешей, {tt} треуг., "
              f"{tb} костей, {len(model.animations)} анимаций, {len(model.anchors)} анкоров")
    if model.anchors:
        for aname in model.anchors.keys():
            Con.anchor(f"  {aname}")
    return model


def load_obj(path, default_color=(0.7,0.7,0.7)):
    if not os.path.exists(path):
        Con.err(f"Нет файла: {path}"); return None
    pos = []; nor = []; uvs = []; faces = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            p = line.split()
            if p[0] == "v": pos.append([float(p[1]), float(p[2]), float(p[3])])
            elif p[0] == "vn": nor.append([float(p[1]), float(p[2]), float(p[3])])
            elif p[0] == "vt": uvs.append([float(p[1]), float(p[2])])
            elif p[0] == "f":
                fc = []
                for t in p[1:]:
                    c = t.split("/")
                    vi = int(c[0]) - 1
                    ti = int(c[1]) - 1 if len(c) > 1 and c[1] else -1
                    ni = int(c[2]) - 1 if len(c) > 2 and c[2] else -1
                    fc.append((vi, ti, ni))
                faces.append(fc)
    if not pos:
        Con.err(f"OBJ пустой: {path}"); return None
    vm = {}; vd = []; idx = []
    for fc in faces:
        for i in range(1, len(fc) - 1):
            tri = [fc[0], fc[i], fc[i+1]]
            for (vi, ti, ni) in tri:
                key = (vi, ti, ni)
                if key not in vm:
                    v = pos[vi] if 0 <= vi < len(pos) else [0,0,0]
                    n = nor[ni] if 0 <= ni < len(nor) else [0,1,0]
                    uv = uvs[ti] if 0 <= ti < len(uvs) else [0,0]
                    uv = [uv[0], 1.0 - uv[1]]
                    vm[key] = len(vd); vd.append(_vr(v, n, default_color, uv))
                idx.append(vm[key])
    mesh = Mesh(np.array(vd, np.float32), np.array(idx, np.uint32))
    mat = Material(color=default_color)
    m = Model(name=os.path.basename(path))
    m.add(mesh, mat, mesh_name="default")
    Con.model(f"OBJ: {os.path.basename(path)} — {len(vd)} вершин")
    return m


# ═══════════════════════════════════════════════════════════════════
#                       ENTITY
# ═══════════════════════════════════════════════════════════════════
class Entity:
    _next_id = 1
    def __init__(self, position=(0,0,0)):
        self.id = Entity._next_id; Entity._next_id += 1
        self.position = np.array(position, np.float32)
        self.rotation = np.zeros(3, np.float32)
        self.scale = 1.0
        self.color = np.array([1,1,1], np.float32)
        self.glow = 0.0; self.emissive = False; self.billboard = False
        self.tag = None; self.alive = True; self.visible = True
        self.user_data = {}; self.on_update = None; self.submeshes = []
        self.bbox_min = np.zeros(3, np.float32); self.bbox_max = np.zeros(3, np.float32)
        self.animator = None; self.model_ref = None
    @classmethod
    def from_mesh(cls, mesh, position=(0,0,0), color=(1,1,1), glow=0.0,
                  emissive=False, tag=None, billboard=False):
        e = cls(position); mat = Material(color=color)
        e.submeshes.append((mesh, mat, np.eye(4, dtype=np.float32), -1))
        e.color = np.array(color, np.float32)
        e.glow = glow; e.emissive = emissive; e.tag = tag; e.billboard = billboard
        v = mesh.verts[:, :3]
        if len(v) > 0: e.bbox_min = v.min(axis=0); e.bbox_max = v.max(axis=0)
        return e
    @classmethod
    def from_model(cls, model, position=(0,0,0), scale=1.0, tag=None):
        e = cls(position); e.scale = scale; e.model_ref = model
        for mm in model.meshes:
            e.submeshes.append((mm.mesh, mm.material, mm.local_matrix.copy(), mm.node_index))
        e.tag = tag; e.bbox_min = model.bbox_min.copy(); e.bbox_max = model.bbox_max.copy()
        if model.animations:
            an = Animator(model)
            if hasattr(model, "_nodes_data"):
                nd = model._nodes_data
                an.setup_nodes(nd["children"], nd["parents"])
                an.setup_default_trs(nd["nodes"])
                if nd.get("skin"): an.setup_skin(nd["skin"][0], nd["skin"][1])
            e.animator = an
        return e
    def set_position(self, x, y, z): self.position[0] = x; self.position[1] = y; self.position[2] = z
    def move(self, dx, dy, dz): self.position[0] += dx; self.position[1] += dy; self.position[2] += dz
    def rotate(self, ry=0.0, rx=0.0, rz=0.0):
        self.rotation[0] += rx; self.rotation[1] += ry; self.rotation[2] += rz
    def world_matrix(self):
        return model_matrix(self.position, self.scale, self.rotation[1], self.rotation[0], self.rotation[2])
    def play_anim(self, name, loop=True, speed=1.0):
        if self.animator is None: return False
        return self.animator.play(name, loop, speed)

    # ── ANCHORS ──
    def get_anchors(self):
        """Список всех PA-анкоров модели."""
        if self.model_ref is None: return []
        return list(self.model_ref.anchors.keys())

    def get_anchor(self, name):
        """Мировая позиция анкора (numpy [x,y,z]) или None."""
        if self.model_ref is None: return None
        if name not in self.model_ref.anchors: return None
        local = self.model_ref.anchors[name]
        world = self.world_matrix() @ local
        return world[:3, 3].copy()

    def get_anchor_matrix(self, name):
        """Мировая матрица анкора (4x4) или None."""
        if self.model_ref is None: return None
        if name not in self.model_ref.anchors: return None
        return self.world_matrix() @ self.model_ref.anchors[name]

    def get_anchor_forward(self, name, fallback=(0,0,-1)):
        """Направление анкора (ось -Z анкора в мире)."""
        m = self.get_anchor_matrix(name)
        if m is None: return np.array(fallback, np.float32)
        # Ось -Z = третий столбец, взятый отрицательным
        return -m[:3, 2].copy()

    # ── PART CONTROL (real-time) ──
    def _find_part_index(self, part_name):
        if self.model_ref is None: return None
        for i, mm in enumerate(self.model_ref.meshes):
            if mm.mesh_name == part_name:
                return i
        return None

    def set_part_visible(self, part_name, visible):
        """Скрыть/показать часть модели."""
        if "_hidden_idx" not in self.user_data:
            self.user_data["_hidden_idx"] = set()
        hidden = self.user_data["_hidden_idx"]
        idxs = [i for i, mm in enumerate(self.model_ref.meshes) if mm.mesh_name == part_name] if self.model_ref else []
        for i in idxs:
            if visible: hidden.discard(i)
            else: hidden.add(i)

    def is_part_visible(self, part_name):
        idxs = [i for i, mm in enumerate(self.model_ref.meshes) if mm.mesh_name == part_name] if self.model_ref else []
        if not idxs: return False
        hidden = self.user_data.get("_hidden_idx", set())
        return not any(i in hidden for i in idxs)

    def set_part_color(self, part_name, color):
        """Изменить цвет части в реальном времени."""
        if self.model_ref is None: return
        for i, mm in enumerate(self.model_ref.meshes):
            if mm.mesh_name == part_name and i < len(self.submeshes):
                _, old_mat, local, node = self.submeshes[i]
                new_mat = Material(color=color, texture=old_mat.texture,
                                   alpha=old_mat.alpha, emissive=old_mat.emissive,
                                   double_sided=old_mat.double_sided)
                self.submeshes[i] = (self.submeshes[i][0], new_mat, local, node)
                return

    def set_part_scale_y(self, part_name, factor):
        """Растянуть часть по Y (для анимации типа 'приседание')."""
        if self.model_ref is None: return
        for i, mm in enumerate(self.model_ref.meshes):
            if mm.mesh_name == part_name and i < len(self.submeshes):
                _, mat, local, node = self.submeshes[i]
                new_local = local.copy()
                new_local[1, :] *= factor
                self.submeshes[i] = (self.submeshes[i][0], mat, new_local, node)
                return

    def free(self):
        for sm in self.submeshes: sm[0].free()


class Inventory:
    def __init__(self):
        self.hotbar = [None] * 9; self.main = [None] * 27; self.selected = 0
    def add(self, item, count=1):
        name = item[0] if isinstance(item, tuple) else item
        for i in range(9):
            s = self.hotbar[i]
            if s and s[0] == name: self.hotbar[i] = (s[0], s[1] + count); return True
        for i in range(9):
            if self.hotbar[i] is None:
                self.hotbar[i] = (item, count) if isinstance(item, tuple) else (name, count); return True
        for i in range(27):
            if self.main[i] is None:
                self.main[i] = (item, count) if isinstance(item, tuple) else (name, count); return True
        return False
    def get_selected(self):
        s = self.hotbar[self.selected]; return s[0] if s else None
    def use_selected(self, amount=1):
        s = self.hotbar[self.selected]
        if s is None: return None
        item = s[0]; nc = s[1] - amount
        if nc <= 0: self.hotbar[self.selected] = None
        else: self.hotbar[self.selected] = (item, nc)
        return item


class Player:
    def __init__(self, config):
        self.pos = np.array(config.get("player", "start_pos", default=[0,2,5]), np.float32)
        self.vel = np.zeros(3, np.float32)
        self.yaw = 0.0; self.pitch = 0.0
        self.height = config.get("player", "height", default=1.7)
        self.width = config.get("player", "width", default=0.6)
        self.speed = 8.0; self.fly = False; self.on_ground = False
        self.selected = 1; self.health = 100.0
    def forward(self):
        cp = math.cos(self.pitch)
        return np.array([math.sin(self.yaw)*cp, math.sin(self.pitch), -math.cos(self.yaw)*cp], np.float32)
    def forward_flat(self): return np.array([math.sin(self.yaw), 0.0, -math.cos(self.yaw)], np.float32)
    def right_flat(self): return np.array([math.cos(self.yaw), 0.0, math.sin(self.yaw)], np.float32)


# ═══════════════════════════════════════════════════════════════════
#                          THEMES
# ═══════════════════════════════════════════════════════════════════
THEMES = {
    "dark": {
        "bg": (0.08,0.08,0.12,0.95), "panel": (0.12,0.12,0.18,0.90),
        "border": (0.30,0.30,0.40,1.00), "text": (0.95,0.95,1.00,1.00),
        "text_dim": (0.60,0.60,0.70,1.00), "primary": (0.40,0.30,0.80,1.00),
        "primary_h": (0.55,0.45,0.95,1.00), "danger": (0.75,0.20,0.20,1.00),
        "danger_h": (0.90,0.30,0.30,1.00), "success": (0.20,0.70,0.30,1.00),
        "ghost": (0.20,0.20,0.28,0.00), "ghost_h": (0.30,0.30,0.40,0.50),
        "accent": (1.00,0.80,0.30,1.00),
    },
    "light": {
        "bg": (0.90,0.90,0.92,0.95), "panel": (0.98,0.98,1.00,0.95),
        "border": (0.30,0.30,0.40,1.00), "text": (0.10,0.10,0.15,1.00),
        "text_dim": (0.45,0.45,0.55,1.00), "primary": (0.30,0.50,0.90,1.00),
        "primary_h": (0.40,0.60,1.00,1.00), "danger": (0.85,0.25,0.25,1.00),
        "danger_h": (0.95,0.35,0.35,1.00), "success": (0.20,0.70,0.30,1.00),
        "ghost": (0.70,0.70,0.75,0.00), "ghost_h": (0.60,0.60,0.70,0.50),
        "accent": (0.90,0.60,0.10,1.00),
    },
}


class Draw2D:
    def __init__(self, engine):
        self.engine = engine; self.w = 1280; self.h = 720
    def _use(self):
        glUseProgram(self.engine._ui_prog)
        glUniform2f(self.engine._ui_u["uScreen"], self.w, self.h)
        glBindBuffer(GL_ARRAY_BUFFER, self.engine._ui_vbo)
        glBindVertexArray(self.engine._ui_vao)
    def _quad(self, x, y, w, h, color, use_tex=0, uv=(0,0,1,1)):
        u0, v0, u1, v1 = uv
        verts = np.array([x,y,u0,v0, x+w,y,u1,v0, x+w,y+h,u1,v1,
                          x,y,u0,v0, x+w,y+h,u1,v1, x,y+h,u0,v1], np.float32)
        glUniform4f(self.engine._ui_u["uColor"], *color)
        glUniform1i(self.engine._ui_u["uUseTex"], use_tex)
        glBufferSubData(GL_ARRAY_BUFFER, 0, verts.nbytes, verts)
        glDrawArrays(GL_TRIANGLES, 0, 6)
    def rect(self, x, y, w, h, color):
        if len(color) == 3: color = (*color, 1.0)
        self._use(); self._quad(x, y, w, h, color); glBindVertexArray(0)
    def rect_outline(self, x, y, w, h, color, t=2):
        if len(color) == 3: color = (*color, 1.0)
        self.rect(x, y, w, t, color); self.rect(x, y+h-t, w, t, color)
        self.rect(x, y, t, h, color); self.rect(x+w-t, y, t, h, color)
    def rect_gradient(self, x, y, w, h, top, bottom, vertical=True):
        if len(top) == 3: top = (*top, 1.0)
        if len(bottom) == 3: bottom = (*bottom, 1.0)
        steps = 16
        for i in range(steps):
            t = i / (steps - 1)
            c = tuple(top[j] * (1 - t) + bottom[j] * t for j in range(4))
            if vertical: self.rect(x, y + i*h/steps, w, h/steps + 1, c)
            else: self.rect(x + i*w/steps, y, w/steps + 1, h, c)
    def rect_rounded(self, x, y, w, h, r, color):
        if len(color) == 3: color = (*color, 1.0)
        r = min(r, w/2, h/2)
        self.rect(x + r, y, w - 2*r, h, color)
        self.rect(x, y + r, w, h - 2*r, color)
        self.circle(x + r, y + r, r, color, 8)
        self.circle(x + w - r, y + r, r, color, 8)
        self.circle(x + r, y + h - r, r, color, 8)
        self.circle(x + w - r, y + h - r, r, color, 8)
    def pixel(self, x, y, color): self.rect(x, y, 1, 1, color)
    def line(self, x1, y1, x2, y2, color, t=2):
        if len(color) == 3: color = (*color, 1.0)
        dx = x2 - x1; dy = y2 - y1
        ln = math.sqrt(dx*dx + dy*dy)
        if ln < 0.001: return
        steps = max(2, int(ln / 2))
        for i in range(steps):
            tt = i / steps
            self.rect(x1 + dx*tt - t/2, y1 + dy*tt - t/2, t, t, color)
    def circle(self, cx, cy, r, color, segments=24):
        if len(color) == 3: color = (*color, 1.0)
        self._use()
        for i in range(segments):
            a = 2 * math.pi * i / segments
            self._quad(cx + math.cos(a)*r - 1, cy + math.sin(a)*r - 1, 2, 2, color)
        glBindVertexArray(0)
    def circle_outline(self, cx, cy, r, color, t=2, segments=32):
        if len(color) == 3: color = (*color, 1.0)
        for i in range(segments):
            a = 2 * math.pi * i / segments
            self.rect(cx + math.cos(a)*r - t/2, cy + math.sin(a)*r - t/2, t, t, color)
    def panel(self, x, y, w, h, bg=(0.1,0.1,0.15,0.9), border=(0.5,0.5,0.6,1.0), bt=2):
        self.rect(x, y, w, h, bg)
        if bt > 0: self.rect_outline(x, y, w, h, border, bt)
    def progress(self, x, y, w, h, v, mv, c=(0.7,0.2,0.2,1), bg=(0.1,0.1,0.1,0.8)):
        self.rect(x, y, w, h, bg)
        if mv > 0:
            p = max(0, min(1, v / mv))
            self.rect(x, y, w * p, h, c)
    def slot(self, x, y, s, item=None, sel=False, bg=(0.1,0.1,0.1,0.7)):
        border = (1.0, 1.0, 0.2, 1.0) if sel else (0.5, 0.5, 0.5, 1.0)
        self.rect(x, y, s, s, bg)
        self.rect_outline(x, y, s, s, border, 2)
        if item:
            name = item[0] if isinstance(item, tuple) else item
            palette = {"grass": (0.30,0.72,0.25), "dirt": (0.52,0.36,0.20),
                       "stone": (0.55,0.55,0.55), "sand": (0.90,0.83,0.55),
                       "wood": (0.40,0.26,0.12), "leaves": (0.15,0.55,0.15)}
            c = palette.get(name, (1.0, 0.5, 1.0))
            self.rect(x + 8, y + 8, s - 16, s - 16, (*c, 0.9))
    def icon(self, texture, x, y, size):
        if texture is None: return
        self._use()
        glUniform4f(self.engine._ui_u["uColor"], 1, 1, 1, 1)
        glUniform1i(self.engine._ui_u["uUseTex"], 1)
        glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_2D, texture.id)
        glUniform1i(self.engine._ui_u["uTex"], 0)
        self._quad(x, y, size, size, (1,1,1,1), use_tex=1)
        glBindVertexArray(0)
    def text(self, x, y, text, size=24, color=(1,1,1,1)):
        if len(color) == 3: color = (*color, 1.0)
        if self.engine.fonts is None: return
        f = self.engine.fonts.get(size)
        if f is None: return
        self._use()
        glUniform4f(self.engine._ui_u["uColor"], *color)
        glUniform1i(self.engine._ui_u["uUseTex"], 1)
        glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_2D, f.atlas_tex)
        glUniform1i(self.engine._ui_u["uTex"], 0)
        cx = x; cy = y
        for ch in text:
            if ch == "\n": cy += size + 4; cx = x; continue
            uv = f.char_uv(ch)
            self._quad(cx, cy, size, size, color, use_tex=1, uv=uv)
            cx += size * 0.55
        glBindVertexArray(0)
    def text_shadow(self, x, y, text, size=24, color=(1,1,1,1),
                    shadow=(0,0,0,0.6), offset=(2,2)):
        self.text(x + offset[0], y + offset[1], text, size, shadow)
        self.text(x, y, text, size, color)
    def text_centered(self, cx, y, text, size=24, color=(1,1,1,1)):
        w = self.engine.text_width(text, size)
        self.text(cx - w/2, y, text, size, color)
    def text_right(self, rx, y, text, size=24, color=(1,1,1,1)):
        w = self.engine.text_width(text, size)
        self.text(rx - w, y, text, size, color)
    def text_wrap(self, x, y, w, text, size=20, color=(1,1,1,1), line_spacing=4):
        if len(color) == 3: color = (*color, 1.0)
        words = text.split(" "); line = ""; cy = y
        for word in words:
            test = line + (" " if line else "") + word
            if self.engine.text_width(test, size) > w and line:
                self.text(x, cy, line, size, color)
                cy += size + line_spacing; line = word
            else: line = test
        if line: self.text(x, cy, line, size, color)
        return cy - y + size
    def screen_size(self): return (self.w, self.h)


class Widget:
    def __init__(self, x, y, w, h):
        self.x = x; self.y = y; self.w = w; self.h = h
        self.hover = False; self.enabled = True; self.visible = True; self.value = None
    def contains(self, mx, my):
        return (self.enabled and self.visible and self.x <= mx <= self.x + self.w
                and self.y <= my <= self.y + self.h)
    def draw(self, e): pass
    def on_click(self, mx, my): pass
    def on_release(self, mx, my): pass
    def on_drag(self, mx, my): pass
    def on_key(self, key): pass


class UIButton(Widget):
    def __init__(self, x, y, w, h, text, callback, style="default", font_size=24):
        super().__init__(x, y, w, h)
        self.text = text; self.callback = callback
        self.style = style; self.font_size = font_size; self.pressed = False
    def draw(self, e):
        if not self.visible: return
        t = e.ui.theme
        if self.style == "primary": bg = t["primary_h"] if self.hover else t["primary"]
        elif self.style == "danger": bg = t["danger_h"] if self.hover else t["danger"]
        elif self.style == "success": bg = t["success"]
        elif self.style == "ghost": bg = t["ghost_h"] if self.hover else t["ghost"]
        else: bg = t["primary_h"] if self.hover else t["panel"]
        e.rect_rounded(self.x, self.y, self.w, self.h, 6, bg)
        e.rect_outline(self.x, self.y, self.w, self.h, t["border"], 2)
        tw = e.text_width(self.text, self.font_size)
        e.text(self.x + (self.w - tw)/2, self.y + (self.h - self.font_size)/2,
               self.text, self.font_size, t["text"])
    def on_click(self, mx, my): self.pressed = True
    def on_release(self, mx, my):
        if self.pressed and self.contains(mx, my) and self.callback: self.callback()
        self.pressed = False


class UILabel(Widget):
    def __init__(self, x, y, w, h, text, style="body", color=None):
        super().__init__(x, y, w, h)
        self.text = text; self.style = style; self.color = color
        self.font_size = {"h1":48, "h2":32, "h3":24, "body":20, "caption":14}.get(style, 20)
    def draw(self, e):
        if not self.visible: return
        c = self.color or e.ui.theme["text"]
        e.text(self.x, self.y, self.text, self.font_size, c)


class UICheckbox(Widget):
    def __init__(self, x, y, w, h, text, value=False, callback=None):
        super().__init__(x, y, w, h)
        self.text = text; self.value = value; self.callback = callback
    def draw(self, e):
        if not self.visible: return
        t = e.ui.theme
        bs = min(self.h, 24); by = self.y + (self.h - bs)/2
        e.rect(self.x, by, bs, bs, t["panel"])
        e.rect_outline(self.x, by, bs, bs, t["border"], 2)
        if self.value: e.rect(self.x + 4, by + 4, bs - 8, bs - 8, t["primary"])
        e.text(self.x + bs + 10, self.y + (self.h - 20)/2, self.text, 20, t["text"])
    def on_click(self, mx, my):
        self.value = not self.value
        if self.callback: self.callback(self.value)


class UISlider(Widget):
    def __init__(self, x, y, w, h, label, min_v, max_v, value, callback=None):
        super().__init__(x, y, w, h)
        self.label = label; self.min_v = min_v; self.max_v = max_v
        self.value = value; self.callback = callback; self.dragging = False
    def draw(self, e):
        if not self.visible: return
        t = e.ui.theme
        e.text(self.x, self.y - 4, self.label, 16, t["text_dim"])
        ty = self.y + 20
        e.rect(self.x, ty, self.w, 6, t["panel"])
        pct = (self.value - self.min_v) / (self.max_v - self.min_v) if self.max_v > self.min_v else 0
        e.rect(self.x, ty, self.w * pct, 6, t["primary"])
        e.circle(self.x + self.w * pct, ty + 3, 10, t["primary"])
        e.text(self.x + self.w + 10, self.y + 10, f"{int(self.value)}", 16, t["text"])
    def on_click(self, mx, my): self.dragging = True; self._upd(mx)
    def on_drag(self, mx, my):
        if self.dragging: self._upd(mx)
    def on_release(self, mx, my): self.dragging = False
    def _upd(self, mx):
        pct = clamp((mx - self.x) / self.w, 0, 1)
        self.value = self.min_v + pct * (self.max_v - self.min_v)
        if self.callback: self.callback(self.value)


class UITextInput(Widget):
    def __init__(self, x, y, w, h, placeholder="", value="", callback=None):
        super().__init__(x, y, w, h)
        self.placeholder = placeholder; self.value = value
        self.callback = callback; self.focused = False; self.cursor_t = 0.0
    def draw(self, e):
        if not self.visible: return
        t = e.ui.theme
        bg = t["primary_h"] if self.focused else t["panel"]
        e.rect(self.x, self.y, self.w, self.h, bg)
        e.rect_outline(self.x, self.y, self.w, self.h,
                       t["primary"] if self.focused else t["border"], 2)
        text = self.value if self.value else self.placeholder
        c = t["text"] if self.value else t["text_dim"]
        e.text(self.x + 10, self.y + (self.h - 20)/2, text, 20, c)
        if self.focused and int(self.cursor_t * 2) % 2 == 0:
            cx = self.x + 10 + e.text_width(self.value, 20)
            e.rect(cx, self.y + 8, 2, self.h - 16, t["text"])
    def on_click(self, mx, my): self.focused = True
    def on_key(self, key):
        if not self.focused: return
        if key == glfw.KEY_BACKSPACE: self.value = self.value[:-1]
        elif key == glfw.KEY_ENTER:
            if self.callback: self.callback(self.value)
            self.focused = False
        else:
            ch = None
            if glfw.KEY_A <= key <= glfw.KEY_Z:
                ch = chr(key - glfw.KEY_A + ord('a'))
            elif glfw.KEY_0 <= key <= glfw.KEY_9:
                ch = chr(key - glfw.KEY_0 + ord('0'))
            elif key == glfw.KEY_SPACE: ch = ' '
            if ch: self.value += ch


class UIProgressBar(Widget):
    def __init__(self, x, y, w, h, value=0.0, max_value=1.0, color=None):
        super().__init__(x, y, w, h)
        self.value = value; self.max_value = max_value; self.color = color
    def draw(self, e):
        if not self.visible: return
        t = e.ui.theme
        c = self.color or t["primary"]
        e.progress(self.x, self.y, self.w, self.h, self.value, self.max_value, c, t["panel"])


class UIImage(Widget):
    def __init__(self, x, y, w, h, texture):
        super().__init__(x, y, w, h); self.texture = texture
    def draw(self, e):
        if not self.visible or self.texture is None: return
        e.icon(self.texture, self.x, self.y, min(self.w, self.h))


class UIDivider(Widget):
    def __init__(self, x, y, w): super().__init__(x, y, w, 2)
    def draw(self, e): e.rect(self.x, self.y, self.w, 1, e.ui.theme["border"])


class UIList(Widget):
    def __init__(self, x, y, w, h, items, on_select=None, item_h=32):
        super().__init__(x, y, w, h)
        self.items = items; self.on_select = on_select
        self.item_h = item_h; self.scroll = 0.0; self.selected = -1
    def draw(self, e):
        if not self.visible: return
        t = e.ui.theme
        e.rect(self.x, self.y, self.w, self.h, t["panel"])
        e.rect_outline(self.x, self.y, self.w, self.h, t["border"], 2)
        vc = int(self.h / self.item_h); st = int(self.scroll)
        for i in range(st, min(st + vc + 1, len(self.items))):
            iy = self.y + (i - st) * self.item_h
            if i == self.selected:
                e.rect(self.x + 2, iy + 2, self.w - 4, self.item_h - 4, t["primary"])
            e.text(self.x + 10, iy + (self.item_h - 20)/2, str(self.items[i]), 20, t["text"])
    def on_click(self, mx, my):
        rel = (my - self.y) / self.item_h + self.scroll
        i = int(rel)
        if 0 <= i < len(self.items):
            self.selected = i
            if self.on_select: self.on_select(i, self.items[i])


class UIDialog(Widget):
    def __init__(self, w, h, title, text, buttons, on_close=None):
        super().__init__(0, 0, w, h)
        self.title = title; self.text = text
        self.buttons = buttons; self.on_close = on_close; self._btns = []
    def build(self, e):
        sw, sh = e.screen_size()
        dw = min(500, sw - 100); dh = 220
        dx = (sw - dw)/2; dy = (sh - dh)/2
        self.x, self.y, self.w, self.h = dx, dy, dw, dh
        self._btns = []
        bw = (dw - 40 - 10 * (len(self.buttons) - 1)) / len(self.buttons)
        for i, (label, cb) in enumerate(self.buttons):
            bx = dx + 20 + i * (bw + 10)
            by = dy + dh - 70
            self._btns.append(UIButton(bx, by, bw, 50, label, cb, style="primary"))
    def draw(self, e):
        if not self.visible: return
        t = e.ui.theme
        sw, sh = e.screen_size()
        e.rect(0, 0, sw, sh, (0, 0, 0, 0.7))
        e.panel(self.x, self.y, self.w, self.h, t["bg"], t["border"], 3)
        e.text(self.x + 20, self.y + 20, self.title, 32, t["text"])
        e.rect(self.x + 20, self.y + 65, self.w - 40, 1, t["border"])
        e.text_wrap(self.x + 20, self.y + 80, self.w - 40, self.text, 20, t["text"])
        for b in self._btns: b.draw(e)


class UIMenu:
    def __init__(self, e, title, subtitle=None):
        self.e = e; self.title = title; self.subtitle = subtitle
        self.y = 300; self.spacing = 15; self.widgets = []
    def header(self):
        sw, sh = self.e.screen_size()
        t = self.e.ui.theme
        if self.title: self.e.text_centered(sw/2, 150, self.title, 64, t["text"])
        if self.subtitle: self.e.text_centered(sw/2, 230, self.subtitle, 20, t["text_dim"])
    def button(self, text, callback, style="default", width=300, height=60):
        sw, sh = self.e.screen_size()
        x = (sw - width)/2
        b = UIButton(x, self.y, width, height, text, callback, style=style)
        self.e.ui.add(b); self.widgets.append(b); self.y += height + self.spacing
        return b


class UIManager:
    def __init__(self, engine):
        self.engine = engine
        self.theme = dict(THEMES["dark"])
        self.widgets = []
        self.active = None
        self.modal = None
    def set_theme(self, name_or_dict):
        if isinstance(name_or_dict, str): self.theme = dict(THEMES.get(name_or_dict, THEMES["dark"]))
        elif isinstance(name_or_dict, dict): self.theme = dict(name_or_dict)
    def add(self, w): self.widgets.append(w); return w
    def clear(self):
        self.widgets.clear(); self.active = None; self.modal = None
    def begin_menu(self, title, subtitle=None):
        m = UIMenu(self.engine, title, subtitle); m.header(); return m
    def dialog(self, title, text, buttons):
        d = UIDialog(0, 0, 500, 250, title, text, buttons); d.build(self.engine)
        self.modal = d; return d
    def button(self, x, y, w, h, text, cb, style="default", fs=24):
        return self.add(UIButton(x, y, w, h, text, cb, style, fs))
    def label(self, x, y, text, style="body"):
        return self.add(UILabel(x, y, 300, 30, text, style))
    def checkbox(self, x, y, w, h, text, value=False, cb=None):
        return self.add(UICheckbox(x, y, w, h, text, value, cb))
    def slider(self, x, y, w, h, label, mn, mx, v, cb=None):
        return self.add(UISlider(x, y, w, h, label, mn, mx, v, cb))
    def text_input(self, x, y, w, h, ph="", v="", cb=None):
        return self.add(UITextInput(x, y, w, h, ph, v, cb))
    def progress_bar(self, x, y, w, h, v=0.0, mv=1.0, c=None):
        return self.add(UIProgressBar(x, y, w, h, v, mv, c))
    def image(self, x, y, w, h, tex): return self.add(UIImage(x, y, w, h, tex))
    def divider(self, x, y, w): return self.add(UIDivider(x, y, w))
    def list_widget(self, x, y, w, h, items, on_sel=None):
        return self.add(UIList(x, y, w, h, items, on_sel))
    def update(self, dt):
        for w in self.widgets:
            if isinstance(w, UITextInput): w.cursor_t += dt
    def draw(self, w, h):
        for wg in self.widgets:
            try: wg.draw(self.engine)
            except Exception as e: Con.err(f"UI draw: {e}")
        if self.modal:
            try: self.modal.draw(self.engine)
            except Exception as e: Con.err(f"Dialog: {e}")
    def on_click(self, mx, my):
        if self.modal:
            for b in self.modal._btns:
                if b.contains(mx, my): b.on_click(mx, my); return True
            return True
        for w in reversed(self.widgets):
            if w.contains(mx, my):
                w.on_click(mx, my); self.active = w; return True
        for w in self.widgets:
            if isinstance(w, UITextInput): w.focused = False
        return False
    def on_release(self, mx, my):
        if self.active:
            self.active.on_release(mx, my); self.active = None
    def on_mouse_move(self, mx, my):
        if self.active and hasattr(self.active, "on_drag"): self.active.on_drag(mx, my)
        for w in self.widgets: w.hover = w.contains(mx, my)
    def on_key(self, key):
        for w in self.widgets:
            if isinstance(w, UITextInput) and w.focused:
                w.on_key(key); return True
        return False


# ═══════════════════════════════════════════════════════════════════
#                       ШЕЙДЕРЫ
# ═══════════════════════════════════════════════════════════════════
MESH_VERT = f"""#version 460 core
layout(location=0) in vec3 aPos;
layout(location=1) in vec3 aNormal;
layout(location=2) in vec3 aColor;
layout(location=3) in vec2 aUV;
layout(location=4) in vec4 aJoints;
layout(location=5) in vec4 aWeights;
uniform mat4 uMVP;
uniform mat4 uModel;
uniform vec3 uCameraRight;
uniform vec3 uCameraUp;
uniform int  uBillboard;
uniform int  uHasSkin;
uniform mat4 uBones[{MAX_BONES}];
out vec3 vColor;
out vec3 vNormal;
out vec2 vUV;
out vec3 vWorldPos;
void main() {{
    vec3 pos = aPos;
    vec3 nrm = aNormal;
    if (uHasSkin == 1) {{
        mat4 skin = mat4(0.0);
        skin += uBones[int(aJoints.x)] * aWeights.x;
        skin += uBones[int(aJoints.y)] * aWeights.y;
        skin += uBones[int(aJoints.z)] * aWeights.z;
        skin += uBones[int(aJoints.w)] * aWeights.w;
        pos = (skin * vec4(aPos, 1.0)).xyz;
        nrm = (skin * vec4(aNormal, 0.0)).xyz;
    }}
    if (uBillboard == 1) pos = uCameraRight * pos.x + uCameraUp * pos.y;
    vec4 wp = uModel * vec4(pos, 1.0);
    vWorldPos = wp.xyz;
    vColor = aColor;
    vNormal = normalize(mat3(uModel) * nrm);
    vUV = aUV;
    gl_Position = uMVP * wp;
}}"""

MESH_FRAG = """#version 460 core
in vec3 vColor;
in vec3 vNormal;
in vec2 vUV;
in vec3 vWorldPos;
uniform vec3 uSunDir;
uniform vec3 uSunColor;
uniform vec3 uAmbient;
uniform vec3 uColorMul;
uniform float uGlow;
uniform float uAlpha;
uniform int uHasTexture;
uniform sampler2D uTexture;
out vec4 FragColor;
void main() {
    vec3 albedo = vColor * uColorMul;
    if (uHasTexture == 1) albedo *= texture(uTexture, vUV).rgb;
    float ndotl = max(dot(normalize(vNormal), normalize(uSunDir)), 0.0);
    vec3 diffuse = albedo * (uAmbient + (1.0 - uAmbient) * ndotl) * uSunColor * 0.9;
    vec3 emissive = albedo * uGlow;
    vec3 color = diffuse + emissive;
    color = color / (1.0 + color * 0.25);
    FragColor = vec4(color, uAlpha);
}"""

SKY_VERT = """#version 460 core
layout(location=0) in vec2 aPos;
out vec2 vUV;
void main() { vUV = aPos * 0.5 + 0.5; gl_Position = vec4(aPos, 0.9999, 1.0); }"""

SKY_FRAG = """#version 460 core
in vec2 vUV;
uniform vec3 uTop;
uniform vec3 uBottom;
out vec4 FragColor;
void main() { FragColor = vec4(mix(uBottom, uTop, vUV.y), 1.0); }"""

UI_VERT = """#version 460 core
layout(location=0) in vec2 aPos;
layout(location=1) in vec2 aUV;
uniform vec2 uScreen;
uniform vec2 uPos;
uniform vec2 uSize;
out vec2 vUV;
void main() {
    vec2 p = (aPos * uSize + uPos) / uScreen * 2.0 - 1.0;
    p.y = -p.y;
    gl_Position = vec4(p, 0.0, 1.0);
    vUV = aUV;
}"""

UI_FRAG = """#version 460 core
in vec2 vUV;
uniform vec4 uColor;
uniform int uUseTex;
uniform sampler2D uTex;
out vec4 FragColor;
void main() {
    if (uUseTex == 1) {
        float a = texture(uTex, vUV).a;
        FragColor = vec4(uColor.rgb, uColor.a * a);
    } else FragColor = uColor;
}"""


def compile_shader_pair(vs, fs):
    v = compileShader(vs, GL_VERTEX_SHADER); f = compileShader(fs, GL_FRAGMENT_SHADER)
    p = compileProgram(v, f); glDeleteShader(v); glDeleteShader(f); return p


def make_fbo(w, h, with_depth=True):
    fbo = glGenFramebuffers(1); glBindFramebuffer(GL_FRAMEBUFFER, fbo)
    color = glGenTextures(1); glBindTexture(GL_TEXTURE_2D, color)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, color, 0)
    depth_tex = None
    if with_depth:
        depth_tex = glGenTextures(1); glBindTexture(GL_TEXTURE_2D, depth_tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT24, w, h, 0, GL_DEPTH_COMPONENT, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depth_tex, 0)
    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    return fbo, color, depth_tex


class ShaderChain:
    def __init__(self, plugins):
        self.plugins = plugins
        self.scene_fbo = None; self.scene_color = None; self.scene_depth = None
        self.ping_fbo = None; self.ping_color = None
        self.width = 0; self.height = 0; self.vao = None
        self._bq()
    def _bq(self):
        self.vao = glGenVertexArrays(1); vbo = glGenBuffers(1)
        verts = np.array([-1,-1,0,0, 1,-1,1,0, 1,1,1,1,
                          -1,-1,0,0, 1,1,1,1, -1,1,0,1], np.float32)
        glBindVertexArray(self.vao); glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0); glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1); glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(8))
        glBindVertexArray(0); self.vbo = vbo
    def ensure_size(self, w, h):
        if self.width == w and self.height == h: return
        self.width, self.height = w, h
        if self.scene_fbo is not None:
            glDeleteFramebuffers(1, [self.scene_fbo]); glDeleteTextures(1, [self.scene_color])
            if self.scene_depth: glDeleteTextures(1, [self.scene_depth])
            glDeleteFramebuffers(1, [self.ping_fbo]); glDeleteTextures(1, [self.ping_color])
        self.scene_fbo, self.scene_color, self.scene_depth = make_fbo(w, h, True)
        self.ping_fbo, self.ping_color, _ = make_fbo(w, h, False)
    def bind_scene(self, w, h):
        self.ensure_size(w, h); glBindFramebuffer(GL_FRAMEBUFFER, self.scene_fbo)
    def unbind(self): glBindFramebuffer(GL_FRAMEBUFFER, 0)
    def apply(self, ctx):
        if not self.plugins: return
        glDisable(GL_DEPTH_TEST); glDisable(GL_CULL_FACE); glDisable(GL_BLEND)
        glBindVertexArray(self.vao); glViewport(0, 0, self.width, self.height)
        src = self.scene_color
        for i, p in enumerate(self.plugins):
            last = (i == len(self.plugins) - 1)
            glBindFramebuffer(GL_FRAMEBUFFER, 0 if last else self.ping_fbo)
            glUseProgram(p.program)
            glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_2D, src)
            p.set_uniform("uScene", 0)
            if p.needs_depth and self.scene_depth:
                glActiveTexture(GL_TEXTURE1); glBindTexture(GL_TEXTURE_2D, self.scene_depth)
                p.set_uniform("uDepth", 1)
            p.set_uniform("uTime", ctx.get("time", 0))
            p.set_uniform("uResolution", ctx.get("resolution", (0,0)))
            p.set_uniform("uCameraPos", ctx.get("camera_pos", (0,0,0)))
            p.set_uniform("uCameraDir", ctx.get("camera_dir", (0,0,0)))
            p.set_uniform("uNear", ctx.get("near", 0.1))
            p.set_uniform("uFar", ctx.get("far", 400.0))
            p.set_uniform("uSunDir", ctx.get("sun_dir", (0,1,0)))
            p.set_uniform("uSunColor", ctx.get("sun_color", (1,1,1)))
            p.set_uniform("uFade", ctx.get("fade", 0.0))
            glDrawArrays(GL_TRIANGLES, 0, 6)
            if not last: src = self.ping_color
        glBindVertexArray(0); glUseProgram(0)
        glEnable(GL_DEPTH_TEST); glEnable(GL_CULL_FACE)


class ShaderPlugin:
    def __init__(self, name, path, module):
        self.name = getattr(module, "SHADER_NAME", name)
        self.author = getattr(module, "SHADER_AUTHOR", "unknown")
        self.desc = getattr(module, "SHADER_DESC", "")
        self.version = getattr(module, "SHADER_VERSION", "1.0")
        self.order = getattr(module, "SHADER_ORDER", 0)
        self.needs_depth = getattr(module, "NEEDS_DEPTH", False)
        self.module = module
        vs = getattr(module, "VERT_SRC", None); fs = getattr(module, "FRAG_SRC", None)
        self.program = compile_shader_pair(vs, fs) if vs and fs else None
        self.uniforms = {}
        if self.program:
            for a in getattr(module, "UNIFORMS", []):
                self.uniforms[a] = glGetUniformLocation(self.program, a)
        self.on_load = getattr(module, "on_load", None)
        self.on_frame = getattr(module, "on_frame", None)
        self.on_unload = getattr(module, "on_unload", None)
    def set_uniform(self, name, value):
        loc = self.uniforms.get(name)
        if loc is None or loc == -1: return
        if isinstance(value, bool): glUniform1i(loc, int(value))
        elif isinstance(value, int): glUniform1i(loc, value)
        elif isinstance(value, float): glUniform1f(loc, value)
        elif isinstance(value, (tuple, list)):
            if len(value) == 2: glUniform2f(loc, *value)
            elif len(value) == 3: glUniform3f(loc, *value)
            elif len(value) == 4: glUniform4f(loc, *value)


_ADDED_PATHS = set()
def _ensure_path(p):
    ap = os.path.abspath(p)
    if ap not in _ADDED_PATHS and os.path.isdir(ap):
        sys.path.insert(0, ap); _ADDED_PATHS.add(ap)
def _ensure_package(d):
    if not os.path.isdir(d): return
    i = os.path.join(d, "__init__.py")
    if not os.path.exists(i):
        try:
            with open(i, "w", encoding="utf-8") as f: f.write("# auto-generated\n")
        except Exception: pass
def _purge(pfx):
    for n in list(sys.modules.keys()):
        for p in pfx:
            if n == p or n.startswith(p + "."): del sys.modules[n]; break


def load_main_system(engine):
    sd = os.path.abspath("System"); par = os.path.dirname(sd)
    _ensure_path(par); _ensure_path(sd); _ensure_package(sd)
    mp = os.path.join(sd, "Main.py")
    if not os.path.exists(mp): return False
    try:
        _purge(["System"])
        import System
        import System.Main
        mod = sys.modules["System.Main"]
        engine.systems.append(mod)
        for n in list(sys.modules.keys()):
            if n.startswith("System."): engine.modules[n] = sys.modules[n]
        sn = getattr(mod, "SYSTEM_NAME", "Main")
        sv = getattr(mod, "SYSTEM_VERSION", "1.0")
        sa = getattr(mod, "SYSTEM_AUTHOR", "unknown")
        Con.plugin(f"System/Main.py: {sn} v{sv} (автор: {sa})")
        # Читаем ABB_COL настройки ДО on_engine_start
        abb_col = getattr(mod, "ABB_COL", False)
        if abb_col:
            cfg = getattr(mod, "ABB_COL_CONFIG", {})
            engine.configure_abb_col(True, cfg)
        if hasattr(mod, "on_engine_start"): mod.on_engine_start(engine)
        return True
    except Exception as e:
        Con.err(f"Main.py: {e}"); traceback.print_exc(); return False


def load_mods(engine):
    md = os.path.abspath("Mods")
    if not os.path.isdir(md): return
    _ensure_path(md)
    for d in sorted(os.listdir(md)):
        dp = os.path.join(md, d)
        if not os.path.isdir(dp) or d.startswith("_") or d.startswith("."): continue
        mf = os.path.join(dp, "mod.py")
        if not os.path.exists(mf): continue
        _ensure_package(dp)
        try:
            _purge([d])
            importlib.import_module(d)
            mod = importlib.import_module(f"{d}.mod")
            engine.mods.append(mod)
            for n in list(sys.modules.keys()):
                if n == d or n.startswith(d + "."): engine.modules[n] = sys.modules[n]
            mn = getattr(mod, "MOD_NAME", d); mv = getattr(mod, "MOD_VERSION", "1.0")
            ma = getattr(mod, "MOD_AUTHOR", "unknown")
            Con.mod(f"Загружен: {mn} v{mv} (автор: {ma})")
            if hasattr(mod, "on_load"): mod.on_load(engine)
        except Exception as e:
            Con.err(f"Mod '{d}': {e}"); traceback.print_exc()


def load_shaders(engine):
    if not os.path.isdir("Shaders"): return []
    sd = os.path.abspath("Shaders"); _ensure_path(sd); _ensure_package(sd)
    files = sorted(f for f in os.listdir(sd) if f.endswith(".py") and not f.startswith("_") and f != "__init__.py")
    pls = []
    for fn in files:
        mn = fn[:-3]
        try:
            _purge([f"Shaders.{mn}"])
            mod = importlib.import_module(f"Shaders.{mn}")
            p = ShaderPlugin(mn, fn, mod); pls.append(p)
            ds = " [depth]" if p.needs_depth else ""
            Con.shader(f"Активирован: {p.name} v{p.version} ({p.author}) — {p.desc}{ds}")
        except Exception as e:
            Con.err(f"Shader '{fn}': {e}"); traceback.print_exc()
    pls.sort(key=lambda p: p.order)
    return pls


# ═══════════════════════════════════════════════════════════════════
#                          ENGINE
# ═══════════════════════════════════════════════════════════════════
class Engine:
    def __init__(self):
        self.config = None; self.player = None; self.window = None
        self.sounds = None
        self.systems = []; self.mods = []; self.shaders = []
        self.modules = {}; self.entities = []; self.chunk_world = None
        self.collision = CollisionWorld(); self.inventory = Inventory()
        self.fonts = None; self.font = None; self.draw2d = None; self.ui = None
        # ABB-Col
        self.abb_col_enabled = False
        self.abb_col_config = {}
        self.abb_col_entities = []  # [{entity_id, submesh_idx, mn, mx, name}]
        self.abb_col_counter = 0
        self.debug_abb_col = False
        self.time = 0.0; self.frame = 0; self.fps = 0; self.running = True
        self.events = {}
        self._draw_3d_hooks = []; self._draw_2d_hooks = []
        self._player_controller = None; self._camera_mode = "fps"
        self._mouse_captured = False; self._keys = {}
        self._mouse_x = 0.0; self._mouse_y = 0.0
        self._mouse_delta = (0.0, 0.0); self._mouse_last = (0.0, 0.0)
        self._pending_mouse_capture = None; self._camera_override = None
        self.models = {}; self.textures = {}
        self._mesh_prog = None; self._mesh_u = None; self._bone_loc = None
        self._sky_prog = None; self._sky_u = None; self._sky_vao = None
        self._ui_prog = None; self._ui_u = None; self._ui_vao = None; self._ui_vbo = None
        self._fb_w = 1280; self._fb_h = 720
        self.debug = False; self.wireframe = False

    def spawn_cube(self, position, size=1.0, color=(1,1,1), glow=0.0, rotation=(0,0,0), tag=None, emissive=False):
        return self.spawn_box(position, (size, size, size), color, glow, rotation, tag, emissive)
    def spawn_box(self, position, size=(1,1,1), color=(1,1,1), glow=0.0, rotation=(0,0,0), tag=None, emissive=False):
        m = make_box(size, color); e = Entity.from_mesh(m, position, color, glow, emissive, tag)
        e.rotation = np.array(rotation, np.float32); self.entities.append(e); return e
    def spawn_sphere(self, position, radius=1.0, color=(1,1,1), glow=0.0, tag=None, emissive=False, rings=16, sectors=24):
        m = make_sphere(radius, rings, sectors, color); e = Entity.from_mesh(m, position, color, glow, emissive, tag)
        self.entities.append(e); return e
    def spawn_cylinder(self, position, radius=1.0, height=2.0, color=(1,1,1), glow=0.0, tag=None, emissive=False):
        m = make_cylinder(radius, height, 24, color); e = Entity.from_mesh(m, position, color, glow, emissive, tag)
        self.entities.append(e); return e
    def spawn_billboard(self, position, size=1.0, color=(1,1,1), glow=0.0, tag=None, emissive=True, texture=None):
        m = make_billboard(size, color); e = Entity.from_mesh(m, position, color, glow, emissive, tag, billboard=True)
        if texture: e.submeshes[0][1].texture = texture
        self.entities.append(e); return e
    def spawn_mesh(self, verts, indices, position, color=(1,1,1), glow=0.0, tag=None, emissive=False, texture=None):
        m = Mesh(np.array(verts, np.float32), np.array(indices, np.uint32))
        e = Entity.from_mesh(m, position, color, glow, emissive, tag)
        if texture: e.submeshes[0][1].texture = texture
        self.entities.append(e); return e
    def spawn_model(self, model, position, scale=1.0, tag=None):
        if isinstance(model, str): model = self.models.get(model) or self.load_gltf(model)
        if model is None: return None
        e = Entity.from_model(model, position, scale, tag)
        self.entities.append(e)
        if self.abb_col_enabled:
            self._spawn_abb_col_for_entity(e)
        return e
    def load_gltf(self, path):
        if path in self.models: return self.models[path]
        if not os.path.isabs(path):
            for c in (path, f"Assets/Models/{path}"):
                if os.path.exists(c): path = c; break
        m = load_gltf(path)
        if m: self.models[path] = m
        return m
    def load_obj(self, path, color=(0.7,0.7,0.7)):
        k = f"obj:{path}:{color}"
        if k in self.models: return self.models[k]
        if not os.path.isabs(path):
            for c in (path, f"Assets/Models/{path}"):
                if os.path.exists(c): path = c; break
        m = load_obj(path, color)
        if m: self.models[k] = m
        return m
    def load_texture(self, path, wrap=True, nearest=False):
        if path in self.textures: return self.textures[path]
        if not os.path.isabs(path):
            for c in (path, f"Assets/Textures/{path}"):
                if os.path.exists(c): path = c; break
        t = load_texture(path, wrap, nearest)
        if t: self.textures[path] = t
        return t

    # ── ABB-Col ──
    def configure_abb_col(self, enabled, config=None):
        self.abb_col_enabled = enabled
        self.abb_col_config = config or {}
        if enabled:
            Con.abb(f"ABB-Col: ВКЛ, моделей в конфиге: {len(self.abb_col_config)}")
        else:
            Con.abb("ABB-Col: ВЫКЛ")

    def _should_collide(self, model_name, part_name):
        cfg = self.abb_col_config.get(model_name, None)
        if cfg is None: return True  # не в конфиге → все части коллизят
        if part_name in cfg.get("exclude", []): return False
        include = cfg.get("include", None)
        if include is not None and part_name not in include: return False
        return True

    def _spawn_abb_col_for_entity(self, entity):
        if not self.abb_col_enabled: return
        if entity.model_ref is None: return
        model = entity.model_ref
        em = entity.world_matrix()
        for si, mm in enumerate(model.meshes):
            if not self._should_collide(model.name, mm.mesh_name): continue
            verts = mm.mesh.verts[:, :3]
            if len(verts) == 0: continue
            # Local -> Model: apply mm.local_matrix
            hom = np.concatenate([verts, np.ones((len(verts), 1), np.float32)], axis=1)
            ms = (mm.local_matrix @ hom.T).T[:, :3]
            # Model -> World: apply entity matrix
            hom2 = np.concatenate([ms, np.ones((len(ms), 1), np.float32)], axis=1)
            ws = (em @ hom2.T).T[:, :3]
            mn = ws.min(axis=0); mx = ws.max(axis=0)
            self.abb_col_counter += 1
            name = f"Colision{self.abb_col_counter}"
            self.add_collider(mn[0], mn[1], mn[2], mx[0], mx[1], mx[2], tag=f"abb_{entity.id}_{si}")
            self.abb_col_entities.append({
                "entity_id": entity.id, "submesh_idx": si,
                "name": name, "mn": mn, "mx": mx,
                "model": model.name, "part": mm.mesh_name,
            })
            if self.debug_abb_col:
                Con.abb(f"  {name}: {model.name}/{mm.mesh_name} "
                        f"mn=({mn[0]:.1f},{mn[1]:.1f},{mn[2]:.1f}) "
                        f"mx=({mx[0]:.1f},{mx[1]:.1f},{mx[2]:.1f})")

    def clear_abb_col_for_entity(self, entity):
        eid = entity.id
        keep = []
        for c in self.abb_col_entities:
            if c["entity_id"] == eid:
                self.collision.remove_by_tag(f"abb_{eid}_{c['submesh_idx']}")
            else:
                keep.append(c)
        self.abb_col_entities = keep

    def update_abb_col_for_entity(self, entity):
        self.clear_abb_col_for_entity(entity)
        self._spawn_abb_col_for_entity(entity)

    def scan_abb_col_all(self):
        if not self.abb_col_enabled: return
        n = 0
        for e in self.entities:
            if e.model_ref is not None and e.alive:
                self._spawn_abb_col_for_entity(e); n += 1
        Con.abb(f"ABB-Col: обработано {n} моделей, создано {self.abb_col_counter} коллайдеров")

    # ── Управление ──
    def remove_by_tag(self, tag):
        removed = []
        for e in self.entities:
            if e.tag == tag:
                if self.abb_col_enabled and e.model_ref is not None:
                    self.clear_abb_col_for_entity(e)
                e.alive = False
                removed.append(e)
        self.entities = [e for e in self.entities if e.alive]
        return removed
    def get_entities_by_tag(self, tag): return [e for e in self.entities if e.tag == tag and e.alive]
    def add_collider(self, mnx, mny, mnz, mxx, mxy, mxz, tag=None):
        self.collision.add_box(mnx, mny, mnz, mxx, mxy, mxz, tag)
    def add_floor(self, mnx, mnz, mxx, mxz, yt): self.collision.add_floor(mnx, mnz, mxx, mxz, yt)
    def collide(self, pos, r, h): return self.collision.collide_aabb(pos, r, h)
    def clear_colliders(self): self.collision.clear()

    # ── 2D прокси ──
    def rect(self, x, y, w, h, c): self.draw2d.rect(x, y, w, h, c)
    def rect_outline(self, x, y, w, h, c, t=2): self.draw2d.rect_outline(x, y, w, h, c, t)
    def rect_gradient(self, x, y, w, h, top, bot, v=True): self.draw2d.rect_gradient(x, y, w, h, top, bot, v)
    def rect_rounded(self, x, y, w, h, r, c): self.draw2d.rect_rounded(x, y, w, h, r, c)
    def pixel(self, x, y, c): self.draw2d.pixel(x, y, c)
    def line(self, x1, y1, x2, y2, c, t=2): self.draw2d.line(x1, y1, x2, y2, c, t)
    def circle(self, cx, cy, r, c, s=24): self.draw2d.circle(cx, cy, r, c, s)
    def circle_outline(self, cx, cy, r, c, t=2): self.draw2d.circle_outline(cx, cy, r, c, t)
    def panel(self, x, y, w, h, bg=(0.1,0.1,0.15,0.9), b=(0.5,0.5,0.6,1), bt=2): self.draw2d.panel(x, y, w, h, bg, b, bt)
    def progress(self, x, y, w, h, v, mv, c=(0.7,0.2,0.2,1), bg=(0.1,0.1,0.1,0.8)): self.draw2d.progress(x, y, w, h, v, mv, c, bg)
    def slot(self, x, y, s, item=None, sel=False, bg=(0.1,0.1,0.1,0.7)): self.draw2d.slot(x, y, s, item, sel, bg)
    def icon(self, tex, x, y, s): self.draw2d.icon(tex, x, y, s)
    def text(self, x, y, t, size=24, c=(1,1,1,1)): self.draw2d.text(x, y, t, size, c)
    def text_shadow(self, x, y, t, size=24, c=(1,1,1,1), sh=(0,0,0,0.6), off=(2,2)): self.draw2d.text_shadow(x, y, t, size, c, sh, off)
    def text_centered(self, cx, y, t, size=24, c=(1,1,1,1)): self.draw2d.text_centered(cx, y, t, size, c)
    def text_right(self, rx, y, t, size=24, c=(1,1,1,1)): self.draw2d.text_right(rx, y, t, size, c)
    def text_wrap(self, x, y, w, t, size=20, c=(1,1,1,1)): return self.draw2d.text_wrap(x, y, w, t, size, c)
    def text_width(self, text, size=24): return self.fonts.text_width(text, size) if self.fonts else len(text)*size*0.55
    def text_height(self, size=24): return size
    def screen_size(self): return (self._fb_w, self._fb_h)
    def draw_rect(self, x, y, w, h, c=(1,1,1,1)): self.rect(x, y, w, h, c)
    def draw_text(self, x, y, t, size=24, c=(1,1,1,1)): self.text(x, y, t, size, c)

    def on(self, ev, h): self.events.setdefault(ev, []).append(h)
    def emit(self, ev, *a, **kw):
        for h in self.events.get(ev, []):
            try: h(*a, **kw)
            except Exception as e: Con.err(f"Event '{ev}': {e}")
    def on_draw_3d(self, h): self._draw_3d_hooks.append(h)
    def on_draw_2d(self, h): self._draw_2d_hooks.append(h)
    def set_player_controller(self, fn): self._player_controller = fn
    def set_camera_mode(self, m): self._camera_mode = m
    def set_camera_override(self, fn): self._camera_override = fn
    def set_chunk_world(self, w): self.chunk_world = w
    def is_key_down(self, k): return self._keys.get(k, False)
    def is_mouse_captured(self): return self._mouse_captured
    def set_mouse_captured(self, c): self._pending_mouse_capture = c
    def get_mouse_delta(self): return self._mouse_delta
    def get_mouse_pos(self): return (self._mouse_x, self._mouse_y)
    def play_sound(self, name, vol=1.0):
        if self.sounds: self.sounds.play(name, vol)
    def play_sound_at(self, name, pos, vol=1.0):
        if self.sounds and self.player: self.sounds.play_at(name, pos, self.player.pos, 32.0, vol)
    def import_module(self, name):
        try: m = importlib.import_module(name); self.modules[name] = m; return m
        except Exception as e: Con.err(f"import_module: {e}"); return None
    def import_mod(self, mn, sub=None):
        full = f"{mn}.{sub}" if sub else mn
        try: m = importlib.import_module(full); self.modules[full] = m; return m
        except Exception as e: Con.err(f"import_mod: {e}"); return None
    def get_module(self, name): return self.modules.get(name) or sys.modules.get(name)
    def quit(self): self.running = False


def boot_folders():
    created = False
    for f in FOLDERS:
        if not os.path.exists(f):
            os.makedirs(f, exist_ok=True); print(f"[BOOT] + {f}/"); created = True
    return created

def boot_check_main(): return os.path.exists("System/Main.py")


def main():
    t0 = time.time()
    Con.banner("VOXEL ENGINE — Build 9.1 (branch 8.1)")

    Con.step("Boot")
    created = boot_folders()
    if not boot_check_main():
        print(); Con.warn("System/Main.py НЕ НАЙДЕН.")
        Con.info("Положи свой System/Main.py с on_engine_start(engine)."); print()
        return

    Con.step("Конфиг")
    config = Config("config.json")
    engine = Engine(); engine.config = config
    engine.sounds = SoundManager(config)

    Con.sep(); Con.step("Окно OpenGL 4.6 Core")
    if not glfw.init(): Con.err("GLFW init failed"); return
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 6)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
    w = config.get("window", "width", default=1280)
    h = config.get("window", "height", default=720)
    title = config.get("window", "title", default="Voxel Engine")
    window = glfw.create_window(w, h, title, None, None)
    if not window: glfw.terminate(); Con.err("window failed"); return
    glfw.make_context_current(window)
    glfw.swap_interval(1 if config.get("render", "vsync", default=False) else 0)
    engine.window = window
    Con.ok(f"OpenGL: {glGetString(GL_VERSION).decode()}")
    Con.ok(f"GPU:    {glGetString(GL_RENDERER).decode()}")

    engine.player = Player(config)
    engine._fb_w = w; engine._fb_h = h

    sizes = config.get("font", "sizes", default=[16,20,24,32,48,64])
    try:
        engine.fonts = FontManager(config.get("font", "path", default=""), sizes)
    except Exception as e: Con.err(f"Fonts: {e}")

    mesh_prog = compile_shader_pair(MESH_VERT, MESH_FRAG)
    mesh_u = {n: glGetUniformLocation(mesh_prog, n) for n in
              ["uMVP","uModel","uCameraRight","uCameraUp","uBillboard","uSunDir",
               "uSunColor","uAmbient","uColorMul","uGlow","uAlpha","uHasTexture",
               "uTexture","uHasSkin"]}
    bone_loc = glGetUniformLocation(mesh_prog, "uBones")
    engine._mesh_prog = mesh_prog; engine._mesh_u = mesh_u; engine._bone_loc = bone_loc

    sky_prog = compile_shader_pair(SKY_VERT, SKY_FRAG)
    engine._sky_prog = sky_prog
    engine._sky_u = {n: glGetUniformLocation(sky_prog, n) for n in ["uTop", "uBottom"]}
    sky_vao = glGenVertexArrays(1); sky_vbo = glGenBuffers(1)
    sv = np.array([-1,-1,0,0, 1,-1,1,0, 1,1,1,1, -1,-1,0,0, 1,1,1,1, -1,1,0,1], np.float32)
    glBindVertexArray(sky_vao); glBindBuffer(GL_ARRAY_BUFFER, sky_vbo)
    glBufferData(GL_ARRAY_BUFFER, sv.nbytes, sv, GL_STATIC_DRAW)
    glEnableVertexAttribArray(0); glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(0))
    glBindVertexArray(0); engine._sky_vao = sky_vao

    ui_prog = compile_shader_pair(UI_VERT, UI_FRAG)
    engine._ui_prog = ui_prog
    engine._ui_u = {n: glGetUniformLocation(ui_prog, n) for n in
                    ["uScreen","uPos","uSize","uColor","uUseTex","uTex"]}
    ui_vao = glGenVertexArrays(1); ui_vbo = glGenBuffers(1)
    glBindVertexArray(ui_vao); glBindBuffer(GL_ARRAY_BUFFER, ui_vbo)
    glBufferData(GL_ARRAY_BUFFER, 24*4*4, None, GL_DYNAMIC_DRAW)
    glEnableVertexAttribArray(0); glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(0))
    glEnableVertexAttribArray(1); glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(8))
    glBindVertexArray(0)
    engine._ui_vao = ui_vao; engine._ui_vbo = ui_vbo
    engine.draw2d = Draw2D(engine)
    engine.ui = UIManager(engine)
    Con.ui("Draw2D + UIManager активированы")

    Con.sep(); Con.step("Загрузка System/Main.py")
    if not load_main_system(engine): Con.err("Main.py не загрузился"); return
    Con.sep(); Con.step("Загрузка Mods")
    load_mods(engine)
    # Скан ABB-Col после модов (на случай если моды создали модели)
    if engine.abb_col_enabled:
        engine.scan_abb_col_all()
    Con.sep(); Con.step("Загрузка Shaders")
    engine.shaders = load_shaders(engine)
    shader_chain = ShaderChain(engine.shaders) if engine.shaders else None
    for p in engine.shaders:
        if p.on_load:
            try: p.on_load(engine)
            except Exception as e: Con.err(f"{p.name}.on_load: {e}")

    glEnable(GL_DEPTH_TEST); glDepthFunc(GL_LESS)
    glEnable(GL_CULL_FACE); glCullFace(GL_BACK); glFrontFace(GL_CCW)
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    state = {"last_t": time.time(), "fps_time": time.time(), "frames": 0}

    def on_key(win, key, sc, action, mods):
        if action == glfw.PRESS:
            if engine.ui.on_key(key): return
            if key == glfw.KEY_ESCAPE: engine.emit("escape")
            elif key == glfw.KEY_F3: engine.debug = not engine.debug
            elif key == glfw.KEY_F4:
                engine.wireframe = not engine.wireframe
                if engine.wireframe: glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                else: glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            elif key == glfw.KEY_F5:
                engine.debug_abb_col = not engine.debug_abb_col
                Con.abb(f"Debug ABB-Col: {'ON' if engine.debug_abb_col else 'OFF'}")
            engine._keys[key] = True
            engine.emit("key_press", key)
        elif action == glfw.RELEASE:
            engine._keys[key] = False
            engine.emit("key_release", key)

    def on_cursor(win, x, y):
        engine._mouse_x = x; engine._mouse_y = y
        if not engine._mouse_captured:
            engine.ui.on_mouse_move(x, y)
            engine._mouse_last = (x, y); return
        dx = x - engine._mouse_last[0]; dy = engine._mouse_last[1] - y
        engine._mouse_last = (x, y)
        engine._mouse_delta = (dx, dy)
        engine.emit("mouse_move", dx, dy)

    def on_mb(win, btn, action, mods):
        if action == glfw.PRESS:
            if not engine._mouse_captured and engine.ui.on_click(engine._mouse_x, engine._mouse_y):
                return
            engine.emit("mouse_click", engine._mouse_x, engine._mouse_y, btn)
            engine.emit("mouse_press", btn)
        elif action == glfw.RELEASE:
            engine.ui.on_release(engine._mouse_x, engine._mouse_y)
            engine.emit("mouse_release", engine._mouse_x, engine._mouse_y, btn)

    glfw.set_key_callback(window, on_key)
    glfw.set_cursor_pos_callback(window, on_cursor)
    glfw.set_mouse_button_callback(window, on_mb)

    Con.sep(); Con.ok(f"ГОТОВО ЗА {time.time()-t0:.2f} СЕК"); print()

    fov = config.get("render", "fov", default=75.0)
    near = config.get("render", "near", default=0.1)
    far = config.get("render", "far", default=400.0)
    sun_dir = np.array(config.get("lighting", "sun_dir", default=[0.55,0.85,0.35]), np.float32)
    sun_dir /= np.linalg.norm(sun_dir) + 1e-9
    sun_color = np.array(config.get("lighting", "sun_color", default=[1.0,0.95,0.85]), np.float32)
    ambient = config.get("lighting", "ambient", default=0.35)
    sky_top = np.array(config.get("render", "sky_top", default=[0.35,0.55,0.85]), np.float32)
    sky_bottom = np.array(config.get("render", "sky_bottom", default=[0.75,0.85,0.95]), np.float32)
    frustum = Frustum()

    while not glfw.window_should_close(window) and engine.running:
        now = time.time()
        dt = min(now - state["last_t"], 0.05)
        state["last_t"] = now
        engine.time = now; engine.frame += 1

        if engine._pending_mouse_capture is not None:
            want = engine._pending_mouse_capture
            if want and not engine._mouse_captured:
                glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)
                engine._mouse_last = glfw.get_cursor_pos(window)
                engine._mouse_captured = True
            elif not want and engine._mouse_captured:
                glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_NORMAL)
                engine._mouse_captured = False
            engine._pending_mouse_capture = None

        if not engine._mouse_captured:
            engine.ui.update(dt)

        if engine._player_controller:
            try: engine._player_controller(engine, dt)
            except Exception as e: Con.err(f"player_controller: {e}")

        for mod in engine.systems + engine.mods:
            if hasattr(mod, "on_update"):
                try: mod.on_update(engine, dt)
                except Exception as e: Con.err(f"on_update: {e}")

        for e in engine.entities:
            if e.on_update:
                try: e.on_update(engine, e, dt)
                except Exception as ex: Con.err(f"entity: {ex}")
            if e.animator is not None: e.animator.update(dt)
        engine.entities = [e for e in engine.entities if e.alive]

        for p in engine.shaders:
            if p.on_frame:
                try: p.on_frame(engine, dt)
                except Exception as e: Con.err(f"{p.name}.on_frame: {e}")

        fb_w, fb_h = glfw.get_framebuffer_size(window)
        engine._fb_w = fb_w; engine._fb_h = fb_h
        engine.draw2d.w = fb_w; engine.draw2d.h = fb_h

        if shader_chain: shader_chain.bind_scene(fb_w, fb_h)
        else: glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(0, 0, fb_w, fb_h)
        glClearColor(sky_bottom[0], sky_bottom[1], sky_bottom[2], 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        aspect = fb_w / max(1, fb_h)
        proj = perspective(fov, aspect, near, far)

        if engine._camera_override:
            eye, fwd = engine._camera_override(engine)
            eye = np.asarray(eye, np.float32); fwd = np.asarray(fwd, np.float32)
        else:
            eye = engine.player.pos + np.array([0, engine.player.height*0.85, 0], np.float32)
            fwd = engine.player.forward()
        view = look_at(eye, eye + fwd, (0.0, 1.0, 0.0))
        mvp = proj @ view

        if config.get("render", "frustum_culling", default=True): frustum.from_matrix(mvp)

        glUseProgram(sky_prog)
        glUniform3fv(engine._sky_u["uTop"], 1, sky_top.tolist())
        glUniform3fv(engine._sky_u["uBottom"], 1, sky_bottom.tolist())
        glBindVertexArray(engine._sky_vao); glDrawArrays(GL_TRIANGLES, 0, 6); glBindVertexArray(0)

        if engine.chunk_world is not None:
            try:
                chunks = engine.chunk_world.visible_chunks(eye) if hasattr(engine.chunk_world, "visible_chunks") else engine.chunk_world.chunks.values()
                for c in chunks:
                    if hasattr(c, "draw"): c.draw()
            except Exception as e: Con.err(f"chunk_world: {e}")

        glUseProgram(mesh_prog)
        cam_right = np.cross(fwd, np.array([0, 1, 0], np.float32))
        cam_right /= (np.linalg.norm(cam_right) + 1e-9)
        cam_up = np.cross(cam_right, fwd)
        glUniformMatrix4fv(mesh_u["uMVP"], 1, GL_FALSE, mvp.flatten(order='F'))
        glUniform3fv(mesh_u["uCameraRight"], 1, cam_right.tolist())
        glUniform3fv(mesh_u["uCameraUp"], 1, cam_up.tolist())
        glUniform3fv(mesh_u["uSunDir"], 1, sun_dir.tolist())
        glUniform3fv(mesh_u["uSunColor"], 1, sun_color.tolist())
        glUniform3f(mesh_u["uAmbient"], ambient, ambient, ambient)
        glUniform3fv(mesh_u["uColorMul"], 1, (1.0, 1.0, 1.0))

        for e in engine.entities:
            if not e.alive or not e.visible: continue
            if config.get("render", "frustum_culling", default=True):
                r = max(1.0, float(np.linalg.norm(e.bbox_max - e.bbox_min)) * e.scale)
                if not frustum.sphere_visible(tuple(e.position), r): continue
            wm = e.world_matrix()
            glUniformMatrix4fv(mesh_u["uModel"], 1, GL_FALSE, wm.flatten(order='F'))
            glUniform1i(mesh_u["uBillboard"], 1 if e.billboard else 0)
            glUniform1f(mesh_u["uGlow"], e.glow)
            bones = e.animator.get_bone_matrices() if e.animator else None
            glUniform1i(mesh_u["uHasSkin"], 1 if bones is not None else 0)
            if bones is not None:
                glUniformMatrix4fv(bone_loc, MAX_BONES, GL_FALSE, bones.reshape(-1, order='F').astype(np.float32))
            hidden = e.user_data.get("_hidden_idx", frozenset())
            for si, (mesh, mat, local, _) in enumerate(e.submeshes):
                if hidden and si in hidden: continue
                ht = mat.bind()
                glUniform1i(mesh_u["uHasTexture"], ht)
                if ht: glUniform1i(mesh_u["uTexture"], 0)
                glUniform3fv(mesh_u["uColorMul"], 1, mat.color)
                glUniform1f(mesh_u["uAlpha"], mat.alpha)
                if mat.double_sided: glDisable(GL_CULL_FACE)
                if e.emissive: glDepthMask(GL_FALSE)
                mesh.draw()
                if e.emissive: glDepthMask(GL_TRUE)
                if mat.double_sided: glEnable(GL_CULL_FACE)
        glBindVertexArray(0); glUseProgram(0)

        ctx = {"time": now, "resolution": (fb_w, fb_h),
               "camera_pos": tuple(eye.tolist()), "camera_dir": tuple(fwd.tolist()),
               "near": near, "far": far,
               "sun_dir": tuple(sun_dir.tolist()), "sun_color": tuple(sun_color.tolist()),
               "projection": proj, "view": view, "mvp": mvp}
        for h in engine._draw_3d_hooks:
            try: h(engine, ctx)
            except Exception as e: Con.err(f"draw_3d: {e}")

        if shader_chain:
            shader_chain.unbind()
            fade = 0.0
            for mod in engine.systems:
                st = getattr(mod, "STATE", None)
                if st and "fade" in st: fade = st["fade"]; break
            ctx["fade"] = fade
            shader_chain.apply(ctx)

        glDisable(GL_DEPTH_TEST); glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        if not engine._mouse_captured:
            try: engine.ui.draw(fb_w, fb_h)
            except Exception as e: Con.err(f"UI draw: {e}")

        for h in engine._draw_2d_hooks:
            try: h(engine, fb_w, fb_h)
            except Exception as e: Con.err(f"draw_2d: {e}")

        glEnable(GL_DEPTH_TEST)
        glfw.swap_buffers(window); glfw.poll_events()

        state["frames"] += 1
        if now - state["fps_time"] >= 1.0:
            engine.fps = state["frames"]; state["frames"] = 0; state["fps_time"] = now
            glfw.set_window_title(window, f"{title} | FPS: {engine.fps} | ent: {len(engine.entities)} | abb: {len(engine.abb_col_entities)}")

    for p in engine.shaders:
        if p.on_unload:
            try: p.on_unload(engine)
            except Exception: pass
    for e in engine.entities: e.free()
    if engine.sounds: engine.sounds.stop_all()
    glfw.terminate()
    Con.ok(f"Выход за {time.time()-t0:.2f} сек")


if __name__ == "__main__":
    try: main()
    except Exception as e:
        Con.err(f"Фатальная: {e}")
        traceback.print_exc()
        sys.exit(1)