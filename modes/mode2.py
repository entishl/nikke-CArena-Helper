import os  # 确保导入 os 模块
import datetime
from core import utils as core_utils
from core import player_processing
# constants 可以通过 context.shared.constants 访问，或直接导入
# from core import constants as cc


def run(context):
    logger = context.shared.logger
    nikke_window = context.shared.nikke_window
    cc = context.shared.constants  # 获取常量模块的引用

    logger.info("===== 运行模式 2: 复盘模式 =====")

    if core_utils.check_stop_signal(context):
        logger.info("模式2：检测到停止信号，提前退出。")
        return

    # 模式特定逻辑开始
    try:
        # 准备 P1 的参数 (从 cc 或 context.mode_config 获取)
        # 复盘模式通常也需要对手信息，所以我们假设与模式1使用相同的常量
        p1_entry_rel = cc.PRED_PLAYER1_ENTRY_REL_M2  # 使用模式2特定常量
        # ... 其他参数 (根据 c_arena_predition.py 中模式2的逻辑调整)

        player1_stitched_path = player_processing.collect_player_data(
            context,
            player_entry_coord_rel=p1_entry_rel,
            player_info_regions_config=cc.M2_PLAYER_INFO_CONFIG_SEQ,
            team_button_coords_rel=cc.M2_TEAM_BUTTONS_REL,
            team_screenshot_region_rel=cc.M2_TEAM_SCREENSHOT_REGION_REL,
            close_player_view_coord_rel=cc.M2_EXIT_PLAYER_VIEW_REL,
            temp_file_prefix="m2_p1",  # 模式和玩家特定的前缀
        )
        if not player1_stitched_path:
            logger.error("模式2: 处理玩家1数据失败。")
            return
        if core_utils.check_stop_signal(context):
            return

        # 截取赛果图
        result_image_path = None
        # 从 mode_config 获取是否包含赛果图的配置
        include_result_config = getattr(context.mode_config, 'm2_include_result', True)

        if include_result_config:
            logger.info("模式2: 准备截取赛果图...")
            mode2_temp_dir = os.path.join(context.shared.base_temp_dir, "mode2_temp")
            os.makedirs(mode2_temp_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            result_image_filename = f"m2_result_temp_{timestamp}.png"  # 临时文件名
            temp_result_path = os.path.join(mode2_temp_dir, result_image_filename)

            if hasattr(cc, 'PRED_RESULT_REGION_REL_M2'):
                if core_utils.take_screenshot(
                    context,
                    relative_region=cc.PRED_RESULT_REGION_REL_M2,
                    window=nikke_window,  # take_screenshot 当前仍需要 window 参数
                    filename=temp_result_path
                ):
                    logger.info(f"模式2: 赛果图已截取到 {temp_result_path}")
                    result_image_path = temp_result_path
                else:
                    logger.error("模式2: 截取赛果图失败。")
            else:
                logger.error("模式2: 未在常量中找到 PRED_RESULT_REGION_REL_M2，无法截取赛果图。")
            if core_utils.check_stop_signal(context):
                return
        else:
            logger.info("模式2: 根据配置，不截取赛果图。")

        # 准备 P2 的参数
        p2_entry_rel = cc.PRED_PLAYER2_ENTRY_REL_M2  # 使用模式2特定常量
        # ... 其他参数

        player2_stitched_path = player_processing.collect_player_data(
            context,
            player_entry_coord_rel=p2_entry_rel,
            player_info_regions_config=cc.M2_PLAYER_INFO_CONFIG_SEQ,
            team_button_coords_rel=cc.M2_TEAM_BUTTONS_REL,
            team_screenshot_region_rel=cc.M2_TEAM_SCREENSHOT_REGION_REL,
            close_player_view_coord_rel=cc.M2_EXIT_PLAYER_VIEW_REL,
            temp_file_prefix="m2_p2",
        )
        if not player2_stitched_path:
            logger.error("模式2: 处理玩家2数据失败。")
            return
        if core_utils.check_stop_signal(context):
            return

        # 拼接
        base_name = getattr(context.mode_config, 'output_filename_prefix', 'NCA')
        suffix = getattr(context.mode_config, 'm2_output_suffix', '_review')  # 使用 mode_config 中的后缀
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        final_output_filename = f"{base_name}{suffix}_{timestamp}.png"
        
        # 使用 core_utils.get_or_create_mode_output_subdir 来获取或创建输出子目录
        # output_subfolder_basename = "reviews" # 基础名称
        # final_output_dir_path = core_utils.get_or_create_mode_output_subdir(context, 2, output_subfolder_basename)
        
        # 根据审查反馈 #12 和 core_utils.py 中的 get_or_create_mode_output_subdir 实现，
        # 该函数会创建类似 "mode2_reviews" 的子目录。
        # 参数 subdir_basename="reviews" 将与 mode_identifier=2 结合。
        final_output_dir_path = core_utils.get_or_create_mode_output_subdir(context, 2, "reviews")

        if not final_output_dir_path:
            logger.error("模式2: 无法创建或获取输出子目录，中止。")
            return  # 或者进行其他错误处理

        final_output_path = os.path.join(final_output_dir_path, final_output_filename)
        # import os # 不再需要在这里单独导入 os，因为 core_utils 会处理目录创建

        images_to_stitch = []
        # 根据配置和赛果图位置添加图片
        result_pos_config = getattr(context.mode_config, 'm2_result_pos', 'center')

        if result_pos_config == 'left' and result_image_path and os.path.exists(result_image_path):
            images_to_stitch.append(result_image_path)
        
        if player1_stitched_path:
            images_to_stitch.append(player1_stitched_path)

        if result_pos_config == 'center' and result_image_path and os.path.exists(result_image_path):
            images_to_stitch.append(result_image_path)

        if player2_stitched_path:
            images_to_stitch.append(player2_stitched_path)

        if result_pos_config == 'right' and result_image_path and os.path.exists(result_image_path):
            images_to_stitch.append(result_image_path)
        
        # 去重，以防万一（例如 result_pos 配置不标准导致重复添加）
        final_images_to_stitch = []
        for p_path in images_to_stitch:
            if p_path not in final_images_to_stitch:
                final_images_to_stitch.append(p_path)
        
        logger.info(f"模式2: 准备拼接的图片列表 (共 {len(final_images_to_stitch)} 张): {final_images_to_stitch}")

        if len(final_images_to_stitch) >= 1:  # 至少有一张图就尝试处理
            if len(final_images_to_stitch) == 1:
                # 如果只有一张图，直接复制/重命名到目标位置
                logger.info(f"模式2: 只有一张图片 '{final_images_to_stitch[0]}', 将其复制到输出路径。")
                try:
                    import shutil  # 确保导入
                    shutil.copy(final_images_to_stitch[0], final_output_path)
                    logger.info(f"模式2: 单张图片已保存到 {final_output_path}")
                except Exception as e_copy:
                    logger.error(f"模式2: 复制单张图片失败: {e_copy}")
            else:  # 多于一张图，进行拼接
                # 背景色从配置读取 (与模式1一致)
                bg_color_str = getattr(context.mode_config, 'stitch_background_color_str', "0,0,0")
                bg_color_tuple = core_utils.parse_color_string(bg_color_str, logger)

                if core_utils.stitch_images_horizontally(
                    context,
                    final_images_to_stitch,
                    final_output_path,
                    spacing=0,  # 硬编码为0
                    bg_color=bg_color_tuple
                ):
                    logger.info(f"模式2: 结果已保存到 {final_output_path}")
                else:
                    logger.error("模式2: 拼接图片失败。")
        else:
            logger.error("模式2: 没有有效的图片进行处理或拼接。")

    except Exception as e:
        logger.exception(f"模式2执行期间发生错误: {e}")
        raise  # 重新抛出异常，以便 app.py 能捕获它
    finally:
        logger.info("模式2执行完毕。")