# Magnetic Imager Tile v3

8×8 磁传感器阵列实时可视化程序，基于 Pygame 构建。

## 功能特性

- **双网格热力图** — 同时显示正常增益和高增益两种模式
- **实时数据流** — 通过串口读取传感器数据，支持 250 Hz ~ 2 kHz 采样率
- **校准系统** — 背景减去校准，200 帧自动采集
- **毛玻璃 UI** — 深色科技风界面，带毛玻璃效果和动画
- **截图导出** — 一键保存画面和原始数据

## 快速开始

### 依赖

```bash
pip install pygame pyserial
```

### 运行

```bash
python main.py
```

### 硬件连接

将 8×8 磁传感器阵列通过 USB 串口连接电脑，程序会自动扫描并连接。

## 操作说明

| 操作 | 效果 |
|------|------|
| ◀ 实时 / ■ 停止 | 切换实时数据流 |
| `Space` 键 | 快捷切换实时/停止 |
| 2k / 1k / 500 / 250 | 高速捕获模式 |
| 校准 | 1 秒延迟后开始校准（200 帧） |
| 重置校准 | 恢复未校准状态 |
| 截图 | 保存画面和数据到 `screenshots/` |
| Max Gain ▲/▼ | 调整量程 |
| `F11` | 全屏切换 |

## 项目结构

```
Magnetic_Imager/
├── main.py            # 主入口：主循环、事件处理、渲染管线
├── config.py          # 全局常量与配置
├── app_state.py       # 运行时状态（dataclass）
├── animation.py       # 动画工具（插值、脉冲）
├── background.py      # 背景渲染（噪点 + 毛玻璃 + 光晕）
├── datastore.py       # 数据存储与校准（线程安全）
├── serial_reader.py   # 串口通信（后台线程）
├── renderer.py        # 网格热力图、色条、悬停提示
├── ui_components.py   # UI 组件（按钮、Toast、状态栏）
├── layout.py          # 按钮布局构建器
├── actions.py         # 动作分发
├── projecttest.pde    # 原始 Processing 草图（参考）
├── Image/             # ESP32-S3 固件（PlatformIO 项目）
│   ├── src/main.cpp   # 传感器读取、SPI 通信、串口输出
│   └── platformio.ini # ESP32-S3-DevKitC-1 配置
└── docs/              # 项目文档
```

## ESP32 固件

`Image/` 目录包含 ESP32-S3 的固件代码，负责从 8×8 磁传感器阵列采集数据。

### 硬件

- **MCU** — ESP32-S3-DevKitC-1
- **ADC** — AD7680（16-bit SPI SAR ADC）
- **传感器** — DRV5053 霍尔效应传感器（±9 mT）
- **采样率** — 921600 baud 串口输出

### 工作模式

| 模式 | 说明 |
|------|------|
| IDLE | 空闲，等待指令 |
| LIVE | 实时逐帧输出 |
| HIGH SPEED 1-4 | 高速批量采集（多帧缓冲） |
| PIXEL | 单像素调试模式 |
| VERIFY | 校验模式 |

### 编译烧录

```bash
cd Image
pio run -t upload
```

## 配置

编辑 `config.py` 可调整：

- **字体** — `FONT_NAME`（默认 SimHei）
- **串口波特率** — `BAUD_RATE`（默认 921600）
- **配色方案** — `COLOR_*` 系列常量
- **量程范围** — `MAX_VALUE`（DRV5053 饱和值 ±9 mT）
- **校准帧数** — `MAX_CALIB_FRAMES`（默认 50）

## 界面预览

左侧双网格显示磁场分布，右侧控制面板管理运行模式，底部状态栏显示串口信息和 FPS。

## License

MIT
