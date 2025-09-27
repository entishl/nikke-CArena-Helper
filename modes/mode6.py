# modes/mode6.py
import time
import os # For path joining if needed, though utils should handle it
import copy # 导入copy模块

from core import utils as core_utils
from core import match_processing
# Constants will be accessed via context.shared.constants

def run(context):
    logger = context.shared.logger
    nikke_window = context.shared.nikke_window
    cc = context.shared.constants
    mode_config = context.mode_config  # 获取模式特定配置

    logger.info("===== 运行模式 6: Reviewer 完整分组赛 =====")

    if not nikke_window:
        logger.error("Mode6: NIKKE 窗口未找到或未激活。")
        return

    # 从 mode_config 获取分组范围和文件前缀
    start_group_idx = getattr(mode_config, 'm6_start_group', 0)  # 0-indexed
    end_group_idx = getattr(mode_config, 'm6_end_group', 7)      # 0-indexed, inclusive
    group_file_prefix_base = getattr(mode_config, 'm6_group_prefix', 'Group')

    # 确保索引在合理范围内 (假设分组按钮键是 group_1 到 group_8)
    # 最大组数是8 (索引7)。
    num_total_groups_available = cc.R_NUM_TOTAL_GROUPS # 使用常量
    start_group_idx = max(0, min(start_group_idx, num_total_groups_available - 1))
    end_group_idx = max(start_group_idx, min(end_group_idx, num_total_groups_available - 1))
    
    groups_to_process_config_indices = range(start_group_idx, end_group_idx + 1)
    
    # 确保 R_MATCH_NAMES 在常量中定义 (已在 core/constants.py 中添加)
    total_matches_overall = len(cc.R_MATCH_NAMES) * len(list(groups_to_process_config_indices))
    completed_matches_overall = 0

    for group_config_idx in groups_to_process_config_indices: # group_config_idx is 0-indexed
        group_actual_number = group_config_idx + 1 # 1-indexed for display and keys

        if core_utils.check_stop_signal(context):
            logger.info(f"Mode6: 检测到停止信号，在处理组 {group_actual_number} (索引 {group_config_idx}) 前退出。")
            return
        
        current_group_file_prefix = f"{group_file_prefix_base}{group_actual_number}"
        logger.info(f"\n====== Mode6: 开始处理组: {current_group_file_prefix} (索引 {group_config_idx}) ======")

        group_button_key = f"group_{group_actual_number}" # Key for R_GROUP_BUTTONS_REL
        group_button_coord_rel = cc.R_GROUP_BUTTONS_REL.get(group_button_key)
        if not group_button_coord_rel:
            logger.error(f"Mode6: 未找到组别 {group_actual_number} (键: {group_button_key}) 的坐标，跳过该组。")
            continue
        
        logger.info(f"Mode6: 点击组别 {group_actual_number} 按钮 at {group_button_coord_rel}...")
        if not core_utils.click_coordinates(context, group_button_coord_rel, nikke_window):
            logger.error(f"Mode6: 点击组别 {group_actual_number} 按钮失败，跳过该组。")
            continue
        time.sleep(cc.R_DELAY_AFTER_GROUP_CLICK) # 使用常量

        if core_utils.check_stop_signal(context):
            logger.info(f"Mode6: 检测到停止信号，在点击组 {group_actual_number} 后退出。")
            return
        
        # 使用结构化的颜色判断常量
        color_logic_cfg = cc.R_4IN2_COLOR_LOGIC_CONFIG
        color_check_coord1_rel = color_logic_cfg['check_point1']
        color_check_coord2_rel = color_logic_cfg['check_point2']
        
        # 默认点击目标
        targets = color_logic_cfg['click_targets_default']
        
        logger.info(f"Mode6: 执行颜色判断 for {current_group_file_prefix}: Coord1={color_check_coord1_rel}, Coord2={color_check_coord2_rel}")
        
        color1_rgb = core_utils.get_pixel_color_relative(context, nikke_window, color_check_coord1_rel)
        if core_utils.check_stop_signal(context): return
        color2_rgb = core_utils.get_pixel_color_relative(context, nikke_window, color_check_coord2_rel)
        if core_utils.check_stop_signal(context): return

        if color1_rgb and color2_rgb:
            b1, b2 = color1_rgb[2], color2_rgb[2] # 比较蓝色值
            logger.info(f"Mode6: 颜色比较 for {current_group_file_prefix}: B1={b1} (from {color_check_coord1_rel}), B2={b2} (from {color_check_coord2_rel})")
            if b2 > b1:
                logger.info(f"Mode6: {current_group_file_prefix} - 第二个颜色点 ({color_check_coord2_rel}) 的蓝色值更高。调整点击目标。")
                targets = color_logic_cfg['click_targets_color2_dominant']
            else:
                logger.info(f"Mode6: {current_group_file_prefix} - 第一个颜色点 ({color_check_coord1_rel}) 的蓝色值更高或相等。使用默认点击目标。")
        else:
            logger.warning(f"Mode6: {current_group_file_prefix} - 无法获取一个或两个颜色点进行比较。将使用默认点击目标。")

        final_target_4in2_1_rel = targets['4in2_1']
        final_target_4in2_2_first_rel = targets['4in2_2_first']
        final_target_2in1_rel = targets['2in1']
        actual_click_4in2_2_second_rel = color_logic_cfg['4in2_2_second_click'] # 这个是固定的

        logger.info(f"Mode6: {current_group_file_prefix} - 最终计算的点击入口: "
                    f"4in2_1={final_target_4in2_1_rel}, "
                    f"4in2_2_first={final_target_4in2_2_first_rel}, "
                    f"4in2_2_second={actual_click_4in2_2_second_rel}, "
                    f"2in1={final_target_2in1_rel}")

        for match_idx, match_name in enumerate(cc.R_MATCH_NAMES):
            if core_utils.check_stop_signal(context):
                logger.info(f"Mode6: 检测到停止信号，在处理比赛 {match_name} (组 {group_actual_number}) 前退出。")
                return

            logger.info(f"\nMode6: -- 开始处理比赛: {current_group_file_prefix}_{match_name} --")
            
            match_specific_entry_coord_rel = None
            match_specific_second_entry_coord_rel = None 

            if match_name.startswith("8in4"):
                match_specific_entry_coord_rel = cc.R_MATCH_8IN4_ENTRIES_REL.get(match_name)
            elif match_name == "4in2_1":
                match_specific_entry_coord_rel = final_target_4in2_1_rel
            elif match_name == "4in2_2":
                match_specific_entry_coord_rel = final_target_4in2_2_first_rel
                match_specific_second_entry_coord_rel = actual_click_4in2_2_second_rel
            elif match_name == "2in1":
                match_specific_entry_coord_rel = final_target_2in1_rel
            
            if not match_specific_entry_coord_rel:
                logger.error(f"Mode6: 未能确定比赛 {match_name} 的入口坐标。跳过此比赛。")
                continue

            # --- 点击比赛入口 ---
            logger.info(f"Mode6: 点击比赛 '{match_name}' 入口 at {match_specific_entry_coord_rel}")
            if not core_utils.click_coordinates(context, match_specific_entry_coord_rel, nikke_window):
                logger.error(f"Mode6: 点击比赛 '{match_name}' 入口失败。跳过此比赛。")
                continue
            
            delay_after_entry = cc.R_DELAY_AFTER_MATCH_ENTRY.get(match_name, cc.R_DELAY_DEFAULT_AFTER_MATCH_ENTRY)
            logger.info(f"Mode6: 等待 {delay_after_entry} 秒...")
            time.sleep(delay_after_entry)
            if core_utils.check_stop_signal(context): return

            if match_specific_second_entry_coord_rel:
                logger.info(f"Mode6: 点击比赛 '{match_name}' 第二入口 at {match_specific_second_entry_coord_rel}")
                if not core_utils.click_coordinates(context, match_specific_second_entry_coord_rel, nikke_window):
                    logger.error(f"Mode6: 点击比赛 '{match_name}' 第二入口失败。跳过此比赛。")
                    continue
                # 使用 cc.R_DELAY_AFTER_SECOND_MATCH_ENTRY，如果常量存在的话
                # 使用常量 cc.R_DELAY_AFTER_SECOND_MATCH_ENTRY
                delay_after_second_entry = cc.R_DELAY_AFTER_SECOND_MATCH_ENTRY if match_name == "4in2_2" else 0
                if delay_after_second_entry > 0:
                    logger.info(f"Mode6: 等待 {delay_after_second_entry} 秒...")
                    time.sleep(delay_after_second_entry)
                if core_utils.check_stop_signal(context): return
            
            # --- 调用核心比赛处理流程 ---
            # 从配置加载延迟并更新 player_info_regions_config
            delay_config = getattr(context.shared, 'delay_config', {})
            delay_value = delay_config.get('after_click_player_details', 2.5) # 使用默认值2.5
            
            player_info_config = copy.deepcopy(cc.R_PLAYER_INFO_CONFIG_SEQ)
            for item in player_info_config:
                if item.get('name') == 'click_detail_info_2':
                    item['delay_after'] = delay_value
                    logger.info(f"Mode6: 已将 'click_detail_info_2' 的延迟更新为 {delay_value} 秒。")
                    break

            # 直接使用常量，移除 getattr
            success = match_processing.process_match_flow(
                context=context,
                file_prefix=f"{current_group_file_prefix}_{match_name.replace(' ', '_')}", # 更具体的文件前缀
                match_name=match_name,
                p1_entry_rel=cc.R_PLAYER1_ENTRY_REL,
                p2_entry_rel=cc.R_PLAYER2_ENTRY_REL,
                result_region_rel=cc.R_RESULT_REGION_REL,
                close_result_rel=cc.R_CLOSE_RESULT_REL,
                player_info_regions_config=player_info_config, # 使用更新后的配置
                team_button_coords_rel=cc.R_TEAM_BUTTONS_REL,
                team_screenshot_region_rel=cc.R_TEAM_SCREENSHOT_REGION_REL,
                close_player_view_coord_rel=cc.R_CLOSE_TEAMVIEW_REL # R_CLOSE_TEAMVIEW_REL 与 R_EXIT_PLAYER_VIEW_REL 等效
            )

            if success:
                completed_matches_overall += 1
                logger.info(f"Mode6: 比赛 {current_group_file_prefix}_{match_name} 处理成功。")
                logger.info(f"Mode6: 整体进度: {completed_matches_overall}/{total_matches_overall} ({completed_matches_overall/total_matches_overall:.1%})")
            else:
                logger.error(f"Mode6: 处理比赛 {current_group_file_prefix}_{match_name} 失败或被中断。")
                if core_utils.check_stop_signal(context): 
                    logger.info(f"Mode6: 因停止信号，中止处理组 {group_actual_number}。")
                    return 

            if core_utils.check_stop_signal(context): 
                logger.info(f"Mode6: 检测到停止信号，完成比赛 {match_name} (组 {group_actual_number}) 后退出。")
                return
            
            if match_idx < len(cc.R_MATCH_NAMES) - 1:
                 time.sleep(cc.R_DELAY_BETWEEN_MATCHES_IN_GROUP)

        logger.info(f"====== Mode6: 完成处理组: {current_group_file_prefix} ======")
        # group_config_idx 是当前处理的组的0-based索引
        # end_group_idx 是配置中要处理的最后一个组的0-based索引
        if group_config_idx < end_group_idx: # Check if it's not the last group to be processed in this run
            time.sleep(cc.R_DELAY_BETWEEN_GROUPS) # 使用常量

    logger.info("===== 模式 6: Reviewer 完整分组赛 执行完毕 =====")
    if completed_matches_overall == total_matches_overall:
        logger.info(f"Mode6: 所有 {total_matches_overall} 场比赛均已成功处理。")
    else:
        logger.warning(f"Mode6: 完成了 {completed_matches_overall} / {total_matches_overall} 场比赛。")