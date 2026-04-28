# -*- coding: utf-8 -*-
"""
Magnetic Imager Tile v3 Python Visualization / 磁成像传感器阵列 v3 Python 可视化
Migrated from Processing sketch (projecttest.pde) / 从 Processing 草图迁移

Two 8x8 grids are shown: normal gain (top) and high-gain (bottom).
显示两个 8x8 网格：正常增益（上方）和高增益（下方）。
The high-gain is particularly useful for low-intensity fields.
高增益模式对低强度磁场特别有用。

Keys (lower-case) / 按键（小写）:
  L  - Live mode. Start streaming data live from the tile. / 实时模式，开始从传感器流式传输数据
  1-4 - High-speed capture at different frequencies. / 不同频率的高速捕获
  C  - Calibrate out background level. / 校准背景电平
  S  - Stop streaming (idle). / 停止数据流（空闲）
  H  - Send 'H' command. / 发送 'H' 命令
  A  - Clear data array. / 清空数据数组
  D  - Print calibration data to console. / 打印校准数据到控制台
  Space - Save screenshot to PNG. / 保存截图
"""

import sys
import threading
import time
import random

import serial
import serial.tools.list_ports
import pygame

# ── Constants / 常量定义 ───────────────────────────────────────────
MAX_SIZE = 8
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 560
PIXEL_SIZE = 30
GRID_SIZE = MAX_SIZE * PIXEL_SIZE  # 240

SIDEBAR_WIDTH = 145
STATUS_BAR_HEIGHT = 22
GRID_GAP = 28  # gap between two side-by-side grids

# Grid area: two grids + gap = GRID_SIZE * 2 + GRID_GAP = 508
# Center it in the content area (WINDOW_WIDTH - SIDEBAR_WIDTH = 655)
GRIDS_TOTAL_WIDTH = GRID_SIZE * 2 + GRID_GAP  # 508
CONTENT_AREA_WIDTH = WINDOW_WIDTH - SIDEBAR_WIDTH  # 655
GRIDS_LEFT = (CONTENT_AREA_WIDTH - GRIDS_TOTAL_WIDTH) // 2  # ~73
GRID_NORMAL_LEFT = GRIDS_LEFT
GRID_HIGH_LEFT = GRIDS_LEFT + GRID_SIZE + GRID_GAP

# Vertical centering: grids + colorbar + labels
GRID_TOP = 50  # top margin for labels
GRID_LABEL_HEIGHT = 16
COLORBAR_TOP = GRID_TOP + GRID_LABEL_HEIGHT + GRID_SIZE + 20
STATUS_BAR_TOP = WINDOW_HEIGHT - STATUS_BAR_HEIGHT

MAX_VALUE = 660.0
MAX_CALIB_FRAMES = 200
BAUD_RATE = 115200

# ── Color Palette / 配色 ──
COLOR_VOID = (13, 21, 32)            # #0D1520
COLOR_SIDEBAR = (22, 34, 48)         # #162230
COLOR_SIDEBAR_EDGE = (56, 76, 100)   # #384C64
COLOR_PANEL = (30, 46, 64)           # #1E2E40
COLOR_PANEL_BORDER = (80, 110, 150)  # #506E96
COLOR_TEXT = (224, 232, 242)         # #E0E8F2
COLOR_TEXT_MUTED = (122, 149, 181)   # #7A95B5
COLOR_ACCENT = (88, 120, 152)        # #587898
COLOR_ACCENT_LIGHT = (120, 160, 200) # #78A0C8

# Frosted glass alphas
FROST_PANEL_ALPHA = 140   # out of 255
FROST_SIDEBAR_ALPHA = 185
FROST_STATUSBAR_ALPHA = 215

# Button
BUTTON_WIDTH = SIDEBAR_WIDTH - 20
BUTTON_HEIGHT = 30
BUTTON_GAP = 4
BUTTON_RADIUS = 6
SIDEBAR_PADDING_TOP = 12
SIDEBAR_PADDING_X = 10

# Toast
TOAST_DURATION_MS = 1500
TOAST_FADE_MS = 260

# Animation
ANIM_SPEED = 12.0  # lerp factor per second
CELL_PULSE_DURATION = 0.3  # seconds

