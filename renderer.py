# -*- coding: utf-8 -*-
"""渲染器：网格、标签、颜色条、单元格提示"""

import pygame
import pygame.freetype
import pygame.gfxdraw

_bar_cache = {}  # (gain, max_value, height) → 色条渐变 Surface（惰性缓存）

from config import (
    MAX_SIZE, GRID_SIZE, PIXEL_SIZE,
    COLOR_PANEL, FROST_PANEL_ALPHA, COLOR_PANEL_BORDER,
    COLOR_TEXT_MUTED, COLOR_TEXT, COLOR_ACCENT_LIGHT,
    GRID_LABEL_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT, SIDEBAR_WIDTH,
)
from animation import CellAnimState, clamp

# 静态渲染资源缓存（只生成一次，避免每帧重绘）
_panel_cache = None     # 网格毛玻璃底板
_border_cache = None    # 单元格边框
_label_cache = None     # 行/列号标签


def _get_panel():
    global _panel_cache
    if _panel_cache is None:
        pw = GRID_SIZE + 32
        _panel_cache = pygame.Surface((pw, pw), pygame.SRCALPHA)
        _panel_cache.fill((*COLOR_PANEL, FROST_PANEL_ALPHA))
        pygame.draw.rect(_panel_cache, (*COLOR_PANEL_BORDER, 60),
                         _panel_cache.get_rect(), 1, border_radius=16)
    return _panel_cache


