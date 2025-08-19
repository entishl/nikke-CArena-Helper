import os # 确保导入 os 模块
import shutil # 用于复制文件
from core import utils as core_utils
from core import player_processing
# constants 可以通过 context.shared.constants 访问，或直接导入
# from core import constants as cc

def run(context):
    logger = context.shared.logger
    nikke_window = context.shared.nikke_window
    cc = context.shared.constants # 获取常量模块的引用

    logger.info("===== 运行模式 3: 反买存档 =====")

    if core_utils.check_stop_signal(context):
        logger.info("模式3：检测到停止信号，提前退出。")
        return

    # 模式特定逻辑开始
    try:
        # 准备 P1 的参数
        # 反买存档模式通常也需要对手信息
        p1_entry_rel = cc.M3_PLAYER1_ENTRY_REL
        # ... 其他参数 (根据 c_arena_prediction.py 中模式3的逻辑调整)

        player1_stitched_path = player_processing.collect_player_data(
            context,
            player_entry_coord_rel=p1_entry_rel,
            player_info_regions_config=cc.M3_PLAYER_INFO_CONFIG_SEQ,
            team_button_coords_rel=cc.M3_TEAM_BUTTONS_REL,
            team_screenshot_region_rel=cc.M3_TEAM_SCREENSHOT_REGION_REL,
            close_player_view_coord_rel=cc.M3_EXIT_PLAYER_VIEW_REL,
            temp_file_prefix="m3_p1", # 模式和玩家特定的前缀
        )
        if not player1_stitched_path:
             logger.error("模式3: 处理玩家1数据失败。")
             return
        if core_utils.check_stop_signal(context): return

        vote_screenshot_path = None
        if getattr(context.mode_config, 'm3_include_vote', False):
            logger.info("模式3: 尝试截取民意投票区域...")
            vote_temp_filename = "m3_people_vote.png" # 临时文件名
            # 路径应基于 context.shared.base_temp_dir
            # 确保 player_processing.collect_player_data 使用的临时文件不会冲突
            # collect_player_data 内部会创建如 m3_p1/player_info_xxx.png 的文件
            # 所以 vote_temp_filename 直接放在 base_temp_dir 应该是安全的
            mode3_temp_dir = os.path.join(context.shared.base_temp_dir, "mode3_temp")
            os.makedirs(mode3_temp_dir, exist_ok=True)
            vote_screenshot_path_temp = os.path.join(mode3_temp_dir, vote_temp_filename)

            if hasattr(cc, 'M3_PEOPLE_VOTE_REGION_REL'):
                if core_utils.take_screenshot(context, cc.M3_PEOPLE_VOTE_REGION_REL, nikke_window, vote_screenshot_path_temp):
                    logger.info(f"模式3: 民意投票截图已保存到 '{vote_screenshot_path_temp}'")
                    vote_screenshot_path = vote_screenshot_path_temp # 存储成功截图的路径
                else:
                    logger.warning("模式3: 未能截取民意投票区域。")
            else:
                logger.warning("模式3: 未在常量中找到 M3_PEOPLE_VOTE_REGION_REL。无法截取民意投票。")
            if core_utils.check_stop_signal(context): return
        
        # 准备 P2 的参数
        p2_entry_rel = cc.M3_PLAYER2_ENTRY_REL
        # ... 其他参数

        player2_stitched_path = player_processing.collect_player_data(
            context,
            player_entry_coord_rel=p2_entry_rel,
            player_info_regions_config=cc.M3_PLAYER_INFO_CONFIG_SEQ,
            team_button_coords_rel=cc.M3_TEAM_BUTTONS_REL,
            team_screenshot_region_rel=cc.M3_TEAM_SCREENSHOT_REGION_REL,
            close_player_view_coord_rel=cc.M3_EXIT_PLAYER_VIEW_REL,
            temp_file_prefix="m3_p2",
        )
        if not player2_stitched_path:
             logger.error("模式3: 处理玩家2数据失败。")
             return
        if core_utils.check_stop_signal(context): return

        # 拼接
        base_name = getattr(context.mode_config, 'output_filename_prefix', 'NCA')
        suffix = getattr(context.mode_config, 'm3_output_suffix', '_counter_save') # 使用 mode_config 中的后缀
        final_output_filename = f"{base_name}{suffix}.png"

        # 使用 core_utils 中的辅助函数获取或创建模式输出子目录
        # mode_number for mode3 is 3. subdir_name is "counter_saves".
        mode_output_dir = core_utils.get_or_create_mode_output_subdir(context, 3, "counter_saves")
        
        if not mode_output_dir:
            logger.error("模式3: 无法创建或获取输出子目录，中止处理。")
            return # 或者进行其他错误处理

        final_output_path = os.path.join(mode_output_dir, final_output_filename)

        images_to_stitch = []
        if player1_stitched_path:
            images_to_stitch.append(player1_stitched_path)
        if vote_screenshot_path: # vote_screenshot_path 仅在成功时被赋值
            images_to_stitch.append(vote_screenshot_path)
        if player2_stitched_path:
            images_to_stitch.append(player2_stitched_path)
            
        # 根据实际收集到的图片数量判断是否拼接
        if len(images_to_stitch) >= 2:
            core_utils.stitch_images_horizontally(
                context,
                images_to_stitch,
                final_output_path,
                spacing=getattr(context.mode_config, 'image_spacing', 50), # 使用 mode_config 中的间距
                bg_color=context.shared.get_stitch_background_color() # 从共享上下文中获取背景色
            )
            logger.info(f"模式3: 结果已保存到 {final_output_path}")
        elif len(images_to_stitch) == 1:
            logger.info(f"模式3: 只收集到一张图片，将其复制到输出路径。源: {images_to_stitch[0]}")
            try:
                shutil.copy(images_to_stitch[0], final_output_path)
                logger.info(f"模式3: 单张图片已复制到 {final_output_path}")
            except Exception as e_copy:
                logger.error(f"模式3: 复制单张图片失败: {e_copy}")
        else:
            logger.error("模式3: 没有足够的图片进行处理。")

    except Exception as e:
        logger.exception(f"模式3执行期间发生错误: {e}")
        raise # 重新抛出异常，以便 app.py 能捕获它
    finally:
        logger.info("模式3执行完毕。")