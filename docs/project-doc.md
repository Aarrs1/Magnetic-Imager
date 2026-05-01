# Magnetic Imager Tile v3 — 项目文档

## 项目概述

磁成像传感器阵列 (8×8) 的 Python 可视化程序，从 Processing 草图 (`projecttest.pde`) 迁移而来。通过串口读取传感器数据，实时渲染两个增益模式（正常/高增益）的网格热力图。

**入口文件：** `main.py`

---

## 文件结构

```
Magnetic_Imager/
├── main.py            # 入口：主循环、事件处理、组件调度
├── config.py          # 全局常量与配置
├── app_state.py       # 运行时可变状态（dataclass 容器）
├── animation.py       # 动画工具函数与类
├── background.py      # 背景渲染（噪点 + 毛玻璃 + 动态光晕）
├── datastore.py       # 数据存储与校准（线程安全）
├── serial_reader.py   # 串口通信（后台线程读取）
├── renderer.py        # 渲染器（网格热力图、渐变色条、悬停提示）
├── ui_components.py   # UI 组件（按钮、Toast、状态栏、增益输入、分组标题）
├── layout.py          # 按钮布局构建器（mode/grid2x2/stack 三模式）
├── actions.py         # 动作分发（按钮点击、增益编辑、截图、自动增益）
├── .gitignore         # Git 忽略规则
├── projecttest.pde    # 原始 Processing 草图（参考用）
├── docs/
│   ├── project-doc.md # 本文档（项目技术文档）
│   └── superpowers/   # 设计规格与实现计划存档
│       ├── specs/     # 设计文档
│       └── plans/     # 实现计划
└── screenshots/       # 截图输出目录（运行时生成）
```

---

## 各文件详细说明

### 1. `config.py` — 全局常量与配置

**作用：** 集中管理所有可调参数。

| 类别 | 关键常量 | 说明 |
|------|---------|------|
| 字体 | `FONT_NAME` | 默认 `"SimHei"` |
| 布局 | `DESIGN_WIDTH` / `DESIGN_HEIGHT` | 2× 虚拟画布 1700×900 |
| 布局 | `GRID_SIZE` | 网格边长 480px (MAX_SIZE × PIXEL_SIZE) |
| 布局 | `SIDEBAR_WIDTH` | 右侧控制栏宽度 290px |
| 布局 | `STATUS_BAR_HEIGHT` | 底部状态栏高度 44px |
| 数据 | `MAX_SIZE` | 传感器阵列大小 8×8 |
| 数据 | `MAX_VALUE` | 最大量程 660.0（初始值） |
| 数据 | `MAX_CALIB_FRAMES` | 校准所需帧数 200 |
| 数据 | `BAUD_RATE` | 串口波特率 115200 |
| 配色 | `COLOR_VOID` / `COLOR_PANEL` / `COLOR_TEXT` 等 | 深色科技风配色 |
| 毛玻璃 | `FROST_PANEL_ALPHA` / `FROST_SIDEBAR_ALPHA` | 各区域透明度 |
| 按钮 | `BUTTON_WIDTH` / `BUTTON_HEIGHT` / `BUTTON_RADIUS` | 按钮尺寸与圆角 |
| 按钮 | `SECTION_GAP` / `SECTION_HEADER_HEIGHT` | 分组间距与标题高度 |
| 按钮 | `HALF_BUTTON_WIDTH` | 半宽按钮（并排/网格用） |
| 按钮 | `BUTTON_SECTIONS` | 三组按钮定义（模式/捕获/工具），支持 icon |
| 动画 | `ANIM_SPEED` / `CELL_PULSE_DURATION` | 插值速度 / 脉冲持续时间 |
| 增益控件 | `GAIN_AREA_WIDTH` / `GAIN_AREA_HEIGHT` / `GAIN_ARROW_WIDTH` | Max Gain 输入框尺寸 |

---

### 2. `app_state.py` — 运行时可变状态

