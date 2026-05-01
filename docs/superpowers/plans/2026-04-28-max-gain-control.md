# Max Gain Custom Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace hardcoded MAX_VALUE=660 with an editable max-gain control in the right sidebar.

**Architecture:** `draw_gain_input()` in `ui_components.py` renders the widget and returns hit-test rects stored in `gain_regions`. `main.py` owns `max_gain` (default 660.0), edit-mode state, handles events. `renderer.py` `draw_grid` and `draw_color_bar_v` receive `max_value` to replace hardcoded `MAX_VALUE` in normalization and tick labels.

**Tech Stack:** pygame, pygame.freetype

---

### Task 1: Add config constants

**Files:**
- Modify: `config.py`

- [ ] After `BUTTON_DEFS` block, add:

```python
# ── Max Gain 输入控件 ──
GAIN_AREA_WIDTH = SIDEBAR_WIDTH - 40       # 250
GAIN_AREA_HEIGHT = 40
GAIN_ARROW_WIDTH = 36
GAIN_ARROW_HEIGHT = 18
GAIN_VALUE_WIDTH = GAIN_AREA_WIDTH - GAIN_ARROW_WIDTH  # 214
GAIN_TOP_OFFSET = 48                        # 与最后一个按钮的间距
```

- [ ] Commit:

```bash
git add config.py
git commit -m "feat: add gain input layout constants"
```

---

### Task 2: Add draw_gain_input() to ui_components.py

**Files:**
- Modify: `ui_components.py`

- [ ] Update config import to include new constants:

```python
from config import (
    BUTTON_RADIUS, COLOR_ACCENT_LIGHT, COLOR_TEXT, COLOR_TEXT_MUTED,
    TOAST_FADE_MS, TOAST_DURATION_MS, WINDOW_WIDTH,
    STATUS_BAR_TOP, STATUS_BAR_HEIGHT, SIDEBAR_WIDTH,
    FROST_STATUSBAR_ALPHA, COLOR_PANEL_BORDER,
    GAIN_ARROW_WIDTH, GAIN_ARROW_HEIGHT, GAIN_VALUE_WIDTH,
)
```

- [ ] Add `_draw_arrow()` and `draw_gain_input()` at end of file:

```python
def _draw_arrow(screen, rect, direction, color):
    """在 rect 内绘制三角形箭头"""
    cx, cy = rect.centerx, rect.centery
    if direction == "up":
        pts = [(cx, cy - 5), (cx - 6, cy + 4), (cx + 6, cy + 4)]
    else:
        pts = [(cx, cy + 5), (cx - 6, cy - 4), (cx + 6, cy - 4)]
    pygame.draw.polygon(screen, color[:3], pts)


def draw_gain_input(screen, font, rect, value, editing, edit_text,
                    cursor_pos, mouse_pos):
    """
    绘制 Max Gain 输入控件。
    mouse_pos: (vx, vy) 虚拟坐标，可为 None。
    返回 {"up": up_rect, "down": down_rect, "value": value_rect}
    """
    mx, my = mouse_pos if mouse_pos else (-1, -1)

    # 标签
    label_surf, _ = font.render("Max Gain", COLOR_TEXT_MUTED)
    label_rect = label_surf.get_rect(midleft=(rect.x + 4, rect.y - 12))
    screen.blit(label_surf, label_rect)

    # 背景面板
    bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(bg, (20, 35, 55, 180), bg.get_rect(), border_radius=BUTTON_RADIUS)
    pygame.draw.rect(bg, (*COLOR_ACCENT_LIGHT, 60), bg.get_rect(), 2,
                     border_radius=BUTTON_RADIUS)
    screen.blit(bg, rect.topleft)

    # 数值区域
    value_rect = pygame.Rect(rect.x + 8, rect.y + 4,
                             GAIN_VALUE_WIDTH - 8, GAIN_AREA_HEIGHT - 8)

    # 箭头区域分隔线
    sep_x = rect.x + GAIN_VALUE_WIDTH
    pygame.draw.line(screen, (*COLOR_ACCENT_LIGHT, 50),
                     (sep_x, rect.y + 6), (sep_x, rect.y + rect.height - 6), 1)

    # 上/下箭头区域
    arrow_left = sep_x + 4
    up_rect = pygame.Rect(arrow_left, rect.y + 4,
                          GAIN_ARROW_WIDTH, GAIN_ARROW_HEIGHT - 2)
    down_rect = pygame.Rect(arrow_left, rect.y + GAIN_ARROW_HEIGHT + 2,
                            GAIN_ARROW_WIDTH, GAIN_ARROW_HEIGHT - 2)

    up_hover = up_rect.collidepoint(mx, my)
    down_hover = down_rect.collidepoint(mx, my)

    arrow_active = (*COLOR_ACCENT_LIGHT, 255)
    arrow_idle = (*COLOR_TEXT_MUTED, 180)
    _draw_arrow(screen, up_rect, "up", arrow_active if up_hover else arrow_idle)
    _draw_arrow(screen, down_rect, "down", arrow_active if down_hover else arrow_idle)

    # 数值显示 / 编辑中
    display = edit_text if editing else f"{int(value)} f"
    display_color = COLOR_TEXT
    text_surf, _ = font.render(display, display_color)
    text_rect = text_surf.get_rect(center=value_rect.center)

    # 裁剪文本避免溢出
    if text_surf.get_width() > value_rect.width - 8:
        clip = pygame.Surface((value_rect.width - 8, text_surf.get_height()),
                              pygame.SRCALPHA)
        clip.blit(text_surf, (0, 0))
        clip_rect = clip.get_rect(center=value_rect.center)
        screen.blit(clip, clip_rect)
    else:
        screen.blit(text_surf, text_rect)

    # 编辑光标闪烁
    if editing and int(pygame.time.get_ticks() / 500) % 2 == 0:
        prefix = edit_text[:cursor_pos]
        prefix_surf, _ = font.render(prefix, COLOR_TEXT)
        cursor_x = text_rect.left + prefix_surf.get_width()
        cursor_y = text_rect.top
        pygame.draw.line(screen, COLOR_TEXT,
                         (cursor_x + 1, cursor_y),
                         (cursor_x + 1, cursor_y + text_surf.get_height()), 2)

    return {"up": up_rect, "down": down_rect, "value": value_rect}
```

