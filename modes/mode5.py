import os
import shutil
from core import utils as core_utils
from core import player_processing
# constants 可以通过 context.shared.constants 访问

def run(context):
    logger = context.shared.logger
    nikke_window = context.shared.nikke_window
    cc = context.shared.constants
    base_temp_dir = context.shared.base_temp_dir
    # base_output_dir 由 core_utils.get_output_path 处理

    logger.info("===== 运行模式 5: 冠军争霸模式 =====")

    if core_utils.check_stop_signal(context):
        logger.info("模式5：检测到停止信号，提前退出。")
        return

    # 从 context.mode_config 获取文件名配置
    # output_filename_prefix 的默认值在 AppContext 中定义为 'NCA'
    # m45_output_suffix 的默认值对于模式5是 '_champ_pred'
    prefix = getattr(context.mode_config, 'output_filename_prefix', 'NCA')
    suffix = getattr(context.mode_config, 'm45_output_suffix', '_champ_pred') # 模式5的默认后缀

    final_output_player_basename = f"{prefix}_player{{}}_stitched{suffix}.png"
    final_output_overview_filename = f"{prefix}_overview{suffix}.png"

    mode5_player_coords_map = [
        cc.CHAMPION_PLAYER1_COORD_REL_M5, cc.CHAMPION_PLAYER2_COORD_REL_M5,
        cc.CHAMPION_PLAYER3_COORD_REL_M5, cc.CHAMPION_PLAYER4_COORD_REL_M5,
        cc.CHAMPION_PLAYER5_COORD_REL_M5, cc.CHAMPION_PLAYER6_COORD_REL_M5,
        cc.CHAMPION_PLAYER7_COORD_REL_M5, cc.CHAMPION_PLAYER8_COORD_REL_M5
    ]
    mode5_individual_stitched_files = []

    try:
        # 获取模式5的专用输出子目录
        mode5_output_dir = core_utils.get_or_create_mode_output_subdir(context, 5, "outputs_champ_pred")
        if not mode5_output_dir:
            logger.error("模式5: 无法创建或获取输出目录，模式终止。")
            context.final_message = "模式5: 创建输出目录失败。"
            return

        for i, player_coord_rel in enumerate(mode5_player_coords_map):
            if core_utils.check_stop_signal(context):
                logger.info(f"模式5：处理玩家 {i+1} 前检测到停止信号。")
                return

            logger.info(f"  处理模式5 - Player {i+1}")
            logger.debug(f"模式5 - Player {i+1}: 调用 collect_player_data 使用的常量: "
                         f"player_info_regions_config 来自 cc.M45_PLAYER_INFO_CONFIG_SEQ, "
                         f"team_button_coords_rel 来自 cc.M45_TEAM_BUTTONS_REL, "
                         f"team_screenshot_region_rel 来自 cc.M45_TEAM_SCREENSHOT_REGION_REL, "
                         f"close_player_view_coord_rel 来自 cc.M45_EXIT_PLAYER_VIEW_REL.")
            p_stitched_temp_path = player_processing.collect_player_data(
                context,
                player_entry_coord_rel=player_coord_rel,
                player_info_regions_config=cc.M45_PLAYER_INFO_CONFIG_SEQ,
                team_button_coords_rel=cc.M45_TEAM_BUTTONS_REL,
                team_screenshot_region_rel=cc.M45_TEAM_SCREENSHOT_REGION_REL,
                close_player_view_coord_rel=cc.M45_EXIT_PLAYER_VIEW_REL,
                temp_file_prefix=f"m5_p{i+1}",
            )

            if p_stitched_temp_path and os.path.exists(p_stitched_temp_path):
                player_output_filename = final_output_player_basename.format(i+1)
                # 在模式专用子目录中为每个玩家图片生成唯一路径
                final_player_image_path = core_utils.generate_unique_filepath(mode5_output_dir, player_output_filename, logger)
                
                shutil.copy2(p_stitched_temp_path, final_player_image_path)
                mode5_individual_stitched_files.append(final_player_image_path)
                logger.info(f"  模式5 - Player {i+1} 截图已保存为 '{final_player_image_path}'")
            else:
                logger.error(f"  处理模式5 - Player {i+1} 失败。未找到截图: {p_stitched_temp_path}")

            if core_utils.check_stop_signal(context):
                logger.info(f"模式5：处理玩家 {i+1} 后检测到停止信号。")
                return
        
        if core_utils.check_stop_signal(context):
             logger.info("模式5：所有玩家处理完毕，拼接前检测到停止信号。")
             return

        if len(mode5_individual_stitched_files) == 8:
            # 为总览图在模式专用子目录中生成唯一路径
            overview_output_path = core_utils.generate_unique_filepath(mode5_output_dir, final_output_overview_filename, logger)
            # 复用 mode4 的总览图拼接逻辑，传递 context
            success = core_utils.stitch_mode4_overview(context, mode5_individual_stitched_files, overview_output_path)

            if success:
                logger.info(f"模式5总览图已生成: {overview_output_path}.")
                save_individual_config_value = getattr(context.mode_config, 'm45_save_individual', False) # 默认为 False
                logger.info(f"模式5: 准备清理单张图片。m45_save_individual 配置值为: {save_individual_config_value}")

                if not save_individual_config_value:
                    logger.info("配置为不保留单张图片 (m45_save_individual=False)，开始清理...")
                    for f_path in mode5_individual_stitched_files:
                        if os.path.exists(f_path):
                            try:
                                os.remove(f_path)
                                logger.debug(f"已删除单张图片: {f_path}")
                            except Exception as e_remove:
                                logger.warning(f"清理单张图片 {f_path} 失败: {e_remove}")
                else:
                    logger.info("配置为保留单张图片 (m45_save_individual=True)。")
                context.final_message = f"模式5总览图已生成: {os.path.basename(overview_output_path)}"
            else:
                logger.error("模式5总览图拼接失败。保留单张截图。")
                context.final_message = f"模式5生成了{len(mode5_individual_stitched_files)}张独立图, 总览图拼接失败。"
        else:
            logger.warning(f"模式5: 未能为所有8个玩家生成截图 (实际: {len(mode5_individual_stitched_files)})，无法拼接总览图。")
            context.final_message = f"模式5生成了{len(mode5_individual_stitched_files)}张独立图, 不足8张无法生成总览。"

    except Exception as e:
        logger.exception(f"模式5执行期间发生错误: {e}")
        context.final_message = f"模式5执行失败: {e}"
        raise # 重新抛出异常，以便 app.py 能捕获它
    finally:
        logger.info("模式5执行完毕。")