BUTTON_DEFS = [
    ("实时 L", "L"),
    ("停止 S", "S"),
    ("H 命令", "H"),
    ("高速 1", "1"),
    ("高速 2", "2"),
    ("高速 3", "3"),
    ("高速 4", "4"),
    ("校准 C", "C"),
    ("清空 A", "A"),
    ("截图 Spc", "SPACE"),
]


def lerp_color(current, target, dt, speed=ANIM_SPEED):
    """Frame-rate-independent color lerp. Returns (r,g,b) tuple."""
    t = min(1.0, speed * dt)
    return (
        int(current[0] + (target[0] - current[0]) * t),
        int(current[1] + (target[1] - current[1]) * t),
        int(current[2] + (target[2] - current[2]) * t),
    )


def lerp_float(current, target, dt, speed=ANIM_SPEED):
    """Frame-rate-independent float lerp."""
    t = min(1.0, speed * dt)
    return current + (target - current) * t


class CellAnimState:
    """Tracks per-cell animation: current displayed color lerping toward target."""
    def __init__(self):
        self.target = (0, 0, 0)
        self.current = (0, 0, 0)
        self.timer = 0.0  # seconds remaining in pulse

    def set_target(self, color, pulse=False):
        self.target = color
        if pulse:
            self.timer = CELL_PULSE_DURATION

    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt
        self.current = lerp_color(self.current, self.target, dt)


def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, v))


def create_cool_frosted_background(size):
    surface = pygame.Surface(size)
    surface.fill(COLOR_BG_BASE)

    noise = pygame.Surface(size, pygame.SRCALPHA)
    rng = random.Random(7)
    for _ in range(900):
        x = rng.randrange(0, size[0])
        y = rng.randrange(0, size[1])
        r = rng.choice([1, 1, 1, 2])
        shade = rng.randrange(22, 60)
        alpha = rng.randrange(12, 26)
        pygame.draw.circle(noise, (shade, shade + 4, shade + 12, alpha), (x, y), r)
    for _ in range(450):
        x = rng.randrange(0, size[0])
        y = rng.randrange(0, size[1])
        r = 1
        shade = rng.randrange(120, 160)
        alpha = rng.randrange(10, 18)
        pygame.draw.circle(noise, (shade, shade + 8, shade + 22, alpha), (x, y), r)

    glow = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.circle(glow, (90, 130, 170, 30), (size[0] - 120, 180), 180)
    pygame.draw.circle(glow, (70, 110, 150, 22), (size[0] - 60, 420), 220)

    frost = pygame.Surface(size, pygame.SRCALPHA)
    frost.fill((200, 215, 235, 18))

    surface.blit(glow, (0, 0))
    surface.blit(frost, (0, 0))
    surface.blit(noise, (0, 0))
    return surface


# ── Data Store / 数据存储 ──────────────────────────────────────────
class DataStore:
    def __init__(self):
        self.data = [[250] * MAX_SIZE for _ in range(MAX_SIZE)]
        self.data_calib = [[0] * MAX_SIZE for _ in range(MAX_SIZE)]
        self.cur_data_idx = 0
        self.num_calib_frames = 0
        self.calibration_enabled = False
        self.is_calibrated = False
        self.lock = threading.Lock()

    def add_row(self, values):
        with self.lock:
            for j in range(MAX_SIZE):
                self.data[self.cur_data_idx][j] = values[j]
                if self.calibration_enabled:
                    self.data_calib[self.cur_data_idx][j] += values[j]

            self.cur_data_idx += 1
            if self.cur_data_idx >= MAX_SIZE:
                self.cur_data_idx = 0
                if self.calibration_enabled:
                    self.num_calib_frames += 1
                    if self.num_calib_frames >= MAX_CALIB_FRAMES:
                        self.calibration_enabled = False
                        self._calibrate()

    def _calibrate(self):
        with self.lock:
            print("Calibration Data:")
            for i in range(MAX_SIZE):
                for j in range(MAX_SIZE):
                    self.data_calib[i][j] = int(
                        self.data_calib[i][j] / MAX_CALIB_FRAMES
                    )
                    print(f"{self.data_calib[i][j]}  ", end="")
                print()
            self.is_calibrated = True

    def reset_idx(self):
        with self.lock:
            self.cur_data_idx = 0

    def start_calibration(self):
        with self.lock:
            for i in range(MAX_SIZE):
                for j in range(MAX_SIZE):
                    self.data_calib[i][j] = 0
            self.num_calib_frames = 0
            self.calibration_enabled = True
            self.is_calibrated = False

    def clear_data(self):
        with self.lock:
            for i in range(MAX_SIZE):
                for j in range(MAX_SIZE):
                    self.data[i][j] = 0
            self.cur_data_idx = 0

    def get_snapshot(self):
        with self.lock:
            data = [row[:] for row in self.data]
            data_calib = [row[:] for row in self.data_calib]
            is_calibrated = self.is_calibrated
        return data, data_calib, is_calibrated

    def print_calib_data(self):
        with self.lock:
            print("Calibration Data:")
            for i in range(MAX_SIZE):
                for j in range(MAX_SIZE):
                    print(f"{self.data_calib[i][j]}  ", end="")
                print()


