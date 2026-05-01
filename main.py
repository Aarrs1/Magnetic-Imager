# -*- coding: utf-8 -*-
"""
Magnetic Imager Tile v3 Python Visualization / 磁成像传感器阵列 v3 Python 可视化

基于 Pygame 的 8×8 磁传感器阵列实时可视化程序。
从 Processing 草图 (projecttest.pde) 迁移而来，支持串口数据流和多种捕获模式。

左侧绘图区：两个 8×8 网格（正常增益 + 高增益），各带渐变色条和悬停提示。
右侧控制栏：分三组（运行模式、高速捕获、工具），外加最大增益输入和自动增益。
底部状态栏：串口信息、Live/Idle 指示灯、实时 FPS。

键盘快捷键：
  Space — 切换实时/停止    F11 — 全屏切换
"""

import os
import sys
import time
import ctypes
from datetime import datetime
import pygame
import pygame.freetype

# Windows 高 DPI 适配（让窗口在 150%/200% 缩放下不模糊）
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from config import (
    FONT_NAME, MAX_SIZE, PIXEL_SIZE,
    DESIGN_WIDTH, DESIGN_HEIGHT,
    SIDEBAR_WIDTH,
    COLOR_SIDEBAR, COLOR_SIDEBAR_EDGE,
    COLOR_TEXT, COLOR_TEXT_MUTED, COLOR_ACCENT_LIGHT,
    TOAST_DURATION_MS, TOAST_FADE_MS,
    FROST_SIDEBAR_ALPHA,
    GRID_SIZE, GRID_TOP, GRID_NORMAL_LEFT, GRID_HIGH_LEFT,
    SECTION_HEADER_HEIGHT, SIDEBAR_PADDING_X,
    COLOR_ACTIVE, COLOR_ACTIVE_DIM,
)
from background import create_background
from datastore import DataStore
from serial_reader import SerialReader
from animation import lerp_float
from renderer import draw_grid, draw_grid_label, draw_color_bar_v, draw_cell_tooltip
from ui_components import draw_button, draw_toast, draw_status_bar, draw_gain_input, draw_section_header
from app_state import AppState
from layout import build_buttons, build_gain_rect, build_auto_gain_rect
from actions import handle_action, handle_gain_keydown, handle_gain_click, handle_auto_gain, show_toast



def create_fonts(font_path):
    """创建四级字体层级：标题 / 按钮 / 小号 / 微小（均为粗体 + 抗锯齿）"""
    if font_path:
        font = pygame.freetype.Font(font_path, 32)
        button_font = pygame.freetype.Font(font_path, 28)
        small_font = pygame.freetype.Font(font_path, 24)
        tiny_font = pygame.freetype.Font(font_path, 22)
    else:
        font = pygame.freetype.SysFont(FONT_NAME, 32)
        button_font = pygame.freetype.SysFont(FONT_NAME, 28)
        small_font = pygame.freetype.SysFont(FONT_NAME, 24)
        tiny_font = pygame.freetype.SysFont(FONT_NAME, 22)

    for f in (font, button_font, small_font, tiny_font):
        f.antialiased = True
        f.kerning = True
    font.strong = True
    button_font.strong = True
    small_font.strong = True
    tiny_font.strong = True
    return font, button_font, small_font, tiny_font


