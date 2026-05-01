# UI Redesign: Cold Blue-Black Glassmorphism
# UI 重设计：冷蓝黑 · 毛玻璃风格

**Date / 日期**: 2026-04-28
**Status / 状态**: Approved / 已确认
**File / 文件**: main.py (~250 lines changed/added)

## Design Decisions / 设计决策

- **Style / 风格**: Modern & Clean glassmorphism / 现代简约毛玻璃 (选项 B)
- **Animation / 动画**: Responsive & Lively micro-interactions / 响应式灵动微交互 (选项 B)
- **Grid cells / 网格单元**: Flat with edge glow, zero gap / 平面风格 + 边缘微光，无间隙 (选项 A)

## Section 1: Layout & Palette / 布局与配色

### Window / 窗口
- 600×600 → **800×560** (safe for 768px screens, height under 650)
- 600×600 → **800×560**（适配 768px 屏幕，高度不超过 650）

### Grids / 网格
- **Side-by-side** (horizontal) instead of stacked — saves vertical space
- **左右并排**（水平布局）替代上下堆叠，节省纵向空间
- Cells: **30px**, **zero gap** (continuous sensor array)
- 单元尺寸：**30px**，**无间隙**（连续传感器阵列）
- Grid panel: frosted glass background with subtle blue border
- 网格底板：毛玻璃背景 + 淡蓝色边框
- Row labels (0–7): left of grid, 8px muted text, external
- 行标签 (0–7)：网格左侧，8px 淡色文字，外部标注
- Col labels (0–7): above grid, 8px muted text, external
- 列标签 (0–7)：网格上方，8px 淡色文字，外部标注

### Sidebar / 侧边栏
- **Right edge** (was left), **145px** wide
- **右侧**（原为左侧），宽度 **145px**
- Frosted glass: `rgba(16,26,38,0.72)` + backdrop blur
- 毛玻璃效果：`rgba(16,26,38,0.72)` + 背景模糊
- All 10 buttons, compact stacked layout
- 全部 10 个按钮，紧凑纵向排列

### Color Bar / 颜色对比条 (NEW / 新增)
- Below grids, **400×18px** horizontal gradient
- 网格下方，**400×18px** 水平渐变条
- Gradient: red → dark void center → green
- 渐变：红色 → 深色零点 → 绿色
- 9 tick marks: −660, −495, −330, −165, 0, +165, +330, +495, +660
- 9 个刻度：−660, −495, −330, −165, 0, +165, +330, +495, +660
- Unit: **f** (center label)
- 单位：**f**（居中标注）
- Direction: S (负场) / N (正场)
- 方向标识：S (负场) / N (正场)
- Frosted card container
- 毛玻璃卡片容器

### Cell Hover Tooltip / 单元格悬停提示 (NEW / 新增)
- Appears on mouse hover over any grid cell
- 鼠标悬停任意网格单元时显示
- Format: `R{row} C{col}  {value} f`
- 格式：`R{行} C{列}  {数值} f`
- Frosted popup, 150ms fade-in, 100ms hover delay
- 毛玻璃弹窗，150ms 淡入，悬停 100ms 后触发
- Follows cell position, not cursor
- 跟随单元格位置，不跟随鼠标光标

### Status Bar / 状态栏 (NEW / 新增)
- Bottom, 22px, frosted: `rgba(8,16,26,0.85)`
- 底部，22px 高，毛玻璃：`rgba(8,16,26,0.85)`
- Left: COM port + baud rate
- 左侧：COM 端口 + 波特率
- Center: Live/Idle indicator (green pulsing dot when live)
- 中间：实时/空闲指示灯（实时模式下绿色脉冲圆点）
- Right: FPS counter
- 右侧：FPS 帧率计数器

### Color Palette / 配色表
| Role / 用途 | Value / 色值 |
|-------------|-------------|
| Deep Void / 深空背景 | `#0D1520` |
| Sidebar / 侧边栏 | `#162230` |
| Panel BG / 面板背景 | `#1E2E40` |
| Accent / 强调色 | `#587898` |
| Text / 文字 | `#E0E8F2` |
| Text Muted / 淡色文字 | `#7A95B5` |

## Section 2: Animations & Interactions / 动画与交互

| Element / 元素 | Trigger / 触发 | Duration / 时长 | Easing / 缓动 |
|---------------|---------------|----------------|--------------|
| Button hover / 按钮悬停 | mouse enter | 200ms | ease-out |
| Button press flash / 按钮点击 | click | 150ms | ease-out |
| Cell hover outline / 单元格悬停 | mouse enter | 150ms | ease-out |
| Cell value pulse / 数据更新 | data update | 300ms | ease-out + overshoot |
| Toast slide in / 提示滑入 | action | 260ms | ease-out + bounce |
| Toast fade out / 提示淡出 | after ~1.2s | 260ms | ease-in |
| Tooltip appear / 提示出现 | hover (100ms delay) | 150ms | ease-out |
| Status dot pulse / 状态脉冲 | continuous (live) | 2s cycle | sinusoidal |
| Background glow drift / 背景光晕漂移 | continuous | 8s cycle | sinusoidal |

### Implementation / 实现方式
- Lerp-based animation: `current += (target - current) * speed * dt`
- 基于线性插值的动画：`current += (target - current) * speed * dt`
- Frame-rate independent
- 帧率无关
- Cell pulse states: 8×8 dict of `{target_rgb, current_rgb, timer}`
- 单元格脉冲状态：8×8 字典 `{target_rgb, current_rgb, timer}`
- No external dependencies — pure Pygame surfaces + math
- 无外部依赖 — 纯 Pygame surface + 数学运算
- ~60 lines for animation logic
- 动画逻辑约 60 行

## Backward Compatibility / 向后兼容
- All key bindings preserved (L, S, H, 1-4, C, D, A, Space)
- 所有按键绑定保持不变（L, S, H, 1-4, C, D, A, 空格）
- All serial communication logic unchanged
- 所有串口通信逻辑不变
- DataStore and SerialReader classes unchanged
- DataStore 和 SerialReader 类不变
- Font loading unchanged (SimHei)
- 字体加载不变（SimHei 黑体）
- Only the render functions and constants change
- 仅渲染函数和常量发生变化
