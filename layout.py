# -*- coding: utf-8 -*-
"""
按钮布局构建器。

根据 config.BUTTON_SECTIONS 配置自动生成按钮 rect 列表，
支持三种布局模式：mode（并排互斥）、grid2x2（2×2 网格）、stack（全宽竖排）。
"""

import pygame
from config import (
    DESIGN_WIDTH, SIDEBAR_WIDTH,
    SIDEBAR_PADDING_X, SIDEBAR_PADDING_TOP,
    BUTTON_WIDTH, BUTTON_HEIGHT, BUTTON_GAP, BUTTON_SECTIONS,
    SECTION_GAP, SECTION_HEADER_HEIGHT, HALF_BUTTON_WIDTH,
    GAIN_AREA_WIDTH, GAIN_AREA_HEIGHT, GAIN_TOP_OFFSET,
    AUTO_GAIN_TOP_OFFSET, AUTO_GAIN_HEIGHT,
)


def build_buttons():
    """根据 BUTTON_SECTIONS 配置生成按钮列表。

    返回 list[dict]，每个 dict 包含：
      rect: pygame.Rect    — 按钮区域
      label: str           — 显示文本
      action: str          — 动作标识符
      section: str         — 所属分组标签
      icon: str or None    — 图标类型（"play"/"stop"）

    布局规则：
      mode     — 两个按钮并排，各占半宽
      grid2x2  — 2×2 网格布局
      stack    — 全宽竖排堆叠
    """
    right_pad = 8
    eff_w = SIDEBAR_WIDTH - SIDEBAR_PADDING_X - right_pad
    half_w = (eff_w - 10) // 2

    buttons = []
    x = SIDEBAR_PADDING_X
    y = SIDEBAR_PADDING_TOP + 48

    for section in BUTTON_SECTIONS:
        y += SECTION_HEADER_HEIGHT
        label = section["label"]
        stype = section["type"]

        if stype == "mode":
            bx = x
            for item in section["items"]:
                name, action = item[0], item[1]
                icon = item[2] if len(item) > 2 else None
                rect = pygame.Rect(
                    DESIGN_WIDTH - SIDEBAR_WIDTH + bx, y,
                    half_w, BUTTON_HEIGHT,
                )
                buttons.append({
                    "label": name, "action": action, "rect": rect,
                    "section": label, "icon": icon,
                })
                bx += half_w + 10
            y += BUTTON_HEIGHT + BUTTON_GAP

        elif stype == "grid2x2":
            start_y = y
            for idx, item in enumerate(section["items"]):
                name, action = item[0], item[1]
                col = idx % 2
                row = idx // 2
                rect = pygame.Rect(
                    DESIGN_WIDTH - SIDEBAR_WIDTH + x + col * (half_w + 10),
                    start_y + row * (BUTTON_HEIGHT + BUTTON_GAP),
                    half_w, BUTTON_HEIGHT,
                )
                buttons.append({
                    "label": name, "action": action, "rect": rect,
                    "section": label,
                })
            y = start_y + 2 * (BUTTON_HEIGHT + BUTTON_GAP) - BUTTON_GAP

        elif stype == "stack":
            for item in section["items"]:
                name, action = item[0], item[1]
                rect = pygame.Rect(
                    DESIGN_WIDTH - SIDEBAR_WIDTH + x, y,
                    eff_w, BUTTON_HEIGHT,
                )
                buttons.append({
                    "label": name, "action": action, "rect": rect,
                    "section": label,
                })
                y += BUTTON_HEIGHT + BUTTON_GAP

        y += SECTION_GAP

    return buttons


def build_gain_rect(buttons):
    """在按钮列表底部之后构建 Max Gain 输入框矩形。
    自动跟随最后一个按钮的位置计算 Y 偏移。"""
    last_y = max(b["rect"].bottom for b in buttons) if buttons else SIDEBAR_PADDING_TOP + 48
    return pygame.Rect(
        DESIGN_WIDTH - SIDEBAR_WIDTH + SIDEBAR_PADDING_X,
        last_y + GAIN_TOP_OFFSET,
        GAIN_AREA_WIDTH, GAIN_AREA_HEIGHT,
    )


def build_auto_gain_rect(gain_rect):
    """在增益输入框下方构建自动增益按钮"""
    return pygame.Rect(
        gain_rect.x,
        gain_rect.bottom + AUTO_GAIN_TOP_OFFSET,
        GAIN_AREA_WIDTH, AUTO_GAIN_HEIGHT,
    )