# ── Serial Reader / 串口读取 ───────────────────────────────────────
class SerialReader:
    def __init__(self, datastore):
        self.datastore = datastore
        self.ser = None
        self.running = False
        self.thread = None

    def connect(self, port=None):
        ports = list(serial.tools.list_ports.comports())
        print("Available Serial Ports:")
        for p in ports:
            print(f"  {p.device}")
        if not ports:
            print("No serial ports available. Running without serial. / 无可用串口，以无串口模式运行")
            return False
        if port is None:
            port = ports[0].device
        print(f"Using port: {port}")
        print("This can be changed in the main() function. / 可在 main() 函数中修改")
        try:
            self.ser = serial.Serial(port, BAUD_RATE, timeout=1)
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            print(f"Failed to open serial port: {e}")
            return False

    def _read_loop(self):
        while self.running:
            try:
                if self.ser and self.ser.is_open:
                    line = self.ser.readline()
                    if line:
                        self._parse_line(line.decode("utf-8", errors="ignore"))
            except Exception as e:
                print(f"Serial read error: {e}")
                time.sleep(0.1)

    def _parse_line(self, line):
        line = line.strip()
        print(f"Receiving: {line}")
        parts = line.split(" ")
        if len(parts) < 2:
            self.datastore.reset_idx()
            return
        try:
            vals = [float(x) for x in parts]
            if len(vals) != MAX_SIZE:
                return
            self.datastore.add_row([int(v) for v in vals])
        except ValueError:
            pass

    def write(self, cmd):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"{cmd}\n".encode())
            except Exception as e:
                print(f"Serial write error: {e}")

    def close(self):
        self.running = False
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass


# ── Renderer / 渲染器 ─────────────────────────────────────────────
def draw_grid(screen, data, data_calib, is_calibrated, offset_y,
              gain_normal, gain_calib):
    # Draw background panel / 绘制背景底板
    panel_rect = (OFFSET_X + PIXEL_SIZE - 10, offset_y + PIXEL_SIZE - 10, GRID_SIZE + 20, GRID_SIZE + 20)
    pygame.draw.rect(screen, COLOR_PANEL, panel_rect, border_radius=8)
    pygame.draw.rect(screen, COLOR_PANEL_BORDER, panel_rect, 1, border_radius=8)

    border_surf = pygame.Surface((PIXEL_SIZE, PIXEL_SIZE), pygame.SRCALPHA)
    pygame.draw.rect(border_surf, (220, 235, 255, 35), border_surf.get_rect(), 1)

    for i in range(MAX_SIZE):
        for j in range(MAX_SIZE):
            y = (MAX_SIZE - i) * PIXEL_SIZE
            x = (MAX_SIZE - j) * PIXEL_SIZE

            if is_calibrated:
                value = (data[i][j] - data_calib[i][j]) / MAX_VALUE
                intensity = int(gain_calib * value)
                if value < 0.0:
                    color = (clamp(-intensity), 0, 0)
                else:
                    color = (0, clamp(intensity), 0)
            else:
                value = data[i][j] / MAX_VALUE
                intensity = int(gain_normal * abs(value - 0.50))
                if value < 0.50:
                    color = (clamp(intensity), 0, 0)
                else:
                    color = (0, clamp(intensity), 0)

            rect = (x + OFFSET_X, y + offset_y, PIXEL_SIZE, PIXEL_SIZE)
            pygame.draw.rect(screen, color, rect)
            screen.blit(border_surf, (x + OFFSET_X, y + offset_y))


