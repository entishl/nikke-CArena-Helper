# core/player_processing.py

import os
import time
import logging # 新增 logging
# pyautogui 和 PIL.Image 已在骨架中，但如果 utils 不再导出它们，则可能需要在这里直接导入
from PIL import Image 

# 从 core.utils 导入必要的函数
from .utils import click_coordinates, take_screenshot, stitch_images_vertically, check_stop_signal
from . import constants as core_constants

def collect_player_data(
    context, # 新增 context 参数
    player_entry_coord_rel: tuple,
    player_info_regions_config: list,
    team_button_coords_rel: list,
    team_screenshot_region_rel: tuple,
    close_player_view_coord_rel: tuple | None, # 允许为 None，如果不总是需要关闭
    temp_file_prefix: str,
    # temp_dir: str, # 将从 context.shared.base_temp_dir 获取
    # initial_delay_after_entry: float, # 将从 context.shared.delay_config 获取
    # delay_after_team_click: float, # 将从 context.shared.delay_config 获取
    # player_info_regions_config 中的 'delay_after' 将用于信息区域操作后的延迟
    delay_after_close_view: float = core_constants.DEFAULT_DELAY_AFTER_CLOSE_VIEW
) -> str | None:
    """
    处理单个玩家的完整信息和队伍截图流程。
    内部使用 context.shared.nikke_window, context.shared.logger。
    临时文件路径基于 context.shared.base_temp_dir 和传入的 temp_file_prefix。
    在适当位置调用 core.utils.check_stop_signal(context) 并提前返回。

    参数:
        context: 应用上下文对象。
        player_entry_coord_rel: 点击进入玩家界面的相对坐标 (x_ratio, y_ratio)。
        player_info_regions_config: 描述玩家各信息区域截图及其导航的配置列表。
        team_button_coords_rel: 5个队伍按钮的相对坐标列表 [(x1,y1), (x2,y2), ...]。
        team_screenshot_region_rel: 单个队伍阵容的相对截图区域 (x,y,w,h)。
        close_player_view_coord_rel: 关闭玩家界面的相对坐标 (x_ratio, y_ratio)，如果为None则不执行关闭。
        temp_file_prefix: 用于生成临时文件名的前缀 (例如 "player1_matchA")。
        initial_delay_after_entry: 点击玩家入口后的初始等待时间。
        delay_after_team_click: 点击每个队伍按钮后的等待时间。
        delay_after_close_view: 点击关闭玩家视图后的等待时间。

    返回:
        成功拼接的玩家汇总图片路径 (str)，或失败时返回 None。
    """
    logger = getattr(context.shared, 'logger', logging) # 从 context 获取 logger
    nikke_window = getattr(context.shared, 'nikke_window', None) # 从 context 获取 nikke_window
    base_temp_dir = getattr(context.shared, 'base_temp_dir', './temp_player_data') # 从 context 获取 base_temp_dir
    
    # 从 context 获取延迟配置，如果缺失则使用硬编码的后备值
    delay_config = getattr(context.shared, 'delay_config', {})
    initial_delay_after_entry = delay_config.get('after_player_entry', 3.0)
    delay_after_team_click = delay_config.get('after_team_click', 1.5)


    if not nikke_window:
        error_msg = f"错误 ({temp_file_prefix} - 玩家数据收集)：NIKKE 窗口未设置。"
        logger.error(error_msg)
        if hasattr(context, 'shared'):
            context.shared.final_message = error_msg
        return None

    logger.info(f"开始为 '{temp_file_prefix}' 收集玩家数据，入口: {player_entry_coord_rel}")

    all_player_screenshots = []
    # 使用 context 中的 base_temp_dir
    current_player_temp_dir = os.path.join(base_temp_dir, temp_file_prefix)
    os.makedirs(current_player_temp_dir, exist_ok=True) # 确保特定玩家的临时目录存在

    # 1. 点击进入玩家界面
    if check_stop_signal(context):
        logger.info(f"操作在点击玩家入口前被取消 ({temp_file_prefix})。")
        return None
    logger.info(f"  点击玩家入口: {player_entry_coord_rel}")
    if not click_coordinates(context, player_entry_coord_rel, nikke_window): # 传递 context
        error_msg = f"错误 ({temp_file_prefix})：未能点击玩家入口 {player_entry_coord_rel}。"
        logger.error(error_msg)
        if hasattr(context, 'shared'):
            context.shared.final_message = error_msg
        return None
    logger.info(f"  等待 {initial_delay_after_entry} 秒...")
    time.sleep(initial_delay_after_entry)
    if check_stop_signal(context):
        logger.info(f"操作在进入玩家界面后被取消 ({temp_file_prefix})。")
        return None

    # 2. 处理玩家信息区域截图 (根据 player_info_regions_config)
    logger.info(f"  开始处理玩家信息区域截图...")
    for i, config_item in enumerate(player_info_regions_config):
        if check_stop_signal(context):
            logger.info(f"操作在处理玩家信息区域 {i} 前被取消 ({temp_file_prefix})。")
            return None # 或者根据逻辑决定是否可以继续部分操作
        action_type = config_item.get('type')
        item_delay_after = config_item.get('delay_after', 0.5) # 每个动作后的默认延迟

        if action_type == 'screenshot':
            region_name = config_item.get('name', f'info_screenshot_{i}')
            region_rel = config_item.get('region_rel')
            if not region_rel:
                logger.warning(f"    配置项 {region_name} 缺少 'region_rel'，跳过截图。")
                continue

            screenshot_filename = f"{temp_file_prefix}_{region_name}.png"
            screenshot_path = os.path.join(current_player_temp_dir, screenshot_filename) # 使用新的临时目录
            logger.info(f"    截图 '{region_name}' 到 {screenshot_path} (区域: {region_rel})")

            try:
                if hasattr(nikke_window, 'activate'): nikke_window.activate()
                time.sleep(core_constants.POST_WINDOW_ACTIVATION_SHORT_DELAY)
            except Exception as e_act:
                logger.debug(f"    尝试激活窗口时出现轻微问题: {e_act}")

            if take_screenshot(context, region_rel, nikke_window, screenshot_path): # 传递 context
                all_player_screenshots.append(screenshot_path)
                logger.info(f"    截图 '{region_name}' 成功。")
            else:
                logger.warning(f"    未能截取 '{region_name}' ({screenshot_path})。")
            time.sleep(item_delay_after)

        elif action_type == 'click':
            coord_rel = config_item.get('coord_rel')
            click_name = config_item.get('name', f'info_click_{i}')
            if not coord_rel:
                logger.warning(f"    配置项 {click_name} 缺少 'coord_rel'，跳过点击。")
                continue

            logger.info(f"    点击 '{click_name}' (坐标: {coord_rel})")
            if not click_coordinates(context, coord_rel, nikke_window): # 传递 context
                logger.warning(f"    未能点击 '{click_name}' ({coord_rel})。")
            time.sleep(item_delay_after)
        else:
            logger.warning(f"    未知的 player_info_regions_config 类型: {action_type}，跳过。")
        if check_stop_signal(context):
            logger.info(f"操作在处理玩家信息区域 {i} 后被取消 ({temp_file_prefix})。")
            return None
    logger.info(f"  玩家信息区域处理完毕。")

    # 3. 循环处理5个队伍
    logger.info(f"  开始处理队伍截图...")
    for i, team_coord_rel in enumerate(team_button_coords_rel):
        if check_stop_signal(context):
            logger.info(f"操作在处理队伍 {i+1} 前被取消 ({temp_file_prefix})。")
            return None
        team_num = i + 1
        logger.info(f"    处理队伍 {team_num}，点击坐标: {team_coord_rel}")
        if not click_coordinates(context, team_coord_rel, nikke_window): # 传递 context
            logger.warning(f"    未能点击队伍 {team_num} ({team_coord_rel})，跳过此队伍。")
            continue

        logger.info(f"    等待 {delay_after_team_click} 秒...")
        time.sleep(delay_after_team_click)
        if check_stop_signal(context):
            logger.info(f"操作在点击队伍 {team_num} 后被取消 ({temp_file_prefix})。")
            return None

        team_screenshot_filename = f"{temp_file_prefix}_team_{team_num}.png"
        team_screenshot_path = os.path.join(current_player_temp_dir, team_screenshot_filename) # 使用新的临时目录
        logger.info(f"    截图队伍 {team_num} 到 {team_screenshot_path} (区域: {team_screenshot_region_rel})")

        try:
            if hasattr(nikke_window, 'activate'): nikke_window.activate()
            time.sleep(core_constants.POST_WINDOW_ACTIVATION_SHORT_DELAY)
        except Exception as e_act:
            logger.debug(f"    尝试激活窗口时出现轻微问题: {e_act}")

        if take_screenshot(context, team_screenshot_region_rel, nikke_window, team_screenshot_path): # 传递 context
            all_player_screenshots.append(team_screenshot_path)
            logger.info(f"    截图队伍 {team_num} 成功。")
        else:
            logger.warning(f"    未能截取队伍 {team_num} ({team_screenshot_path})。")
        if check_stop_signal(context):
            logger.info(f"操作在截图队伍 {team_num} 后被取消 ({temp_file_prefix})。")
            return None
    logger.info(f"  队伍截图处理完毕。")

    # 4. 垂直拼接 all_player_screenshots
    if not all_player_screenshots:
        warn_msg = f"警告 ({temp_file_prefix})：未能截取任何玩家图片，无法进行拼接。"
        logger.warning(warn_msg)
        # 即使没有图片，也尝试关闭视图，但这本身不是一个“最终错误”，除非调用者期望必须有图片
        # final_message 更多用于指示流程的最终状态或关键错误
        # 如果需要，可以在调用此函数的地方根据返回值 None 和此警告来设置更高级别的 final_message
        if hasattr(context, 'shared'):
             context.shared.final_message = warn_msg # 可以考虑是否将警告也设为 final_message

        if close_player_view_coord_rel:
            if check_stop_signal(context):
                logger.info(f"操作在关闭空视图前被取消 ({temp_file_prefix})。")
                # context.shared.final_message = f"操作取消 ({temp_file_prefix})：关闭空视图前。" # 取消一般不设为final_message
                return None
            logger.info(f"  尝试关闭玩家视图 ({temp_file_prefix})，即使没有截图...")
            if not click_coordinates(context, close_player_view_coord_rel, nikke_window): # 传递 context
                logger.warning(f"  未能点击关闭玩家视图坐标 {close_player_view_coord_rel} ({temp_file_prefix})。")
            else:
                time.sleep(delay_after_close_view)
        return None

    stitched_image_filename = f"{temp_file_prefix}_stitched.png"
    # 拼接后的图片也放在特定玩家的临时目录中，或者可以考虑放在 base_temp_dir 的上一级或 output_dir
    stitched_image_path = os.path.join(current_player_temp_dir, stitched_image_filename)
    logger.info(f"  开始垂直拼接 {len(all_player_screenshots)} 张图片到 {stitched_image_path}...")

    if check_stop_signal(context):
        logger.info(f"操作在拼接图片前被取消 ({temp_file_prefix})。")
        return None
    if not stitch_images_vertically(context, all_player_screenshots, stitched_image_path): # 传递 context
        error_msg = f"错误 ({temp_file_prefix})：垂直拼接玩家截图失败。"
        logger.error(error_msg)
        if hasattr(context, 'shared'):
            context.shared.final_message = error_msg
        
        if close_player_view_coord_rel:
            if check_stop_signal(context):
                logger.info(f"操作在关闭拼接失败视图前被取消 ({temp_file_prefix})。")
                # context.shared.final_message = f"操作取消 ({temp_file_prefix})：关闭拼接失败视图前。"
                return None
            logger.info(f"  拼接失败 ({temp_file_prefix})，但仍尝试关闭玩家视图...")
            if not click_coordinates(context, close_player_view_coord_rel, nikke_window): # 传递 context
                logger.warning(f"  未能点击关闭玩家视图坐标 {close_player_view_coord_rel} ({temp_file_prefix})。")
            else:
                time.sleep(delay_after_close_view)
        return None

    logger.info(f"  玩家 {temp_file_prefix} 的截图已成功垂直拼接至: {stitched_image_path}")

    # 5. (可选) 清理单个截图文件 (在拼接成功后)
    # 注意：如果拼接后的图片与原始截图在同一目录，并且后续流程需要这个目录（例如打包），则不应删除
    # 这里假设 current_player_temp_dir 只是临时存放，最终的拼接图会被移走或复制
    logger.info(f"  清理 {temp_file_prefix} 的单个截图文件...")
    for temp_path in all_player_screenshots:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.debug(f"    已删除临时文件: {temp_path}")
            except OSError as e:
                logger.warning(f"    无法删除临时文件 {temp_path}: {e}")

    # 6. 点击关闭玩家界面 (如果提供了坐标)
    if close_player_view_coord_rel:
        if check_stop_signal(context):
            logger.info(f"操作在最后关闭视图前被取消 ({temp_file_prefix})。")
            return stitched_image_path # 即使取消，拼接图已生成
        logger.info(f"  点击关闭玩家视图: {close_player_view_coord_rel}")
        if not click_coordinates(context, close_player_view_coord_rel, nikke_window): # 传递 context
            logger.warning(f"  未能点击关闭玩家视图坐标 {close_player_view_coord_rel}。")
        else:
            logger.info(f"  等待 {delay_after_close_view} 秒...")
            time.sleep(delay_after_close_view)
            if check_stop_signal(context):
                logger.info(f"操作在等待关闭视图后被取消 ({temp_file_prefix})。")
                return stitched_image_path # 拼接图已生成

    logger.info(f"为 '{temp_file_prefix}' 收集玩家数据完成，返回拼接图: {stitched_image_path}")
    return stitched_image_path

if __name__ == '__main__':
    # 配置基本的日志记录器以进行测试
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    print("player_processing.py 被直接运行 (通常作为模块导入)")