- [ ] Commit:

```bash
git add ui_components.py
git commit -m "feat: add draw_gain_input() widget with up/down arrows and text edit"
```

---

### Task 3: Update renderer.py — pass max_value through draw_grid and draw_color_bar_v

**Files:**
- Modify: `renderer.py`

- [ ] Update `draw_grid()` to accept `max_value` parameter. Change signature:

```python
def draw_grid(screen, data, data_calib, is_calibrated, grid_left, grid_top,
              gain_normal, gain_calib, max_value, cell_states, mouse_pos, font_tiny):
```

- [ ] Replace all `MAX_VALUE` references inside `draw_grid()` with `max_value` (lines 65 and 72).

- [ ] Update `draw_color_bar_v()` signature to:

```python
def draw_color_bar_v(screen, font_tiny, left, top, height, gain=255,
                     max_value=660.0, labels_left=False):
```

- [ ] Replace the hardcoded tick labels with dynamic generation. Replace the `ticks` list with:

```python
mv = int(max_value)
half = mv // 2
ticks = [
    (top,                   f"+{mv}"),
    (top + height // 4,     f"+{half}"),
    (top + height // 2,     "0"),
    (top + height * 3 // 4, f"-{half}"),
    (top + height - 1,      f"-{mv}"),
]
```

- [ ] Commit:

```bash
git add renderer.py
git commit -m "feat: make grid and color bar use dynamic max_value"
```

---

### Task 4: Integrate into main.py

**Files:**
- Modify: `main.py`

- [ ] Update imports:

```python
from config import (
    ..., GAIN_AREA_WIDTH, GAIN_AREA_HEIGHT, GAIN_TOP_OFFSET,
)
from ui_components import draw_button, draw_toast, draw_status_bar, draw_gain_input
```

- [ ] After `button_flash = {}`, add state:

```python
max_gain = 660.0
gain_editing = False
gain_edit_text = ""
gain_edit_cursor = 0
gain_regions = {}
```

- [ ] After button creation loop, add gain input rect:

```python
gain_rect = pygame.Rect(
    DESIGN_WIDTH - SIDEBAR_WIDTH + SIDEBAR_PADDING_X,
    button_y + GAIN_TOP_OFFSET,
    GAIN_AREA_WIDTH, GAIN_AREA_HEIGHT,
)
```

