# 详细计划：创建 “小组赛模式 (mode 41)”

**目标**：创建一个新的模式，该模式能够：
1.  针对小组赛中的四名指定玩家，分别调用 `collect_player_data` 函数截图其阵容和数据。
2.  将这四张生成的玩家汇总图片（每张图片本身是垂直拼接的）进行水平拼接。
3.  水平拼接时，图片之间间隔50像素，并用黑色填充间隔区域。
4.  最终生成一张包含所有四名玩家信息的大图。

---

## 阶段一：环境与配置准备

### 1. 定义常量 (`core/constants.py`)

在 `core/constants.py` 文件中，添加新的常量来存储小组赛四名玩家的入口相对坐标。这些绝对坐标 (1480,860), (1480,1130), (1480,1400), (1480,1670) 将使用 `_to_rel_coord` 函数转换为相对坐标。

```python
# (在适当的位置，例如其他模式特定坐标附近)
# --- Mode 41 (小组赛模式) 特有入口坐标 ---
_M41_PLAYER1_COORD_ABS = (1480, 860)
_M41_PLAYER2_COORD_ABS = (1480, 1130)
_M41_PLAYER3_COORD_ABS = (1480, 1400)
_M41_PLAYER4_COORD_ABS = (1480, 1670)

M41_PLAYER1_ENTRY_REL = _to_rel_coord(_M41_PLAYER1_COORD_ABS)
M41_PLAYER2_ENTRY_REL = _to_rel_coord(_M41_PLAYER2_COORD_ABS)
M41_PLAYER3_ENTRY_REL = _to_rel_coord(_M41_PLAYER3_COORD_ABS)
M41_PLAYER4_ENTRY_REL = _to_rel_coord(_M41_PLAYER4_COORD_ABS)

M41_PLAYER_ENTRIES_REL = [
    M41_PLAYER1_ENTRY_REL,
    M41_PLAYER2_ENTRY_REL,
    M41_PLAYER3_ENTRY_REL,
    M41_PLAYER4_ENTRY_REL
]
```

### 2. 更新应用配置 (`config.json`)

*   在 `modes_meta` 数组中为 `mode 41` 添加一个新的条目：
    ```json
    // ... (其他 modes_meta 条目) ...
    {
      "id": 41,
      "name": "小组赛模式",
      "desc": "截图小组赛中小组内四名玩家的阵容和数据，并水平拼接。",
      "enabled": true
      // "asset_image": "assets/mode41_icon.png" // 可选
    }
    // ...
    ```
*   在 `mode_specific_defaults` 对象中为 `mode41` 添加默认配置：
    ```json
    // ... (其他 mode_specific_defaults) ...
    "mode41": {
      "output_filename_suffix": "_group_stage_match",
      "player_temp_prefix": "gs_player"
    }
    // ...
    ```

### 3. 更新主应用逻辑 (`app.py`)

*   在 `ModeSpecificConfig` 类中添加 `_load_mode41_config` 方法：
    ```python
    # (在 ModeSpecificConfig 类定义内)
    def _load_mode41_config(self, mode_defaults):
        self.m41_output_suffix = mode_defaults.get('output_filename_suffix', '_group_stage_match')
        self.m41_player_temp_prefix = mode_defaults.get('player_temp_prefix', 'gs_player')
    ```
*   将 `_load_mode41_config` 添加到 `ModeSpecificConfig` 的 `mode_loaders` 字典中：
    ```python
    # (在 ModeSpecificConfig.__init__ 方法内的 mode_loaders 字典)
    mode_loaders = {
        # ... 其他模式 ...
        41: self._load_mode41_config, # 新增
    }
    ```
*   更新 `main` 函数中的模式选择菜单文本，加入 "41: 小组赛模式"。
    ```python
    # (在 main 函数的模式选择打印部分)
    # ... 其他模式打印 ...
    print("  9: 图片处理与打包")
    print("  41: 小组赛模式") # 新增
    print("  0: 退出程序")
    # ...
    ```