**作用：** 使用 Python `@dataclass` 集中管理所有运行时可变状态，避免分散的全局变量。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `toast_message` | `str` | `""` | Toast 通知文本 |
| `toast_status` | `str` | `"info"` | Toast 状态：info/success/warning/stop |
| `toast_start_ms` | `int` | `0` | Toast 开始的 pygame ticks |
| `screenshot_number` | `int` | `0` | 截图计数 |
| `is_live` | `bool` | `False` | 实时数据流是否开启 |
| `capture_active` | `str \| None` | `None` | 当前捕获模式 "1"/"2"/"3"/"4" |
| `calib_delay_until` | `float` | `0.0` | 校准延迟启动的时间戳 |
| `max_gain` | `float` | `2000.0` | 当前最大量程 |
| `gain_editing` | `bool` | `False` | 是否正在编辑增益值 |
| `gain_edit_text` | `str` | `""` | 编辑中的文本 |
| `gain_edit_cursor` | `int` | `0` | 编辑光标位置 |
| `gain_dropdown_open` | `bool` | `False` | 增益预设下拉面板是否展开 |
| `cursor_anim_norm` | `float` | `0.0` | 正常增益色条光标值（平滑插值） |
| `cursor_anim_high` | `float` | `0.0` | 高增益色条光标值（平滑插值） |

---

### 3. `animation.py` — 动画工具

**作用：** 帧率无关的颜色/浮点插值，以及单元格动画状态机。

| 名称 | 类型 | 说明 |
|------|------|------|
| `lerp_color(current, target, dt, speed)` | 函数 | 颜色线性插值，返回 `(r, g, b)` |
| `lerp_float(current, target, dt, speed)` | 函数 | 浮点线性插值 |
| `CellAnimState` | 类 | 单单元格动画状态 |
| `CellAnimState.set_target(color, pulse)` | 方法 | 设置目标颜色，`pulse=True` 触发脉冲 |
| `CellAnimState.update(dt)` | 方法 | 每帧更新插值 |
| `clamp(v, lo, hi)` | 函数 | 数值钳制（默认 0–255） |

---

### 4. `background.py` — 背景渲染

**作用：** 创建带噪点和毛玻璃效果的静态背景，以及动态环境光晕。

| 名称 | 类型 | 说明 |
|------|------|------|
| `create_background(size)` | 函数 | 创建暗色噪点 + 霜状覆盖层，仅初始化时调用一次 |
| `draw_background_glow(screen, time_sec)` | 函数 | 每帧绘制两个缓慢漂移的彩色光晕 |

---

### 5. `datastore.py` — 数据存储与校准

**作用：** 线程安全地存储 8×8 传感器数据，支持校准（背景减去）。

| 名称 | 类型 | 说明 |
|------|------|------|
| `DataStore` | 类 | 数据存储核心 |
| `DataStore.add_row(values)` | 方法 | 添加一行传感器数据（8 个 int），逐行填充 |
| `DataStore.start_calibration()` | 方法 | 开始校准：重置缓冲并采集 200 帧后自动计算背景 |
| `DataStore.cancel_calibration()` | 方法 | 取消进行中的校准 |
| `DataStore.reset_calibration()` | 方法 | 重置校准数据为零，恢复未校准状态 |
| `DataStore.clear_data()` | 方法 | 清空所有数据 |
| `DataStore.fill_gradient()` | 方法 | 填充 +max → −max 对角渐变（无串口时的默认显示） |
| `DataStore.get_snapshot()` | 方法 | 线程安全获取 `(data, data_calib, is_calibrated)` |
| `DataStore.get_calib_progress()` | 方法 | 返回校准进度 0.0–1.0 |
| `DataStore.print_calib_data()` | 方法 | 打印校准数据到控制台 |

---

### 6. `serial_reader.py` — 串口通信

**作用：** 管理串口连接，后台线程读取传感器数据并写入 DataStore。

| 名称 | 类型 | 说明 |
|------|------|------|
| `SerialReader(datastore)` | 类 | 构造函数接收 DataStore 实例 |
| `SerialReader.connect(port=None)` | 方法 | 自动扫描并连接；`port` 为 `None` 时用第一个端口 |
| `SerialReader.write(cmd)` | 方法 | 向串口写入单字符命令（如 `"L"`、`"S"`） |
| `SerialReader.close()` | 方法 | 停止读取线程并关闭串口 |
| `SerialReader.ser` | 属性 | 底层 `serial.Serial` 对象（`None` 表示未连接） |

**协议：** 每行数据为空格分隔的 8 个数值，如 `"100 200 150 ..."`

---

### 7. `layout.py` — 按钮布局构建器

**作用：** 根据 `config.BUTTON_SECTIONS` 配置自动生成按钮 rect 列表，支持三种布局模式。

