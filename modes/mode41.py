# modes/mode41.py
import os
from core import utils as core_utils
import copy # 导入copy模块
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

            # 从配置加载延迟并更新 player_info_regions_config
            delay_config = getattr(context.shared, 'delay_config', {})
            delay_value = delay_config.get('after_click_player_details', 2.5) # 使用默认值2.5
            
            player_info_config = copy.deepcopy(cc.R_PLAYER_INFO_CONFIG_SEQ)
            for item in player_info_config:
                if item.get('name') == 'click_detail_info_2':
                    item['delay_after'] = delay_value
                    logger.info(f"Mode41: 已将 'click_detail_info_2' 的延迟更新为 {delay_value} 秒。")
                    break

            stitched_path = player_processing.collect_player_data(
                context,
                player_entry_coord_rel=player_entry_rel,
                player_info_regions_config=player_info_config, # 使用更新后的配置
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
            spacing=getattr(mode_config, 'image_spacing', 20),
            bg_color=context.shared.get_stitch_background_color(),
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
