"""
╔══════════════════════════════════════════════════════════════════╗
║  VOXEL ENGINE v8.1 — Draw2D EDITION                              ║
║                                                                  ║
║  НОВОЕ:                                                          ║
║  • Draw2D — удобный 2D API (rect, line, circle, panel, etc.)     ║
║  • engine.rect / line / circle / panel / progress / slot         ║
║  • engine.text / text_centered / text_right                      ║
║  • engine.screen_size()                                          ║
║                                                                  ║
║  Всё старое сохранено:                                           ║
║  • 3D меши, GLTF, OBJ, текстуры                                  ║
║  • AABB коллизии, инвентарь                                      ║
║  • Frustum culling, skybox, звук                                 ║
║  • GUI кнопки, шейдер-плагины, шрифт                             ║
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


# ═══════════════════════════════════════════════════════════════════
#                          КОНСОЛЬ
# ═══════════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════════
#                          CONFIG
# ═══════════════════════════════════════════════════════════════════
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
    "font": {"path": "", "size": 24, "cell": 32},
}

FOLDERS = ["System", "Mods", "Shaders", "Worlds", "Assets",
           "Assets/Textures", "Assets/Models", "Assets/Sounds"]

MAX_BONES = 128


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
        except Exception:
            pass
    def _merge(self, base, over):
        for k, v in over.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._merge(base[k], v)
            else:
                base[k] = v
    def get(self, *keys, default=None):
        cur = self.data
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur


def clamp(v, a, b):
    return max(a, min(b, v))


# ═══════════════════════════════════════════════════════════════════
#                       SOUND MANAGER
# ═══════════════════════════════════════════════════════════════════
class SoundManager:
    def __init__(self, config):
        self.enabled = config.get("audio", "enabled", default=True)
        self.master_volume = config.get("audio", "master_volume", default=0.8)
        self.backend = None
        self.cache = {}
        self._init_backend()
    def _init_backend(self):
        if not self.enabled: return
        try:
            import pygame
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
            self.backend = ("pygame", pygame)
            Con.sound("pygame.mixer")
            return
        except Exception: pass
        try:
            import winsound
            self.backend = ("winsound", winsound)
            Con.sound("winsound")
            return
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
                snd.set_volume(v)
                snd.play(loops=-1 if loop else 0)
            elif self.backend[0] == "winsound":
                flags = self.backend[1].SND_FILENAME | self.backend[1].SND_ASYNC
                if loop: flags |= self.backend[1].SND_LOOP
                self.backend[1].PlaySound(snd, flags)
        except Exception: pass
    def play_at(self, name, src, listener, max_dist=32.0, volume=1.0):
        if not self.backend: return
        d = math.sqrt(sum((a - b) ** 2 for a, b in zip(src, listener)))
        if d > max_dist: return
        self.play(name, volume=volume * (1.0 - d / max_dist) ** 2)
    def stop_all(self):
        try:
            if self.backend and self.backend[0] == "pygame":
                self.backend[1].mixer.stop()
        except Exception: pass


# ═══════════════════════════════════════════════════════════════════
#                       МАТЕМАТИКА
# ═══════════════════════════════════════════════════════════════════
def perspective(fovy_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2.0)
    m = np.zeros((4, 4), np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
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
        r = a + t * (b - a)
        return r / (np.linalg.norm(r) + 1e-9)
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


# ═══════════════════════════════════════════════════════════════════
#                    FRUSTUM CULLING
# ═══════════════════════════════════════════════════════════════════
class Frustum:
    def __init__(self):
        self.planes = np.zeros((6, 4), np.float32)
    def from_matrix(self, m):
        self.planes[0] = m[3, :] + m[0, :]
        self.planes[1] = m[3, :] - m[0, :]
        self.planes[2] = m[3, :] + m[1, :]
        self.planes[3] = m[3, :] - m[1, :]
        self.planes[4] = m[3, :] + m[2, :]
        self.planes[5] = m[3, :] - m[2, :]
        for i in range(6):
            n = np.linalg.norm(self.planes[i, :3])
            if n > 1e-9: self.planes[i] /= n
    def aabb_visible(self, mn, mx):
        for i in range(6):
            p = self.planes[i]
            px = mx[0] if p[0] > 0 else mn[0]
            py = mx[1] if p[1] > 0 else mn[1]
            pz = mx[2] if p[2] > 0 else mn[2]
            if p[0]*px + p[1]*py + p[2]*pz + p[3] < 0:
                return False
        return True
    def sphere_visible(self, center, radius):
        for i in range(6):
            p = self.planes[i]
            d = p[0]*center[0] + p[1]*center[1] + p[2]*center[2] + p[3]
            if d < -radius: return False
        return True


# ═══════════════════════════════════════════════════════════════════
#                       КОЛЛИЗИИ
# ═══════════════════════════════════════════════════════════════════
class CollisionWorld:
    def __init__(self):
        self.boxes = []
        self.floors = []
    def add_box(self, mnx, mny, mnz, mxx, mxy, mxz):
        self.boxes.append((mnx, mny, mnz, mxx, mxy, mxz))
    def add_floor(self, mnx, mnz, mxx, mxz, y_top):
        self.floors.append((mnx, mnz, mxx, mxz, y_top))
    def clear(self):
        self.boxes.clear(); self.floors.clear()
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
        px, pz = float(pos[0]), float(pos[2])
        py = float(pos[1])
        best_y = None
        for (mnx, mnz, mxx, mxz, y_top) in self.floors:
            if mnx <= px <= mxx and mnz <= pz <= mxz:
                if y_top <= py + 0.1:
                    if best_y is None or y_top > best_y:
                        best_y = y_top
        return best_y


# ═══════════════════════════════════════════════════════════════════
#                       ТЕКСТУРЫ
# ═══════════════════════════════════════════════════════════════════
class Texture:
    def __init__(self, gl_id, width, height):
        self.id = gl_id; self.width = width; self.height = height
    def bind(self, unit=0):
        glActiveTexture(GL_TEXTURE0 + unit)
        glBindTexture(GL_TEXTURE_2D, self.id)
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
        Con.warn(f"Pillow: {e}")
        return None

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
    tex = Texture(tex_id, w, h)
    _texture_cache[path] = tex
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


# ═══════════════════════════════════════════════════════════════════
#                          FONT
# ═══════════════════════════════════════════════════════════════════
class Font:
    def __init__(self, path="", size=24, cell=32):
        self.cell = cell
        self.size = size
        self.charset = self._build_charset()
        self.char_map = {}
        self.atlas_tex = None
        self.cols = 16
        self.rows = (len(self.charset) + self.cols - 1) // self.cols
        self._build_atlas(path, size)
    def _build_charset(self):
        chars = ""
        for c in range(32, 127):
            chars += chr(c)
        chars += "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
        chars += "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        return chars
    def _build_atlas(self, font_path, size):
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            Con.warn("Pillow не установлен — текст не работает")
            return
        candidates = []
        if font_path: candidates.append(font_path)
        candidates += [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        font = None
        for p in candidates:
            if os.path.exists(p):
                try:
                    font = ImageFont.truetype(p, size)
                    Con.font(f"Шрифт: {os.path.basename(p)}")
                    break
                except Exception:
                    continue
        if font is None:
            try:
                font = ImageFont.load_default()
                Con.font("Дефолтный PIL-шрифт")
            except Exception:
                return
        cell = self.cell
        atlas_w = self.cols * cell
        atlas_h = self.rows * cell
        img = Image.new("RGBA", (atlas_w, atlas_h), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for i, ch in enumerate(self.charset):
            col = i % self.cols
            row = i // self.cols
            x = col * cell; y = row * cell
            try:
                bbox = draw.textbbox((0, 0), ch, font=font)
                tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
                tx = x + (cell - tw) // 2 - bbox[0]
                ty = y + (cell - th) // 2 - bbox[1]
                draw.text((tx, ty), ch, fill=(255, 255, 255, 255), font=font)
            except Exception:
                pass
            self.char_map[ch] = (col, row)
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        data = np.array(img, dtype=np.uint8)
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, atlas_w, atlas_h, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glBindTexture(GL_TEXTURE_2D, 0)
        self.atlas_tex = tex_id
        self.atlas_w = atlas_w
        self.atlas_h = atlas_h
        Con.ok(f"Атлас шрифта: {atlas_w}x{atlas_h}, {len(self.charset)} символов")
    def char_uv(self, ch):
        if ch not in self.char_map: ch = "?"
        col, row = self.char_map[ch]
        cw = 1.0 / self.cols
        ch_ = 1.0 / self.rows
        u0 = col * cw
        u1 = (col + 1) * cw
        v0 = 1.0 - (row + 1) * ch_
        v1 = 1.0 - row * ch_
        return (u0, v0, u1, v1)


# ═══════════════════════════════════════════════════════════════════
#                          MESH
# ═══════════════════════════════════════════════════════════════════
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
        stride = VERTEX_STRIDE
        glEnableVertexAttribArray(0); glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1); glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3*4))
        glEnableVertexAttribArray(2); glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(6*4))
        glEnableVertexAttribArray(3); glVertexAttribPointer(3, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(9*4))
        glEnableVertexAttribArray(4); glVertexAttribPointer(4, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(11*4))
        glEnableVertexAttribArray(5); glVertexAttribPointer(5, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(15*4))
        glBindVertexArray(0)
    def draw(self):
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, len(self.indices), GL_UNSIGNED_INT, None)
    def free(self):
        try:
            glDeleteBuffers(1, [self.vbo]); glDeleteBuffers(1, [self.ebo])
            glDeleteVertexArrays(1, [self.vao])
        except Exception: pass


def _make_vertex_row(pos, normal, color, uv, joints=(0,0,0,0), weights=(0,0,0,0)):
    return [pos[0], pos[1], pos[2],
            normal[0], normal[1], normal[2],
            color[0], color[1], color[2],
            uv[0], uv[1],
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
            verts.append(_make_vertex_row((x, y, z), (x*inv, y*inv, z*inv), color, (0, 0)))
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
            verts.append(_make_vertex_row(p, n, color, uvs[i]))
        indices.extend([base, base+1, base+2, base, base+2, base+3])
    return Mesh(np.array(verts, np.float32), np.array(indices, np.uint32))


def make_cube(size=1.0, color=(1,1,1)):
    return make_box((size, size, size), color)


def make_billboard(size=1.0, color=(1,1,1)):
    s = size / 2
    pts = [(-s,-s,0),(s,-s,0),(s,s,0),(-s,s,0)]
    uvs = [(0,0),(1,0),(1,1),(0,1)]
    verts = []
    for p, uv in zip(pts, uvs):
        verts.append(_make_vertex_row(p, (0,0,1), color, uv))
    return Mesh(np.array(verts, np.float32), np.array([0,1,2,0,2,3], np.uint32))


def make_cylinder(radius=1.0, height=2.0, segments=24, color=(1,1,1)):
    verts = []; indices = []
    hh = height / 2
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        x = radius * math.cos(a); z = radius * math.sin(a)
        nx, nz = math.cos(a), math.sin(a)
        verts.append(_make_vertex_row((x, -hh, z), (nx, 0, nz), color, (0, 0)))
        verts.append(_make_vertex_row((x, hh, z), (nx, 0, nz), color, (0, 1)))
    for i in range(segments):
        a = i * 2
        indices.extend([a, a+2, a+1, a+1, a+2, a+3])
    top_c = len(verts)
    verts.append(_make_vertex_row((0, hh, 0), (0, 1, 0), color, (0.5, 0.5)))
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        verts.append(_make_vertex_row((radius*math.cos(a), hh, radius*math.sin(a)),
                                       (0, 1, 0), color, (0, 0)))
    for i in range(segments):
        indices.extend([top_c, top_c+i+1, top_c+i+2])
    bot_c = len(verts)
    verts.append(_make_vertex_row((0, -hh, 0), (0, -1, 0), color, (0.5, 0.5)))
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        verts.append(_make_vertex_row((radius*math.cos(a), -hh, radius*math.sin(a)),
                                       (0, -1, 0), color, (0, 0)))
    for i in range(segments):
        indices.extend([bot_c, bot_c+i+2, bot_c+i+1])
    return Mesh(np.array(verts, np.float32), np.array(indices, np.uint32))


# ═══════════════════════════════════════════════════════════════════
#                       MATERIAL / MODEL
# ═══════════════════════════════════════════════════════════════════
class Material:
    def __init__(self, color=(1,1,1), texture=None, alpha=1.0,
                 emissive=0.0, double_sided=False):
        self.color = tuple(color); self.texture = texture
        self.alpha = alpha; self.emissive = emissive
        self.double_sided = double_sided
    def bind(self):
        if self.texture: self.texture.bind(0); return 1
        return 0


class ModelMesh:
    def __init__(self, mesh, material, local_matrix=None, node_index=-1):
        self.mesh = mesh
        self.material = material
        self.local_matrix = local_matrix if local_matrix is not None else np.eye(4, dtype=np.float32)
        self.node_index = node_index


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
        alpha = (t - t0) / span
        v0, v1 = self.values[lo], self.values[hi]
        if self.interpolation == "STEP": return v0
        elif self.interpolation == "CUBICSPLINE":
            if v0.ndim == 1 and len(v0) % 3 == 0:
                k = len(v0) // 3
                return v0[k:2*k]
            return v0
        else:
            if self.path == "rotation" and len(v0) == 4:
                return quat_slerp(v0, v1, alpha)
            return v0 * (1 - alpha) + v1 * alpha


class Animation:
    def __init__(self, name="anim"):
        self.name = name; self.channels = []; self.duration = 0.0
    def add_channel(self, ch):
        self.channels.append(ch)
        self.duration = max(self.duration, ch.duration)


class Model:
    def __init__(self, name="model"):
        self.name = name; self.meshes = []; self.animations = {}
        self.bbox_min = np.array([1e9]*3, np.float32)
        self.bbox_max = np.array([-1e9]*3, np.float32)
    def add(self, mesh, material, local_matrix=None, node_index=-1):
        self.meshes.append(ModelMesh(mesh, material, local_matrix, node_index))
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
            self._default_trs[i] = (np.array(t, np.float32),
                                    np.array(r, np.float32),
                                    np.array(s, np.float32))
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
        for i, (t, r, s) in self._default_trs.items():
            local_trs[i] = (t.copy(), r.copy(), s.copy())
        if self.current is not None:
            for ch in self.current.channels:
                val = ch.sample(self.time)
                if val is None: continue
                node_i = ch.target_node
                if node_i not in local_trs: continue
                t, r, s = local_trs[node_i]
                if ch.path == "translation": t = np.array(val, np.float32)
                elif ch.path == "rotation": r = np.array(val, np.float32)
                elif ch.path == "scale": s = np.array(val, np.float32)
                local_trs[node_i] = (t, r, s)
        world = {}
        def compute_world(idx, parent_mat):
            if idx in world: return
            t, r, s = local_trs.get(idx, (np.zeros(3, np.float32),
                                          np.array([0,0,0,1], np.float32),
                                          np.ones(3, np.float32)))
            local = trs_matrix(t, r, s)
            world[idx] = parent_mat @ local
            for c in self._node_children.get(idx, []):
                compute_world(c, world[idx])
        I = np.eye(4, dtype=np.float32)
        for i in self._default_trs.keys():
            if self._node_parent.get(i, -1) == -1:
                compute_world(i, I)
        for i in self._default_trs.keys():
            if i not in world: compute_world(i, I)
        result = np.zeros((MAX_BONES, 4, 4), np.float32)
        for k, joint_idx in enumerate(self._skin_joints):
            if k >= MAX_BONES: break
            w = world.get(joint_idx, I)
            ibm = self._skin_ibm[k] if k < len(self._skin_ibm) else I
            result[k] = w @ ibm
        return result


# ═══════════════════════════════════════════════════════════════════
#                       GLTF / OBJ
# ═══════════════════════════════════════════════════════════════════
_GLTF_COMP_SIZE = {5120:1, 5121:1, 5122:2, 5123:2, 5125:4, 5126:4}
_GLTF_DTYPE = {5120:np.int8, 5121:np.uint8, 5122:np.int16,
               5123:np.uint16, 5125:np.uint32, 5126:np.float32}
_GLTF_NCOMP = {"SCALAR":1, "VEC2":2, "VEC3":3, "VEC4":4, "MAT2":4, "MAT3":9, "MAT4":16}


def _gltf_read_accessor(gltf, acc_idx, buffers):
    if acc_idx is None: return None
    acc = gltf["accessors"][acc_idx]
    if "bufferView" not in acc: return None
    bv = gltf["bufferViews"][acc["bufferView"]]
    buf = buffers[bv["buffer"]]
    comp_size = _GLTF_COMP_SIZE[acc["componentType"]]
    n_comp = _GLTF_NCOMP[acc["type"]]
    n_elem = acc["count"]
    dtype = _GLTF_DTYPE[acc["componentType"]]
    byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    byte_stride = bv.get("byteStride", comp_size * n_comp)
    if byte_stride == comp_size * n_comp:
        data = np.frombuffer(buf, dtype=dtype, count=n_elem * n_comp, offset=byte_offset)
        data = data.reshape(n_elem, n_comp).copy()
    else:
        data = np.zeros((n_elem, n_comp), dtype=dtype)
        for i in range(n_elem):
            off = byte_offset + i * byte_stride
            data[i] = np.frombuffer(buf, dtype=dtype, count=n_comp, offset=off)
    if acc.get("normalized", False) and dtype != np.float32:
        if dtype == np.uint8: data = data.astype(np.float32) / 255.0
        elif dtype == np.uint16: data = data.astype(np.float32) / 65535.0
        elif dtype == np.int8: data = np.maximum(data.astype(np.float32) / 127.0, -1.0)
        elif dtype == np.int16: data = np.maximum(data.astype(np.float32) / 32767.0, -1.0)
    return data


def _gltf_decode_uri(uri):
    if uri.startswith("data:"):
        header, data = uri.split(",", 1)
        if ";base64" in header: return base64.b64decode(data)
        return data.encode("utf-8")
    return None


def _gltf_load_buffers(gltf, base_dir, glb_bin=None):
    buffers = []
    for buf in gltf.get("buffers", []):
        if "uri" in buf:
            uri = buf["uri"]
            decoded = _gltf_decode_uri(uri)
            if decoded is not None: buffers.append(decoded)
            else:
                path = os.path.join(base_dir, uri)
                with open(path, "rb") as f: buffers.append(f.read())
        else:
            buffers.append(glb_bin if glb_bin is not None else b"")
    return buffers


def _gltf_load_texture(gltf, tex_idx, base_dir, buffers):
    if tex_idx is None: return None
    tex = gltf["textures"][tex_idx]
    src_idx = tex.get("source")
    if src_idx is None: return None
    img = gltf["images"][src_idx]
    if "uri" in img:
        decoded = _gltf_decode_uri(img["uri"])
        if decoded is not None:
            try:
                from PIL import Image
                import io as _io
                image = Image.open(_io.BytesIO(decoded)).convert("RGBA")
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                return _tex_from_array(np.array(image, dtype=np.uint8))
            except Exception: return None
        else:
            return load_texture(os.path.join(base_dir, img["uri"]))
    elif "bufferView" in img:
        bv = gltf["bufferViews"][img["bufferView"]]
        buf = buffers[bv["buffer"]]
        off = bv.get("byteOffset", 0); length = bv["byteLength"]
        raw = buf[off:off+length]
        try:
            from PIL import Image
            import io as _io
            image = Image.open(_io.BytesIO(raw)).convert("RGBA")
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
            return _tex_from_array(np.array(image, dtype=np.uint8))
        except Exception: return None
    return None


def _gltf_flatten_nodes(gltf):
    result = []
    if "nodes" not in gltf: return result
    def walk(idx, parent):
        node = gltf["nodes"][idx]
        if "matrix" in node:
            local = np.array(node["matrix"], np.float32).reshape(4, 4).T
        else:
            t = node.get("translation", [0,0,0])
            r = node.get("rotation", [0,0,0,1])
            s = node.get("scale", [1,1,1])
            local = trs_matrix(t, r, s)
        world = parent @ local
        if "mesh" in node: result.append((idx, node["mesh"], world))
        for child in node.get("children", []): walk(child, world)
    scene = gltf.get("scenes", [{}])[gltf.get("scene", 0)]
    I = np.eye(4, dtype=np.float32)
    for root in scene.get("nodes", []): walk(root, I)
    return result


def _gltf_build_material(gltf, mat_idx, base_dir, buffers):
    if mat_idx is None: return Material()
    m = gltf["materials"][mat_idx]
    pbr = m.get("pbrMetallicRoughness", {})
    color = pbr.get("baseColorFactor", [1,1,1,1])
    alpha = color[3] if len(color) == 4 else 1.0
    if m.get("alphaMode", "OPAQUE") == "BLEND": alpha = min(alpha, 1.0)
    tex = None
    if "baseColorTexture" in pbr:
        tex = _gltf_load_texture(gltf, pbr["baseColorTexture"].get("index"), base_dir, buffers)
    emissive = m.get("emissiveFactor", [0,0,0])
    emissive_f = max(emissive) if isinstance(emissive, (list, tuple)) else 0.0
    return Material(color=(color[0], color[1], color[2]), texture=tex, alpha=alpha,
                    emissive=emissive_f, double_sided=m.get("doubleSided", False))


def _gltf_build_mesh(gltf, mesh_idx, buffers, base_dir, skin_data):
    g_mesh = gltf["meshes"][mesh_idx]
    result = []
    for prim in g_mesh.get("primitives", []):
        if prim.get("mode", 4) != 4: continue
        attrs = prim.get("attributes", {})
        pos = _gltf_read_accessor(gltf, attrs.get("POSITION"), buffers)
        if pos is None: continue
        n_verts = len(pos)
        norms = (_gltf_read_accessor(gltf, attrs["NORMAL"], buffers)
                 if "NORMAL" in attrs else np.zeros((n_verts, 3), np.float32))
        if "TEXCOORD_0" in attrs:
            uvs = _gltf_read_accessor(gltf, attrs["TEXCOORD_0"], buffers).copy()
            uvs[:, 1] = 1.0 - uvs[:, 1]
        else: uvs = np.zeros((n_verts, 2), np.float32)
        if "COLOR_0" in attrs:
            colors = _gltf_read_accessor(gltf, attrs["COLOR_0"], buffers)
            if colors.shape[1] == 3:
                colors = np.concatenate([colors, np.ones((n_verts, 1), colors.dtype)], axis=1)
        else: colors = np.ones((n_verts, 4), np.float32)
        if "indices" in prim:
            indices = _gltf_read_accessor(gltf, prim["indices"], buffers).flatten()
        else: indices = np.arange(n_verts, dtype=np.uint32)
        has_skin = False
        joints_arr = np.zeros((n_verts, 4), np.float32)
        weights_arr = np.zeros((n_verts, 4), np.float32)
        if skin_data is not None and "JOINTS_0" in attrs and "WEIGHTS_0" in attrs:
            joints_arr = _gltf_read_accessor(gltf, attrs["JOINTS_0"], buffers).astype(np.float32)
            weights_arr = _gltf_read_accessor(gltf, attrs["WEIGHTS_0"], buffers).astype(np.float32)
            has_skin = True
        verts = np.zeros((n_verts, 19), np.float32)
        verts[:, 0:3] = pos; verts[:, 3:6] = norms; verts[:, 6:9] = colors[:, :3]
        verts[:, 9:11] = uvs; verts[:, 11:15] = joints_arr; verts[:, 15:19] = weights_arr
        mesh = Mesh(verts, indices.astype(np.uint32), has_skin=has_skin)
        material = _gltf_build_material(gltf, prim.get("material"), base_dir, buffers)
        result.append((mesh, material))
    return result


def load_gltf(path):
    if not os.path.exists(path):
        Con.err(f"Нет файла: {path}"); return None
    base_dir = os.path.dirname(os.path.abspath(path))
    with open(path, "rb") as f:
        head = f.read(4); f.seek(0)
        if head[:4] == b"glTF":
            data = f.read()
            magic, version, length = struct.unpack_from("<III", data, 0)
            offset = 12; gltf_json = None; glb_bin = None
            while offset < length:
                clen, ctype = struct.unpack_from("<II", data, offset)
                offset += 8; cdata = data[offset:offset+clen]; offset += clen
                if ctype == 0x4E4F534A: gltf_json = json.loads(cdata.decode("utf-8"))
                elif ctype == 0x004E4942: glb_bin = cdata
            if gltf_json is None: Con.err("GLB: нет JSON"); return None
            buffers = _gltf_load_buffers(gltf_json, base_dir, glb_bin)
        else:
            gltf_json = json.load(f)
            buffers = _gltf_load_buffers(gltf_json, base_dir)
    model = Model(name=os.path.basename(path))
    skin_data_global = None
    node_children = {}; node_parent = {}
    if "nodes" in gltf_json:
        for i, n in enumerate(gltf_json["nodes"]):
            for c in n.get("children", []):
                node_children.setdefault(i, []).append(c); node_parent[c] = i
    if gltf_json.get("skins"):
        skin = gltf_json["skins"][0]
        joints_list = skin.get("joints", [])
        ibm_idx = skin.get("inverseBindMatrices")
        ibm = None
        if ibm_idx is not None:
            raw = _gltf_read_accessor(gltf_json, ibm_idx, buffers)
            if raw is not None:
                ibm = raw.reshape(-1, 4, 4).transpose(0, 2, 1).copy()
        skin_data_global = (joints_list, ibm)
    nodes = _gltf_flatten_nodes(gltf_json)
    if not nodes:
        for mi in range(len(gltf_json.get("meshes", []))):
            nodes.append((-1, mi, np.eye(4, dtype=np.float32)))
    total_tris = 0
    total_bones = len(skin_data_global[0]) if skin_data_global else 0
    for node_idx, mesh_idx, world_mat in nodes:
        try:
            parts = _gltf_build_mesh(gltf_json, mesh_idx, buffers, base_dir, skin_data_global)
        except Exception as e:
            Con.err(f"GLTF mesh {mesh_idx}: {e}"); continue
        for mesh, mat in parts:
            model.add(mesh, mat, world_mat, node_idx)
            total_tris += len(mesh.indices) // 3
    for anim_data in gltf_json.get("animations", []):
        anim = Animation(anim_data.get("name", "anim"))
        for ch in anim_data.get("channels", []):
            target = ch["target"]
            node_i = target.get("node", -1)
            path = target.get("path", "")
            if node_i < 0 or path not in ("translation", "rotation", "scale"): continue
            sampler = anim_data["samplers"][ch["sampler"]]
            times = _gltf_read_accessor(gltf_json, sampler["input"], buffers)
            values = _gltf_read_accessor(gltf_json, sampler["output"], buffers)
            if times is None or values is None: continue
            interp = sampler.get("interpolation", "LINEAR")
            anim.add_channel(AnimationChannel(node_i, path,
                times.flatten().astype(np.float32), values.astype(np.float32), interp))
        if anim.channels: model.animations[anim.name] = anim
    model._nodes_data = {"nodes": gltf_json.get("nodes", []),
                        "children": node_children, "parents": node_parent,
                        "skin": skin_data_global}
    Con.model(f"GLTF: {os.path.basename(path)} — {len(model.meshes)} подмешей, "
              f"{total_tris} треуг., {total_bones} костей, {len(model.animations)} анимаций")
    return model


def load_obj(path, default_color=(0.7,0.7,0.7)):
    if not os.path.exists(path):
        Con.err(f"Нет файла: {path}"); return None
    positions = []; normals = []; uvs = []; faces = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            parts = line.split()
            if parts[0] == "v": positions.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif parts[0] == "vn": normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif parts[0] == "vt": uvs.append([float(parts[1]), float(parts[2])])
            elif parts[0] == "f":
                face = []
                for token in parts[1:]:
                    comps = token.split("/")
                    vi = int(comps[0]) - 1
                    ti = int(comps[1]) - 1 if len(comps) > 1 and comps[1] else -1
                    ni = int(comps[2]) - 1 if len(comps) > 2 and comps[2] else -1
                    face.append((vi, ti, ni))
                faces.append(face)
    if not positions:
        Con.err(f"OBJ пустой: {path}"); return None
    vertex_map = {}; verts_data = []; indices = []
    for face in faces:
        for i in range(1, len(face) - 1):
            tri = [face[0], face[i], face[i+1]]
            for (vi, ti, ni) in tri:
                key = (vi, ti, ni)
                if key not in vertex_map:
                    v = positions[vi] if 0 <= vi < len(positions) else [0,0,0]
                    n = normals[ni] if 0 <= ni < len(normals) else [0,1,0]
                    uv = uvs[ti] if 0 <= ti < len(uvs) else [0,0]
                    uv = [uv[0], 1.0 - uv[1]]
                    row = _make_vertex_row(v, n, default_color, uv)
                    vertex_map[key] = len(verts_data); verts_data.append(row)
                indices.append(vertex_map[key])
    mesh = Mesh(np.array(verts_data, np.float32), np.array(indices, np.uint32))
    material = Material(color=default_color)
    model = Model(name=os.path.basename(path))
    model.add(mesh, material)
    Con.model(f"OBJ: {os.path.basename(path)} — {len(verts_data)} вершин")
    return model


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
        self.bbox_min = np.zeros(3, np.float32)
        self.bbox_max = np.zeros(3, np.float32)
        self.animator = None; self.model_ref = None
    @classmethod
    def from_mesh(cls, mesh, position=(0,0,0), color=(1,1,1), glow=0.0,
                  emissive=False, tag=None, billboard=False):
        e = cls(position)
        mat = Material(color=color)
        e.submeshes.append((mesh, mat, np.eye(4, dtype=np.float32), -1))
        e.color = np.array(color, np.float32)
        e.glow = glow; e.emissive = emissive; e.tag = tag; e.billboard = billboard
        v = mesh.verts[:, :3]
        if len(v) > 0:
            e.bbox_min = v.min(axis=0); e.bbox_max = v.max(axis=0)
        return e
    @classmethod
    def from_model(cls, model, position=(0,0,0), scale=1.0, tag=None):
        e = cls(position)
        e.scale = scale; e.model_ref = model
        for mm in model.meshes:
            e.submeshes.append((mm.mesh, mm.material, mm.local_matrix.copy(), mm.node_index))
        e.tag = tag
        e.bbox_min = model.bbox_min.copy(); e.bbox_max = model.bbox_max.copy()
        if model.animations:
            animator = Animator(model)
            if hasattr(model, "_nodes_data"):
                nd = model._nodes_data
                animator.setup_nodes(nd["children"], nd["parents"])
                animator.setup_default_trs(nd["nodes"])
                if nd.get("skin"): animator.setup_skin(nd["skin"][0], nd["skin"][1])
            e.animator = animator
        return e
    def set_position(self, x, y, z):
        self.position[0] = x; self.position[1] = y; self.position[2] = z
    def move(self, dx, dy, dz):
        self.position[0] += dx; self.position[1] += dy; self.position[2] += dz
    def rotate(self, ry=0.0, rx=0.0, rz=0.0):
        self.rotation[0] += rx; self.rotation[1] += ry; self.rotation[2] += rz
    def world_matrix(self):
        return model_matrix(self.position, self.scale,
                            self.rotation[1], self.rotation[0], self.rotation[2])
    def play_anim(self, name, loop=True, speed=1.0):
        if self.animator is None: return False
        return self.animator.play(name, loop, speed)
    def free(self):
        for sm in self.submeshes: sm[0].free()


# ═══════════════════════════════════════════════════════════════════
#                       INVENTORY
# ═══════════════════════════════════════════════════════════════════
class Inventory:
    def __init__(self):
        self.hotbar = [None] * 9
        self.main = [None] * 27
        self.selected = 0
    def add(self, item, count=1):
        name = item[0] if isinstance(item, tuple) else item
        for i in range(9):
            slot = self.hotbar[i]
            if slot and slot[0] == name:
                self.hotbar[i] = (slot[0], slot[1] + count)
                return True
        for i in range(9):
            if self.hotbar[i] is None:
                self.hotbar[i] = (item, count) if isinstance(item, tuple) else (name, count)
                return True
        for i in range(27):
            if self.main[i] is None:
                self.main[i] = (item, count) if isinstance(item, tuple) else (name, count)
                return True
        return False
    def get_selected(self):
        s = self.hotbar[self.selected]
        return s[0] if s else None
    def use_selected(self, amount=1):
        s = self.hotbar[self.selected]
        if s is None: return None
        item = s[0]
        new_count = s[1] - amount
        if new_count <= 0:
            self.hotbar[self.selected] = None
        else:
            self.hotbar[self.selected] = (item, new_count)
        return item


# ═══════════════════════════════════════════════════════════════════
#                       PLAYER
# ═══════════════════════════════════════════════════════════════════
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
        return np.array([math.sin(self.yaw)*cp, math.sin(self.pitch),
                         -math.cos(self.yaw)*cp], np.float32)
    def forward_flat(self):
        return np.array([math.sin(self.yaw), 0.0, -math.cos(self.yaw)], np.float32)
    def right_flat(self):
        return np.array([math.cos(self.yaw), 0.0, math.sin(self.yaw)], np.float32)


# ═══════════════════════════════════════════════════════════════════
#                       GUI
# ═══════════════════════════════════════════════════════════════════
class Button:
    def __init__(self, x, y, w, h, text, callback, font_size=24,
                 color=(0.2, 0.2, 0.25, 0.9),
                 hover_color=(0.35, 0.35, 0.5, 1.0),
                 text_color=(1, 1, 1, 1)):
        self.x = x; self.y = y; self.w = w; self.h = h
        self.text = text; self.callback = callback
        self.font_size = font_size
        self.color = color; self.hover_color = hover_color
        self.text_color = text_color
        self.hover = False
        self.enabled = True
    def contains(self, mx, my):
        return (self.enabled and self.x <= mx <= self.x + self.w
                and self.y <= my <= self.y + self.h)
    def on_click(self):
        if self.enabled and self.callback:
            self.callback()


# ═══════════════════════════════════════════════════════════════════
#                       Draw2D — УДОБНЫЙ 2D API
# ═══════════════════════════════════════════════════════════════════
class Draw2D:
    """Удобный 2D API. Все методы используют уже скомпилированный UI-шейдер."""
    def __init__(self, engine):
        self.engine = engine
        self.w = 1280
        self.h = 720

    def _use_ui(self):
        glUseProgram(self.engine._ui_prog)
        glUniform2f(self.engine._ui_u["uScreen"], self.w, self.h)
        glBindBuffer(GL_ARRAY_BUFFER, self.engine._ui_vbo)
        glBindVertexArray(self.engine._ui_vao)

    def _quad(self, x, y, w, h, color, use_tex=0, uv=(0, 0, 1, 1)):
        u0, v0, u1, v1 = uv
        verts = np.array([
            x, y, u0, v0,
            x + w, y, u1, v0,
            x + w, y + h, u1, v1,
            x, y, u0, v0,
            x + w, y + h, u1, v1,
            x, y + h, u0, v1,
        ], np.float32)
        glUniform4f(self.engine._ui_u["uColor"], *color)
        glUniform1i(self.engine._ui_u["uUseTex"], use_tex)
        glBufferSubData(GL_ARRAY_BUFFER, 0, verts.nbytes, verts)
        glDrawArrays(GL_TRIANGLES, 0, 6)

    # ─── Примитивы ───
    def rect(self, x, y, w, h, color):
        if len(color) == 3: color = (*color, 1.0)
        self._use_ui()
        self._quad(x, y, w, h, color)
        glBindVertexArray(0)

    def rect_outline(self, x, y, w, h, color, thickness=2):
        if len(color) == 3: color = (*color, 1.0)
        self.rect(x, y, w, thickness, color)
        self.rect(x, y + h - thickness, w, thickness, color)
        self.rect(x, y, thickness, h, color)
        self.rect(x + w - thickness, y, thickness, h, color)

    def pixel(self, x, y, color):
        self.rect(x, y, 1, 1, color)

    def line(self, x1, y1, x2, y2, color, thickness=2):
        if len(color) == 3: color = (*color, 1.0)
        dx = x2 - x1; dy = y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.001: return
        steps = max(2, int(length / 2))
        for i in range(steps):
            t = i / steps
            px = x1 + dx * t
            py = y1 + dy * t
            self.rect(px - thickness/2, py - thickness/2, thickness, thickness, color)

    def circle(self, cx, cy, radius, color, segments=24):
        if len(color) == 3: color = (*color, 1.0)
        self._use_ui()
        for i in range(segments):
            a = 2 * math.pi * i / segments
            px = cx + math.cos(a) * radius - 1
            py = cy + math.sin(a) * radius - 1
            self._quad(px, py, 2, 2, color)
        glBindVertexArray(0)

    def panel(self, x, y, w, h, bg=(0.1, 0.1, 0.15, 0.9),
              border=(0.5, 0.5, 0.6, 1.0), border_thickness=2):
        self.rect(x, y, w, h, bg)
        if border_thickness > 0:
            self.rect_outline(x, y, w, h, border, border_thickness)

    def progress(self, x, y, w, h, value, max_value,
                 color=(0.7, 0.2, 0.2, 1.0), bg=(0.1, 0.1, 0.1, 0.8)):
        self.rect(x, y, w, h, bg)
        if max_value > 0:
            v = max(0, min(1, value / max_value))
            self.rect(x, y, w * v, h, color)

    def slot(self, x, y, size, item=None, selected=False,
             bg=(0.1, 0.1, 0.1, 0.7)):
        border = (1.0, 1.0, 0.2, 1.0) if selected else (0.5, 0.5, 0.5, 1.0)
        self.rect(x, y, size, size, bg)
        self.rect_outline(x, y, size, size, border, 2)
        if item:
            name = item[0] if isinstance(item, tuple) else item
            palette = {
                "grass": (0.30, 0.72, 0.25), "dirt": (0.52, 0.36, 0.20),
                "stone": (0.55, 0.55, 0.55), "sand": (0.90, 0.83, 0.55),
                "wood": (0.40, 0.26, 0.12), "leaves": (0.15, 0.55, 0.15),
            }
            c = palette.get(name, (1.0, 0.5, 1.0))
            self.rect(x + 8, y + 8, size - 16, size - 16, (*c, 0.9))

    # ─── Текст ───
    def text(self, x, y, text, size=24, color=(1, 1, 1, 1)):
        if len(color) == 3: color = (*color, 1.0)
        if self.engine.font is None: return
        self._use_ui()
        glUniform4f(self.engine._ui_u["uColor"], *color)
        glUniform1i(self.engine._ui_u["uUseTex"], 1)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.engine.font.atlas_tex)
        glUniform1i(self.engine._ui_u["uTex"], 0)

        cx = x; cy = y
        for ch in text:
            if ch == "\n":
                cy += size + 4
                cx = x
                continue
            u0, v0, u1, v1 = self.engine.font.char_uv(ch)
            self._quad(cx, cy, size, size, color, use_tex=1, uv=(u0, v0, u1, v1))
            cx += size * 0.65
        glBindVertexArray(0)

    def text_centered(self, cx, y, text, size=24, color=(1, 1, 1, 1)):
        w = self.engine.text_width(text, size)
        self.text(cx - w / 2, y, text, size, color)

    def text_right(self, rx, y, text, size=24, color=(1, 1, 1, 1)):
        w = self.engine.text_width(text, size)
        self.text(rx - w, y, text, size, color)

    def screen_size(self):
        return (self.w, self.h)


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
    if (uBillboard == 1) {{
        pos = uCameraRight * pos.x + uCameraUp * pos.y;
    }}
    vec4 wp = uModel * vec4(pos, 1.0);
    vWorldPos = wp.xyz;
    vColor = aColor;
    vNormal = normalize(mat3(uModel) * nrm);
    vUV = aUV;
    gl_Position = uMVP * wp;
}}
"""

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
    if (uHasTexture == 1) {
        vec4 tex = texture(uTexture, vUV);
        albedo *= tex.rgb;
    }
    float ndotl = max(dot(normalize(vNormal), normalize(uSunDir)), 0.0);
    vec3 diffuse = albedo * (uAmbient + (1.0 - uAmbient) * ndotl) * uSunColor * 0.9;
    vec3 emissive = albedo * uGlow;
    vec3 color = diffuse + emissive;
    color = color / (1.0 + color * 0.25);
    FragColor = vec4(color, uAlpha);
}
"""

SKY_VERT = """#version 460 core
layout(location=0) in vec2 aPos;
out vec2 vUV;
void main() {
    vUV = aPos * 0.5 + 0.5;
    gl_Position = vec4(aPos, 0.9999, 1.0);
}
"""

SKY_FRAG = """#version 460 core
in vec2 vUV;
uniform vec3 uTop;
uniform vec3 uBottom;
out vec4 FragColor;
void main() {
    vec3 c = mix(uBottom, uTop, vUV.y);
    FragColor = vec4(c, 1.0);
}
"""

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
}
"""

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
    } else {
        FragColor = uColor;
    }
}
"""


def compile_shader_pair(vs, fs):
    v = compileShader(vs, GL_VERTEX_SHADER)
    f = compileShader(fs, GL_FRAGMENT_SHADER)
    p = compileProgram(v, f)
    glDeleteShader(v); glDeleteShader(f)
    return p


# ═══════════════════════════════════════════════════════════════════
#                       ПОСТ-ОБРАБОТКА
# ═══════════════════════════════════════════════════════════════════
def make_fbo(w, h, with_depth=True):
    fbo = glGenFramebuffers(1)
    glBindFramebuffer(GL_FRAMEBUFFER, fbo)
    color = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, color)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, color, 0)
    depth_tex = None
    if with_depth:
        depth_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, depth_tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT24, w, h, 0,
                     GL_DEPTH_COMPONENT, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depth_tex, 0)
    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    return fbo, color, depth_tex


class ShaderChain:
    def __init__(self, plugins):
        self.plugins = plugins
        self.scene_fbo = None; self.scene_color = None; self.scene_depth = None
        self.ping_fbo = None; self.ping_color = None
        self.width = 0; self.height = 0
        self.vao = None
        self._build_quad()
    def _build_quad(self):
        self.vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        verts = np.array([-1,-1,0,0, 1,-1,1,0, 1,1,1,1,
                          -1,-1,0,0, 1,1,1,1, -1,1,0,1], np.float32)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4*4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4*4, ctypes.c_void_p(2*4))
        glBindVertexArray(0)
        self.vbo = vbo
    def ensure_size(self, w, h):
        if self.width == w and self.height == h: return
        self.width, self.height = w, h
        if self.scene_fbo is not None:
            glDeleteFramebuffers(1, [self.scene_fbo])
            glDeleteTextures(1, [self.scene_color])
            if self.scene_depth: glDeleteTextures(1, [self.scene_depth])
            glDeleteFramebuffers(1, [self.ping_fbo])
            glDeleteTextures(1, [self.ping_color])
        self.scene_fbo, self.scene_color, self.scene_depth = make_fbo(w, h, True)
        self.ping_fbo, self.ping_color, _ = make_fbo(w, h, False)
    def bind_scene(self, w, h):
        self.ensure_size(w, h)
        glBindFramebuffer(GL_FRAMEBUFFER, self.scene_fbo)
    def unbind(self):
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
    def apply(self, ctx):
        if not self.plugins: return
        glDisable(GL_DEPTH_TEST); glDisable(GL_CULL_FACE); glDisable(GL_BLEND)
        glBindVertexArray(self.vao)
        glViewport(0, 0, self.width, self.height)
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
            p.set_uniform("uTime", ctx["time"])
            p.set_uniform("uResolution", ctx["resolution"])
            p.set_uniform("uCameraPos", ctx["camera_pos"])
            p.set_uniform("uCameraDir", ctx["camera_dir"])
            p.set_uniform("uNear", ctx["near"]); p.set_uniform("uFar", ctx["far"])
            p.set_uniform("uSunDir", ctx["sun_dir"]); p.set_uniform("uSunColor", ctx["sun_color"])
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
            for attr in getattr(module, "UNIFORMS", []):
                self.uniforms[attr] = glGetUniformLocation(self.program, attr)
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


# ═══════════════════════════════════════════════════════════════════
#                       МОДУЛЬНЫЕ ИМПОРТЫ
# ═══════════════════════════════════════════════════════════════════
_ADDED_PATHS = set()

def _ensure_path(path):
    p = os.path.abspath(path)
    if p not in _ADDED_PATHS and os.path.isdir(p):
        sys.path.insert(0, p); _ADDED_PATHS.add(p)

def _ensure_package(dirpath):
    if not os.path.isdir(dirpath): return
    init = os.path.join(dirpath, "__init__.py")
    if not os.path.exists(init):
        try:
            with open(init, "w", encoding="utf-8") as f:
                f.write("# auto-generated\n")
        except Exception: pass

def _purge_from_sys_modules(prefixes):
    for name in list(sys.modules.keys()):
        for p in prefixes:
            if name == p or name.startswith(p + "."):
                del sys.modules[name]; break


def load_main_system(engine):
    sys_dir = os.path.abspath("System")
    parent = os.path.dirname(sys_dir)
    _ensure_path(parent); _ensure_path(sys_dir); _ensure_package(sys_dir)
    main_path = os.path.join(sys_dir, "Main.py")
    if not os.path.exists(main_path): return False
    try:
        _purge_from_sys_modules(["System"])
        import System
        import System.Main
        mod = sys.modules["System.Main"]
        engine.systems.append(mod)
        for name in list(sys.modules.keys()):
            if name.startswith("System."): engine.modules[name] = sys.modules[name]
        sname = getattr(mod, "SYSTEM_NAME", "Main")
        sver = getattr(mod, "SYSTEM_VERSION", "1.0")
        sauth = getattr(mod, "SYSTEM_AUTHOR", "unknown")
        Con.plugin(f"System/Main.py: {sname} v{sver} (автор: {sauth})")
        if hasattr(mod, "on_engine_start"): mod.on_engine_start(engine)
        return True
    except Exception as e:
        Con.err(f"Main.py: {e}"); traceback.print_exc(); return False


def load_mods(engine):
    mods_dir = os.path.abspath("Mods")
    if not os.path.isdir(mods_dir): return
    _ensure_path(mods_dir)
    for d in sorted(os.listdir(mods_dir)):
        dpath = os.path.join(mods_dir, d)
        if not os.path.isdir(dpath): continue
        if d.startswith("_") or d.startswith("."): continue
        mod_file = os.path.join(dpath, "mod.py")
        if not os.path.exists(mod_file): continue
        _ensure_package(dpath)
        try:
            _purge_from_sys_modules([d])
            importlib.import_module(d)
            mod = importlib.import_module(f"{d}.mod")
            engine.mods.append(mod)
            for name in list(sys.modules.keys()):
                if name == d or name.startswith(d + "."): engine.modules[name] = sys.modules[name]
            mname = getattr(mod, "MOD_NAME", d)
            mver = getattr(mod, "MOD_VERSION", "1.0")
            mauth = getattr(mod, "MOD_AUTHOR", "unknown")
            Con.mod(f"Загружен: {mname} v{mver} (автор: {mauth})")
            if hasattr(mod, "on_load"): mod.on_load(engine)
        except Exception as e:
            Con.err(f"Mod '{d}': {e}"); traceback.print_exc()


def load_shaders(engine):
    if not os.path.isdir("Shaders"): return []
    shaders_dir = os.path.abspath("Shaders")
    _ensure_path(shaders_dir); _ensure_package(shaders_dir)
    files = sorted(f for f in os.listdir(shaders_dir)
                   if f.endswith(".py") and not f.startswith("_") and f != "__init__.py")
    plugins = []
    for fname in files:
        mod_name = fname[:-3]
        try:
            _purge_from_sys_modules([f"Shaders.{mod_name}"])
            mod = importlib.import_module(f"Shaders.{mod_name}")
            p = ShaderPlugin(mod_name, fname, mod)
            plugins.append(p)
            d_str = " [depth]" if p.needs_depth else ""
            Con.shader(f"Активирован: {p.name} v{p.version} ({p.author}) — {p.desc}{d_str}")
        except Exception as e:
            Con.err(f"Shader '{fname}': {e}"); traceback.print_exc()
    plugins.sort(key=lambda p: p.order)
    return plugins


# ═══════════════════════════════════════════════════════════════════
#                          ENGINE
# ═══════════════════════════════════════════════════════════════════
class Engine:
    def __init__(self):
        self.config = None
        self.player = None
        self.window = None
        self.sounds = None
        self.systems = []; self.mods = []; self.shaders = []
        self.modules = {}
        self.entities = []
        self.chunk_world = None
        self.collision = CollisionWorld()
        self.inventory = Inventory()
        self.font = None
        self.buttons = []
        self.draw2d = None
        self.time = 0.0; self.frame = 0; self.fps = 0; self.running = True
        self.events = {}
        self._draw_3d_hooks = []; self._draw_2d_hooks = []
        self._player_controller = None
        self._camera_mode = "fps"
        self._mouse_captured = False
        self._keys = {}
        self._mouse_x = 0.0; self._mouse_y = 0.0
        self._mouse_delta = (0.0, 0.0); self._mouse_last = (0.0, 0.0)
        self._pending_mouse_capture = None
        self._camera_override = None
        self.models = {}; self.textures = {}
        self._mesh_prog = None; self._mesh_u = None; self._bone_loc = None
        self._sky_prog = None; self._sky_u = None; self._sky_vao = None
        self._ui_prog = None; self._ui_u = None; self._ui_vao = None
        self._ui_vbo = None
        self._fb_w = 1280; self._fb_h = 720
        self.debug = False
        self.wireframe = False

    # ── Спавн ──
    def spawn_cube(self, position, size=1.0, color=(1,1,1), glow=0.0,
                   rotation=(0,0,0), tag=None, emissive=False):
        return self.spawn_box(position, (size, size, size), color, glow, rotation, tag, emissive)

    def spawn_box(self, position, size=(1,1,1), color=(1,1,1), glow=0.0,
                  rotation=(0,0,0), tag=None, emissive=False):
        m = make_box(size, color)
        e = Entity.from_mesh(m, position, color, glow, emissive, tag)
        e.rotation = np.array(rotation, np.float32)
        self.entities.append(e); return e

    def spawn_sphere(self, position, radius=1.0, color=(1,1,1), glow=0.0,
                     tag=None, emissive=False, rings=16, sectors=24):
        m = make_sphere(radius, rings, sectors, color)
        e = Entity.from_mesh(m, position, color, glow, emissive, tag)
        self.entities.append(e); return e

    def spawn_cylinder(self, position, radius=1.0, height=2.0, color=(1,1,1),
                       glow=0.0, tag=None, emissive=False):
        m = make_cylinder(radius, height, 24, color)
        e = Entity.from_mesh(m, position, color, glow, emissive, tag)
        self.entities.append(e); return e

    def spawn_billboard(self, position, size=1.0, color=(1,1,1), glow=0.0,
                        tag=None, emissive=True, texture=None):
        m = make_billboard(size, color)
        e = Entity.from_mesh(m, position, color, glow, emissive, tag, billboard=True)
        if texture: e.submeshes[0][1].texture = texture
        self.entities.append(e); return e

    def spawn_mesh(self, verts, indices, position, color=(1,1,1), glow=0.0,
                   tag=None, emissive=False, texture=None):
        m = Mesh(np.array(verts, np.float32), np.array(indices, np.uint32))
        e = Entity.from_mesh(m, position, color, glow, emissive, tag)
        if texture: e.submeshes[0][1].texture = texture
        self.entities.append(e); return e

    def spawn_model(self, model, position, scale=1.0, tag=None):
        if isinstance(model, str):
            model = self.models.get(model) or self.load_gltf(model)
        if model is None: return None
        e = Entity.from_model(model, position, scale, tag)
        self.entities.append(e); return e

    # ── Загрузка ──
    def load_gltf(self, path):
        if path in self.models: return self.models[path]
        if not os.path.isabs(path):
            for c in (path, f"Assets/Models/{path}"):
                if os.path.exists(c): path = c; break
        m = load_gltf(path)
        if m: self.models[path] = m
        return m

    def load_obj(self, path, color=(0.7,0.7,0.7)):
        key = f"obj:{path}:{color}"
        if key in self.models: return self.models[key]
        if not os.path.isabs(path):
            for c in (path, f"Assets/Models/{path}"):
                if os.path.exists(c): path = c; break
        m = load_obj(path, color)
        if m: self.models[key] = m
        return m

    def load_texture(self, path, wrap=True, nearest=False):
        if path in self.textures: return self.textures[path]
        if not os.path.isabs(path):
            for c in (path, f"Assets/Textures/{path}"):
                if os.path.exists(c): path = c; break
        t = load_texture(path, wrap, nearest)
        if t: self.textures[path] = t
        return t

    # ── Управление ──
    def remove_by_tag(self, tag):
        for e in self.entities:
            if e.tag == tag: e.alive = False
        self.entities = [e for e in self.entities if e.alive]

    def get_entities_by_tag(self, tag):
        return [e for e in self.entities if e.tag == tag and e.alive]

    # ── Коллизии ──
    def add_collider(self, mnx, mny, mnz, mxx, mxy, mxz):
        self.collision.add_box(mnx, mny, mnz, mxx, mxy, mxz)
    def add_floor(self, mnx, mnz, mxx, mxz, y_top):
        self.collision.add_floor(mnx, mnz, mxx, mxz, y_top)
    def collide(self, pos, radius, height):
        return self.collision.collide_aabb(pos, radius, height)
    def clear_colliders(self):
        self.collision.clear()

    # ── GUI ──
    def add_button(self, x, y, w, h, text, callback, font_size=24,
                   color=(0.2, 0.2, 0.25, 0.9),
                   hover_color=(0.35, 0.35, 0.5, 1.0)):
        btn = Button(x, y, w, h, text, callback, font_size, color, hover_color)
        self.buttons.append(btn)
        return btn

    def clear_buttons(self):
        self.buttons.clear()

    def handle_gui_click(self, mx, my):
        for btn in self.buttons:
            if btn.contains(mx, my):
                btn.on_click()
                return True
        return False

    def update_gui_hover(self):
        for btn in self.buttons:
            btn.hover = btn.contains(self._mouse_x, self._mouse_y)

    # ── 2D рисование (прокси к Draw2D) ──
    def rect(self, x, y, w, h, color):
        if self.draw2d: self.draw2d.rect(x, y, w, h, color)
    def rect_outline(self, x, y, w, h, color, thickness=2):
        if self.draw2d: self.draw2d.rect_outline(x, y, w, h, color, thickness)
    def pixel(self, x, y, color):
        if self.draw2d: self.draw2d.pixel(x, y, color)
    def line(self, x1, y1, x2, y2, color, thickness=2):
        if self.draw2d: self.draw2d.line(x1, y1, x2, y2, color, thickness)
    def circle(self, cx, cy, radius, color, segments=24):
        if self.draw2d: self.draw2d.circle(cx, cy, radius, color, segments)
    def panel(self, x, y, w, h, bg=(0.1,0.1,0.15,0.9), border=(0.5,0.5,0.6,1.0),
              border_thickness=2):
        if self.draw2d: self.draw2d.panel(x, y, w, h, bg, border, border_thickness)
    def progress(self, x, y, w, h, value, max_value,
                 color=(0.7,0.2,0.2,1.0), bg=(0.1,0.1,0.1,0.8)):
        if self.draw2d: self.draw2d.progress(x, y, w, h, value, max_value, color, bg)
    def slot(self, x, y, size, item=None, selected=False, bg=(0.1,0.1,0.1,0.7)):
        if self.draw2d: self.draw2d.slot(x, y, size, item, selected, bg)

    # ── Старое 2D (совместимость) ──
    def draw_rect(self, x, y, w, h, color=(1,1,1,1)):
        self.rect(x, y, w, h, color)

    def draw_text(self, x, y, text, size=24, color=(1,1,1,1)):
        if self.draw2d: self.draw2d.text(x, y, text, size, color)

    def text(self, x, y, text, size=24, color=(1,1,1,1)):
        if self.draw2d: self.draw2d.text(x, y, text, size, color)
    def text_centered(self, cx, y, text, size=24, color=(1,1,1,1)):
        if self.draw2d: self.draw2d.text_centered(cx, y, text, size, color)
    def text_right(self, rx, y, text, size=24, color=(1,1,1,1)):
        if self.draw2d: self.draw2d.text_right(rx, y, text, size, color)

    def text_width(self, text, size=24):
        return len(text) * size * 0.65

    def text_height(self, size=24):
        return size

    def screen_size(self):
        return (self._fb_w, self._fb_h)

    def draw_button(self, btn):
        color = btn.hover_color if btn.hover else btn.color
        self.rect(btn.x, btn.y, btn.w, btn.h, color)
        tw = self.text_width(btn.text, btn.font_size)
        th = btn.font_size
        tx = btn.x + (btn.w - tw) / 2
        ty = btn.y + (btn.h - th) / 2
        self.text(tx, ty, btn.text, btn.font_size, btn.text_color)

    # ── События ──
    def on(self, event, handler): self.events.setdefault(event, []).append(handler)
    def emit(self, event, *args, **kw):
        for h in self.events.get(event, []):
            try: h(*args, **kw)
            except Exception as e: Con.err(f"Event '{event}': {e}")

    # ── Хуки ──
    def on_draw_3d(self, handler): self._draw_3d_hooks.append(handler)
    def on_draw_2d(self, handler): self._draw_2d_hooks.append(handler)
    def set_player_controller(self, fn): self._player_controller = fn
    def set_camera_mode(self, mode): self._camera_mode = mode
    def set_camera_override(self, fn): self._camera_override = fn
    def set_chunk_world(self, world): self.chunk_world = world

    # ── Ввод ──
    def is_key_down(self, key): return self._keys.get(key, False)
    def is_mouse_captured(self): return self._mouse_captured
    def set_mouse_captured(self, cap): self._pending_mouse_capture = cap
    def get_mouse_delta(self): return self._mouse_delta
    def get_mouse_pos(self): return (self._mouse_x, self._mouse_y)

    # ── Звук ──
    def play_sound(self, name, volume=1.0):
        if self.sounds: self.sounds.play(name, volume)
    def play_sound_at(self, name, pos, volume=1.0):
        if self.sounds and self.player:
            self.sounds.play_at(name, pos, self.player.pos, 32.0, volume)

    # ── Импорты ──
    def import_module(self, name):
        try:
            m = importlib.import_module(name); self.modules[name] = m; return m
        except Exception as e: Con.err(f"import_module('{name}'): {e}"); return None
    def import_mod(self, mod_name, sub=None):
        full = f"{mod_name}.{sub}" if sub else mod_name
        try:
            m = importlib.import_module(full); self.modules[full] = m; return m
        except Exception as e: Con.err(f"import_mod('{full}'): {e}"); return None
    def reload_module(self, name):
        if name in sys.modules:
            try: return importlib.reload(sys.modules[name])
            except Exception as e: Con.err(f"reload: {e}")
        return None
    def get_module(self, name): return self.modules.get(name) or sys.modules.get(name)
    def quit(self): self.running = False


# ═══════════════════════════════════════════════════════════════════
#                       BOOT
# ═══════════════════════════════════════════════════════════════════
def boot_folders():
    created = False
    for f in FOLDERS:
        if not os.path.exists(f):
            os.makedirs(f, exist_ok=True)
            print(f"[BOOT] + {f}/")
            created = True
    return created

def boot_check_main():
    return os.path.exists("System/Main.py")


# ═══════════════════════════════════════════════════════════════════
#                          MAIN
# ═══════════════════════════════════════════════════════════════════
def main():
    t_start = time.time()
    Con.banner("VOXEL ENGINE v8.1 — Draw2D EDITION")

    Con.step("Boot")
    created = boot_folders()
    if not boot_check_main():
        print()
        Con.warn("System/Main.py НЕ НАЙДЕН.")
        Con.info("Положи свой System/Main.py с функцией on_engine_start(engine).")
        print()
        return

    Con.step("Конфиг")
    config = Config("config.json")

    engine = Engine()
    engine.config = config
    engine.sounds = SoundManager(config)

    Con.sep(); Con.step("Окно OpenGL 4.6 Core")
    if not glfw.init():
        Con.err("GLFW init failed"); return
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 6)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
    w = config.get("window", "width", default=1280)
    h = config.get("window", "height", default=720)
    title = config.get("window", "title", default="Voxel Engine")
    window = glfw.create_window(w, h, title, None, None)
    if not window:
        glfw.terminate(); Con.err("window failed"); return
    glfw.make_context_current(window)
    glfw.swap_interval(1 if config.get("render", "vsync", default=False) else 0)
    engine.window = window
    Con.ok(f"OpenGL: {glGetString(GL_VERSION).decode()}")
    Con.ok(f"GPU:    {glGetString(GL_RENDERER).decode()}")

    engine.player = Player(config)
    engine._fb_w = w; engine._fb_h = h

    # Шрифт
    try:
        engine.font = Font(path=config.get("font", "path", default=""),
                           size=config.get("font", "size", default=24),
                           cell=config.get("font", "cell", default=32))
    except Exception as e:
        Con.err(f"Шрифт: {e}")

    # 3D шейдер
    mesh_prog = compile_shader_pair(MESH_VERT, MESH_FRAG)
    mesh_u = {n: glGetUniformLocation(mesh_prog, n)
              for n in ["uMVP","uModel","uCameraRight","uCameraUp","uBillboard",
                        "uSunDir","uSunColor","uAmbient","uColorMul","uGlow",
                        "uAlpha","uHasTexture","uTexture","uHasSkin"]}
    bone_loc = glGetUniformLocation(mesh_prog, "uBones")
    engine._mesh_prog = mesh_prog; engine._mesh_u = mesh_u; engine._bone_loc = bone_loc

    # Sky шейдер
    sky_prog = compile_shader_pair(SKY_VERT, SKY_FRAG)
    engine._sky_prog = sky_prog
    engine._sky_u = {n: glGetUniformLocation(sky_prog, n) for n in ["uTop", "uBottom"]}
    sky_vao = glGenVertexArrays(1); sky_vbo = glGenBuffers(1)
    sky_verts = np.array([-1,-1,0,0, 1,-1,1,0, 1,1,1,1,
                          -1,-1,0,0, 1,1,1,1, -1,1,0,1], np.float32)
    glBindVertexArray(sky_vao)
    glBindBuffer(GL_ARRAY_BUFFER, sky_vbo)
    glBufferData(GL_ARRAY_BUFFER, sky_verts.nbytes, sky_verts, GL_STATIC_DRAW)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4*4, ctypes.c_void_p(0))
    glBindVertexArray(0)
    engine._sky_vao = sky_vao

    # UI шейдер
    ui_prog = compile_shader_pair(UI_VERT, UI_FRAG)
    engine._ui_prog = ui_prog
    engine._ui_u = {n: glGetUniformLocation(ui_prog, n)
                    for n in ["uScreen","uPos","uSize","uColor","uUseTex","uTex"]}
    ui_vao = glGenVertexArrays(1); ui_vbo = glGenBuffers(1)
    glBindVertexArray(ui_vao)
    glBindBuffer(GL_ARRAY_BUFFER, ui_vbo)
    glBufferData(GL_ARRAY_BUFFER, 24*4*4, None, GL_DYNAMIC_DRAW)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4*4, ctypes.c_void_p(0))
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4*4, ctypes.c_void_p(2*4))
    glBindVertexArray(0)
    engine._ui_vao = ui_vao; engine._ui_vbo = ui_vbo

    # Draw2D
    engine.draw2d = Draw2D(engine)
    Con.ui("Draw2D активирован")

    # System/Main.py
    Con.sep(); Con.step("Загрузка System/Main.py")
    if not load_main_system(engine):
        Con.err("Main.py не загрузился"); return

    Con.sep(); Con.step("Загрузка Mods")
    load_mods(engine)

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
            if key == glfw.KEY_ESCAPE: engine.emit("escape")
            elif key == glfw.KEY_F3: engine.debug = not engine.debug
            elif key == glfw.KEY_F4:
                engine.wireframe = not engine.wireframe
                if engine.wireframe: glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                else: glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            engine._keys[key] = True
            engine.emit("key_press", key)
        elif action == glfw.RELEASE:
            engine._keys[key] = False
            engine.emit("key_release", key)

    def on_cursor(win, x, y):
        engine._mouse_x = x; engine._mouse_y = y
        if not engine._mouse_captured:
            engine._mouse_last = (x, y); return
        dx = x - engine._mouse_last[0]; dy = engine._mouse_last[1] - y
        engine._mouse_last = (x, y)
        engine._mouse_delta = (dx, dy)
        engine.emit("mouse_move", dx, dy)

    def on_mb(win, btn, action, mods):
        if action != glfw.PRESS: return
        engine.emit("mouse_click", engine._mouse_x, engine._mouse_y, btn)
        engine.emit("mouse_press", btn)

    glfw.set_key_callback(window, on_key)
    glfw.set_cursor_pos_callback(window, on_cursor)
    glfw.set_mouse_button_callback(window, on_mb)

    Con.sep()
    Con.ok(f"ГОТОВО ЗА {time.time()-t_start:.2f} СЕК")
    print()

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
            engine.update_gui_hover()

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
                except Exception as ex: Con.err(f"entity {e.id}: {ex}")
            if e.animator is not None: e.animator.update(dt)
        engine.entities = [e for e in engine.entities if e.alive]

        for p in engine.shaders:
            if p.on_frame:
                try: p.on_frame(engine, dt)
                except Exception as e: Con.err(f"{p.name}.on_frame: {e}")

        fb_w, fb_h = glfw.get_framebuffer_size(window)
        engine._fb_w = fb_w; engine._fb_h = fb_h
        if engine.draw2d: engine.draw2d.w = fb_w; engine.draw2d.h = fb_h

        if shader_chain: shader_chain.bind_scene(fb_w, fb_h)
        else: glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(0, 0, fb_w, fb_h)

        bg = sky_bottom
        glClearColor(bg[0], bg[1], bg[2], 1.0)
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

        if config.get("render", "frustum_culling", default=True):
            frustum.from_matrix(mvp)

        # Sky
        glUseProgram(sky_prog)
        glUniform3fv(engine._sky_u["uTop"], 1, sky_top.tolist())
        glUniform3fv(engine._sky_u["uBottom"], 1, sky_bottom.tolist())
        glBindVertexArray(engine._sky_vao)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)

        # Chunks
        if engine.chunk_world is not None:
            try:
                if hasattr(engine.chunk_world, "visible_chunks"):
                    chunks = engine.chunk_world.visible_chunks(eye)
                else: chunks = engine.chunk_world.chunks.values()
                for c in chunks:
                    if hasattr(c, "draw"): c.draw()
            except Exception as e: Con.err(f"chunk_world: {e}")

        # Meshes
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
                radius = max(1.0, float(np.linalg.norm(e.bbox_max - e.bbox_min)) * e.scale)
                if not frustum.sphere_visible(tuple(e.position), radius):
                    continue

            world = e.world_matrix()
            glUniformMatrix4fv(mesh_u["uModel"], 1, GL_FALSE, world.flatten(order='F'))
            glUniform1i(mesh_u["uBillboard"], 1 if e.billboard else 0)
            glUniform1f(mesh_u["uGlow"], e.glow)

            bones = None
            if e.animator is not None: bones = e.animator.get_bone_matrices()
            has_skin = 1 if bones is not None else 0
            glUniform1i(mesh_u["uHasSkin"], has_skin)
            if bones is not None:
                flat = bones.reshape(-1, order='F').astype(np.float32)
                glUniformMatrix4fv(bone_loc, MAX_BONES, GL_FALSE, flat)

            for (mesh, mat, local, _) in e.submeshes:
                has_tex = mat.bind()
                glUniform1i(mesh_u["uHasTexture"], has_tex)
                if has_tex: glUniform1i(mesh_u["uTexture"], 0)
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

        # 2D GUI
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        for btn in engine.buttons:
            try: engine.draw_button(btn)
            except Exception as e: Con.err(f"draw_button: {e}")

        for h in engine._draw_2d_hooks:
            try: h(engine, fb_w, fb_h)
            except Exception as e: Con.err(f"draw_2d: {e}")

        glEnable(GL_DEPTH_TEST)

        glfw.swap_buffers(window); glfw.poll_events()

        state["frames"] += 1
        if now - state["fps_time"] >= 1.0:
            engine.fps = state["frames"]; state["frames"] = 0; state["fps_time"] = now
            glfw.set_window_title(window,
                f"{title} | FPS: {engine.fps} | ent: {len(engine.entities)}")

    for p in engine.shaders:
        if p.on_unload:
            try: p.on_unload(engine)
            except Exception: pass
    for e in engine.entities: e.free()
    if engine.sounds: engine.sounds.stop_all()
    glfw.terminate()
    Con.ok(f"Выход за {time.time()-t_start:.2f} сек")


if __name__ == "__main__":
    try: main()
    except Exception as e:
        Con.err(f"Фатальная: {e}")
        traceback.print_exc()
        sys.exit(1)