| 名称 | 类型 | 说明 |
|------|------|------|
| `build_buttons()` | 函数 | 生成按钮列表，每个按钮含 rect/label/action/section/icon |
| `build_gain_rect(buttons)` | 函数 | 在按钮列表底部构建 Max Gain 输入框矩形 |
| `build_auto_gain_rect(gain_rect)` | 函数 | 在增益输入框下方构建自动增益按钮矩形 |

**布局模式：**

| 模式 | 说明 | 用例 |
|------|------|------|
| `mode` | 两个按钮并排，各占半宽 | 实时/停止 |
| `grid2x2` | 2×2 网格布局 | 高速捕获频率选择 |
| `stack` | 全宽竖排堆叠 | 校准/重置/清空/截图 |

---

### 8. `actions.py` — 动作分发

**作用：** 集中管理所有用户交互逻辑，将 UI 事件与数据层解耦。

| 名称 | 类型 | 说明 |
|------|------|------|
| `show_toast(state, message, status)` | 函数 | 显示 Toast 通知，status 决定圆点颜色 |
| `handle_action(state, action, datastore, serial_reader, screen)` | 函数 | 分发按钮动作（截图/清空/实时/捕获/校准） |
| `handle_gain_keydown(event, state)` | 函数 | 处理 Max Gain 输入框的键盘编辑（Enter/Esc/方向键等） |
| `handle_gain_click(vx, vy, state, gain_rect, gain_regions)` | 函数 | 处理 Max Gain 区域的鼠标点击，返回是否已消费 |
| `handle_auto_gain(state, datastore)` | 函数 | 自动检测正常增益网格最大值，调整为 115% |

---

### 9. `renderer.py` — 渲染器

**作用：** 核心可视化：网格热力图、标题、垂直渐变色条、单元格悬停提示。

| 名称 | 类型 | 说明 |
|------|------|------|
| `draw_grid(screen, data, data_calib, is_calibrated, grid_left, grid_top, gain_normal, gain_calib, max_value, cell_states, mouse_pos, font)` | 函数 | 绘制 8×8 网格。行号在左侧（从上到下 7→0），列号在下方。返回悬停 `(row, col)` 或 `None` |
| `draw_grid_label(screen, font, text, grid_center_x, grid_top)` | 函数 | 在网格上方居中绘制标题 |
| `draw_color_bar_v(screen, font, left, top, height, gain, max_value, labels_left)` | 函数 | 绘制垂直渐变色条（上绿下红），刻度值由 max_value 动态生成 |
| `draw_cell_tooltip(screen, font, row, col, value, cell_rect)` | 函数 | 在悬停单元格旁绘制毛玻璃提示框 |

**颜色映射：** 正值 → 绿色，负值 → 红色，零 → 黑色。`gain_normal`/`gain_calib` 控制颜色强度，`max_value` 控制归一化范围。

---

### 10. `ui_components.py` — UI 组件

**作用：** 可复用的 UI 组件：毛玻璃按钮、Toast 通知、状态栏、Max Gain 输入、分组标题。

| 名称 | 类型 | 说明 |
|------|------|------|
| `draw_button(screen, rect, text, font, hover, press_flash, active, icon, progress)` | 函数 | 毛玻璃按钮。`active` 高亮为柔绿色；`icon` 支持 `"play"`（三角）/ `"stop"`（方框）；`progress` 0–1 显示底部细进度条 |
| `draw_toast(screen, font, message, elapsed_ms)` | 函数 | Toast 通知。自动处理滑入/停留/淡出动画 |
| `draw_status_bar(screen, font, com_info, is_live, fps, time_sec)` | 函数 | 底部状态栏：COM 端口 + Live 指示灯（脉冲动画）+ FPS |
| `draw_gain_input(screen, font, rect, value, editing, edit_text, cursor_pos, mouse_pos)` | 函数 | Max Gain 输入控件，返回 `{"up": rect, "down": rect, "value": rect}` |
| `draw_section_header(screen, font, text, x, y)` | 函数 | 绘制右侧栏分组标题 |

**Toast 动画阶段：**
1. **0–260ms**：滑入 + 淡入
2. **260–1500ms**：稳定显示
3. **1500–1760ms**：指数淡出

---

### 11. `main.py` — 主入口

**作用：** 程序入口，负责：
- 初始化 pygame 窗口（锁定 17:9 比例）、虚拟画布（2× 超采样）、字体
- 构建右侧三组按钮布局 + Max Gain 输入控件
- 处理鼠标/键盘事件（仅 Space 键切换实时/停止）
- 每帧渲染：背景 → 光晕 → 侧边栏 → 网格 → 颜色条 → 按钮 → 状态栏 → Toast → 缩放输出
- 管理动画状态、FPS 平滑、校准延迟与取消逻辑

