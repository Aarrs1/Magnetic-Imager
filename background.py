# -*- coding: utf-8 -*-
"""背景渲染：静态噪点 + 毛玻璃层 + 动态光晕"""

import random
import math
import pygame

from config import COLOR_VOID


def create_background(size):
    """创建基础背景（静态噪点 + 毛玻璃层）"""
    surface = pygame.Surface(size)
    surface.fill(COLOR_VOID)

    noise = pygame.Surface(size, pygame.SRCALPHA)
    rng = random.Random(7)
    for _ in range(600):
        x = rng.randrange(0, size[0])
        y = rng.randrange(0, size[1])
        r = rng.choice([1, 1, 1, 2])
        shade = rng.randrange(18, 50)
        alpha = rng.randrange(8, 20)
        pygame.draw.circle(noise, (shade, shade + 4, shade + 14, alpha), (x, y), r)
    for _ in range(300):
        x = rng.randrange(0, size[0])
        y = rng.randrange(0, size[1])
        r = 1
        shade = rng.randrange(90, 140)
        alpha = rng.randrange(6, 14)
        pygame.draw.circle(noise, (shade, shade + 8, shade + 24, alpha), (x, y), r)

    frost = pygame.Surface(size, pygame.SRCALPHA)
    frost.fill((180, 200, 225, 12))

    surface.blit(frost, (0, 0))
    surface.blit(noise, (0, 0))
    return surface


def draw_background_glow(screen, time_sec):
    """绘制动态环境光晕（缓慢漂移）"""
    glow = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    # Glow 1: 右上区域
    cx1 = screen.get_width() - 120 + int(20 * math.sin(time_sec * 0.4))
    cy1 = 160 + int(15 * math.cos(time_sec * 0.35))
    alpha1 = int(25 + 10 * math.sin(time_sec * 0.6))
    pygame.draw.circle(glow, (80, 120, 170, alpha1), (cx1, cy1), 200)

    # Glow 2: 左下区域
    cx2 = 100 + int(18 * math.cos(time_sec * 0.45))
    cy2 = screen.get_height() - 140 + int(12 * math.sin(time_sec * 0.5))
    alpha2 = int(18 + 8 * math.cos(time_sec * 0.55))
    pygame.draw.circle(glow, (60, 100, 150, alpha2), (cx2, cy2), 180)

    screen.blit(glow, (0, 0))
