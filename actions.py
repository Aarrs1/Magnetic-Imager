# -*- coding: utf-8 -*-
"""
动作分发：按钮点击、键盘事件、截图保存、增益编辑。

集中管理所有用户交互逻辑，将 UI 事件与数据层解耦。
"""

import os
import time
from datetime import datetime
import pygame

from config import MAX_SIZE


def show_toast(state, message, status="info"):
    """显示 Toast 通知。status 决定状态圆点颜色：info/success/warning/stop。"""
    state.toast_message = message
    state.toast_status = status
    state.toast_start_ms = pygame.time.get_ticks()


def handle_action(state, action, datastore, serial_reader, screen):
    """分发按钮动作到对应的数据/串口操作。

    action 映射：
      SPACE — 截图（保存画面 + 数据文本到 screenshots/时间戳/）
      A     — 清空数据
      L     — 开启实时数据流
      S     — 停止数据流
      1~4   — 高速捕获（自动退出实时模式）
      C     — 启动校准（1 秒延迟）
      R     — 重置校准
    """
    if action == "SPACE":
        base_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(base_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        folder = os.path.join(base_dir, ts)
        os.makedirs(folder)
        pygame.image.save(screen, os.path.join(folder, "screenshot.png"))
        data, data_calib, is_calib = datastore.get_snapshot()
        txt_path = os.path.join(folder, "data.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            for i in range(MAX_SIZE):
                f.write(f"row {i}: {' '.join(f'{data[i][j]:.3f}' for j in range(MAX_SIZE))}\n")
            if is_calib:
                f.write("\n--- calibrated ---\n")
                for i in range(MAX_SIZE):
                    f.write(f"row {i}: {' '.join(f'{(data[i][j] - data_calib[i][j]):.3f}' for j in range(MAX_SIZE))}\n")
        state.screenshot_number += 1
        show_toast(state, f"Saved: {ts}")
        return

    if action == "A":
        datastore.clear_data()
        show_toast(state, "Data cleared")
        return

    if action == "L":
        serial_reader.write("L")
        state.is_live = True
        state.capture_active = None
        state.banner_visible = False
        show_toast(state, "Live Feed")
        return

    if action == "S":
        serial_reader.write("S")
        state.is_live = False
        state.capture_active = None
        show_toast(state, "Stopped", "stop")
        return

    if action in ("1", "2", "3", "4"):
        if state.is_live:
            serial_reader.write("S")
            state.is_live = False
        serial_reader.write(action)
        state.capture_active = action
        state.banner_visible = False
        freq_map = {"1": "Max speed", "2": "1 ms delay", "3": "2 ms delay", "4": "4 ms delay"}
        show_toast(state, f"{freq_map[action]} 捕获")
        return

    if action == "C":
        state.calib_delay_until = time.time() + 1.0
        show_toast(state, "Calibrating in 1s...")
        return

    if action == "R":
        datastore.reset_calibration()
        show_toast(state, "Calibration reset")
        return


def handle_gain_keydown(event, state):
    """处理 Max Gain 输入框的按键编辑。

    支持：Enter 提交、Esc 取消、Backspace/Delete 删除、
    ←→ 光标移动、数字/小数点输入。返回 True 表示事件已消费。
    """
    if event.key == pygame.K_RETURN:
        try:
            new_val = float(state.gain_edit_text)
            if new_val > 0:
                state.max_gain = new_val
        except ValueError:
            pass
        state.gain_editing = False
        return True
    if event.key == pygame.K_ESCAPE:
        state.gain_editing = False
        return True
    if event.key == pygame.K_BACKSPACE:
        if state.gain_edit_cursor > 0:
            state.gain_edit_text = (
                state.gain_edit_text[:state.gain_edit_cursor - 1]
                + state.gain_edit_text[state.gain_edit_cursor:]
            )
            state.gain_edit_cursor -= 1
        return True
    if event.key == pygame.K_DELETE:
        if state.gain_edit_cursor < len(state.gain_edit_text):
            state.gain_edit_text = (
                state.gain_edit_text[:state.gain_edit_cursor]
                + state.gain_edit_text[state.gain_edit_cursor + 1:]
            )
        return True
    if event.key == pygame.K_LEFT:
        if state.gain_edit_cursor > 0:
            state.gain_edit_cursor -= 1
        return True
    if event.key == pygame.K_RIGHT:
        if state.gain_edit_cursor < len(state.gain_edit_text):
            state.gain_edit_cursor += 1
        return True
    if event.unicode and event.unicode.isprintable():
        ch = event.unicode
        if ch.isdigit() or ch == '.':
            state.gain_edit_text = (
                state.gain_edit_text[:state.gain_edit_cursor]
                + ch
                + state.gain_edit_text[state.gain_edit_cursor:]
            )
            state.gain_edit_cursor += 1
        return True
    return False


def handle_gain_click(vx, vy, state, gain_rect, gain_regions):
    """处理 Max Gain 区域的鼠标点击。

    检测顺序：下拉预设项 → 增益区外 → 下拉箭头 → ±步进 → 数值编辑。
    返回 True 表示事件已消费，不再传播到按钮检测。
    """
    if not gain_regions:
        return False

    # 下拉面板中的预设项（可能浮在 gain_rect 外部，因此最先检测）
    for item_rect, val in gain_regions.get("dropdown_items", []):
        if item_rect.collidepoint(vx, vy):
            state.max_gain = float(val)
            state.gain_dropdown_open = False
            state.gain_editing = False
            return True

    # 点击在增益区域外
    if not gain_rect.collidepoint(vx, vy):
        if state.gain_dropdown_open:
            state.gain_dropdown_open = False
            if state.gain_editing:
                try:
                    new_val = float(state.gain_edit_text)
                    if new_val > 0:
                        state.max_gain = new_val
                except ValueError:
                    pass
                state.gain_editing = False
            return True
        # 编辑中 — 不消费，让 main 提交并回退到按钮检测
        return False

    # 下拉箭头
    if gain_regions["dropdown"].collidepoint(vx, vy):
        state.gain_dropdown_open = not state.gain_dropdown_open
        state.gain_editing = False
        return True

    if gain_regions["up"].collidepoint(vx, vy):
        state.gain_editing = False
        state.gain_dropdown_open = False
        state.max_gain = round(state.max_gain + 0.5, 1)
    elif gain_regions["down"].collidepoint(vx, vy):
        state.gain_editing = False
        state.gain_dropdown_open = False
        if state.max_gain > 0.5:
            state.max_gain = round(state.max_gain - 0.5, 1)
    elif gain_regions["value"].collidepoint(vx, vy):
        if not state.gain_editing:
            state.gain_editing = True
            state.gain_dropdown_open = False
            state.gain_edit_text = f"{state.max_gain:.1f}"
            state.gain_edit_cursor = len(state.gain_edit_text)
    return True


def handle_auto_gain(state, datastore):
    """自动增益：扫描正常增益网格当前帧绝对值最大值，将增益调整为 115% 覆盖。"""
    data, _calib, _ = datastore.get_snapshot()
    max_val = 0.0
    for i in range(MAX_SIZE):
        for j in range(MAX_SIZE):
            v = abs(data[i][j])
            if v > max_val:
                max_val = v
    if max_val > 0:
        state.max_gain = round(max_val * 1.15, 1)
