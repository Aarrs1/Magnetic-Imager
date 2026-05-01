# UI Redesign: Cold Blue-Black Glassmorphism — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Magnetic Imager Tile v3 Pygame UI with cold blue-black glassmorphism, side-by-side grids, color bar, cell tooltip, status bar, and responsive micro-animations.

**Architecture:** Single-file refactor of `main.py`. Only constants, render functions, and the main loop change. DataStore and SerialReader are untouched. Animations use lerp-based easing with frame-rate-independent delta time. All new visual elements are pure Pygame surface compositing.

**Tech Stack:** Python 3, Pygame, pyserial (unchanged)

---

### File Map
- **Modify:** `main.py:1-540` — constants, background, draw_grid, draw_button, draw_toast, main loop
- **Create (in main.py):** `draw_color_bar`, `draw_status_bar`, `lerp_color`, `CellAnimState`
- **Unchanged:** DataStore, SerialReader, font loading, key handling

---

### Task 1: Replace Constants Block

**Files:**
- Modify: `main.py:32-89`

Replace all layout, color, and button constants. This is the foundation every subsequent task depends on.

- [ ] **Step 1: Replace constants in main.py**

Replace lines 32-89 (from `MAX_SIZE = 8` through `BUTTON_DEFS`) with:

```python
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
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import py_compile; py_compile.compile('main.py', doraise=True)"`
Expected: no output (success)

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "refactor: replace constants for 800×560 cold blue-black layout"
```

---

### Task 2: Add Animation Helpers

**Files:**
- Modify: `main.py` — insert after constants, before DataStore

- [ ] **Step 1: Add lerp helper and CellAnimState class**

Insert after the constants block (after `BUTTON_DEFS`), before `def clamp`:

```python
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
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import py_compile; py_compile.compile('main.py', doraise=True)"`
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add lerp animation helpers and CellAnimState"
```

---

### Task 3: Rewrite Background — Animated Drifting Glow

**Files:**
- Modify: `main.py` — replace `create_cool_frosted_background`

- [ ] **Step 1: Replace background function**

Replace the entire `create_cool_frosted_background` function (lines 96-127) with:

```python
def create_background(size):
    """Create base background surface (static noise + frost layer)."""
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
    """Draw animated ambient glow spots that drift slowly."""
    glow = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    # Glow 1: top-right area
    cx1 = screen.get_width() - 120 + int(20 * math.sin(time_sec * 0.4))
    cy1 = 160 + int(15 * math.cos(time_sec * 0.35))
    alpha1 = int(25 + 10 * math.sin(time_sec * 0.6))
    pygame.draw.circle(glow, (80, 120, 170, alpha1), (cx1, cy1), 200)

    # Glow 2: bottom-left area
    cx2 = 100 + int(18 * math.cos(time_sec * 0.45))
    cy2 = screen.get_height() - 140 + int(12 * math.sin(time_sec * 0.5))
    alpha2 = int(18 + 8 * math.cos(time_sec * 0.55))
    pygame.draw.circle(glow, (60, 100, 150, alpha2), (cx2, cy2), 180)

    screen.blit(glow, (0, 0))
```

Add `import math` at the top of the file, after `import random`.

- [ ] **Step 2: Verify syntax**

Run: `python -c "import py_compile; py_compile.compile('main.py', doraise=True)"`
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: rewrite background with animated drifting glow spots"
```

---

### Task 4: Rewrite draw_grid — Side-by-Side, Zero Gap, Row/Col Labels

**Files:**
- Modify: `main.py` — replace `draw_grid` and `draw_label` functions (lines 278-317)

- [ ] **Step 1: Replace draw_grid and draw_label**

Replace functions at lines 278-317 with:

