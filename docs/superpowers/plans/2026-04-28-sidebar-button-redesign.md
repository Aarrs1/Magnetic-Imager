# Sidebar Button Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign sidebar buttons with section grouping, clear labels, mode highlighting, and simplified keyboard shortcuts (Space only for live/stop toggle).

**Architecture:** `BUTTON_SECTIONS` in config replaces flat `BUTTON_DEFS`, each section has `type` (mode/grid2x2/stack) driving layout. `draw_button()` gains `active` param for muted-green highlight. `main.py` precomputes all button rects from sections, handles Space as live/stop toggle, and sets active state from `is_live`/`is_calibrating`.

**Tech Stack:** pygame, pygame.freetype

---

### Task 1: Rewrite config.py — BUTTON_SECTIONS replaces BUTTON_DEFS

**Files:**
- Modify: `config.py`

- [ ] Replace `BUTTON_DEFS` with `BUTTON_SECTIONS`:

```python
# ── 按钮区域间距 ──
SECTION_GAP = 18
SECTION_HEADER_HEIGHT = 22
HALF_BUTTON_WIDTH = (BUTTON_WIDTH - 10) // 2

# ── 按钮分组定义 ──
# type: "mode" (侧并排互斥), "grid2x2" (2×2网格), "stack" (全宽竖排)
BUTTON_SECTIONS = [
    {
        "label": "运行模式",
        "type": "mode",
        "items": [
            ("▶ 实时", "L"),
            ("■ 停止", "S"),
        ],
    },
    {
        "label": "高速捕获",
        "type": "grid2x2",
        "items": [
            ("2 kHz", "1"),
            ("1 kHz", "2"),
            ("500 Hz", "3"),
            ("250 Hz", "4"),
        ],
    },
    {
        "label": "工具",
        "type": "stack",
        "items": [
            ("🔍 校准", "C"),
            ("🗑 清空", "A"),
            ("📷 截图", "SPACE"),
        ],
    },
]

# 按钮激活态柔绿色
COLOR_ACTIVE = (60, 160, 90)
COLOR_ACTIVE_DIM = (40, 110, 65)
```

- [ ] Commit

---

### Task 2: Update draw_button() — add active param

**Files:**
- Modify: `ui_components.py`

- [ ] Update `draw_button()` signature from:

```python
def draw_button(screen, rect, text, font, hover=False, press_flash=0.0):
```

to:

```python
def draw_button(screen, rect, text, font, hover=False, press_flash=0.0, active=False):
```

- [ ] Add active-state rendering before the hover logic. Replace:

```python
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
```

with:

```python
    if active:
        base_alpha = int(40 + press_flash * 30)
        fill_color = (60, 160, 90, min(255, base_alpha))
        pygame.draw.rect(button, fill_color, button.get_rect(),
                         border_radius=BUTTON_RADIUS)
        border_alpha = min(255, 160 + int(press_flash * 40))
        pygame.draw.rect(button, (80, 180, 110, border_alpha), button.get_rect(), 2,
                         border_radius=BUTTON_RADIUS)
        highlight_alpha = 80
        pygame.draw.line(button, (120, 200, 140, highlight_alpha),
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
```

- [ ] Add `draw_section_header()`:

```python
def draw_section_header(screen, font, text, x, y):
    text_surf, _ = font.render(text, COLOR_TEXT_MUTED)
    text_rect = text_surf.get_rect(midleft=(x + 4, y))
    screen.blit(text_surf, text_rect)
```

- [ ] Commit

---

### Task 3: Rewrite main.py — sections, Space toggle, active states

**Files:**
- Modify: `main.py`

- [ ] Update config imports to add:

```python
from config import (
    ..., BUTTON_SECTIONS, SECTION_GAP, SECTION_HEADER_HEIGHT, HALF_BUTTON_WIDTH,
    COLOR_ACTIVE, COLOR_ACTIVE_DIM,
)
from ui_components import draw_button, draw_toast, draw_status_bar, draw_gain_input, draw_section_header
```

- [ ] Replace the button creation loop with section-based precomputation:

