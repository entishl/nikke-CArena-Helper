# 项目延迟与魔法数字分析总结

## 1. 延迟来源分析

项目中的延迟是**有意为之**的，其主要目的是为了确保自动化脚本在与游戏UI交互时的稳定性和可靠性。延迟主要分为以下几类：

### 1.1. GUI启动延迟
- **来源**: [`gui_app.py:793`](gui_app.py:793)
- **描述**: 在用户点击“启动脚本”后，有一个固定的 **5秒** `time.sleep()`。这是在任何实际游戏操作之前发生的最主要、与用户交互无关的等待。

### 1.2. 核心操作延迟
- **来源**: [`core/utils.py`](core/utils.py)
- **描述**:
    - **点击延迟**: 每次模拟点击后，都会通过 `time.sleep(core_constants.UNIVERSAL_ACTION_DELAY)` ([`core/utils.py:88`](core/utils.py:88)) 固定等待 **1.2秒**。这是最频繁的延迟来源。
    - **窗口与截图延迟**: 在窗口激活、截图等底层操作后，存在多个 **0.1秒 到 1.0秒** 不等的短暂等待，用于确保系统操作完成。

### 1.3. 流程步骤延迟
- **来源**: [`core/player_processing.py`](core/player_processing.py), [`core/match_processing.py`](core/match_processing.py)
- **描述**: 在处理玩家信息、比赛结果等复杂流程中，包含了多个为等待UI响应和动画播放而设置的延迟。这些延迟的值（范围从 **0.3秒 到 3.0秒**）大部分已在 [`core/constants.py`](core/constants.py) 中常量化，并通过函数参数传递。

### 1.4. 模式特定延迟
- **来源**: [`modes/mode6.py`](modes/mode6.py), [`modes/mode7.py`](modes/mode7.py), [`modes/mode8.py`](modes/mode8.py)
- **描述**: 在 Reviewer 相关的模式中，为等待游戏内特定事件（如切换分组、进入比赛）设置了延迟，范围在 **1.0秒 到 5.0秒** 之间。这些值也已在 [`core/constants.py`](core/constants.py) 中常量化。