def draw_label(screen, font, text, offset_y):
    label = font.render(text, True, COLOR_TEXT)
    # Center the label / 居中标签
    label_rect = label.get_rect(center=(GRID_CENTER_X, offset_y + 5))
    screen.blit(label, label_rect)


def draw_button(screen, rect, text, font, hover=False):
    shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(shadow, BUTTON_SHADOW, shadow.get_rect(), border_radius=BUTTON_RADIUS)
    screen.blit(shadow, (rect.x, rect.y + 2))

    button = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    fill = BUTTON_FILL_HOVER if hover else BUTTON_FILL
    pygame.draw.rect(button, fill, button.get_rect(), border_radius=BUTTON_RADIUS)
    pygame.draw.rect(button, BUTTON_BORDER, button.get_rect(), 1, border_radius=BUTTON_RADIUS)
    pygame.draw.line(button, (230, 242, 255, 80), (10, 6), (rect.width - 10, 6))
    screen.blit(button, rect.topleft)

    text_surf = font.render(text, True, COLOR_TEXT)
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)


def draw_toast(screen, font, message, elapsed_ms):
    if elapsed_ms < 0:
        return

    if elapsed_ms < TOAST_FADE_MS:
        t = elapsed_ms / TOAST_FADE_MS
        alpha = t * t
    elif elapsed_ms > TOAST_DURATION_MS - TOAST_FADE_MS:
        t = (elapsed_ms - (TOAST_DURATION_MS - TOAST_FADE_MS)) / TOAST_FADE_MS
        alpha = pow(2, -6 * t)
    else:
        alpha = 1.0

    alpha = max(0.0, min(1.0, alpha))
    if alpha <= 0.0:
        return

    text_surf = font.render(message, True, COLOR_TEXT)
    text_surf.set_alpha(int(255 * alpha))
    toast_rect = text_surf.get_rect()
    toast_rect.inflate_ip(32, 14)
    toast_rect.midtop = (GRID_CENTER_X, TOAST_TOP)

    toast = pygame.Surface((toast_rect.width, toast_rect.height), pygame.SRCALPHA)
    back_alpha = int(TOAST_BACK_ALPHA * alpha)
    fill_alpha = int(TOAST_SOLID_ALPHA * alpha)
    border_alpha = int(TOAST_BORDER_ALPHA * alpha)
    highlight_alpha = int(150 * alpha)
    pygame.draw.rect(toast, (26, 32, 44, back_alpha), toast.get_rect(), border_radius=12)
    pygame.draw.rect(toast, (210, 225, 245, fill_alpha), toast.get_rect(), border_radius=12)
    pygame.draw.rect(toast, (230, 240, 255, border_alpha), toast.get_rect(), 1, border_radius=12)
    pygame.draw.line(
        toast,
        (230, 242, 255, highlight_alpha),
        (12, 6),
        (toast_rect.width - 12, 6)
    )
    screen.blit(toast, toast_rect.topleft)

    text_rect = text_surf.get_rect(center=toast_rect.center)
    screen.blit(text_surf, text_rect)


