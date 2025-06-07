# 行动计划：简化版延迟可配置化

**目标**: 将三个指定的延迟移至 `config.json`，并通过 `gui_app.py` 提供UI进行调整。

要配置化的延迟项:
1.  `GUI_STARTUP_DELAY` (来自 `gui_app.py`，当前在 `core/constants.py` 中定义为 5.0)
2.  `DEFAULT_INITIAL_DELAY_AFTER_ENTRY` (来自 `core/constants.py`，值为 3.0)
3.  `DEFAULT_DELAY_AFTER_TEAM_CLICK` (来自 `core/constants.py`，值为 1.5)

---

## 第一阶段: 配置中心化

1.  **修改 `config.json`**:
    *   在 `config.json` 中添加一个新的顶级键 `delay_settings`。
    *   在该键下，添加以下三个键值对，并设置默认值：
        *   `gui_startup`: 5.0
        *   `after_player_entry`: 3.0
        *   `after_team_click`: 1.5

2.  **修改 `app.py`**:
    *   在 `SharedResources` 类中添加 `self.delay_config = {}`。
    *   在 `initialize_app_context` 函数中，从加载的 `app_config_data` 中提取 `delay_settings` 部分，并赋值给 `context.shared.delay_config`。如果 `delay_settings` 不存在或缺少键，则使用内置的默认值填充，并记录警告。

3.  **修改 `core/constants.py`**:
    *   删除或注释掉 `GUI_STARTUP_DELAY`, `DEFAULT_INITIAL_DELAY_AFTER_ENTRY`, `DEFAULT_DELAY_AFTER_TEAM_CLICK` 这三行。

---

## 第二阶段: 代码适配

1.  **修改 `gui_app.py`**:
    *   在 `execute_script_thread` 方法中，将 `time.sleep(GUI_STARTUP_DELAY)` 修改为 `time.sleep(self.app_context.shared.delay_config.get('gui_startup', 5.0))`。

2.  **修改 `core/player_processing.py`** (及其他相关文件):
    *   搜索 `DEFAULT_INITIAL_DELAY_AFTER_ENTRY` 和 `DEFAULT_DELAY_AFTER_TEAM_CLICK` 的使用位置。
    *   修改使用这些常量的地方，改为从传入的 `app_context.shared.delay_config` 中获取值。
    *   确保所有调用这些逻辑的函数都传递了 `app_context`。

---

## 第三阶段: GUI交互

1.  **修改 `gui_app.py`**:
    *   在 `create_widgets` 方法的侧边栏 `sidebar_frame` 中，添加三个标签和输入框，分别对应 `gui_startup`, `after_player_entry`, `after_team_click`。
    *   在 `__init__` 方法中，用从 `app_context` 加载的延迟值来设置这些输入框的初始内容。
    *   添加一个“保存延迟设置”按钮。点击该按钮时，会触发一个新方法：
        *   该方法从输入框读取值，验证它们是有效的浮点数。
        *   更新 `self.app_context.shared.delay_config` 中的值。
        *   将 `self.app_context.shared.app_config` (包含了更新后的 `delay_settings`) 完整地写回到 `config.json` 文件。

---

## 流程图

```mermaid
graph TD
    subgraph "配置与加载"
        A[config.json] -- 包含 delay_settings --> B[app.py 加载配置];
        B --> C[app_context];
        C -- 存储 delay_config --> D[共享上下文 a.c.shared];
    end

    subgraph "GUI"
        E[gui_app.py] -- 读取 a.c.shared.delay_config --> F[显示3个延迟输入框];
        F --> G{用户修改值};
        G --> H["点击"保存""];
        H --> I{更新 a.c.shared.delay_config};
        I --> J[写回 config.json];
    end

    subgraph "执行"
        K[gui_app.py] -- 读取 'gui_startup' --> L[启动延迟];
        M[核心处理模块] -- 传入 app_context --> N{读取 'after_player_entry' & 'after_team_click'};
        N --> O[流程步骤延迟];
    end

    D --> E;
    D --> K;
    D --> M;