- [ ] In KEYDOWN handler, after `if action:` block, add edit-mode key handling:

```python
if gain_editing:
    if event.key == pygame.K_RETURN:
        try:
            new_val = float(gain_edit_text)
            if new_val >= 1:
                max_gain = new_val
        except ValueError:
            pass
        gain_editing = False
    elif event.key == pygame.K_ESCAPE:
        gain_editing = False
    elif event.key == pygame.K_BACKSPACE:
        if gain_edit_cursor > 0:
            gain_edit_text = (
                gain_edit_text[:gain_edit_cursor - 1]
                + gain_edit_text[gain_edit_cursor:]
            )
            gain_edit_cursor -= 1
    elif event.key == pygame.K_DELETE:
        if gain_edit_cursor < len(gain_edit_text):
            gain_edit_text = (
                gain_edit_text[:gain_edit_cursor]
                + gain_edit_text[gain_edit_cursor + 1:]
            )
    elif event.key == pygame.K_LEFT:
        if gain_edit_cursor > 0:
            gain_edit_cursor -= 1
    elif event.key == pygame.K_RIGHT:
        if gain_edit_cursor < len(gain_edit_text):
            gain_edit_cursor += 1
    elif event.unicode and event.unicode.isprintable():
        ch = event.unicode
        if ch.isdigit() or ch == '.':
            gain_edit_text = (
                gain_edit_text[:gain_edit_cursor]
                + ch
                + gain_edit_text[gain_edit_cursor:]
            )
            gain_edit_cursor += 1
```

- [ ] Replace the MOUSEBUTTONDOWN block with:

```python
elif event.type == pygame.MOUSEBUTTONDOWN:
    if event.button == 1:
        vx, vy = to_virtual(event.pos, win_w, win_h)

        gain_handled = False
        if gain_rect.collidepoint(vx, vy) and gain_regions:
            if gain_regions["up"].collidepoint(vx, vy):
                gain_editing = False
                max_gain += 1
                gain_handled = True
            elif gain_regions["down"].collidepoint(vx, vy):
                gain_editing = False
                if max_gain > 1:
                    max_gain -= 1
                gain_handled = True
            elif gain_regions["value"].collidepoint(vx, vy):
                if not gain_editing:
                    gain_editing = True
                    gain_edit_text = str(int(max_gain))
                    gain_edit_cursor = len(gain_edit_text)
                gain_handled = True

        if not gain_handled:
            if gain_editing:
                try:
                    new_val = float(gain_edit_text)
                    if new_val >= 1:
                        max_gain = new_val
                except ValueError:
                    pass
                gain_editing = False
            else:
                for button in buttons:
                    if button["rect"].collidepoint(vx, vy):
                        handle_action(button["action"])
                        button_flash[button["action"]] = 0.15
                        break
```

- [ ] Update `draw_grid` calls to pass `max_gain`:

```python
hover_normal = draw_grid(virtual, data, data_calib, is_calibrated,
                         GRID_NORMAL_LEFT, GRID_TOP, NORM_GAIN, NORM_GAIN,
                         max_gain,
                         cell_states_normal, (vx, vy), tiny_font)
hover_high = draw_grid(virtual, data, data_calib, is_calibrated,
                       GRID_HIGH_LEFT, GRID_TOP, HIGH_GAIN, HIGH_GAIN,
                       max_gain,
                       cell_states_high, (vx, vy), tiny_font)
```

- [ ] Update `draw_color_bar_v` calls to pass `max_gain`:

```python
draw_color_bar_v(virtual, tiny_font, norm_bar_left, GRID_TOP, GRID_SIZE,
                 gain=NORM_GAIN, max_value=max_gain, labels_left=True)
draw_color_bar_v(virtual, tiny_font, high_bar_left, GRID_TOP, GRID_SIZE,
                 gain=HIGH_GAIN, max_value=max_gain)
```

- [ ] Add `draw_gain_input` call in rendering section (after button loop, before status bar):

```python
gain_regions = draw_gain_input(virtual, button_font, gain_rect,
                               max_gain, gain_editing, gain_edit_text,
                               gain_edit_cursor, (vx, vy))
```

- [ ] Commit:

```bash
git add main.py
git commit -m "feat: integrate max gain control into main loop"
```