**交互说明：**

| 操作 | 效果 |
|------|------|
| 点击 ◀ 实时 | 进入实时数据流模式（按钮高亮绿） |
| 点击 ■ 停止 | 停止数据流 |
| Space 键 | 切换 实时/停止 |
| 点击 2 kHz / 1 kHz / 500 Hz / 250 Hz | 高速捕获（自动退出实时模式，按钮高亮） |
| 点击 校准 | 等待 1 秒后开始校准（按钮高亮 + 进度条） |
| Hover 校准中 | 文字变为"取消校准"，点击取消 |
| 点击 重置校准 | 恢复未校准状态 |
| 点击 清空 | 清空数据阵列 |
| 点击 截图 | 保存画面和数据到 `screenshots/时间戳/` 文件夹 |
| Max Gain ▲/▼ | 增减最大量程 |
| 点击 Max Gain 数值 | 直接输入，Enter 生效，Esc 取消 |

**窗口特性：** 拖动窗口时宽度决定高度，始终保持 1700×900 (17:9) 比例，最小宽度 400px。

**截图文件结构：**
```
screenshots/
├── 2026-04-29_14-30-25/
│   ├── screenshot.png   # 当前画面
│   └── data.txt         # 8×8 原始数据（含校准值）
```

---

## 依赖库总览

| 库 | 用途 | 使用文件 |
|----|------|---------|
| `pygame` | 窗口、渲染、事件处理 | `main.py`、`background.py`、`renderer.py`、`ui_components.py`、`layout.py` |
| `serial` (pyserial) | 串口通信 | `serial_reader.py` |
| `threading` | 后台串口读取、数据锁 | `serial_reader.py`、`datastore.py` |
| `dataclasses` | 状态容器（dataclass 装饰器） | `app_state.py` |
| `math` | 三角函数（光晕/脉冲动画） | `background.py`、`ui_components.py` |
| `random` | 背景噪点生成 | `background.py` |
| `time` | 计时 | `main.py`、`actions.py`、`serial_reader.py` |
| `datetime` | 截图文件夹时间戳 | `actions.py` |
| `os` | 截图文件夹创建 | `actions.py` |
| `sys` | 程序退出 | `main.py` |
| `ctypes` | Windows DPI 感知 | `main.py` |

---

## 快速修改指南

- **改字体：** 编辑 `config.py` 第 5 行 `FONT_NAME`
- **改初始量程：** 编辑 `config.py` 中 `MAX_VALUE`（运行时可通过 Max Gain 控件调整）
- **改配色：** 编辑 `config.py` 中 `COLOR_*` 常量
- **改串口波特率：** 编辑 `config.py` 中 `BAUD_RATE`
- **改 Toast 持续时间：** 编辑 `config.py` 中 `TOAST_DURATION_MS` / `TOAST_FADE_MS`
- **改增益系数：** 编辑 `main.py` 中 `NORM_GAIN` (500) / `HIGH_GAIN` (1500)
- **改校准帧数：** 编辑 `config.py` 中 `MAX_CALIB_FRAMES`
- **改按钮布局：** 编辑 `config.py` 中 `BUTTON_SECTIONS` 列表
- **改增益预设值：** 编辑 `config.py` 中 `GAIN_PRESETS` 列表
- **改增益推荐值：** 编辑 `config.py` 中 `GAIN_PRESET_RECOMMENDED`
- **改动画速度：** 编辑 `config.py` 中 `ANIM_SPEED`
- **改鼠标悬停颜色：** 编辑 `config.py` 中 `SIDEBAR_WIDTH`

## 架构概述

```
┌──────────────────────────────────────────────────────┐
│                    main.py (入口)                     │
│  主循环：事件处理 → 动画更新 → 渲染管线                │
├──────────────────────────────────────────────────────┤
│  app_state.py    config.py      animation.py         │
│  (运行时状态)     (全局常量)      (插值/颜色工具)       │
├─────────────┬────────────────┬───────────────────────┤
│  renderer.py │ ui_components │ layout.py + actions.py│
│  (网格/色条)  │ (按钮/Toast)   │ (布局构建+动作分发)    │
├─────────────┴────────────────┴───────────────────────┤
│  datastore.py          serial_reader.py              │
│  (数据存储+校准)         (串口后台线程)                 │
└──────────────────────────────────────────────────────┘
```
