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
    # base_output_dir = context.shared.base_output_dir # core_utils.get_output_path will handle this

    logger.info("===== 运行模式 4: 64进8专用模式 =====")

    if core_utils.check_stop_signal(context):
        logger.info("模式4：检测到停止信号，提前退出。")
        return

    # 从 context.mode_config 获取文件名配置
    # output_filename_prefix 的默认值在 AppContext 中定义为 'NCA'
    # m45_output_suffix 的默认值对于模式4是 '_64in8'
    prefix = getattr(context.mode_config, 'output_filename_prefix', 'NCA')
    suffix = getattr(context.mode_config, 'm45_output_suffix', '_64in8') # 模式4的默认后缀

    final_output_player_basename_template = f"{prefix}_player{{}}_stitched{suffix}.png" # Renamed for clarity
    final_output_overview_basename = f"{prefix}_overview{suffix}.png" # Renamed for clarity

    mode4_player_coords_map = [
        cc.P64IN8_PLAYER1_COORD_REL_M4, cc.P64IN8_PLAYER2_COORD_REL_M4,
        cc.P64IN8_PLAYER3_COORD_REL_M4, cc.P64IN8_PLAYER4_COORD_REL_M4,
        cc.P64IN8_PLAYER5_COORD_REL_M4, cc.P64IN8_PLAYER6_COORD_REL_M4,
        cc.P64IN8_PLAYER7_COORD_REL_M4, cc.P64IN8_PLAYER8_COORD_REL_M4
    ]
    mode4_individual_stitched_files = []

    try:
        for i, player_coord_rel in enumerate(mode4_player_coords_map):
            if core_utils.check_stop_signal(context):
                logger.info(f"模式4：处理玩家 {i+1} 前检测到停止信号。")
                return

            logger.info(f"  处理模式4 - Player {i+1}")
            logger.debug(f"模式4 - Player {i+1}: 调用 collect_player_data 使用的常量: "
                         f"player_info_regions_config 来自 cc.M45_PLAYER_INFO_CONFIG_SEQ, "
                         f"team_button_coords_rel 来自 cc.M45_TEAM_BUTTONS_REL, "
                         f"team_screenshot_region_rel 来自 cc.M45_TEAM_SCREENSHOT_REGION_REL, "
                         f"close_player_view_coord_rel 来自 cc.M45_EXIT_PLAYER_VIEW_REL.")
            p_stitched_temp_path = player_processing.collect_player_data(
                context, # Pass context
                player_entry_coord_rel=player_coord_rel,
                player_info_regions_config=cc.M45_PLAYER_INFO_CONFIG_SEQ,
                team_button_coords_rel=cc.M45_TEAM_BUTTONS_REL,
                team_screenshot_region_rel=cc.M45_TEAM_SCREENSHOT_REGION_REL,
                close_player_view_coord_rel=cc.M45_EXIT_PLAYER_VIEW_REL,
                temp_file_prefix=f"m4_p{i+1}", # Mode and player specific prefix
                # temp_dir is handled by collect_player_data using context.shared.base_temp_dir
            )

            if p_stitched_temp_path and os.path.exists(p_stitched_temp_path):
                # 获取/创建模式4的输出子目录
                # 使用 "mode4_outputs" 作为子目录基础名示例
                mode4_output_dir = core_utils.get_or_create_mode_output_subdir(context, 4, "outputs_64in8")
                if not mode4_output_dir:
                    logger.error(f"  模式4 - Player {i+1}: 无法创建输出目录，跳过保存。")
                    continue # 或者 return，取决于错误处理策略

                player_output_basename = final_output_player_basename_template.format(i+1)
                final_player_image_path = core_utils.generate_unique_filepath(mode4_output_dir, player_output_basename, logger)
                
                shutil.copy2(p_stitched_temp_path, final_player_image_path)
                mode4_individual_stitched_files.append(final_player_image_path)
                logger.info(f"  模式4 - Player {i+1} 截图已保存为 '{final_player_image_path}'")
            else:
                logger.error(f"  处理模式4 - Player {i+1} 失败。未找到截图: {p_stitched_temp_path}")
            
            if core_utils.check_stop_signal(context):
                logger.info(f"模式4：处理玩家 {i+1} 后检测到停止信号。")
                return
        
        if core_utils.check_stop_signal(context):
             logger.info("模式4：所有玩家处理完毕，拼接前检测到停止信号。")
             return

        if len(mode4_individual_stitched_files) == 8:
            # 获取/创建模式4的输出子目录 (如果之前未获取)
            mode4_output_dir = core_utils.get_or_create_mode_output_subdir(context, 4, "outputs_64in8")
            if not mode4_output_dir:
                logger.error("模式4: 无法创建总览图输出目录，中止拼接。")
                # 根据情况设置 final_message
                context.final_message = f"模式4生成了{len(mode4_individual_stitched_files)}张独立图, 但无法创建总览图输出目录。"
                return

            unique_overview_output_path = core_utils.generate_unique_filepath(mode4_output_dir, final_output_overview_basename, logger)
            
            # stitch_mode4_overview 现在接收已经唯一化处理的路径
            # 并且其内部不再进行文件名唯一化
            actual_saved_overview_path = core_utils.stitch_mode4_overview(context, mode4_individual_stitched_files, unique_overview_output_path)

            if actual_saved_overview_path: # stitch_mode4_overview 返回实际保存的路径或 None
                logger.info(f"模式4总览图已生成: {actual_saved_overview_path}.")
                # 清理逻辑基于 m45_save_individual 配置
                save_individual_config_value = getattr(context.mode_config, 'm45_save_individual', False)
                logger.info(f"模式4: 准备清理单张图片。m45_save_individual 配置值为: {save_individual_config_value}")
                if not save_individual_config_value:
                    logger.info("配置为不保留单张图片 (m45_save_individual=False)，开始清理...")
                    for f_path in mode4_individual_stitched_files:
                        if os.path.exists(f_path):
                            try:
                                os.remove(f_path)
                                logger.debug(f"已删除单张图片: {f_path}")
                            except Exception as e_remove:
                                logger.warning(f"清理单张图片 {f_path} 失败: {e_remove}")
                else:
                    logger.info("配置为保留单张图片 (m45_save_individual=True)。")
                context.final_message = f"模式4总览图已生成: {os.path.basename(actual_saved_overview_path)}"
            else:
                logger.error("模式4总览图拼接失败。保留单张截图。")
                context.final_message = f"模式4生成了{len(mode4_individual_stitched_files)}张独立图, 总览图拼接失败。"
        else:
            logger.warning(f"模式4: 未能为所有8个玩家生成截图 (实际: {len(mode4_individual_stitched_files)})，无法拼接总览图。")
            context.final_message = f"模式4生成了{len(mode4_individual_stitched_files)}张独立图, 不足8张无法生成总览。"

    except Exception as e:
        logger.exception(f"模式4执行期间发生错误: {e}")
        context.final_message = f"模式4执行失败: {e}"
        raise # 重新抛出异常，以便 app.py 能捕获它
    finally:
        # 模式特定的临时文件（如果不由 collect_player_data 清理）可以在此清理
        # 但 collect_player_data 应该使用 context.shared.base_temp_dir 下的模式特定临时文件
        logger.info("模式4执行完毕。")