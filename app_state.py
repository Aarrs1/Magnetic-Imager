# -*- coding: utf-8 -*-
"""
应用全局可变状态

使用 @dataclass 集中管理所有运行时可变状态，避免分散的全局变量。
所有字段均有默认值，程序启动时通过 AppState() 创建初始实例。
"""

from dataclasses import dataclass, field


@dataclass
class AppState:
    """运行时可变状态容器。

    包含：Toast 通知状态、截图计数、实时/捕获模式标志、
    校准延迟、Max Gain 编辑状态、色条光标动画值。
    """
    # Toast 通知
    toast_message: str = ""
    toast_status: str = "info"       # "info" / "success" / "warning" / "stop"
    toast_start_ms: int = 0

    # 初始横幅（点击实时后自动消失）
    banner_visible: bool = True

    # 截图
    screenshot_number: int = 0

    # 运行模式
    is_live: bool = False            # 实时数据流开启
    capture_active: str | None = None  # 当前捕获模式 "1"/"2"/"3"/"4"，None 表示无

    # 校准
    calib_delay_until: float = 0.0   # 延迟启动校准的时间戳（秒）

    # Max Gain 编辑
    max_gain: float = 20.0          # 当前最大量程 mT（运行时动态调整）
    gain_editing: bool = False       # 是否正在编辑增益值
    gain_edit_text: str = ""         # 编辑中的文本
    gain_edit_cursor: int = 0        # 编辑光标位置
    gain_dropdown_open: bool = False # 预设下拉面板是否展开

    # 色条光标动画（平滑插值用）
    cursor_anim_norm: float = 0.0    # 正常增益色条光标值
    cursor_anim_high: float = 0.0    # 高增益色条光标值
