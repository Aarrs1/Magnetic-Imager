# -*- coding: utf-8 -*-
"""动画工具：颜色/浮点插值、单元格动画状态"""

from config import ANIM_SPEED, CELL_PULSE_DURATION


def lerp_color(current, target, dt, speed=ANIM_SPEED):
    """帧率无关的颜色线性插值，返回 (r, g, b)"""
    t = min(1.0, speed * dt)
    return (
        int(current[0] + (target[0] - current[0]) * t),
        int(current[1] + (target[1] - current[1]) * t),
        int(current[2] + (target[2] - current[2]) * t),
    )


def lerp_float(current, target, dt, speed=ANIM_SPEED):
    """帧率无关的浮点线性插值"""
    t = min(1.0, speed * dt)
    return current + (target - current) * t


class CellAnimState:
    """每个单元格的动画状态：当前颜色 lerp 到目标颜色"""

    def __init__(self):
        self.target = (0, 0, 0)
        self.current = (0, 0, 0)
        self.timer = 0.0

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