def _get_border():
    global _border_cache
    if _border_cache is None:
        _border_cache = pygame.Surface((PIXEL_SIZE, PIXEL_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(_border_cache, (200, 225, 245, 28),
                         _border_cache.get_rect(), 2)
    return _border_cache


def _get_labels(font):
    global _label_cache
    if _label_cache is None:
        labels = {}
        for i in range(MAX_SIZE):
            s, _ = font.render(str(i), COLOR_TEXT_MUTED)
            labels[("row", i)] = s
            s, _ = font.render(str(i), COLOR_TEXT_MUTED)
            labels[("col", i)] = s
        _label_cache = labels
    return _label_cache


def draw_grid(screen, data, data_calib, is_calibrated, grid_left, grid_top,
              gain_normal, gain_calib, max_value, cell_states, mouse_pos, font_tiny):
    """绘制 8×8 传感器网格热力图。

    参数:
        gain_normal: 正常增益颜色强度系数
        gain_calib: 校准后颜色强度系数
        max_value: 归一化上限（即 Max Gain）
        cell_states: dict — 单元格动画状态（由调用方管理）
    返回: 悬停 (row, col) 或 None
    """
    # 网格底板（毛玻璃圆角面板）
    panel_padding = 16
    panel_rect = pygame.Rect(
        grid_left - panel_padding, grid_top - panel_padding,
        GRID_SIZE + 32, GRID_SIZE + 32,
    )
    screen.blit(_get_panel(), panel_rect.topleft)

    # 行号（左侧，7→0 从上到下）和列号（下方）
    labels = _get_labels(font_tiny)
    for i in range(MAX_SIZE):
        screen.blit(labels[("row", i)],
                    labels[("row", i)].get_rect(
                        midright=(grid_left - 12,
                                  grid_top + i * PIXEL_SIZE + PIXEL_SIZE // 2)))
        screen.blit(labels[("col", i)],
                    labels[("col", i)].get_rect(
                        midtop=(grid_left + i * PIXEL_SIZE + PIXEL_SIZE // 2,
                                grid_top + GRID_SIZE + 8)))

    border_surf = _get_border()

    # 悬停检测：鼠标位置 → (row, col)
    hover_idx = None
    if mouse_pos:
        mx, my = mouse_pos
        rel_x = mx - grid_left
        rel_y = my - grid_top
        if 0 <= rel_x < GRID_SIZE and 0 <= rel_y < GRID_SIZE:
            hover_col = rel_x // PIXEL_SIZE
            hover_row = rel_y // PIXEL_SIZE
            hover_idx = (hover_row, hover_col)

    # 逐单元格绘制：颜色映射 + 动画插值
    for i in range(MAX_SIZE):
        for j in range(MAX_SIZE):
            y = i * PIXEL_SIZE
            x = j * PIXEL_SIZE

            # 计算目标颜色：正值 → 绿色（下方），负值 → 红色（上方）
            if is_calibrated:
                value = (data[i][j] - data_calib[i][j]) / max_value
                if value > 0:
                    target_color = (0, clamp(int(gain_calib * value)), 0)
                elif value < 0:
                    target_color = (clamp(int(-gain_calib * value)), 0, 0)
                else:
                    target_color = (0, 0, 0)
            else:
                value = data[i][j] / max_value
                if value > 0:
                    target_color = (0, clamp(int(gain_normal * value)), 0)
                elif value < 0:
                    target_color = (clamp(int(-gain_normal * value)), 0, 0)
                else:
                    target_color = (0, 0, 0)

            # 动画状态管理：目标变化时触发脉冲
            key = (i, j)
            if key not in cell_states:
                cell_states[key] = CellAnimState()
            prev_target = cell_states[key].target
            cell_states[key].set_target(target_color, pulse=(prev_target != target_color))

            rect = (x + grid_left, y + grid_top, PIXEL_SIZE, PIXEL_SIZE)
            color = cell_states[key].current
            pygame.draw.rect(screen, color, rect)
            screen.blit(border_surf, (x + grid_left, y + grid_top))

            # 悬停高亮外框
            if hover_idx == key:
                hover_outline = pygame.Surface((PIXEL_SIZE, PIXEL_SIZE), pygame.SRCALPHA)
                pygame.draw.rect(hover_outline, (180, 210, 240, 150), hover_outline.get_rect(), 3)
                screen.blit(hover_outline, (x + grid_left, y + grid_top))

    return hover_idx


def draw_grid_label(screen, font, text, grid_center_x, grid_top, accent=None):
    text_surf, _ = font.render(text, COLOR_TEXT)
    label_rect = text_surf.get_rect(center=(grid_center_x, grid_top - GRID_LABEL_HEIGHT - 12))
    screen.blit(text_surf, label_rect)

    if accent:
        line_y = label_rect.bottom + 4
        pygame.draw.line(screen, (*accent, 120),
                         (label_rect.left, line_y),
                         (label_rect.right, line_y), 2)
        pygame.draw.line(screen, (*accent, 60),
                         (label_rect.left, line_y + 2),
                         (label_rect.right, line_y + 2), 1)


def draw_color_bar_v(screen, font_tiny, left, top, height, gain=255,
                     max_value=660.0, labels_left=False, cursor_value=None):
    """绘制垂直渐变色条 — 上方绿色(+max) → 中间黑色(0) → 下方红色(−max)。

    gain 控制颜色强度映射。labels_left=True 时刻度在左侧。
    cursor_value 为鼠标悬停单元格的当前值，驱动白色光标条平滑移动。
    色条表面使用惰性缓存避免每帧重建。
    """
    bar_width = 20

    # 惰性生成渐变色条 Surface（参数变化时重建）
    cache_key = (gain, max_value, height)
    if cache_key not in _bar_cache:
        gen = pygame.Surface((1, height))
        for py in range(height):
            t = py / (height - 1)
            if t < 0.5:
                g = int(gain * (1 - 2 * t))
                r = 0
            elif t > 0.5:
                g = 0
                r = int(gain * 2 * (t - 0.5))
            else:
                r, g = 0, 0
            dist_from_center = abs(t - 0.5) * 2
            void = 1 - dist_from_center * 0.7  # 中间区域偏暗
            r = clamp(int(r * void))
            g = clamp(int(g * void))
            gen.set_at((0, py), (r, g, 0))
        bar = pygame.transform.scale(gen, (bar_width, height))
        pygame.draw.rect(bar, (*COLOR_PANEL_BORDER, 60), bar.get_rect(), 1, border_radius=4)
        _bar_cache[cache_key] = bar
    screen.blit(_bar_cache[cache_key], (left, top))

    # 五档刻度标签：+max, +half, 0, −half, −max
    mv = int(max_value)
    half = mv // 2
    ticks = [
        (top,                   f"+{mv}mT"),
        (top + height // 4,     f"+{half}mT"),
        (top + height // 2,     "0mT"),
        (top + height * 3 // 4, f"-{half}mT"),
        (top + height - 1,      f"-{mv}mT"),
    ]
    for y, label in ticks:
        if labels_left:
            tick_x = left - 6
            pygame.draw.line(screen, (*COLOR_PANEL_BORDER, 80),
                             (tick_x + 2, y), (tick_x - 4, y), 1)
            text_surf, _ = font_tiny.render(label, COLOR_TEXT_MUTED)
            text_rect = text_surf.get_rect(midright=(tick_x - 8, y))
        else:
            tick_x = left + bar_width + 4
            pygame.draw.line(screen, (*COLOR_PANEL_BORDER, 80),
                             (tick_x - 2, y), (tick_x + 4, y), 1)
            text_surf, _ = font_tiny.render(label, COLOR_TEXT_MUTED)
            text_rect = text_surf.get_rect(midleft=(tick_x + 8, y))
        screen.blit(text_surf, text_rect)

    # 白色光标条（始终显示，带 glow 光晕，位置由 cursor_value 映射到色条 Y 坐标）
    v = max(-max_value, min(max_value, cursor_value)) if cursor_value is not None else 0.0
    cursor_w, cursor_h = 22, 5
    cy = top + int((1 - v / max_value) * height / 2) - cursor_h // 2
    cy = max(top, min(top + height - cursor_h, cy))
    cx = left + (bar_width - cursor_w) // 2

    # glow 光晕
    glow_w, glow_h = cursor_w + 8, cursor_h + 8
    gx, gy = cx - 4, cy - 4
    glow = pygame.Surface((glow_w, glow_h), pygame.SRCALPHA)
    pygame.draw.rect(glow, (180, 210, 250, 50), glow.get_rect(), border_radius=5)
    screen.blit(glow, (gx, gy))

    cur = pygame.Surface((cursor_w, cursor_h), pygame.SRCALPHA)
    pygame.draw.rect(cur, (255, 255, 255, 230), cur.get_rect(), border_radius=3)
    pygame.draw.rect(cur, (255, 255, 255, 255), cur.get_rect(), 1, border_radius=3)
    screen.blit(cur, (cx, cy))

    # 方向标注（N 上 / S 下，对应磁传感器方位）
    text_surf, _ = font_tiny.render("N", COLOR_TEXT)
    screen.blit(text_surf, text_surf.get_rect(center=(left + bar_width // 2, top - 14)))
    text_surf, _ = font_tiny.render("S", COLOR_TEXT)
    screen.blit(text_surf, text_surf.get_rect(center=(left + bar_width // 2, top + height + 14)))


def draw_cell_tooltip(screen, font_tiny, row, col, value, cell_rect,
                      calib=None):
    """在单元格旁绘制毛玻璃气泡提示框，显示 R/C 坐标、当前值和校准值。

    自动避让右边界：右侧空间不足时翻转到单元格左侧。
    渲染层级：阴影 → 外发光环 → 主体背景 → 三角箭头 → 文本。
    """
    arrow_w, arrow_h = 10, 7
    font_tiny.strong = True
    lines = [f"行{row} 列{col}  {value:.3f} mT"]
    if calib is not None:
        lines.append(f"  校准: {calib:.3f} mT")
    text_surfs = [font_tiny.render(line, COLOR_TEXT)[0] for line in lines]
    font_tiny.strong = False
    line_h = text_surfs[0].get_height() + 4
    tw = max(s.get_width() for s in text_surfs)
    th = line_h * len(lines)
    content_rect = pygame.Rect(0, 0, tw + 32, th + 20)

    # 默认右侧弹出；右边界不足时翻转到左侧
    tooltip_x = cell_rect.right + 16
    tooltip_y = cell_rect.centery - content_rect.height // 2
    arrow_left = True
    if tooltip_x + content_rect.width > WINDOW_WIDTH - SIDEBAR_WIDTH:
        tooltip_x = cell_rect.left - content_rect.width - 16
        arrow_left = False
    tooltip_y = max(0, min(tooltip_y, WINDOW_HEIGHT - content_rect.height))

    tw_full, th_full = content_rect.width, content_rect.height

    # 柔和阴影（向下偏移 4px）
    shadow = pygame.Surface((tw_full, th_full), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 140), shadow.get_rect(), border_radius=10)
    screen.blit(shadow, (tooltip_x, tooltip_y + 4))

    # 外发光环（半透明浅蓝）
    glow_pad = 4
    glow = pygame.Surface((tw_full + glow_pad * 2, th_full + glow_pad * 2), pygame.SRCALPHA)
    pygame.draw.rect(glow, (80, 130, 180, 25), glow.get_rect(), border_radius=12)
    screen.blit(glow, (tooltip_x - glow_pad, tooltip_y - glow_pad))

    # 主体背景（深色半透明 + 蓝灰边框）
    tooltip = pygame.Surface((tw_full, th_full), pygame.SRCALPHA)
    pygame.draw.rect(tooltip, (4, 10, 18, 237), tooltip.get_rect(), border_radius=10)
    pygame.draw.rect(tooltip, (*COLOR_ACCENT_LIGHT, 128), tooltip.get_rect(), 1, border_radius=10)
    screen.blit(tooltip, (tooltip_x, tooltip_y))

    # 三角箭头（指向源单元格）
    mid_y = tooltip_y + th_full // 2
    if arrow_left:
        tip_x, tip_y = tooltip_x, mid_y
        base_x, base_y = tooltip_x + arrow_w, mid_y
    else:
        tip_x, tip_y = tooltip_x + tw_full, mid_y
        base_x, base_y = tooltip_x + tw_full - arrow_w, mid_y
    pygame.gfxdraw.filled_trigon(screen,
        tip_x, tip_y,
        base_x, base_y - arrow_h,
        base_x, base_y + arrow_h,
        (100, 150, 200, 220))
    pygame.gfxdraw.aatrigon(screen,
        tip_x, tip_y,
        base_x, base_y - arrow_h,
        base_x, base_y + arrow_h,
        (*COLOR_ACCENT_LIGHT, 220))

    # 逐行绘制文本
    for idx, surf in enumerate(text_surfs):
        line_y = tooltip_y + 10 + idx * line_h
        line_x = tooltip_x + (tw_full - surf.get_width()) // 2
        screen.blit(surf, (line_x, line_y))