*   确保 `main` 函数中的模式编号范围检查逻辑能正确处理新的模式编号 41。

---

## 阶段二：模式实现

### 1. 创建新模式文件 (`modes/mode41.py`)

文件路径: `modes/mode41.py`
内容如下：

```python
# modes/mode41.py
import os
from core import utils as core_utils
from core import player_processing
# 常量将通过 context.shared.constants 访问

def run(context):
    logger = context.shared.logger
    cc = context.shared.constants
    mode_config = context.mode_config

    logger.info("===== 运行模式 41: 小组赛模式 =====")
    context.shared.final_message = "模式41：正在初始化..."

    if core_utils.check_stop_signal(context):
        logger.info("模式41：检测到停止信号，提前退出。")
        context.shared.final_message = "模式41：操作在开始前被用户取消。"
        return

    player_stitched_image_paths = []
    player_entries = getattr(cc, 'M41_PLAYER_ENTRIES_REL', [])

    if not player_entries or len(player_entries) != 4:
        logger.error("模式41: 小组赛玩家入口坐标 M41_PLAYER_ENTRIES_REL 未在 core.constants 中正确定义或数量不为4。")
        context.shared.final_message = "模式41执行失败：内部配置错误（玩家入口坐标）。"
        return

    player_temp_prefix_base = getattr(mode_config, 'm41_player_temp_prefix', 'gs_player')

    try:
        for i, player_entry_rel in enumerate(player_entries):
            player_num = i + 1
            current_player_temp_prefix = f"{player_temp_prefix_base}_{player_num}"
            logger.info(f"模式41: 开始处理玩家 {player_num} (临时文件前缀: {current_player_temp_prefix})...")

            if core_utils.check_stop_signal(context):
                logger.info(f"模式41: 处理玩家 {player_num} 前检测到停止信号。")
                context.shared.final_message = f"模式41：操作在处理玩家 {player_num} 前被用户取消。"
                return

            stitched_path = player_processing.collect_player_data(
                context,
                player_entry_coord_rel=player_entry_rel,
                player_info_regions_config=cc.R_PLAYER_INFO_CONFIG_SEQ,
                team_button_coords_rel=cc.R_TEAM_BUTTONS_REL,
                team_screenshot_region_rel=cc.R_TEAM_SCREENSHOT_REGION_REL,
                close_player_view_coord_rel=cc.R_CLOSE_TEAMVIEW_REL,
                temp_file_prefix=current_player_temp_prefix,
            )

            if not stitched_path:
                logger.error(f"模式41: 处理玩家 {player_num} 数据失败。")
                logger.warning(f"模式41: 将跳过玩家 {player_num} 并尝试继续处理其他玩家。")
                continue

            player_stitched_image_paths.append(stitched_path)
            logger.info(f"模式41: 玩家 {player_num} 数据处理完成，图片路径: {stitched_path}")

            if core_utils.check_stop_signal(context):
                logger.info(f"模式41: 处理玩家 {player_num} 后检测到停止信号。")
                context.shared.final_message = f"模式41：操作在处理玩家 {player_num} 后被用户取消。\n已收集 {len(player_stitched_image_paths)} 张玩家图片。"
                return

        if not player_stitched_image_paths:
             logger.error("模式41: 未能成功收集任何玩家的图片，无法进行最终拼接。")
             context.shared.final_message = "模式41执行失败：未能收集到任何玩家的图片。"
             return
        elif len(player_stitched_image_paths) < 4:
             logger.warning(f"模式41: 仅收集到 {len(player_stitched_image_paths)}/4 张玩家图片。将尝试拼接现有图片。")

        base_name = getattr(context.mode_config, 'output_filename_prefix', 'NCA')
        suffix = getattr(mode_config, 'm41_output_suffix', '_group_stage_match')
        
        timestamp = core_utils.get_timestamp_for_filename() # 假设 core_utils.get_timestamp_for_filename() 存在
        final_output_filename = f"{base_name}{suffix}_{timestamp}.png"

        output_dir_for_mode41 = core_utils.get_or_create_mode_output_subdir(context, 41, "group_stage_matches")
        
        if not output_dir_for_mode41:
            logger.error("模式41: 无法获取或创建输出子目录，中止。")
            context.shared.final_message = "模式41执行失败：无法创建输出目录。"
            return

        final_output_path = os.path.join(output_dir_for_mode41, final_output_filename)
        logger.info(f"模式41: 最终输出文件名将是: {final_output_filename} (在目录: {output_dir_for_mode41})")

        success_stitch = core_utils.stitch_images_horizontally(
            context,
            player_stitched_image_paths,
            final_output_path,
            spacing=50,
            background_color=(0, 0, 0),
            alignment='center'
        )

        if success_stitch:
            msg = f"模式41执行成功！\n小组赛截图已保存到: {final_output_path}"
            if len(player_stitched_image_paths) < 4:
                msg += f"\n注意：仅拼接了 {len(player_stitched_image_paths)} 张有效收集的玩家图片。"
            logger.info(msg)
            context.shared.final_message = msg
        else:
            logger.error(f"模式41: 水平拼接图片失败。")
            context.shared.final_message = f"模式41执行失败：水平拼接图片时发生错误。\n部分玩家图片可能已生成在临时目录中: {context.shared.base_temp_dir}"

    except Exception as e:
        logger.exception(f"模式41执行期间发生未预料的错误: {e}")
        context.shared.final_message = f"模式41执行期间发生严重错误: {e}"
    finally:
        logger.info("模式41执行完毕。")
```

