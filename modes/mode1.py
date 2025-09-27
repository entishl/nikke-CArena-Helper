from core import utils as core_utils
import os
import datetime
from core import player_processing
# constants 可以通过 context.shared.constants 访问，或直接导入
# from core import constants as cc

def run(context):
    logger = context.shared.logger
    nikke_window = context.shared.nikke_window
    cc = context.shared.constants # 获取常量模块的引用
    mode_config = context.mode_config # 获取模式特定配置

    logger.info("===== 运行模式 1: 买马预测 =====")

    if core_utils.check_stop_signal(context):
        logger.info("模式1：检测到停止信号，提前退出。")
        return

    # 模式特定逻辑开始
    try:
        # 准备 P1 的参数 (从 cc 或 context.mode_config 获取)
        p1_entry_rel = cc.PRED_PLAYER1_ENTRY_REL

        player1_stitched_path = player_processing.collect_player_data(
            context,
            player_entry_coord_rel=p1_entry_rel,
            player_info_regions_config=cc.PRED_PLAYER_INFO_CONFIG_SEQ,
            team_button_coords_rel=cc.PRED_TEAM_BUTTONS_REL,
            team_screenshot_region_rel=cc.PRED_TEAM_SCREENSHOT_REGION_REL,
            close_player_view_coord_rel=cc.PRED_EXIT_PLAYER_VIEW_REL,
            temp_file_prefix="m1_p1", # 模式和玩家特定的前缀
            # temp_dir 将由 collect_player_data 内部使用 context.shared.base_temp_dir
        )
        if not player1_stitched_path:
             logger.error("模式1: 处理玩家1数据失败。")
             return
        if core_utils.check_stop_signal(context): return

        # 准备 P2 的参数
        p2_entry_rel = cc.PRED_PLAYER2_ENTRY_REL

        player2_stitched_path = player_processing.collect_player_data(
            context,
            player_entry_coord_rel=p2_entry_rel,
            player_info_regions_config=cc.PRED_PLAYER2_INFO_CONFIG_SEQ,
            team_button_coords_rel=cc.PRED_PLAYER2_TEAM_BUTTONS_REL,
            team_screenshot_region_rel=cc.PRED_PLAYER2_TEAM_SCREENSHOT_REGION_REL,
            close_player_view_coord_rel=cc.PRED_PLAYER2_EXIT_PLAYER_VIEW_REL,
            temp_file_prefix="m1_p2",
        )
        if not player2_stitched_path:
             logger.error("模式1: 处理玩家2数据失败。")
             return
        if core_utils.check_stop_signal(context): return

        # 拼接
        # 从 mode_config 获取配置来构建文件名
        base_name = getattr(mode_config, 'output_filename_prefix', 'NCA')
        suffix = getattr(mode_config, 'm1_output_suffix', '_prediction')
        player1_name_for_file = getattr(mode_config, 'm1_player1_name', 'P1').replace(' ', '_')
        player2_name_for_file = getattr(mode_config, 'm1_player2_name', 'P2').replace(' ', '_')
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        final_output_filename = f"{base_name}_{player1_name_for_file}_vs_{player2_name_for_file}{suffix}_{timestamp}.png"
        
        # 使用新的辅助函数获取或创建模式输出子目录
        output_dir_for_mode1 = core_utils.get_or_create_mode_output_subdir(context, 1, "predictions")
        
        if not output_dir_for_mode1:
            logger.error("模式1: 无法获取或创建输出子目录，中止。")
            return # 或者进行其他错误处理

        final_output_path = os.path.join(output_dir_for_mode1, final_output_filename)
        logger.info(f"模式1: 最终输出文件名将是: {final_output_filename} (在目录: {output_dir_for_mode1})")

        images_to_stitch = [p for p in [player1_stitched_path, player2_stitched_path] if p]
        if len(images_to_stitch) == 2:
            core_utils.stitch_images_horizontally(
                context,
                images_to_stitch,
                final_output_path,
                spacing=getattr(mode_config, 'image_spacing', 20),  # 从配置读取
                bg_color=core_utils.parse_color_string(getattr(mode_config, 'stitch_background_color_str', "0,0,0"), logger) # 从配置读取并解析
            )
            logger.info(f"模式1: 结果已保存到 {final_output_path}")
        else:
            logger.error("模式1: 缺少足够的图片进行拼接。")

    except Exception as e:
        logger.exception(f"模式1执行期间发生错误: {e}")
        raise # 重新抛出异常，以便 app.py 能捕获它
    finally:
        # 可以在这里进行模式特有的临时文件清理（如果需要的话）
        # 但主要的临时文件应由 collect_player_data 内部管理或 app.py 统一清理
        logger.info("模式1执行完毕。")