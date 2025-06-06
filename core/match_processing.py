# core/match_processing.py
import os
import time
import logging

from .utils import click_coordinates, take_screenshot, stitch_images_horizontally, check_stop_signal # stitch_images_horizontally 稍后添加
from .player_processing import collect_player_data

def process_match_flow(
    context,
    file_prefix: str,
    match_name: str, # 用于日志和可能的文件名部分
    p1_entry_rel: tuple,
    p2_entry_rel: tuple,
    result_region_rel: tuple,
    close_result_rel: tuple,
    # 根据 c_arena_reviewer.py 的 process_single_match，可能还需要其他配置
    player_info_regions_config: list, # 从主配置传入
    team_button_coords_rel: list,     # 从主配置传入
    team_screenshot_region_rel: tuple,# 从主配置传入
    close_player_view_coord_rel: tuple | None, # 从主配置传入
    # 可以在这里添加更多针对单场比赛特有的延迟或配置
    delay_after_result_screenshot: float = 0.5,
    delay_after_player_collection: float = 0.5,
    delay_after_close_result: float = 1.0
) -> str | None:
    """
    处理单场比赛的完整流程：截图赛果、收集双方玩家数据、拼接总图、关闭赛果。

    参数:
        context: 应用上下文对象。
        file_prefix: 用于该场比赛所有文件名的基础前缀 (例如 "group1_match1")。
        match_name: 比赛的描述性名称 (例如 "小组赛第一场")。
        p1_entry_rel: 玩家1入口的相对坐标。
        p2_entry_rel: 玩家2入口的相对坐标。
        result_region_rel: 比赛结果截图的相对区域。
        close_result_rel: 关闭比赛结果界面的相对坐标。
        player_info_regions_config: 传递给 collect_player_data 的玩家信息区域配置。
        team_button_coords_rel: 传递给 collect_player_data 的队伍按钮坐标。
        team_screenshot_region_rel: 传递给 collect_player_data 的队伍截图区域。
        close_player_view_coord_rel: 传递给 collect_player_data 的关闭玩家视图坐标。
        delay_after_result_screenshot: 截取赛果后的等待时间。
        delay_after_player_collection: 收集完一个玩家数据后的等待时间。
        delay_after_close_result: 关闭赛果后的等待时间。

    返回:
        成功生成的该场比赛总览图片路径 (str)，或失败时返回 None。
    """
    logger = getattr(context.shared, 'logger', logging)
    nikke_window = getattr(context.shared, 'nikke_window', None)
    base_output_dir = getattr(context.shared, 'base_output_dir', './match_outputs')
    base_temp_dir = getattr(context.shared, 'base_temp_dir', './temp_match_data') # 用于存放赛果和玩家拼接图

    if not nikke_window:
        error_msg = f"错误 ({match_name} - 比赛流程): NIKKE 窗口未设置。"
        logger.error(error_msg)
        if hasattr(context, 'shared'):
            context.shared.final_message = error_msg
        return None

    logger.info(f"开始处理比赛: {match_name} (文件前缀: {file_prefix})")

    # 为这场比赛创建一个独立的临时子目录，用于存放赛果图和两个玩家的汇总图
    match_temp_dir = os.path.join(base_temp_dir, file_prefix)
    os.makedirs(match_temp_dir, exist_ok=True)

    # 为这场比赛的最终输出图创建一个输出子目录 (如果尚不存在)
    # 最终的横向拼接图会直接保存到 base_output_dir 下，以 file_prefix 命名
    # os.makedirs(base_output_dir, exist_ok=True) # 主程序应该已经创建了 base_output_dir

    images_to_stitch_horizontally = []

    # 1. 截图赛果
    if check_stop_signal(context):
        logger.info(f"操作在截图赛果前被取消 ({match_name})。")
        return None
    
    result_screenshot_filename = f"{file_prefix}_result.png"
    result_screenshot_path = os.path.join(match_temp_dir, result_screenshot_filename)
    logger.info(f"  ({match_name}) 截取赛果图: {result_screenshot_path} (区域: {result_region_rel})")
    
    if not take_screenshot(context, result_region_rel, nikke_window, result_screenshot_path):
        error_msg = f"错误 ({match_name})：未能截取赛果图。"
        logger.error(f"  {error_msg}")
        if hasattr(context, 'shared'):
            context.shared.final_message = error_msg
        # 即使赛果截图失败，也可能需要尝试关闭赛果界面（如果后续逻辑允许）
        # 但通常赛果是后续操作的基础，失败则中止
        return None # 或者根据策略决定是否继续
    images_to_stitch_horizontally.append(result_screenshot_path)
    logger.info(f"  ({match_name}) 赛果图截取成功。等待 {delay_after_result_screenshot} 秒...")
    time.sleep(delay_after_result_screenshot)

    # 2. 收集玩家1数据
    if check_stop_signal(context):
        logger.info(f"操作在收集玩家1数据前被取消 ({match_name})。")
        return None # 返回 None，因为比赛未完成
        
    logger.info(f"  ({match_name}) 开始收集玩家1数据...")
    player1_prefix = f"{file_prefix}_player1"
    # collect_player_data 会在 context.shared.base_temp_dir 下创建 player1_prefix 子目录
    player1_stitched_image_path = collect_player_data(
        context,
        p1_entry_rel,
        player_info_regions_config,
        team_button_coords_rel,
        team_screenshot_region_rel,
        close_player_view_coord_rel,
        player1_prefix, # temp_file_prefix for collect_player_data
        # initial_delay_after_entry, delay_after_team_click 等参数使用 collect_player_data 的默认值或从配置传入
    )
    if check_stop_signal(context): # 检查 collect_player_data 内部是否触发了停止
        logger.info(f"操作在收集玩家1数据期间被取消 ({match_name})。")
        return None
        
    if player1_stitched_image_path:
        images_to_stitch_horizontally.append(player1_stitched_image_path)
        logger.info(f"  ({match_name}) 玩家1数据收集完成: {player1_stitched_image_path}")
    else:
        # player_processing.collect_player_data 内部会设置 final_message
        # 此处仅记录日志，如果需要，可以覆盖或追加 final_message
        logger.warning(f"  ({match_name}) 未能收集玩家1的数据。总览图可能不完整。")
        # 如果严格要求双方数据，则应在此处返回 None 并设置 final_message
        # 例如:
        # error_msg = f"错误 ({match_name}): 未能收集玩家1的数据。"
        # logger.error(error_msg)
        # if hasattr(context, 'shared'):
        #     context.shared.final_message = error_msg # 这会覆盖 player_processing 设置的消息
        # return None

    time.sleep(delay_after_player_collection) # 收集完一个玩家数据后的等待

    # 3. 收集玩家2数据
    if check_stop_signal(context):
        logger.info(f"操作在收集玩家2数据前被取消 ({match_name})。")
        return None

    logger.info(f"  ({match_name}) 开始收集玩家2数据...")
    player2_prefix = f"{file_prefix}_player2"
    player2_stitched_image_path = collect_player_data(
        context,
        p2_entry_rel,
        player_info_regions_config,
        team_button_coords_rel,
        team_screenshot_region_rel,
        close_player_view_coord_rel,
        player2_prefix,
    )
    if check_stop_signal(context):
        logger.info(f"操作在收集玩家2数据期间被取消 ({match_name})。")
        return None

    if player2_stitched_image_path:
        images_to_stitch_horizontally.append(player2_stitched_image_path)
        logger.info(f"  ({match_name}) 玩家2数据收集完成: {player2_stitched_image_path}")
    else:
        logger.warning(f"  ({match_name}) 未能收集玩家2的数据。总览图可能不完整。")
        # 同样，如果严格要求，可以在此返回 None 并设置 final_message
        # 例如:
        # error_msg = f"错误 ({match_name}): 未能收集玩家2的数据。"
        # logger.error(error_msg)
        # if hasattr(context, 'shared'):
        #     context.shared.final_message = error_msg
        # return None

    time.sleep(delay_after_player_collection) # 收集完一个玩家数据后的等待 (如果适用)

    # 4. 横向拼接图片 (赛果, 玩家1汇总, 玩家2汇总)
    if not images_to_stitch_horizontally or len(images_to_stitch_horizontally) < 1: # 至少要有赛果图
        error_msg = f"错误 ({match_name})：没有足够的图片进行总览图拼接（至少需要赛果图）。"
        logger.error(f"  {error_msg}")
        if hasattr(context, 'shared'):
            context.shared.final_message = error_msg
        # 仍尝试关闭赛果界面
        if close_result_rel:
            if check_stop_signal(context): return None
            logger.info(f"  ({match_name}) 尝试关闭赛果界面 (无图拼接)...")
            click_coordinates(context, close_result_rel, nikke_window)
            time.sleep(delay_after_close_result)
        return None

    # 最终拼接的图片保存到基于 context.shared.base_output_dir 的路径
    final_stitched_filename = f"{file_prefix}_overview.png"
    final_stitched_path = os.path.join(base_output_dir, final_stitched_filename)
    
    # 确保 base_output_dir 存在
    os.makedirs(base_output_dir, exist_ok=True)

    logger.info(f"  ({match_name}) 开始横向拼接 {len(images_to_stitch_horizontally)} 张图片到 {final_stitched_path}...")
    
    if check_stop_signal(context):
        logger.info(f"操作在横向拼接前被取消 ({match_name})。")
        return None # 返回 None，因为最终图片未生成

    # TODO: 实现 stitch_images_horizontally 并在 utils 中导入
    # 假设 stitch_images_horizontally(context, image_paths, output_path, alignment='center', spacing=10)
    # alignment 可以是 'top', 'center', 'bottom'
    # spacing 是图片间的间距
    # stitch_images_horizontally 应该在 core.utils.py 中定义
    if not stitch_images_horizontally(context, images_to_stitch_horizontally, final_stitched_path):
        error_msg = f"错误 ({match_name})：横向拼接总览图片失败。"
        logger.error(f"  {error_msg}")
        if hasattr(context, 'shared'):
            context.shared.final_message = error_msg
        # 即使拼接失败，也尝试关闭赛果界面
        if close_result_rel:
            if check_stop_signal(context): return None
            logger.info(f"  ({match_name}) 拼接失败，尝试关闭赛果界面...")
            click_coordinates(context, close_result_rel, nikke_window)
            time.sleep(delay_after_close_result)
        return None
    
    logger.info(f"  ({match_name}) 总览图片已成功横向拼接至: {final_stitched_path}")

    # 5. 关闭赛果界面
    if close_result_rel:
        if check_stop_signal(context):
            logger.info(f"操作在关闭赛果界面前被取消 ({match_name})，但总览图已生成: {final_stitched_path}")
            return final_stitched_path # 总览图已生成

        logger.info(f"  ({match_name}) 点击关闭赛果界面: {close_result_rel}")
        if not click_coordinates(context, close_result_rel, nikke_window):
            logger.warning(f"  ({match_name}) 未能点击关闭赛果界面坐标 {close_result_rel}。")
            # 即使关闭失败，总览图已生成
        else:
            logger.info(f"  ({match_name}) 等待 {delay_after_close_result} 秒...")
            time.sleep(delay_after_close_result)
            if check_stop_signal(context):
                logger.info(f"操作在等待关闭赛果后被取消 ({match_name})，总览图: {final_stitched_path}")
                return final_stitched_path

    logger.info(f"比赛 {match_name} 处理完成。最终图片: {final_stitched_path}")
    return final_stitched_path

if __name__ == '__main__':
    # 配置基本的日志记录器以进行测试
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    print("match_processing.py 被直接运行 (通常作为模块导入)")
    # 此处可以添加测试 process_match_flow 的代码，但需要模拟 context 和相关配置