---

## 阶段三：测试与验证 (由开发者执行)

1.  确保 NIKKE 游戏运行在小组赛界面，并且四名玩家的头像位于预期的坐标。
2.  从命令行或通过应用的 GUI (如果已集成) 运行模式 41。
3.  检查日志输出是否有错误。
4.  检查 `output_app/mode41_group_stage_matches/` 目录下是否生成了正确的拼接图片。
5.  验证图片内容是否正确，包括四名玩家的数据和截图，以及它们之间的间隔和背景色。

---

## Mermaid 流程图

```mermaid
graph TD
    A[开始 Mode 41] --> B{检查停止信号};
    B -- 是 --> Z[结束];
    B -- 否 --> C[初始化空列表: player_stitched_images];
    C --> D[获取M41_PLAYER_ENTRIES_REL常量];
    D --> E{常量有效且数量为4?};
    E -- 否 --> F[记录错误: 入口坐标配置错误];
    F --> Z;
    E -- 是 --> G[循环处理4名玩家 (P1, P2, P3, P4)];
    G -- 对每个玩家 --> H{检查停止信号};
    H -- 是 --> Z;
    H -- 否 --> I[准备 collect_player_data 参数];
    I --> J[调用 collect_player_data];
    J --> K{成功获取玩家截图?};
    K -- 否 --> L[记录错误: 处理该玩家失败, 可选: 继续或中止];
    L -- 中止 --> Z;
    L -- 继续 --> G;
    K -- 是 --> M[将截图路径添加到 player_stitched_images];
    M --> N{检查停止信号};
    N -- 是 --> Z;
    N -- 否 --> G;
    G -- 循环结束 --> O{收集到有效图片?};
    O -- 否 --> P[记录错误: 图片数量不足];
    P --> Z;
    O -- 是 --> Q[准备最终输出文件名和路径];
    Q --> R[调用 stitch_images_horizontally (水平拼接)];
    R --> S{拼接成功?};
    S -- 是 --> T[记录成功信息, 设置 final_message];
    S -- 否 --> U[记录错误: 拼接失败, 设置 final_message];
    T --> Z;
    U --> Z;