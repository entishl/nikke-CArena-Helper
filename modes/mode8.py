# modes/mode8.py
import time
import os

from core import utils as core_utils
from core import match_processing
# Constants will be accessed via context.shared.constants

# Removed _get_pixel_color_for_mode as it's now in core_utils.get_pixel_color_relative

def run(context):
    logger = context.shared.logger
    nikke_window = context.shared.nikke_window
    cc = context.shared.constants
    mode_config = context.mode_config

    logger.info("===== 运行模式 8: Reviewer 冠军赛截图 =====")

    if not nikke_window:
        logger.error("Mode8: NIKKE 窗口未找到或未激活。")
        return

    base_name_from_config = getattr(mode_config, 'm8_file_prefix', 'champion_tournament')
    output_suffix = getattr(mode_config, 'm8_output_suffix', '_champ_matches') # 使用 mode_config 中的后缀
    file_prefix_base = f"{base_name_from_config}{output_suffix}"
    logger.info(f"Mode8: 将使用文件名前缀基准: {file_prefix_base}")

    # For Champion mode, MATCH_NAMES might be the same, but entry points differ.
    # We will use R_M8_MATCH_KEY_MAP to map standard match names to M8 specific keys if needed.
    match_names_to_process = cc.R_MATCH_NAMES 
    total_matches_overall = len(match_names_to_process)
    completed_matches_overall = 0
    
    if core_utils.check_stop_signal(context):
        logger.info("Mode8: 检测到停止信号，在开始处理前退出。")
        return

    logger.info(f"\n====== Mode8: 开始处理冠军赛: {file_prefix_base} ======")

    # 使用结构化的颜色判断常量
    color_logic_cfg = cc.R_M8_4IN2_COLOR_LOGIC_CONFIG
    color_check_coord1_rel = color_logic_cfg['check_point1']
    color_check_coord2_rel = color_logic_cfg['check_point2']
    
    # 默认点击目标
    targets = color_logic_cfg['click_targets_default']
    
    logger.info(f"Mode8: 执行颜色判断 for {file_prefix_base}: Coord1={color_check_coord1_rel}, Coord2={color_check_coord2_rel}")
    
    color1_rgb = core_utils.get_pixel_color_relative(context, nikke_window, color_check_coord1_rel) # nikke_window is still needed by get_pixel_color_relative
    if core_utils.check_stop_signal(context): return
    color2_rgb = core_utils.get_pixel_color_relative(context, nikke_window, color_check_coord2_rel) # nikke_window is still needed by get_pixel_color_relative
    if core_utils.check_stop_signal(context): return

    if color1_rgb and color2_rgb:
        b1, b2 = color1_rgb[2], color2_rgb[2] # 比较蓝色值
        logger.info(f"Mode8: 颜色比较 for {file_prefix_base}: B1={b1} (from {color_check_coord1_rel}), B2={b2} (from {color_check_coord2_rel})")
        if b2 > b1:
            logger.info(f"Mode8: {file_prefix_base} - 第二个颜色点 ({color_check_coord2_rel}) 的蓝色值更高。调整点击目标。")
            targets = color_logic_cfg['click_targets_color2_dominant']
        else:
            logger.info(f"Mode8: {file_prefix_base} - 第一个颜色点 ({color_check_coord1_rel}) 的蓝色值更高或相等。使用默认点击目标。")
    else:
        logger.warning(f"Mode8: {file_prefix_base} - 无法获取一个或两个颜色点进行比较。将使用默认点击目标。")

    final_target_4in2_1_rel = targets['4in2_1']
    final_target_4in2_2_first_rel = targets['4in2_2_first']
    final_target_2in1_rel = targets['2in1']
    actual_click_4in2_2_second_rel = color_logic_cfg['4in2_2_second_click'] # 这个是固定的

    logger.info(f"Mode8: {file_prefix_base} - 最终计算的点击入口: "
                f"4in2_1={final_target_4in2_1_rel}, "
                f"4in2_2_first={final_target_4in2_2_first_rel}, "
                f"4in2_2_second={actual_click_4in2_2_second_rel}, "
                f"2in1={final_target_2in1_rel}")

    for match_idx, match_name_std in enumerate(match_names_to_process): # match_name_std is like "8in4_1", "4in2_1"
        if core_utils.check_stop_signal(context):
            logger.info(f"Mode8: 检测到停止信号，在处理比赛 {match_name_std} (冠军赛) 前退出。")
            return

        # Map standard match name to Mode 8 specific key if necessary
        m8_match_key = cc.R_M8_MATCH_KEY_MAP.get(match_name_std, match_name_std)
        logger.info(f"\nMode8: -- 开始处理比赛: {file_prefix_base}_{match_name_std} (using key: {m8_match_key}) --")
        
        match_specific_entry_coord_rel = None
        match_specific_second_entry_coord_rel = None

        if match_name_std.startswith("8in4"):
            match_specific_entry_coord_rel = cc.R_M8_MATCH_8IN4_ENTRIES_REL.get(m8_match_key)
        elif match_name_std == "4in2_1":
            match_specific_entry_coord_rel = final_target_4in2_1_rel # This was already determined using M8 constants
        elif match_name_std == "4in2_2":
            match_specific_entry_coord_rel = final_target_4in2_2_first_rel # Determined using M8 constants
            match_specific_second_entry_coord_rel = actual_click_4in2_2_second_rel # Specific M8 constant
        elif match_name_std == "2in1":
            match_specific_entry_coord_rel = final_target_2in1_rel # Determined using M8 constants
        
        if not match_specific_entry_coord_rel:
            logger.error(f"Mode8: 未能确定比赛 {match_name_std} (key: {m8_match_key}) 的入口坐标。跳过此比赛。")
            continue

            # --- 点击比赛入口 ---
            logger.info(f"Mode8: 点击比赛 '{match_name_std}' 入口 at {match_specific_entry_coord_rel}")
            if not core_utils.click_coordinates(context, match_specific_entry_coord_rel, nikke_window):
                logger.error(f"Mode8: 点击比赛 '{match_name_std}' 入口失败。跳过此比赛。")
                continue
            
            # 使用新的延迟常量 R_M8_DELAY_AFTER_MATCH_ENTRY (字典)
            delay_after_entry = cc.R_M8_DELAY_AFTER_MATCH_ENTRY.get(m8_match_key, cc.R_DELAY_DEFAULT_AFTER_MATCH_ENTRY)
            logger.info(f"Mode8: 等待 {delay_after_entry} 秒...")
            time.sleep(delay_after_entry)
            if core_utils.check_stop_signal(context): return

            if match_specific_second_entry_coord_rel:
                logger.info(f"Mode8: 点击比赛 '{match_name_std}' 第二入口 at {match_specific_second_entry_coord_rel}")
                if not core_utils.click_coordinates(context, match_specific_second_entry_coord_rel, nikke_window):
                    logger.error(f"Mode8: 点击比赛 '{match_name_std}' 第二入口失败。跳过此比赛。")
                    continue
                # 使用新的延迟常量 R_M8_DELAY_AFTER_SECOND_MATCH_ENTRY
                delay_after_second_entry = cc.R_M8_DELAY_AFTER_SECOND_MATCH_ENTRY if match_name_std == "4in2_2" else 0
                if delay_after_second_entry > 0:
                    logger.info(f"Mode8: 等待 {delay_after_second_entry} 秒...")
                    time.sleep(delay_after_second_entry)
                if core_utils.check_stop_signal(context): return

            # --- 调用核心比赛处理流程 ---
            # 直接使用常量，移除 getattr (根据用户确认，模式8使用通用常量)
            success = match_processing.process_match_flow(
                context=context,
                file_prefix=f"{file_prefix_base}_{match_name_std.replace(' ', '_')}",
                match_name=match_name_std, # Use standard name for file naming consistency
                p1_entry_rel=cc.R_PLAYER1_ENTRY_REL,
                p2_entry_rel=cc.R_PLAYER2_ENTRY_REL,
                result_region_rel=cc.R_RESULT_REGION_REL,
                close_result_rel=cc.R_CLOSE_RESULT_REL,
                player_info_regions_config=cc.R_PLAYER_INFO_CONFIG_SEQ, # 直接使用通用常量
                team_button_coords_rel=cc.R_TEAM_BUTTONS_REL, # 直接使用通用常量
                team_screenshot_region_rel=cc.R_TEAM_SCREENSHOT_REGION_REL, # 直接使用通用常量
                close_player_view_coord_rel=cc.R_CLOSE_TEAMVIEW_REL # 或 R_EXIT_PLAYER_VIEW_REL，它们是等效的
            )

        if success:
            completed_matches_overall += 1
            logger.info(f"Mode8: 比赛 {file_prefix_base}_{match_name_std} 处理成功。")
            logger.info(f"Mode8: 冠军赛进度: {completed_matches_overall}/{total_matches_overall} ({completed_matches_overall/total_matches_overall:.1%})")
        else:
            logger.error(f"Mode8: 处理比赛 {file_prefix_base}_{match_name_std} 失败或被中断。")
            if core_utils.check_stop_signal(context):
                logger.info("Mode8: 因停止信号，中止处理冠军赛。")
                return

        if core_utils.check_stop_signal(context):
            logger.info(f"Mode8: 检测到停止信号，完成比赛 {match_name_std} (冠军赛) 后退出。")
            return
        
        if match_idx < len(match_names_to_process) - 1:
             time.sleep(cc.R_M8_DELAY_BETWEEN_MATCHES) # 使用新的常量

    logger.info(f"====== Mode8: 完成处理冠军赛: {file_prefix_base} ======")
    if completed_matches_overall == total_matches_overall:
        logger.info(f"Mode8: 冠军赛所有 {total_matches_overall} 场比赛均已成功处理。")
    else:
        logger.warning(f"Mode8: 冠军赛完成了 {completed_matches_overall} / {total_matches_overall} 场比赛。")
    
    logger.info("===== 模式 8: Reviewer 冠军赛截图 执行完毕 =====")