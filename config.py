# -*- coding: utf-8 -*-
"""全局常量与配置 — 基于 2× 设计分辨率 (1700×900)"""

# ── 字体 ──
FONT_NAME = "SimHei"  # 可改为系统中任意中文字体，如 "microsoft yahei", "simsun", "kaiti" 等

# ── 布局（2× 设计分辨率，基于复古 Processing 草图缩放） ──
MAX_SIZE = 8                # 传感器阵列 8×8
WINDOW_WIDTH = 1700         # 设计/虚拟画布尺寸（2× 超采样）
WINDOW_HEIGHT = 900
DESIGN_WIDTH = 1700
DESIGN_HEIGHT = 900
INITIAL_WIDTH = 850         # 初始窗口尺寸（½ 设计尺寸）
INITIAL_HEIGHT = 450
PIXEL_SIZE = 60             # 单元格像素（原 Processing 30px × 2）
GRID_SIZE = MAX_SIZE * PIXEL_SIZE  # 480

SIDEBAR_WIDTH = 290         # 侧边栏宽（原 145×2）
STATUS_BAR_HEIGHT = 44      # 状态栏高（原 22×2）
GRID_GAP = 56               # 双网格间距（原 28×2）

GRIDS_TOTAL_WIDTH = GRID_SIZE * 2 + GRID_GAP          # 1016
CONTENT_AREA_WIDTH = DESIGN_WIDTH - SIDEBAR_WIDTH      # 1410
GRIDS_LEFT = (CONTENT_AREA_WIDTH - GRIDS_TOTAL_WIDTH) // 2  # 197
GRID_NORMAL_LEFT = GRIDS_LEFT
GRID_HIGH_LEFT = GRIDS_LEFT + GRID_SIZE + GRID_GAP     # 733

GRID_TOP = 190              # 网格顶部边距（原 50×2，下移 10%）
GRID_LABEL_HEIGHT = 32      # 标签高度（原 16×2）
COLORBAR_TOP = GRID_TOP + GRID_LABEL_HEIGHT + GRID_SIZE + 20  # 632
STATUS_BAR_TOP = DESIGN_HEIGHT - STATUS_BAR_HEIGHT     # 856

# ── 数据 ──
MAX_VALUE = 9.0  # DRV5053 VA saturation ±9 mT
MAX_CALIB_FRAMES = 50
BAUD_RATE = 921600

# ── 配色 ──
COLOR_VOID = (13, 21, 32)
COLOR_SIDEBAR = (22, 34, 48)
COLOR_SIDEBAR_EDGE = (56, 76, 100)
COLOR_PANEL = (30, 46, 64)
COLOR_PANEL_BORDER = (80, 110, 150)
COLOR_TEXT = (224, 232, 242)
COLOR_TEXT_MUTED = (122, 149, 181)
COLOR_ACCENT = (88, 120, 152)
COLOR_ACCENT_LIGHT = (120, 160, 200)

# ── 毛玻璃透明度 ──
FROST_PANEL_ALPHA = 140
FROST_SIDEBAR_ALPHA = 185
FROST_STATUSBAR_ALPHA = 215

# ── 按钮（2×） ──
BUTTON_WIDTH = SIDEBAR_WIDTH - 20               # 270
BUTTON_HEIGHT = 60                               # 原 30×2
BUTTON_GAP = 8                                   # 原 4×2
BUTTON_RADIUS = 12                               # 原 6×2
SIDEBAR_PADDING_TOP = 24                         # 原 12×2
SIDEBAR_PADDING_X = 20                           # 原 10×2
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
            ("实时", "L", "play"),
            ("停止", "S", "stop"),
        ],
    },
    {
        "label": "高速捕获",
        "type": "grid2x2",
        "items": [
            ("Max", "1"),
            ("1 ms", "2"),
            ("2 ms", "3"),
            ("4 ms", "4"),
        ],
    },
    {
        "label": "工具",
        "type": "stack",
        "items": [
            ("校准", "C"),
            ("重置校准", "R"),
            ("清空", "A"),
            ("截图", "SPACE"),
        ],
    },
]

# 按钮激活态柔绿色
COLOR_ACTIVE = (60, 160, 90)
COLOR_ACTIVE_DIM = (40, 110, 65)

# ── Toast ──
TOAST_DURATION_MS = 1500
TOAST_FADE_MS = 260

# ── 动画 ──
ANIM_SPEED = 12.0
CELL_PULSE_DURATION = 0.3

# ── Max Gain 输入控件 ──
GAIN_AREA_WIDTH = SIDEBAR_WIDTH - 40       # 250
GAIN_AREA_HEIGHT = 40
GAIN_ARROW_WIDTH = 36
GAIN_ARROW_HEIGHT = 18
GAIN_DROPDOWN_WIDTH = 28
GAIN_VALUE_WIDTH = GAIN_AREA_WIDTH - GAIN_ARROW_WIDTH - GAIN_DROPDOWN_WIDTH  # 186
GAIN_TOP_OFFSET = 48                        # 与最后一个按钮的间距

# ── 增益预设 (mT) ──
GAIN_PRESETS = [1, 2, 5, 6, 7, 10, 12, 15, 20, 30]
GAIN_PRESET_RECOMMENDED = 6
GAIN_PRESET_ITEM_HEIGHT = 28
GAIN_DROPDOWN_PANEL_WIDTH = 88

# ── 自动增益按钮 ──
AUTO_GAIN_TOP_OFFSET = 12
AUTO_GAIN_HEIGHT = 44