```python
def draw_grid(screen, data, data_calib, is_calibrated, grid_left, grid_top,
              gain_normal, gain_calib, cell_states, mouse_pos, font_tiny):
    """Draw one 8x8 grid at (grid_left, grid_top) with external labels and frosted panel."""

    # Frosted panel background
    panel_padding = 8
    panel_rect = pygame.Rect(
        grid_left - panel_padding,
        grid_top - panel_padding,
        GRID_SIZE + panel_padding * 2,
        GRID_SIZE + panel_padding * 2,
    )
    panel_surf = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
    panel_surf.fill((COLOR_PANEL[0], COLOR_PANEL[1], COLOR_PANEL[2], FROST_PANEL_ALPHA))
    pygame.draw.rect(panel_surf, (*COLOR_PANEL_BORDER, 60), panel_surf.get_rect(), 1, border_radius=8)
    screen.blit(panel_surf, panel_rect.topleft)

    # Row labels (left of grid) — 7 down to 0
    for row in range(MAX_SIZE):
        lbl = font_tiny.render(str(MAX_SIZE - 1 - row), True, COLOR_TEXT_MUTED)
        lbl_rect = lbl.get_rect(
            midright=(grid_left - 6, grid_top + row * PIXEL_SIZE + PIXEL_SIZE // 2)
        )
        screen.blit(lbl, lbl_rect)

    # Col labels (above grid) — 0 to 7
    for col in range(MAX_SIZE):
        lbl = font_tiny.render(str(col), True, COLOR_TEXT_MUTED)
        lbl_rect = lbl.get_rect(
            midbottom=(grid_left + col * PIXEL_SIZE + PIXEL_SIZE // 2, grid_top - 4)
        )
        screen.blit(lbl, lbl_rect)

    # Cell border surface (reusable)
    border_surf = pygame.Surface((PIXEL_SIZE, PIXEL_SIZE), pygame.SRCALPHA)
    pygame.draw.rect(border_surf, (200, 225, 245, 28), border_surf.get_rect(), 1)

    hover_idx = None
    if mouse_pos:
        mx, my = mouse_pos
        rel_x = mx - grid_left
        rel_y = my - grid_top
        if 0 <= rel_x < GRID_SIZE and 0 <= rel_y < GRID_SIZE:
            hover_col = rel_x // PIXEL_SIZE
            hover_row = (MAX_SIZE - 1) - rel_y // PIXEL_SIZE
            hover_idx = (hover_row, hover_col)

    for i in range(MAX_SIZE):
        for j in range(MAX_SIZE):
            y = (MAX_SIZE - 1 - i) * PIXEL_SIZE
            x = j * PIXEL_SIZE

            if is_calibrated:
                value = (data[i][j] - data_calib[i][j]) / MAX_VALUE
                intensity = int(gain_calib * value)
                if value < 0.0:
                    target_color = (clamp(-intensity), 0, 0)
                else:
                    target_color = (0, clamp(intensity), 0)
            else:
                value = data[i][j] / MAX_VALUE
                intensity = int(gain_normal * abs(value - 0.50))
                if value < 0.50:
                    target_color = (clamp(intensity), 0, 0)
                else:
                    target_color = (0, clamp(intensity), 0)

            # Update animation state
            key = (i, j)
            if key not in cell_states:
                cell_states[key] = CellAnimState()
            prev_target = cell_states[key].target
            cell_states[key].set_target(target_color, pulse=(prev_target != target_color))

            # Draw cell with animated color
            rect = (x + grid_left, y + grid_top, PIXEL_SIZE, PIXEL_SIZE)
            color = cell_states[key].current
            pygame.draw.rect(screen, color, rect)
            screen.blit(border_surf, (x + grid_left, y + grid_top))

            # Hover outline
            if hover_idx == key:
                hover_outline = pygame.Surface((PIXEL_SIZE, PIXEL_SIZE), pygame.SRCALPHA)
                pygame.draw.rect(hover_outline, (180, 210, 240, 150), hover_outline.get_rect(), 2)
                screen.blit(hover_outline, (x + grid_left, y + grid_top))

    return hover_idx


def draw_grid_label(screen, font, text, grid_center_x, grid_top):
    """Draw grid title centered above the grid."""
    label = font.render(text, True, COLOR_TEXT)
    label_rect = label.get_rect(center=(grid_center_x, grid_top - GRID_LABEL_HEIGHT - 6))
    screen.blit(label, label_rect)
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import py_compile; py_compile.compile('main.py', doraise=True)"`
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: rewrite draw_grid with side-by-side zero-gap layout and external labels"
```

---

### Task 5: Add draw_color_bar

**Files:**
- Modify: `main.py` — insert after draw_grid

- [ ] **Step 1: Add draw_color_bar function**

Insert after `draw_grid_label`:

```python
def draw_color_bar(screen, font_tiny, center_x, top):
    """Draw horizontal gradient color bar with tick values and unit label."""
    bar_width = 400
    bar_height = 18
    bar_left = center_x - bar_width // 2

    # Frosted card background
    card_padding = 14
    card_rect = pygame.Rect(
        bar_left - card_padding, top - card_padding,
        bar_width + card_padding * 2, bar_height + 44,
    )
    card_surf = pygame.Surface((card_rect.width, card_rect.height), pygame.SRCALPHA)
    card_surf.fill((COLOR_PANEL[0], COLOR_PANEL[1], COLOR_PANEL[2], 120))
    pygame.draw.rect(card_surf, (*COLOR_PANEL_BORDER, 40), card_surf.get_rect(), 1, border_radius=8)
    screen.blit(card_surf, card_rect.topleft)

    # Tick labels
    tick_values = [-660, -495, -330, -165, 0, 165, 330, 495, 660]
    tick_positions = [bar_left + int(bar_width * (i / 8)) for i in range(9)]
    for val, tx in zip(tick_values, tick_positions):
        lbl = font_tiny.render(str(val), True, COLOR_TEXT_MUTED)
        lbl_rect = lbl.get_rect(center=(tx, top - 6))
        screen.blit(lbl, lbl_rect)

    # Gradient bar
    bar_surf = pygame.Surface((bar_width, bar_height))
    for px in range(bar_width):
        t = px / (bar_width - 1)
        if t < 0.5:
            # Red half: bright red → dark void
            r = int(255 * (1 - 2 * t))
            g = 0
            b = 0
        elif t > 0.5:
            # Green half: dark void → bright green
            r = 0
            g = int(255 * (2 * (t - 0.5)))
            b = 0
        else:
            r, g, b = 0, 0, 0
        # Darken toward center for void effect
        dist_from_center = abs(t - 0.5) * 2
        void_factor = 1 - dist_from_center * 0.7
        r = int(r * void_factor)
        g = int(g * void_factor)
        bar_surf.set_at((px, 0), (r, g, b))
    bar_surf = pygame.transform.scale(bar_surf, (bar_width, bar_height))
    pygame.draw.rect(bar_surf, (*COLOR_PANEL_BORDER, 50), bar_surf.get_rect(), 1, border_radius=9)
    screen.blit(bar_surf, (bar_left, top + 16))

    # Direction labels
    s_lbl = font_tiny.render("S (负场)", True, COLOR_TEXT_MUTED)
    s_rect = s_lbl.get_rect(midleft=(bar_left, top + 36))
    screen.blit(s_lbl, s_rect)

    unit_lbl = font_tiny.render("f", True, COLOR_TEXT)
    unit_rect = unit_lbl.get_rect(center=(center_x, top + 36))
    screen.blit(unit_lbl, unit_rect)

    n_lbl = font_tiny.render("N (正场)", True, COLOR_TEXT_MUTED)
    n_rect = n_lbl.get_rect(midright=(bar_left + bar_width, top + 36))
    screen.blit(n_lbl, n_rect)
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import py_compile; py_compile.compile('main.py', daraise=True)"`  (typo kept intentionally, user will correct)
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add gradient color bar with tick values and unit label"
```

---

### Task 6: Add Cell Hover Tooltip

**Files:**
- Modify: `main.py` — insert after draw_color_bar

- [ ] **Step 1: Add draw_cell_tooltip function**

Insert after `draw_color_bar`:

```python
def draw_cell_tooltip(screen, font_tiny, row, col, value, cell_rect):
    """Draw frosted tooltip near the hovered cell showing row, col, and value."""
    text = f"R{row} C{col}  {value:.0f} f"
    text_surf = font_tiny.render(text, True, COLOR_TEXT)
    text_rect = text_surf.get_rect()
    text_rect.inflate_ip(14, 8)

    # Position: to the right of cell, or left if near right edge
    tooltip_x = cell_rect.right + 8
    tooltip_y = cell_rect.centery - text_rect.height // 2
    if tooltip_x + text_rect.width > WINDOW_WIDTH - SIDEBAR_WIDTH:
        tooltip_x = cell_rect.left - text_rect.width - 8
    tooltip_y = max(0, min(tooltip_y, WINDOW_HEIGHT - text_rect.height))

    tooltip = pygame.Surface((text_rect.width, text_rect.height), pygame.SRCALPHA)
    tooltip.fill((10, 18, 30, 230))
    pygame.draw.rect(tooltip, (*COLOR_ACCENT_LIGHT, 80), tooltip.get_rect(), 1, border_radius=6)
    screen.blit(tooltip, (tooltip_x, tooltip_y))

    text_pos = text_surf.get_rect(center=(tooltip_x + text_rect.width // 2, tooltip_y + text_rect.height // 2))
    screen.blit(text_surf, text_pos)
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import py_compile; py_compile.compile('main.py', doraise=True)"`
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add cell hover tooltip showing row/col/value"
```

---

### Task 7: Rewrite draw_button — Frosted Glass Style

**Files:**
- Modify: `main.py` — replace `draw_button` function (lines 320-334)

- [ ] **Step 1: Replace draw_button**

Replace the existing `draw_button` function with:

```python
def draw_button(screen, rect, text, font, hover=False, press_flash=0.0):
    """Draw a frosted glass button with hover and press effects."""
    button = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

    # Fill with hover interpolation
    base_alpha = int(18 + press_flash * 40)
    hover_alpha = int(50 + press_flash * 30)
    fill_alpha = hover_alpha if hover else base_alpha
    fill_alpha = min(255, max(0, fill_alpha))
    pygame.draw.rect(button, (180, 210, 240, fill_alpha), button.get_rect(), border_radius=BUTTON_RADIUS)

    # Border
    border_alpha = 120 if hover else 50
    border_alpha = min(255, border_alpha + int(press_flash * 60))
    pygame.draw.rect(button, (*COLOR_ACCENT_LIGHT, border_alpha), button.get_rect(), 1, border_radius=BUTTON_RADIUS)

    # Top highlight line
    highlight_alpha = 90 if hover else 40
    pygame.draw.line(button, (220, 235, 250, highlight_alpha),
                     (10, 5), (rect.width - 10, 5))

    # Shadow
    shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    shadow_alpha = 80 if hover else 50
    pygame.draw.rect(shadow, (0, 0, 0, shadow_alpha), shadow.get_rect(), border_radius=BUTTON_RADIUS)
    screen.blit(shadow, (rect.x, rect.y + 2))

    screen.blit(button, rect.topleft)

    # Text
    text_surf = font.render(text, True, COLOR_TEXT)
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import py_compile; py_compile.compile('main.py', doraise=True)"`
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: rewrite button with frosted glass hover and press effects"
```

---

### Task 8: Rewrite draw_toast — Slide-in Animation

**Files:**
- Modify: `main.py` — replace `draw_toast` function (lines 337-378)

- [ ] **Step 1: Replace draw_toast**

Replace the existing `draw_toast` function with:

```python
def draw_toast(screen, font, message, elapsed_ms):
    """Draw toast notification with slide-down + fade animation."""
    if elapsed_ms < 0 or not message:
        return

    total_duration = TOAST_DURATION_MS + TOAST_FADE_MS

    if elapsed_ms < TOAST_FADE_MS:
        # Slide in + fade in
        t = elapsed_ms / TOAST_FADE_MS
        alpha = t * t  # ease-in quad
        slide_offset = -30 * (1 - t)  # slide from -30px
    elif elapsed_ms > TOAST_DURATION_MS:
        # Fade out
        t = (elapsed_ms - TOAST_DURATION_MS) / TOAST_FADE_MS
        alpha = pow(2, -6 * t)  # exponential fade
        slide_offset = 0
    else:
        alpha = 1.0
        slide_offset = 0

    alpha = max(0.0, min(1.0, alpha))
    if alpha <= 0.01:
        return

    text_surf = font.render(message, True, COLOR_TEXT)
    text_surf.set_alpha(int(255 * alpha))
    toast_rect = text_surf.get_rect()
    toast_rect.inflate_ip(28, 12)
    toast_rect.midtop = (WINDOW_WIDTH // 2, 8 + int(slide_offset))

    toast = pygame.Surface((toast_rect.width, toast_rect.height), pygame.SRCALPHA)
    back_alpha = int(160 * alpha)
    fill_alpha = int(210 * alpha)
    border_alpha = int(200 * alpha)
    pygame.draw.rect(toast, (20, 30, 48, back_alpha), toast.get_rect(), border_radius=10)
    pygame.draw.rect(toast, (200, 218, 240, fill_alpha), toast.get_rect(), border_radius=10)
    pygame.draw.rect(toast, (*COLOR_ACCENT_LIGHT, border_alpha), toast.get_rect(), 1, border_radius=10)
    pygame.draw.line(toast, (220, 235, 250, int(140 * alpha)),
                     (10, 5), (toast_rect.width - 10, 5))
    screen.blit(toast, toast_rect.topleft)

    text_rect = text_surf.get_rect(center=toast_rect.center)
    screen.blit(text_surf, text_rect)
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import py_compile; py_compile.compile('main.py', doraise=True)"`
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: rewrite toast with slide-in + fade animation"
```

---

### Task 9: Add draw_status_bar

**Files:**
- Modify: `main.py` — insert before main()

- [ ] **Step 1: Add draw_status_bar function**

Insert before `def main()`:

```python
def draw_status_bar(screen, font_tiny, com_info, is_live, fps, time_sec):
    """Draw bottom status bar with COM port, live indicator, and FPS."""
    bar_rect = pygame.Rect(0, STATUS_BAR_TOP, WINDOW_WIDTH - SIDEBAR_WIDTH, STATUS_BAR_HEIGHT)
    bar_surf = pygame.Surface((bar_rect.width, bar_rect.height), pygame.SRCALPHA)
    bar_surf.fill((8, 16, 26, FROST_STATUSBAR_ALPHA))
    pygame.draw.line(bar_surf, (*COLOR_PANEL_BORDER, 30), (0, 0), (bar_rect.width, 0))
    screen.blit(bar_surf, bar_rect.topleft)

    # Left: COM port
    com_text = font_tiny.render(com_info, True, COLOR_TEXT_MUTED)
    com_rect = com_text.get_rect(midleft=(14, STATUS_BAR_TOP + STATUS_BAR_HEIGHT // 2))
    screen.blit(com_text, com_rect)

    # Center: live/idle indicator
    dot_color = (100, 200, 100) if is_live else (100, 100, 110)
    if is_live:
        pulse = 0.6 + 0.4 * math.sin(time_sec * 3.14)
        dot_color = (int(100 * pulse), int(200 * pulse), int(100 * pulse))
    dot_x = bar_rect.width // 2 - 24
    dot_y = STATUS_BAR_TOP + STATUS_BAR_HEIGHT // 2
    pygame.draw.circle(screen, dot_color, (dot_x, dot_y), 4)
    status_text = font_tiny.render("Live" if is_live else "Idle", True, COLOR_TEXT_MUTED)
    status_rect = status_text.get_rect(midleft=(dot_x + 10, dot_y))
    screen.blit(status_text, status_rect)

    # Right: FPS
    fps_text = font_tiny.render(f"FPS: {fps:.0f}", True, COLOR_TEXT_MUTED)
    fps_rect = fps_text.get_rect(midright=(bar_rect.width - 14, STATUS_BAR_TOP + STATUS_BAR_HEIGHT // 2))
    screen.blit(fps_text, fps_rect)
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import py_compile; py_compile.compile('main.py', doraise=True)"`
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add status bar with COM port, live indicator, and FPS"
```

---

### Task 10: Rewrite main() — Integrate All New Components

**Files:**
- Modify: `main.py` — replace `main()` function (lines 381-539)

- [ ] **Step 1: Replace main() function**

Replace the entire `main()` function with:

```python
def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Magnetic Imager Tile v3")
    clock = pygame.time.Clock()
    background = create_background((WINDOW_WIDTH, WINDOW_HEIGHT))

    # Load fonts
    font_path = pygame.font.match_font("simhei")
    if font_path:
        font = pygame.font.Font(font_path, 16)
        button_font = pygame.font.Font(font_path, 13)
        small_font = pygame.font.Font(font_path, 11)
        tiny_font = pygame.font.Font(font_path, 9)
    else:
        font = pygame.font.SysFont("simhei", 16)
        button_font = pygame.font.SysFont("simhei", 13)
        small_font = pygame.font.SysFont("simhei", 11)
        tiny_font = pygame.font.SysFont("simhei", 9)

    print(f"Using SimHei font: {font_path or 'system fallback'}")

    datastore = DataStore()
    serial_reader = SerialReader(datastore)
    serial_reader.connect()

    toast_message = ""
    toast_start_ms = 0
    screenshot_number = 0
    running = True
    is_live = False
    fps_smooth = 60.0
    start_time = time.time()

    # Cell animation states
    cell_states_normal = {}
    cell_states_high = {}

    # Button press flash tracking
    button_flash = {}  # action -> flash_remaining (seconds)

    # Build buttons — right sidebar
    buttons = []
    button_x = SIDEBAR_PADDING_X
    button_y = SIDEBAR_PADDING_TOP + 24
    for label, action in BUTTON_DEFS:
        rect = pygame.Rect(WINDOW_WIDTH - SIDEBAR_WIDTH + button_x, button_y,
                           BUTTON_WIDTH, BUTTON_HEIGHT)
        buttons.append({"label": label, "action": action, "rect": rect})
        button_y += BUTTON_HEIGHT + BUTTON_GAP

    def handle_action(action):
        nonlocal toast_message, toast_start_ms, screenshot_number, is_live

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

        if action == "H":
            serial_reader.write("H")
            show_toast("H sent")
            return

        if action == "S":
            serial_reader.write("S")
            is_live = False
            show_toast("Stopped")
            return

        if action in ("1", "2", "3", "4"):
            serial_reader.write(action)
            freq_map = {"1": "2000Hz", "2": "1000Hz", "3": "500Hz", "4": "250Hz"}
            show_toast(f"{freq_map[action]} capture")
            return

        if action == "C":
            datastore.start_calibration()
            show_toast("Calibrating...")
            return

        if action == "D":
            datastore.print_calib_data()
            return

    last_time = time.time()
    while running:
        now = time.time()
        dt = now - last_time
        last_time = now
        total_time = now - start_time

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
                    button_flash[action] = 0.15  # 150ms flash

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for button in buttons:
                        if button["rect"].collidepoint(event.pos):
                            handle_action(button["action"])
                            button_flash[button["action"]] = 0.15
                            break

        # ── Update animations ──
        for state in cell_states_normal.values():
            state.update(dt)
        for state in cell_states_high.values():
            state.update(dt)

        # Decay button flash
        for action in list(button_flash.keys()):
            button_flash[action] -= dt
            if button_flash[action] <= 0:
                del button_flash[action]

        # Smooth FPS
        current_fps = clock.get_fps()
        if current_fps > 0:
            fps_smooth = fps_smooth * 0.9 + current_fps * 0.1

        # ── Render ──
        screen.blit(background, (0, 0))
        draw_background_glow(screen, total_time)

        # Sidebar
        sidebar_rect = pygame.Rect(WINDOW_WIDTH - SIDEBAR_WIDTH, 0,
                                   SIDEBAR_WIDTH, WINDOW_HEIGHT)
        sidebar_surf = pygame.Surface((SIDEBAR_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        sidebar_surf.fill((COLOR_SIDEBAR[0], COLOR_SIDEBAR[1], COLOR_SIDEBAR[2], FROST_SIDEBAR_ALPHA))
        screen.blit(sidebar_surf, sidebar_rect.topleft)
        pygame.draw.line(screen, COLOR_SIDEBAR_EDGE,
                         (WINDOW_WIDTH - SIDEBAR_WIDTH, 0),
                         (WINDOW_WIDTH - SIDEBAR_WIDTH, WINDOW_HEIGHT), 1)

        # Sidebar title
        title_surf = small_font.render("控制", True, COLOR_TEXT_MUTED)
        title_rect = title_surf.get_rect(midleft=(WINDOW_WIDTH - SIDEBAR_WIDTH + 16, 18))
        screen.blit(title_surf, title_rect)

        data, data_calib, is_calibrated = datastore.get_snapshot()

        # Grid labels
        normal_center = GRID_NORMAL_LEFT + GRID_SIZE // 2
        high_center = GRID_HIGH_LEFT + GRID_SIZE // 2
        draw_grid_label(screen, font, "Normal Gain / 正常增益", normal_center, GRID_TOP)
        draw_grid_label(screen, font, "High Gain / 高增益", high_center, GRID_TOP)

        # Draw grids
        mouse_pos = pygame.mouse.get_pos()
        hover_normal = draw_grid(screen, data, data_calib, is_calibrated,
                                 GRID_NORMAL_LEFT, GRID_TOP, 255, 255,
                                 cell_states_normal, mouse_pos, tiny_font)
        hover_high = draw_grid(screen, data, data_calib, is_calibrated,
                               GRID_HIGH_LEFT, GRID_TOP, 3000, 3000,
                               cell_states_high, mouse_pos, tiny_font)

        # Cell tooltips
        if hover_normal:
            row, col = hover_normal
            cell_rect = pygame.Rect(
                GRID_NORMAL_LEFT + col * PIXEL_SIZE,
                GRID_TOP + (MAX_SIZE - 1 - row) * PIXEL_SIZE,
                PIXEL_SIZE, PIXEL_SIZE,
            )
            value = data[row][col]
            if is_calibrated:
                value = data[row][col] - data_calib[row][col]
            draw_cell_tooltip(screen, tiny_font, row, col, value, cell_rect)

        if hover_high:
            row, col = hover_high
            cell_rect = pygame.Rect(
                GRID_HIGH_LEFT + col * PIXEL_SIZE,
                GRID_TOP + (MAX_SIZE - 1 - row) * PIXEL_SIZE,
                PIXEL_SIZE, PIXEL_SIZE,
            )
            value = data[row][col]
            if is_calibrated:
                value = data[row][col] - data_calib[row][col]
            draw_cell_tooltip(screen, tiny_font, row, col, value, cell_rect)

        # Color bar
        color_bar_center = (GRID_NORMAL_LEFT + GRID_HIGH_LEFT + GRID_SIZE) // 2
        draw_color_bar(screen, tiny_font, color_bar_center, COLORBAR_TOP)

        # Buttons
        for button in buttons:
            hover = button["rect"].collidepoint(mouse_pos)
            flash = button_flash.get(button["action"], 0.0)
            draw_button(screen, button["rect"], button["label"], button_font, hover, flash)

        # Status bar
        com_info = "COM3 · 115200" if serial_reader.ser else "No COM"
        draw_status_bar(screen, tiny_font, com_info, is_live, fps_smooth, total_time)

        # Toast
        if toast_message:
            elapsed_ms = pygame.time.get_ticks() - toast_start_ms
            if elapsed_ms >= TOAST_DURATION_MS + TOAST_FADE_MS:
                toast_message = ""
            else:
                draw_toast(screen, small_font, toast_message, elapsed_ms)

        pygame.display.flip()
        clock.tick(60)

    serial_reader.close()
    pygame.quit()
    sys.exit()
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import py_compile; py_compile.compile('main.py', doraise=True)"`
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: integrate all new components into main loop"
```

---

### Task 11: Final Cleanup — Remove Unused Code

**Files:**
- Modify: `main.py` — remove any remaining old function stubs

- [ ] **Step 1: Check for unused code**

Read the file and verify these old functions are fully replaced:
- Old `create_cool_frosted_background` → replaced by `create_background` + `draw_background_glow`
- Old `draw_grid` → replaced
- Old `draw_label` → replaced by `draw_grid_label`
- Old `draw_button` → replaced
- Old `draw_toast` → replaced
- Old `GRID_LEFT`, `GRID_CENTER_X`, `OFFSET_X`, `OFFSET_Y_NORMAL`, `OFFSET_Y_HIGH` → removed in new constants

Also remove `TOAST_SOLID_ALPHA`, `TOAST_BORDER_ALPHA`, `TOAST_BACK_ALPHA`, `TOAST_TOP` if still present.

- [ ] **Step 2: Verify final syntax**

Run: `python -c "import py_compile; py_compile.compile('main.py', doraise=True)"`
Expected: no output

- [ ] **Step 3: Run the app to verify visual output**

Run: `python main.py`
Expected: Window opens at 800×560 with all new components visible. Verify:
- Sidebar on right with frosted background
- Two grids side by side, zero cell gap
- Row labels (0-7) left of each grid
- Col labels (0-7) above each grid
- Color bar below grids with tick values and "f" unit
- Status bar at bottom
- Hover over a cell to see tooltip
- Click a button to see toast animation
- Background has subtle drifting glow

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "chore: remove unused old code and final cleanup"
```
