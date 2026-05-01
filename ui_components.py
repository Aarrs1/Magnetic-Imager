# -*- coding: utf-8 -*-
"""
UI 组件：毛玻璃按钮、Toast 通知、状态栏、Max Gain 输入控件、分组标题。

所有组件均为可复用绘制函数，使用缓存 Surface 优化性能。
按钮支持：hover 高亮、press_flash 闪烁、active 激活态、icon 图标、progress 进度条。
Toast 支持：滑入 + 指数淡出动画，多状态颜色（info/success/warning/stop）。
"""

import math
import pygame
import pygame.freetype

from config import (
    BUTTON_RADIUS, COLOR_ACCENT_LIGHT, COLOR_TEXT, COLOR_TEXT_MUTED,
    TOAST_FADE_MS, TOAST_DURATION_MS, WINDOW_WIDTH,
    STATUS_BAR_TOP, STATUS_BAR_HEIGHT, SIDEBAR_WIDTH,
    FROST_STATUSBAR_ALPHA, COLOR_PANEL_BORDER,
    GAIN_ARROW_WIDTH, GAIN_ARROW_HEIGHT, GAIN_VALUE_WIDTH,
    GAIN_DROPDOWN_WIDTH, GAIN_PRESETS, GAIN_PRESET_ITEM_HEIGHT,
    GAIN_DROPDOWN_PANEL_WIDTH, GAIN_PRESET_RECOMMENDED,
)


def draw_button(screen, rect, text, font, hover=False, press_flash=0.0, active=False,
                 icon=None, progress=0.0):
    """毛玻璃风格按钮。

    active=True 时显示柔绿色激活态（含顶部高光线）。
    icon 支持 "play"（三角箭头）/ "stop"（方框），绘制在文本左侧。
    progress 0~1 时在按钮底部显示细进度条（用于校准中状态）。
    press_flash 0~0.15 时触发短暂的点击闪烁效果。
    """
    button = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

    if active:
        fill_alpha = int(40 + press_flash * 30)
        pygame.draw.rect(button, (60, 160, 90, min(255, fill_alpha)),
                         button.get_rect(), border_radius=BUTTON_RADIUS)
        border_alpha = min(255, 160 + int(press_flash * 40))
        pygame.draw.rect(button, (80, 180, 110, border_alpha), button.get_rect(), 2,
                         border_radius=BUTTON_RADIUS)
        pygame.draw.line(button, (120, 200, 140, 80),
                         (20, 10), (rect.width - 20, 10), 2)
    else:
        base_alpha = int(18 + press_flash * 40)
        hover_alpha = int(50 + press_flash * 30)
        fill_alpha = hover_alpha if hover else base_alpha
        fill_alpha = min(255, max(0, fill_alpha))
        pygame.draw.rect(button, (180, 210, 240, fill_alpha), button.get_rect(),
                         border_radius=BUTTON_RADIUS)
        border_alpha = 120 if hover else 50
        border_alpha = min(255, border_alpha + int(press_flash * 60))
        pygame.draw.rect(button, (*COLOR_ACCENT_LIGHT, border_alpha), button.get_rect(), 2,
                         border_radius=BUTTON_RADIUS)
        highlight_alpha = 90 if hover else 40
        pygame.draw.line(button, (220, 235, 250, highlight_alpha),
                         (20, 10), (rect.width - 20, 10), 2)

    shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    shadow_alpha = 80 if hover else 50
    pygame.draw.rect(shadow, (0, 0, 0, shadow_alpha), shadow.get_rect(),
                     border_radius=BUTTON_RADIUS)
    screen.blit(shadow, (rect.x, rect.y + 4))

    screen.blit(button, rect.topleft)

    # 图标
    icon_offset = 0
    if icon in ("play", "stop"):
        cx = rect.x + 28
        cy = rect.centery
        if icon == "play":
            pts = [(cx - 5, cy - 7), (cx - 5, cy + 7), (cx + 6, cy)]
            pygame.draw.polygon(screen, COLOR_TEXT, pts)
        else:
            sq = pygame.Rect(cx - 6, cy - 6, 12, 12)
            pygame.draw.rect(screen, COLOR_TEXT, sq)
        icon_offset = 16

    text_surf, _ = font.render(text, COLOR_TEXT)
    text_rect = text_surf.get_rect(center=rect.center)
    text_rect.x += icon_offset
    screen.blit(text_surf, text_rect)

    # 进度条
    if progress > 0:
        bar_h = 3
        bar_y = rect.bottom - bar_h - 2
        bar_max_w = rect.width - 24
        bar_w = int(bar_max_w * progress)
        bar_bg = pygame.Rect(rect.x + 12, bar_y, bar_max_w, bar_h)
        bar_fill = pygame.Rect(rect.x + 12, bar_y, bar_w, bar_h)
        pygame.draw.rect(screen, (20, 40, 30, 120), bar_bg, border_radius=1)
        pygame.draw.rect(screen, (60, 160, 90), bar_fill, border_radius=1)