```python
    buttons = []
    button_x = SIDEBAR_PADDING_X
    button_y = SIDEBAR_PADDING_TOP + 48

    for section in BUTTON_SECTIONS:
        button_y += SECTION_HEADER_HEIGHT  # section header space
        section_label = section["label"]
        section_type = section["type"]

        if section_type == "mode":
            # 两个半宽按钮并排
            y = button_y
            x = button_x
            for label, action in section["items"]:
                rect = pygame.Rect(
                    DESIGN_WIDTH - SIDEBAR_WIDTH + x, y,
                    HALF_BUTTON_WIDTH, BUTTON_HEIGHT,
                )
                buttons.append({
                    "label": label, "action": action, "rect": rect,
                    "section": section_label,
                })
                x += HALF_BUTTON_WIDTH + 10
            button_y += BUTTON_HEIGHT + BUTTON_GAP

        elif section_type == "grid2x2":
            # 2×2 网格
            start_y = button_y
            for idx, (label, action) in enumerate(section["items"]):
                col = idx % 2
                row = idx // 2
                rect = pygame.Rect(
                    DESIGN_WIDTH - SIDEBAR_WIDTH + button_x + col * (HALF_BUTTON_WIDTH + 10),
                    start_y + row * (BUTTON_HEIGHT + BUTTON_GAP),
                    HALF_BUTTON_WIDTH, BUTTON_HEIGHT,
                )
                buttons.append({
                    "label": label, "action": action, "rect": rect,
                    "section": section_label,
                })
            button_y = start_y + 2 * (BUTTON_HEIGHT + BUTTON_GAP) - BUTTON_GAP

        elif section_type == "stack":
            for label, action in section["items"]:
                rect = pygame.Rect(
                    DESIGN_WIDTH - SIDEBAR_WIDTH + button_x, button_y,
                    BUTTON_WIDTH, BUTTON_HEIGHT,
                )
                buttons.append({
                    "label": label, "action": action, "rect": rect,
                    "section": section_label,
                })
                button_y += BUTTON_HEIGHT + BUTTON_GAP

        button_y += SECTION_GAP
```

- [ ] In KEYDOWN handler, replace action key detection with Space-only toggle:

Replace:
```python
            elif event.type == pygame.KEYDOWN:
                k = event.unicode.lower() if event.unicode else ""
                action = None

                if not gain_editing:
                    if event.key == pygame.K_SPACE:
                        action = "SPACE"
                    elif k in {"a", "l", "h", "s", "1", "2", "3", "4", "c", "d"}:
                        action = k.upper()

                    if action:
                        handle_action(action)
                        button_flash[action] = 0.15
                else:
                    ...
```

with:

```python
            elif event.type == pygame.KEYDOWN:
                if not gain_editing:
                    if event.key == pygame.K_SPACE:
                        if is_live:
                            handle_action("S")
                            button_flash["S"] = 0.15
                        else:
                            handle_action("L")
                            button_flash["L"] = 0.15
                else:
                    ...
```

- [ ] Update `handle_action` — remove H case, simplify SPACE (now handled by key only for live/stop toggle; screenshot only via button):

```python
        def show_toast(message):
            nonlocal toast_message, toast_start_ms
            toast_message = message
            toast_start_ms = pygame.time.get_ticks()

        if action == "SPACE":
            filename = f"screenshot-{screenshot_number}.png"
            pygame.image.save(screen, filename)
            print(f"Screenshot saved: {filename}")
            screenshot_number += 1
            show_toast("Screenshot saved")
            return

        if action == "A":
            datastore.clear_data()
            show_toast("Data cleared")
            return

        if action == "L":
            serial_reader.write("L")
            is_live = True
            show_toast("Live Feed")
            return

        if action == "S":
            serial_reader.write("S")
            is_live = False
            show_toast("Stopped")
            return

        if action in ("1", "2", "3", "4"):
            serial_reader.write(action)
            freq_map = {"1": "2 kHz", "2": "1 kHz", "3": "500 Hz", "4": "250 Hz"}
            show_toast(f"{freq_map[action]} 捕获")
            return

        if action == "C":
            datastore.start_calibration()
            show_toast("Calibrating...")
            return
```

(Remove `if action == "H"` and the `D` print_calib_data case)

- [ ] In the rendering loop, compute active states and pass to draw_button. Also render section headers. Replace the button drawing loop:

```python
        shown_sections = set()
        for button in buttons:
            # Draw section header once per section
            sec = button.get("section")
            if sec and sec not in shown_sections:
                shown_sections.add(sec)
                header_y = button["rect"].top - SECTION_HEADER_HEIGHT
                draw_section_header(virtual, tiny_font, sec,
                                    DESIGN_WIDTH - SIDEBAR_WIDTH + SIDEBAR_PADDING_X + 4,
                                    header_y)

            hover = button["rect"].collidepoint(vx, vy)
            flash = button_flash.get(button["action"], 0.0)
            action = button["action"]

            # Active state: mode buttons show current mode; calibrate shows during calibration
            active = False
            if action == "L" and is_live:
                active = True
            elif action == "S" and not is_live:
                active = True
            elif action == "C" and datastore.calibration_enabled:
                active = True

            draw_button(virtual, button["rect"], button["label"], button_font,
                        hover, flash, active)
```

- [ ] Update sidebar title. Remove the "控制" title (section headers replace it). Or keep it but move it up. Simpler: keep it as-is.

- [ ] Commit

---

### Task 4: Fixup — ensure Gap and Max Gain positioning

**Files:**
- Modify: `main.py`

- [ ] Adjust the `gain_rect` position. After the button precomputation loop, `button_y` is already at the correct position. The existing line:

```python
    gain_rect = pygame.Rect(
        DESIGN_WIDTH - SIDEBAR_WIDTH + SIDEBAR_PADDING_X,
        button_y + GAIN_TOP_OFFSET,
        GAIN_AREA_WIDTH, GAIN_AREA_HEIGHT,
    )
```

stays correct — the loop ends at the bottom of the last section + SECTION_GAP.

- [ ] Commit