# ── Main / 主程序 ─────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Magnetic Imager Tile v3")
    clock = pygame.time.Clock()
    background = create_cool_frosted_background((WINDOW_WIDTH, WINDOW_HEIGHT))

    # Load font / 加载固定黑体字体（simhei）
    font_path = pygame.font.match_font("simhei")
    if font_path:
        font = pygame.font.Font(font_path, 20)
        button_font = pygame.font.Font(font_path, 16)
        small_font = pygame.font.Font(font_path, 14)
    else:
        font = pygame.font.SysFont("simhei", 20)
        button_font = pygame.font.SysFont("simhei", 16)
        small_font = pygame.font.SysFont("simhei", 14)

    print(f"Using SimHei font: {font_path or 'system fallback'}")

    datastore = DataStore()
    serial_reader = SerialReader(datastore)
    serial_reader.connect()

    toast_message = ""
    toast_start_ms = 0
    screenshot_number = 0
    running = True

    buttons = []
    button_x = (SIDEBAR_WIDTH - BUTTON_WIDTH) // 2
    button_y = SIDEBAR_PADDING_TOP + 26
    for label, action in BUTTON_DEFS:
        rect = pygame.Rect(button_x, button_y, BUTTON_WIDTH, BUTTON_HEIGHT)
        buttons.append({"label": label, "action": action, "rect": rect})
        button_y += BUTTON_HEIGHT + BUTTON_GAP

    def handle_action(action):
        nonlocal toast_message, toast_start_ms, screenshot_number

        def show_toast(message):
            nonlocal toast_message, toast_start_ms
            toast_message = message
            toast_start_ms = pygame.time.get_ticks()

        if action == "SPACE":
            filename = f"screenshot-{screenshot_number}.png"
            pygame.image.save(screen, filename)
            print(f"Screenshot saved: {filename}")
            screenshot_number += 1
            return

        if action == "A":
            datastore.clear_data()
            return

        if action == "L":
            serial_reader.write("L")
            show_toast("Live Feed")
            return

        if action == "H":
            serial_reader.write("H")
            return

        if action == "S":
            serial_reader.write("S")
            show_toast("已停止")
            return

        if action in ("1", "2", "3", "4"):
            serial_reader.write(action)
            show_toast({
                "1": "2000Hz capture",
                "2": "1000Hz capture",
                "3": "500Hz capture",
                "4": "250Hz capture",
            }[action])
            return

        if action == "C":
            datastore.start_calibration()
            show_toast("Calibrating")
            return

        if action == "D":
            datastore.print_calib_data()
            return

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                k = event.unicode.lower() if event.unicode else ""
                action = None
                if event.key == pygame.K_SPACE:
                    action = "SPACE"
                elif k in {"a", "l", "h", "s", "1", "2", "3", "4", "c", "d"}:
                    action = k.upper()

                if action:
                    handle_action(action)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for button in buttons:
                        if button["rect"].collidepoint(event.pos):
                            handle_action(button["action"])
                            break

        # ── Render / 渲染 ──────────────────────────────────────
        screen.blit(background, (0, 0))

        # Sidebar / 左侧控制面板
        sidebar_rect = pygame.Rect(0, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(screen, COLOR_SIDEBAR, sidebar_rect)
        pygame.draw.line(screen, COLOR_SIDEBAR_EDGE, (SIDEBAR_WIDTH, 0), (SIDEBAR_WIDTH, WINDOW_HEIGHT), 2)

        title_surf = small_font.render("控制", True, COLOR_TEXT_MUTED)
        title_rect = title_surf.get_rect(midleft=(18, SIDEBAR_PADDING_TOP))
        screen.blit(title_surf, title_rect)

        data, data_calib, is_calibrated = datastore.get_snapshot()

        # Normal gain grid (top) / 正常增益网格（上方）
        draw_label(screen, font, "Normal Gain / 正常增益", OFFSET_Y_NORMAL)
        draw_grid(screen, data, data_calib, is_calibrated,
                  OFFSET_Y_NORMAL, gain_normal=255, gain_calib=255)

        # High gain grid (bottom) / 高增益网格（下方）
        draw_label(screen, font, "High Gain / 高增益", OFFSET_Y_HIGH)
        draw_grid(screen, data, data_calib, is_calibrated,
                  OFFSET_Y_HIGH, gain_normal=3000, gain_calib=3000)

        # Status text / 状态文字
        mouse_pos = pygame.mouse.get_pos()
        for button in buttons:
            hover = button["rect"].collidepoint(mouse_pos)
            draw_button(screen, button["rect"], button["label"], button_font, hover)

        if toast_message:
            elapsed_ms = pygame.time.get_ticks() - toast_start_ms
            if elapsed_ms >= TOAST_DURATION_MS:
                toast_message = ""
            else:
                draw_toast(screen, font, toast_message, elapsed_ms)

        pygame.display.flip()
        clock.tick(60)

    serial_reader.close()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