_toast_bg_cache = None  # (w, h) → frosted bg surface


def _get_toast_bg(w, h):
    global _toast_bg_cache
    key = (w, h)
    if _toast_bg_cache and _toast_bg_cache[0] == key:
        return _toast_bg_cache[1]
    bg = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(bg, (10, 18, 32, 170), bg.get_rect(), border_radius=24)
    pygame.draw.rect(bg, (200, 218, 240, 100), bg.get_rect(), 1, border_radius=24)
    pygame.draw.line(bg, (220, 235, 250, 80), (24, 10), (w - 24, 10), 1)
    _toast_bg_cache = (key, bg)
    return bg


_DOT_COLORS = {
    "info":    (100, 210, 120),   # green
    "success": (100, 210, 120),   # green
    "warning": (240, 180, 60),    # amber
    "stop":    (230, 80, 80),     # red
}


def draw_toast(screen, font, message, elapsed_ms, status="info"):
    """Toast — 滑入 + 淡出，绘图区居中，毛玻璃风格"""
    if elapsed_ms < 0 or not message:
        return

    draw_area_w = WINDOW_WIDTH - SIDEBAR_WIDTH

    if elapsed_ms < TOAST_FADE_MS:
        t = elapsed_ms / TOAST_FADE_MS
        alpha = t * t
        slide_offset = -60 * (1 - t)
    elif elapsed_ms > TOAST_DURATION_MS:
        t = (elapsed_ms - TOAST_DURATION_MS) / TOAST_FADE_MS
        alpha = pow(2, -6 * t)
        slide_offset = 0
    else:
        alpha = 1.0
        slide_offset = 0

    alpha = max(0.0, min(1.0, alpha))
    if alpha <= 0.01:
        return

    text_surf, _ = font.render(message, COLOR_TEXT)
    text_w, text_h = text_surf.get_size()

    dot_r = 5
    pad_x, pad_y = 40, 22
    content_w = dot_r * 2 + 10 + text_w
    tw = content_w + pad_x * 2
    th = max(text_h, dot_r * 2) + pad_y * 2

    toast_rect = pygame.Rect(0, 0, tw, th)
    toast_rect.midtop = (draw_area_w // 2, 16 + int(slide_offset))
    tx, ty = toast_rect.topleft

    # 柔和阴影
    shadow = pygame.Surface((tw, th), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, int(100 * alpha)), shadow.get_rect(), border_radius=24)
    screen.blit(shadow, (tx, ty + 6))

    # 毛玻璃主体（缓存的背景模板 + 逐帧 alpha 叠加）
    bg_tpl = _get_toast_bg(tw, th)
    bg = bg_tpl.copy()
    bg.set_alpha(int(255 * alpha))
    screen.blit(bg, (tx, ty))

    # 状态圆点
    base_color = _DOT_COLORS.get(status, _DOT_COLORS["info"])
    dot_color = (*base_color, int(255 * alpha))
    dot_surf = pygame.Surface((dot_r * 2, dot_r * 2), pygame.SRCALPHA)
    pygame.draw.circle(dot_surf, dot_color, (dot_r, dot_r), dot_r)
    screen.blit(dot_surf, dot_surf.get_rect(
        midleft=(tx + pad_x, ty + th // 2)))

    # 文本
    text_surf.set_alpha(int(255 * alpha))
    screen.blit(text_surf, text_surf.get_rect(
        midleft=(tx + pad_x + dot_r * 2 + 10, ty + th // 2)))


def draw_status_bar(screen, font_tiny, com_info, is_live, fps, time_sec):
    """绘制底部状态栏：COM 端口信息（左）、Live/Idle 指示灯（中）、FPS（右）。

    Live 状态下指示灯带脉冲呼吸动画（正弦波调制）。
    """
    bar_rect = pygame.Rect(0, STATUS_BAR_TOP, WINDOW_WIDTH - SIDEBAR_WIDTH, STATUS_BAR_HEIGHT)
    bar_surf = pygame.Surface((bar_rect.width, bar_rect.height), pygame.SRCALPHA)
    bar_surf.fill((8, 16, 26, FROST_STATUSBAR_ALPHA))
    pygame.draw.line(bar_surf, (*COLOR_PANEL_BORDER, 30), (0, 0), (bar_rect.width, 0))
    screen.blit(bar_surf, bar_rect.topleft)

    text_surf, _ = font_tiny.render(com_info, COLOR_TEXT_MUTED)
    com_rect = text_surf.get_rect(midleft=(28, STATUS_BAR_TOP + STATUS_BAR_HEIGHT // 2))
    screen.blit(text_surf, com_rect)

    dot_color = (100, 200, 100) if is_live else (100, 100, 110)
    if is_live:
        pulse = 0.6 + 0.4 * math.sin(time_sec * 3.14)
        dot_color = (int(100 * pulse), int(200 * pulse), int(100 * pulse))
    dot_x = bar_rect.width // 2 - 48
    dot_y = STATUS_BAR_TOP + STATUS_BAR_HEIGHT // 2
    pygame.draw.circle(screen, dot_color, (dot_x, dot_y), 8)
    text_surf, _ = font_tiny.render("Live" if is_live else "Idle", COLOR_TEXT_MUTED)
    status_rect = text_surf.get_rect(midleft=(dot_x + 20, dot_y))
    screen.blit(text_surf, status_rect)

    text_surf, _ = font_tiny.render(f"FPS: {fps:.0f}", COLOR_TEXT_MUTED)
    fps_rect = text_surf.get_rect(
        midright=(bar_rect.width - 28, STATUS_BAR_TOP + STATUS_BAR_HEIGHT // 2)
    )
    screen.blit(text_surf, fps_rect)


_dropdown_panel_cache = None  # frosted dropdown panel surface


def _get_dropdown_panel():
    global _dropdown_panel_cache
    if _dropdown_panel_cache is not None:
        return _dropdown_panel_cache
    n = len(GAIN_PRESETS)
    pw = GAIN_DROPDOWN_PANEL_WIDTH
    ph = n * GAIN_PRESET_ITEM_HEIGHT
    panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
    pygame.draw.rect(panel, (16, 26, 44, 235), panel.get_rect(), border_radius=12)
    pygame.draw.rect(panel, (*COLOR_ACCENT_LIGHT, 50), panel.get_rect(), 1, border_radius=12)
    for i, val in enumerate(GAIN_PRESETS):
        iy = i * GAIN_PRESET_ITEM_HEIGHT
        if i < n - 1:
            pygame.draw.line(panel, (*COLOR_ACCENT_LIGHT, 25),
                             (10, iy + GAIN_PRESET_ITEM_HEIGHT),
                             (pw - 10, iy + GAIN_PRESET_ITEM_HEIGHT), 1)
    _dropdown_panel_cache = panel
    return panel


def _draw_dropdown_item(screen, font, val, item_rect, hover):
    is_rec = (val == GAIN_PRESET_RECOMMENDED)
    color = (*COLOR_ACCENT_LIGHT, 255) if hover else (*COLOR_TEXT_MUTED, 200)
    bg_alpha = 80 if hover else 0
    if bg_alpha:
        hover_bg = pygame.Surface((item_rect.width, item_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(hover_bg, (*COLOR_ACCENT_LIGHT, bg_alpha), hover_bg.get_rect(), border_radius=6)
        screen.blit(hover_bg, item_rect.topleft)
    text_surf, _ = font.render(str(val), color)
    star_w = 0
    if is_rec:
        star_raw, _ = font.render("★", (*COLOR_ACCENT_LIGHT, 200))
        star_w = int(star_raw.get_width() * 0.6)
        star_h = int(star_raw.get_height() * 0.6)
        star_surf = pygame.transform.smoothscale(star_raw, (star_w, star_h))
        star_x = item_rect.centerx - (text_surf.get_width() + star_w + 4) // 2
        screen.blit(star_surf, star_surf.get_rect(
            centery=item_rect.centery, x=star_x))
        star_w += 4
    else:
        star_w = 0
    tx = item_rect.centerx - (text_surf.get_width() + star_w) // 2 + star_w
    screen.blit(text_surf, text_surf.get_rect(centery=item_rect.centery, x=tx))


def draw_gain_input(screen, font, rect, value, editing, edit_text,
                    cursor_pos, mouse_pos, label_font=None, dropdown_open=False):
    """Max Gain 输入控件：下拉预设面板 + 数值编辑 + ±步进按钮。

    布局：左侧 ▼ 下拉箭头 | 中间数值显示 | 右侧 +/− 按钮。
    返回区域字典 {"up", "down", "value", "dropdown", "dropdown_items"} 供事件处理使用。
    editing=True 时数值区变为可编辑模式（光标闪烁 + 文本输入）。
    """
    mx, my = mouse_pos if mouse_pos else (-1, -1)
    lf = label_font or font

    pygame.draw.circle(screen, (*COLOR_ACCENT_LIGHT, 100), (rect.x + 4, rect.y - 14), 3)
    label_surf, _ = lf.render("最大增益", COLOR_TEXT_MUTED)
    screen.blit(label_surf, label_surf.get_rect(midleft=(rect.x + 14, rect.y - 14)))

    # 主体背景
    bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(bg, (18, 30, 48, 200), bg.get_rect(), border_radius=BUTTON_RADIUS)
    pygame.draw.rect(bg, (*COLOR_ACCENT_LIGHT, 50), bg.get_rect(), 1, border_radius=BUTTON_RADIUS)
    screen.blit(bg, rect.topleft)

    # ── 下拉箭头区域（最左侧） ──
    dd_rect = pygame.Rect(rect.x + 2, rect.y + 2, GAIN_DROPDOWN_WIDTH, rect.height - 4)
    dd_hover = dd_rect.collidepoint(mx, my)
    dd_arrow_color = (*COLOR_TEXT, 230) if dd_hover else (*COLOR_TEXT_MUTED, 160)
    # 三角箭头 ▼
    arrow_cx = dd_rect.centerx
    arrow_cy = dd_rect.centery
    arrow_sz = 5
    pts = [(arrow_cx - arrow_sz, arrow_cy - 2),
           (arrow_cx + arrow_sz, arrow_cy - 2),
           (arrow_cx, arrow_cy + 4)]
    pygame.draw.polygon(screen, dd_arrow_color, pts)

    # 下拉分隔线
    sep1_x = rect.x + GAIN_DROPDOWN_WIDTH + 2
    pygame.draw.line(screen, (*COLOR_ACCENT_LIGHT, 30),
                     (sep1_x, rect.y + 8), (sep1_x, rect.y + rect.height - 8), 1)

    # ── 数值显示 ──
    value_left = rect.x + GAIN_DROPDOWN_WIDTH + 8
    value_rect = pygame.Rect(value_left, rect.y + 4,
                             GAIN_VALUE_WIDTH - 8, rect.height - 8)

    # 分隔线（数值 丨 +/-）
    sep2_x = rect.x + GAIN_DROPDOWN_WIDTH + GAIN_VALUE_WIDTH
    pygame.draw.line(screen, (*COLOR_ACCENT_LIGHT, 40),
                     (sep2_x, rect.y + 8), (sep2_x, rect.y + rect.height - 8), 1)

    # ── ± 按钮 ──
    btn_w = GAIN_ARROW_WIDTH
    btn_h = GAIN_ARROW_HEIGHT - 2
    up_rect = pygame.Rect(sep2_x + 4, rect.y + 4, btn_w, btn_h)
    down_rect = pygame.Rect(sep2_x + 4, rect.y + GAIN_ARROW_HEIGHT + 2, btn_w, btn_h)

    up_hover = up_rect.collidepoint(mx, my)
    down_hover = down_rect.collidepoint(mx, my)

    def _draw_pm_btn(btn_rect, hover, text):
        c = (*COLOR_ACCENT_LIGHT, 220) if hover else (*COLOR_TEXT_MUTED, 150)
        t, _ = font.render(text, c)
        screen.blit(t, t.get_rect(center=btn_rect.center))

    _draw_pm_btn(up_rect, up_hover, "+")
    _draw_pm_btn(down_rect, down_hover, "-")

    # 数值文本
    display = edit_text if editing else f"{value:.1f}".rstrip('0').rstrip('.')
    text_surf, _ = font.render(display, COLOR_TEXT)
    text_rect2 = text_surf.get_rect(center=value_rect.center)

    if text_surf.get_width() > value_rect.width - 8:
        clip = pygame.Surface((value_rect.width - 8, text_surf.get_height()),
                              pygame.SRCALPHA)
        clip.blit(text_surf, (0, 0))
        screen.blit(clip, clip.get_rect(center=value_rect.center))
    else:
        screen.blit(text_surf, text_rect2)

    if editing and int(pygame.time.get_ticks() / 500) % 2 == 0:
        prefix = edit_text[:cursor_pos]
        prefix_surf, _ = font.render(prefix, COLOR_TEXT)
        cursor_x = text_rect2.left + prefix_surf.get_width()
        pygame.draw.line(screen, COLOR_TEXT,
                         (cursor_x + 1, text_rect2.top),
                         (cursor_x + 1, text_rect2.top + text_surf.get_height()), 2)

    # ── 下拉面板 ──
    dropdown_items = []
    if dropdown_open:
        panel = _get_dropdown_panel()
        pw, ph = panel.get_size()
        panel_x = rect.x + 2
        panel_y = rect.y - ph - 4
        screen.blit(panel, (panel_x, panel_y))
        for i, val in enumerate(GAIN_PRESETS):
            item_rect = pygame.Rect(panel_x, panel_y + i * GAIN_PRESET_ITEM_HEIGHT,
                                    pw, GAIN_PRESET_ITEM_HEIGHT)
            item_hover = item_rect.collidepoint(mx, my)
            _draw_dropdown_item(screen, lf, val, item_rect, item_hover)
            dropdown_items.append((item_rect, val))

    return {
        "up": up_rect, "down": down_rect, "value": value_rect,
        "dropdown": dd_rect, "dropdown_items": dropdown_items,
    }


def draw_section_header(screen, font, text, x, y):
    """绘制右侧栏分组标题（圆点 + 文本）"""
    dot_x = x
    pygame.draw.circle(screen, (*COLOR_ACCENT_LIGHT, 100), (dot_x, y), 3)
    text_surf, _ = font.render(text, COLOR_TEXT_MUTED)
    text_rect = text_surf.get_rect(midleft=(x + 10, y))
    screen.blit(text_surf, text_rect)