def main():
    pygame.init()
    pygame.freetype.init()

    screen = pygame.display.set_mode((DESIGN_WIDTH, DESIGN_HEIGHT),
                                      pygame.RESIZABLE | pygame.SCALED)
    pygame.display.set_caption("Magnetic Imager Tile v3")
    clock = pygame.time.Clock()

    is_fullscreen = False
    background = create_background((DESIGN_WIDTH, DESIGN_HEIGHT))

    # ── 初始化：字体、数据存储、串口、应用状态 ──
    font_path = pygame.freetype.match_font(FONT_NAME)
    font, button_font, small_font, tiny_font = create_fonts(font_path)
    print(f"Using font '{FONT_NAME}': {font_path or 'system fallback'} (freetype, 2× supersampling)")

    datastore = DataStore()
    datastore.fill_gradient()  # 初始数据：对角渐变（串口数据到达后自动覆盖）
    serial_reader = SerialReader(datastore)
    has_serial = serial_reader.connect()

    state = AppState()
    # 串口状态消息 → Toast
    serial_reader.status_callback = lambda msg, st: show_toast(state, msg, st)
    running = True
    fps_smooth = 60.0
    start_time = time.time()
    cell_states_normal = {}
    cell_states_high = {}
    button_flash = {}
    gain_regions = {}
    calib_dot_phase = 0

    buttons = build_buttons()
    gain_rect = build_gain_rect(buttons)
    auto_gain_rect = build_auto_gain_rect(gain_rect)

    last_time = time.time()
    while running:
        now = time.time()
        dt = now - last_time
        last_time = now
        total_time = now - start_time

        # ── 事件处理（键盘 + 鼠标） ──
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    # 全屏/窗口切换（保留 SCALED 以维持虚拟画布）
                    is_fullscreen = not is_fullscreen
                    flags = pygame.FULLSCREEN | pygame.SCALED if is_fullscreen else pygame.RESIZABLE | pygame.SCALED
                    screen = pygame.display.set_mode((DESIGN_WIDTH, DESIGN_HEIGHT), flags)
                elif state.gain_editing:
                    handle_gain_keydown(event, state)
                elif event.key == pygame.K_SPACE:
                    # Space 键：实时↔停止切换
                    if state.is_live:
                        handle_action(state, "S", datastore, serial_reader, screen)
                        button_flash["S"] = 0.15
                    else:
                        handle_action(state, "L", datastore, serial_reader, screen)
                        button_flash["L"] = 0.15

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    vx, vy = event.pos

                    # 优先级：增益控件 → 编辑提交 → 自动增益 → 按钮
                    if not handle_gain_click(vx, vy, state, gain_rect, gain_regions):
                        if state.gain_editing:
                            # 点击增益输入框外：提交编辑值
                            try:
                                new_val = float(state.gain_edit_text)
                                if new_val >= 1:
                                    state.max_gain = new_val
                            except ValueError:
                                pass
                            state.gain_editing = False
                        elif auto_gain_rect.collidepoint(vx, vy):
                            handle_auto_gain(state, datastore)
                            button_flash["AG"] = 0.15
                            show_toast(state, f"Auto gain: {state.max_gain:.0f}", "success")
                        else:
                            for button in buttons:
                                if button["rect"].collidepoint(vx, vy):
                                    action = button["action"]
                                    # 校准中悬停→取消校准；否则正常触发
                                    if action == "C" and (datastore.calibration_enabled or state.calib_delay_until > 0):
                                        datastore.cancel_calibration()
                                        state.calib_delay_until = 0
                                        button_flash["C"] = 0.15
                                        show_toast(state, "Calibration cancelled", "warning")
                                    else:
                                        handle_action(state, action, datastore, serial_reader, screen)
                                        button_flash[action] = 0.15
                                    break

        # ── 更新动画（单元格颜色插值 + 按钮闪烁衰减 + 校准延迟启动） ──
        for s in cell_states_normal.values():
            s.update(dt)
        for s in cell_states_high.values():
            s.update(dt)
        for action in list(button_flash):
            button_flash[action] -= dt
            if button_flash[action] <= 0:
                del button_flash[action]
        if state.calib_delay_until > 0 and time.time() >= state.calib_delay_until:
            state.calib_delay_until = 0
            datastore.start_calibration()

        current_fps = clock.get_fps()
        if current_fps > 0:
            fps_smooth = fps_smooth * 0.9 + current_fps * 0.1

        # ── 渲染管线 ──
        screen.blit(background, (0, 0))

        # 右侧控制栏背景（毛玻璃 + 左边缘发光分割线）
        sidebar_rect = pygame.Rect(DESIGN_WIDTH - SIDEBAR_WIDTH, 0, SIDEBAR_WIDTH, DESIGN_HEIGHT)
        sidebar_surf = pygame.Surface((SIDEBAR_WIDTH, DESIGN_HEIGHT), pygame.SRCALPHA)
        sidebar_surf.fill((*COLOR_SIDEBAR, FROST_SIDEBAR_ALPHA))
        screen.blit(sidebar_surf, sidebar_rect.topleft)
        pygame.draw.line(screen, COLOR_SIDEBAR_EDGE,
                         (DESIGN_WIDTH - SIDEBAR_WIDTH, 0),
                         (DESIGN_WIDTH - SIDEBAR_WIDTH, DESIGN_HEIGHT), 2)

        # 控制面板标题栏（"控制面板" + 装饰分割线）
        header_rect = pygame.Rect(DESIGN_WIDTH - SIDEBAR_WIDTH, 0,
                                   SIDEBAR_WIDTH, 52)
        header = pygame.Surface((SIDEBAR_WIDTH, 52), pygame.SRCALPHA)
        header.fill((*COLOR_SIDEBAR, 230))
        pygame.draw.line(header, (*COLOR_ACCENT_LIGHT, 40),
                         (20, 50), (SIDEBAR_WIDTH - 20, 50), 1)
        screen.blit(header, header_rect.topleft)
        title_surf, _ = small_font.render("控制面板", COLOR_TEXT)
        screen.blit(title_surf, title_surf.get_rect(
            midleft=(DESIGN_WIDTH - SIDEBAR_WIDTH + 24, 26)))

        # ── 初始横幅（未启动数据记录时显示） ──
        if state.banner_visible:
            banner_text = "未启动数据记录 · 正在展示示例数据"
            banner_surf, _ = small_font.render(banner_text, COLOR_TEXT)
            bw, bh = banner_surf.get_size()
            pad_x, pad_y = 28, 14
            banner_rect = pygame.Rect(0, 0, bw + pad_x * 2, bh + pad_y * 2)
            banner_rect.centerx = (DESIGN_WIDTH - SIDEBAR_WIDTH) // 2
            banner_rect.top = 40
            banner_bg = pygame.Surface((banner_rect.width, banner_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(banner_bg, (4, 10, 18, 220), banner_bg.get_rect(), border_radius=10)
            pygame.draw.rect(banner_bg, (*COLOR_ACCENT_LIGHT, 80), banner_bg.get_rect(), 1, border_radius=10)
            screen.blit(banner_bg, banner_rect.topleft)
            screen.blit(banner_surf, banner_surf.get_rect(center=banner_rect.center))

        # 网格标题 + 传感器热力图
        data, data_calib, is_calibrated = datastore.get_snapshot()

        normal_center = GRID_NORMAL_LEFT + GRID_SIZE // 2
        high_center = GRID_HIGH_LEFT + GRID_SIZE // 2
        draw_grid_label(screen, font, "Normal Gain  ·  正常增益", normal_center, GRID_TOP,
                        accent=(80, 160, 220))
        draw_grid_label(screen, font, "High Gain  ·  高增益", high_center, GRID_TOP,
                        accent=(100, 200, 140))

        vx, vy = pygame.mouse.get_pos()

        # 正常/高增益的颜色强度系数（高增益 3× 更敏感）
        NORM_GAIN, HIGH_GAIN = 500, 1500
        hover_normal = draw_grid(screen, data, data_calib, is_calibrated,
                                 GRID_NORMAL_LEFT, GRID_TOP, NORM_GAIN, NORM_GAIN,
                                 state.max_gain, cell_states_normal, (vx, vy), tiny_font)
        hover_high = draw_grid(screen, data, data_calib, is_calibrated,
                               GRID_HIGH_LEFT, GRID_TOP, HIGH_GAIN, HIGH_GAIN,
                               state.max_gain, cell_states_high, (vx, vy), tiny_font)

        # ── 垂直渐变色条（网格两侧） ──
        bar_width = 20
        panel_pad = 16
        bar_gap = 8
        norm_bar_left = GRID_NORMAL_LEFT - panel_pad - bar_gap - bar_width
        high_bar_left = GRID_HIGH_LEFT + GRID_SIZE + panel_pad + bar_gap

        # 色条光标值＝当前悬停单元格的校准后数值（无悬停则为 0）
        def _hover_value(hover):
            if not hover:
                return 0.0
            r, c = hover
            return data[r][c] - data_calib[r][c] if is_calibrated else data[r][c]

        # 光标平滑插值（避免跳动）
        state.cursor_anim_norm = lerp_float(state.cursor_anim_norm, _hover_value(hover_normal), dt)
        state.cursor_anim_high = lerp_float(state.cursor_anim_high, _hover_value(hover_high), dt)

        draw_color_bar_v(screen, tiny_font, norm_bar_left, GRID_TOP, GRID_SIZE,
                         gain=NORM_GAIN, max_value=state.max_gain, labels_left=True,
                         cursor_value=state.cursor_anim_norm)
        draw_color_bar_v(screen, tiny_font, high_bar_left, GRID_TOP, GRID_SIZE,
                         gain=HIGH_GAIN, max_value=state.max_gain,
                         cursor_value=state.cursor_anim_high)

        # ── 右侧控制栏按钮 ──
        calib_dot_phase = int(total_time * 2) % 3  # 校准中动画点（0/1/2）
        calib_progress = datastore.get_calib_progress()
        shown_sections = set()  # 追踪已绘制的分组标题（避免重复）

        for button in buttons:
            sec = button.get("section")
            if sec and sec not in shown_sections:
                shown_sections.add(sec)
                header_y = button["rect"].top - SECTION_HEADER_HEIGHT
                draw_section_header(screen, tiny_font, sec,
                                    DESIGN_WIDTH - SIDEBAR_WIDTH + SIDEBAR_PADDING_X + 4, header_y)

            hover = button["rect"].collidepoint(vx, vy)
            flash = button_flash.get(button["action"], 0.0)
            action = button["action"]
            icon = button.get("icon")
            label = button["label"]
            progress = 0.0
            active = False

            if action == "L" and state.is_live:
                active = True
            elif action == "S" and not state.is_live and state.capture_active is None:
                active = True
            elif action in ("1", "2", "3", "4") and state.capture_active == action:
                active = True
            elif action == "C" and (datastore.calibration_enabled or state.calib_delay_until > 0):
                active = True
                if hover:
                    label = "取消校准"
                else:
                    label = "校准中" + "." * (calib_dot_phase + 1)
                    progress = calib_progress if datastore.calibration_enabled else 0.0

            draw_button(screen, button["rect"], label, button_font,
                        hover, flash, active, icon, progress)

        gain_regions = draw_gain_input(screen, button_font, gain_rect,
                                       state.max_gain, state.gain_editing,
                                       state.gain_edit_text, state.gain_edit_cursor, (vx, vy),
                                       label_font=tiny_font,
                                       dropdown_open=state.gain_dropdown_open)

        auto_hover = auto_gain_rect.collidepoint(vx, vy)
        auto_flash = button_flash.get("AG", 0.0)
        draw_button(screen, auto_gain_rect, "自动增益", button_font,
                    auto_hover, auto_flash)

        # ── 底部状态栏 ──
        com_info = f"{serial_reader.ser.port} · {serial_reader.ser.baudrate}" if serial_reader.ser else "No COM"
        draw_status_bar(screen, tiny_font, com_info, state.is_live, fps_smooth, total_time)


        # ── Toast 通知（滑入 + 淡出） ──
        if state.toast_message:
            elapsed_ms = pygame.time.get_ticks() - state.toast_start_ms
            if elapsed_ms >= TOAST_DURATION_MS + TOAST_FADE_MS:
                state.toast_message = ""
            else:
                draw_toast(screen, small_font, state.toast_message, elapsed_ms, state.toast_status)

        # ── 单元格悬停气泡提示（最上层） ──
        def _draw_tooltip(hover, grid_left):
            if not hover:
                return
            r, c = hover
            cell_rect = pygame.Rect(
                grid_left + c * PIXEL_SIZE,
                GRID_TOP + r * PIXEL_SIZE,
                PIXEL_SIZE, PIXEL_SIZE,
            )
            value = data[r][c] - data_calib[r][c] if is_calibrated else data[r][c]
            cal = data_calib[r][c] if is_calibrated else 0.0
            draw_cell_tooltip(screen, tiny_font, r, c, value, cell_rect, cal)

        _draw_tooltip(hover_normal, GRID_NORMAL_LEFT)
        _draw_tooltip(hover_high, GRID_HIGH_LEFT)

        pygame.display.flip()
        clock.tick(60)

    serial_reader.close()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
