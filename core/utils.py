# core/utils.py
import os
import sys
import time
import logging
import pyautogui
from PIL import Image
import pygetwindow
import win32gui
import win32con
import win32process
import psutil
import zipfile
from . import constants as core_constants

def get_asset_path(asset_name: str) -> str:
    """
    获取指定资源文件在 'assets' 目录下的绝对路径。
    如果项目根目录没有 'assets' 文件夹，或者需要更复杂的路径解析，
    此函数可能需要调整。

    参数:
        asset_name: 资源文件名 (例如 "image.png", "icon.ico")。

    返回:
        资源文件的绝对路径。
    """
    # 假设此 utils.py 文件位于 core 包内，即 project_root/core/utils.py
    # 我们需要找到项目根目录，然后拼接 "assets" 和 asset_name
    # 获取当前文件 (utils.py) 的目录: project_root/core/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取项目根目录: project_root/
    project_root = os.path.dirname(current_dir)
    # 构建到 assets 文件夹的路径
    assets_dir = os.path.join(project_root, "assets")
    return os.path.join(assets_dir, asset_name)

# --- 临时的常量和控制函数 (后续会移到 core.constants 和 core.runtime_control) ---
# ACTION_DELAY = 1.2  # 已迁移到 core_constants.UNIVERSAL_ACTION_DELAY

def check_stop_signal(context):
    """检查是否收到了停止信号，如果收到则记录并返回 True，否则返回 False。"""
    if hasattr(context, 'shared') and hasattr(context.shared, 'stop_requested') and context.shared.stop_requested:
        if hasattr(context, 'shared') and hasattr(context.shared, 'logger'):
            context.shared.logger.warning("检测到停止信号。")
        else:
            logging.warning("检测到停止信号 (context.shared.logger 不可用)。")
        return True
    return False
# --- 临时定义结束 ---


def click_coordinates(context, relative_coord: tuple, window: pygetwindow.Win32Window):
    """
    根据相对坐标和当前窗口尺寸/位置，计算实际屏幕坐标并模拟点击。
    相对坐标是 (比例X, 比例Y)，相对于窗口的客户区（内容区域）。
    """
    logger = getattr(context.shared, 'logger', logging)
    if check_stop_signal(context):
        logger.info("操作已取消 (click_coordinates)。")
        return False
    if not window:
        logger.error("错误 (click_coordinates): 'window' 参数无效 (None)。")
        return False
    try:
        hwnd = window._hWnd
        if not hwnd:
             logger.error("错误：无法从 pygetwindow 对象获取窗口句柄 (HWND)。")
             return False

        client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
        client_width = client_right - client_left
        client_height = client_bottom - client_top

        if client_width <= 0 or client_height <= 0:
             logger.error(f"错误：获取到的窗口客户区尺寸无效 (Width={client_width}, Height={client_height})。")
             return False

        screen_client_left, screen_client_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))

        screen_x = screen_client_left + round(relative_coord[0] * client_width)
        screen_y = screen_client_top + round(relative_coord[1] * client_height)

        logger.info(f"相对坐标 {relative_coord} -> 屏幕坐标 ({screen_x}, {screen_y}) (基于窗口 '{window.title}' HWND:{hwnd} 的客户区 at [{screen_client_left},{screen_client_top}] size [{client_width}x{client_height}])")

        pyautogui.moveTo(screen_x, screen_y, duration=0.2)
        pyautogui.click(screen_x, screen_y)
        time.sleep(core_constants.UNIVERSAL_ACTION_DELAY)
        return True

    except Exception as e:
        logger.error(f"计算或点击相对坐标 {relative_coord} 时出错: {e}")
        return False

def take_screenshot(context, relative_region: tuple, window: pygetwindow.Win32Window, filename: str):
    """
    根据相对区域定义和当前窗口尺寸/位置，计算实际屏幕区域并截图保存。
    相对区域格式: (rel_left, rel_top, rel_width, rel_height)
    (此函数从 _backup/c_arena_predition.py 迁移)
    """
    logger = getattr(context.shared, 'logger', logging)
    if not all(isinstance(val, (int, float)) for val in relative_region) or len(relative_region) != 4:
        logger.error(f"无效的相对截图区域格式: {relative_region}. 需要 (rel_left, rel_top, rel_width, rel_height)。")
        return False

    if check_stop_signal(context):
        logger.info("操作已取消 (take_screenshot)。")
        return False
    if not window:
        logger.error("错误 (take_screenshot): 'window' 参数无效 (None)。")
        return False
    try:
        hwnd = window._hWnd
        if not hwnd:
             logger.error("错误：无法从 pygetwindow 对象获取窗口句柄 (HWND)。")
             return False

        client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
        client_width = client_right - client_left
        client_height = client_bottom - client_top

        if client_width <= 0 or client_height <= 0:
             logger.error(f"错误：获取到的窗口客户区尺寸无效 (Width={client_width}, Height={client_height})。")
             return False

        screen_client_left, screen_client_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))

        region_left = screen_client_left + round(relative_region[0] * client_width)
        region_top = screen_client_top + round(relative_region[1] * client_height)
        region_width = round(relative_region[2] * client_width)
        region_height = round(relative_region[3] * client_height)

        if region_width <= 0 or region_height <= 0:
             logger.error(f"计算得到的截图区域尺寸无效: 宽度={region_width}, 高度={region_height} (基于客户区大小 {client_width}x{client_height} 和相对区域 {relative_region})。")
             return False

        actual_region = (region_left, region_top, region_width, region_height)

        logger.info(f"相对区域 {relative_region} -> 屏幕区域 {actual_region} (基于窗口 '{window.title}' HWND:{hwnd} 的客户区 at [{screen_client_left},{screen_client_top}] size [{client_width}x{client_height}])")
        logger.info(f"正在截取区域 {actual_region} 并保存为 '{filename}'...")

        # 确保目录存在
        # 如果 filename 是绝对路径，os.path.dirname 可能返回空，所以需要检查
        dir_name = os.path.dirname(filename)
        if dir_name: # 只有当 dirname 不是空（即 filename 不是只有文件名）时才创建目录
            os.makedirs(dir_name, exist_ok=True)

        screenshot = pyautogui.screenshot(region=actual_region)
        screenshot.save(filename)
        logger.info(f"截图已保存为 '{filename}'")
        time.sleep(0.2)
        return True

    except Exception as e:
        logger.error(f"截取或保存截图 '{filename}' (相对区域 {relative_region}) 时出错: {e}")
        return False

def stitch_images_vertically(context, image_paths: list, output_path: str):
    """
    将一系列图片从上到下垂直拼接成一张图片。
    """
    logger = getattr(context.shared, 'logger', logging)
    logger.info(f"开始垂直拼接图片到 '{output_path}'...")
    if check_stop_signal(context):
        logger.info("操作已取消 (stitch_images_vertically)。")
        return False
    if not image_paths:
        logger.warning("没有提供用于垂直拼接的图片路径。")
        return False

    images = []
    total_height = 0
    max_width = 0

    try:
        for path in image_paths:
            if not os.path.exists(path):
                logger.warning(f"跳过拼接：找不到图片文件 '{path}'")
                continue
            img = Image.open(path)
            images.append(img)
            total_height += img.height
            if img.width > max_width:
                max_width = img.width
            logger.debug(f"读取图片 '{path}' 尺寸: {img.size}")

        if not images:
             logger.error("无法打开任何有效的图片进行垂直拼接。")
             return False

        logger.debug(f"创建垂直拼接画布，尺寸: ({max_width}, {total_height})")
        stitched_image = Image.new('RGB', (max_width, total_height))

        current_y = 0
        for img in images:
            if check_stop_signal(context):
                logger.info("垂直拼接操作在循环中被中断。")
                # 清理已打开的图片
                for open_img in images: # images 列表包含了所有已成功打开的 Image 对象
                    try:
                        open_img.close()
                    except Exception as e_close:
                        logger.debug(f"关闭图片时出错 (中断后清理): {e_close}")
                return False # 或者根据需要返回部分结果的状态
            paste_x = (max_width - img.width) // 2
            stitched_image.paste(img, (paste_x, current_y))
            current_y += img.height
            # img.close() # 在循环结束后统一关闭

        for img in images: # 确保所有图片都被关闭
            try:
                img.close()
            except Exception as e_close:
                logger.debug(f"关闭图片时出错 (正常结束): {e_close}")


        # 确保目录存在
        dir_name = os.path.dirname(output_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        stitched_image.save(output_path)
        logger.info(f"垂直拼接完成，图片已保存为 '{output_path}'")
        return True
    except FileNotFoundError as e:
        logger.error(f"垂直拼接时找不到文件：{e}")
        return False
    except Exception as e:
        logger.error(f"垂直拼接图片时出错: {e}")
        for img in images: # 确保在异常情况下也尝试关闭图片
            try:
                img.close()
            except:
                pass
        return False

def find_and_activate_window(context, selected_window_title_override: str = None):
    """
    查找与 core_constants.TARGET_PROCESS_NAME 关联且窗口标题匹配的窗口，并将其激活。
    优先使用 context.shared.selected_target_window_title (如果非 None)。
    如果 context.shared.selected_target_window_title 为 None (自动选择)，
    或提供了 selected_window_title_override，则按以下顺序确定目标标题：
    1. selected_window_title_override (如果提供)
    2. (如果上述都为 None) 遍历 core_constants.POSSIBLE_TARGET_WINDOW_TITLES 尝试查找。
    """
    logger = getattr(context.shared, 'logger', logging)
    target_process_name = core_constants.TARGET_PROCESS_NAME
    
    title_from_context = None
    if hasattr(context, 'shared') and hasattr(context.shared, 'selected_target_window_title'):
        title_from_context = context.shared.selected_target_window_title

    titles_to_try = []

    if selected_window_title_override:
        logger.info(f"使用覆盖的窗口标题进行查找: '{selected_window_title_override}'")
        titles_to_try.append(selected_window_title_override)
    elif title_from_context is not None: # GUI选择了特定服务器
        logger.info(f"使用来自上下文的窗口标题进行查找: '{title_from_context}' (通常来自GUI选择)")
        titles_to_try.append(title_from_context)
    else: # GUI选择了“自动”或上下文标题不可用
        logger.info("未指定特定窗口标题 (上下文标题为 None 或 override 未提供)，将尝试所有已知标题 (自动模式)。")
        if core_constants.POSSIBLE_TARGET_WINDOW_TITLES:
            titles_to_try.extend(core_constants.POSSIBLE_TARGET_WINDOW_TITLES)
        else:
            logger.error("错误：自动模式下，core_constants.POSSIBLE_TARGET_WINDOW_TITLES 为空。无法查找窗口。")
            return None

    if not titles_to_try:
        logger.error("错误：没有可供尝试的窗口标题。")
        return None

    # 查找进程 PID (只需要执行一次)
    target_pid = None
    process_name_lower = target_process_name.lower()
    found_pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == process_name_lower:
                found_pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as e_proc:
            logger.warning(f"迭代进程时发生跳过错误: {e_proc}")
            continue

    if not found_pids:
        logger.error(f"错误：未找到正在运行的进程 '{target_process_name}'。请确保游戏已启动。")
        return None

    if len(found_pids) > 1:
        logger.warning(f"警告：找到多个名为 '{target_process_name}' 的进程实例 (PIDs: {found_pids})。将逐个检查其窗口。")

    # 遍历所有要尝试的标题
    for title_to_match in titles_to_try:
        logger.info(f"正在尝试查找进程 '{target_process_name}' 且窗口标题为 '{title_to_match}' 的窗口...")
        
        target_hwnd = None
        # 遍历找到的PID，查找与 PID 关联且标题匹配的窗口句柄 (HWND)
        for pid_to_check in found_pids:
            # logger.debug(f"检查 PID {pid_to_check} 的窗口 (针对标题 '{title_to_match}')...")
            top_windows = []
            try:
                win32gui.EnumWindows(lambda hwnd, param: param.append(hwnd), top_windows)
            except Exception as e_enum:
                logger.error(f"枚举 PID {pid_to_check} 的窗口时出错: {e_enum}")
                continue

            for hwnd_candidate in top_windows:
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd_candidate)
                    if pid == pid_to_check:
                        if win32gui.IsWindowVisible(hwnd_candidate):
                            current_window_title = win32gui.GetWindowText(hwnd_candidate)
                            if current_window_title == title_to_match:
                                logger.info(f"找到匹配窗口: PID={pid}, HWND={hwnd_candidate}, 标题='{current_window_title}'")
                                target_hwnd = hwnd_candidate
                                break # 找到完全匹配的窗口
                except Exception:
                    continue # 忽略无法获取信息的窗口
            if target_hwnd:
                break # 已找到目标窗口，无需再检查其他PID

        if target_hwnd: # 如果当前 title_to_match 找到了窗口
            logger.info(f"将激活窗口 HWND: {target_hwnd} (标题: '{title_to_match}')")
            try:
                if win32gui.IsIconic(target_hwnd):
                    logger.info("窗口已最小化，正在恢复...")
                    win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                    time.sleep(1.0)

                logger.info("正在激活窗口...")
                try:
                    win32gui.SetForegroundWindow(target_hwnd)
                except Exception as e_set_fg: # pywintypes.error 可能发生
                    logger.warning(f"SetForegroundWindow 失败({e_set_fg})，尝试用 ShowWindow 激活...")
                    win32gui.ShowWindow(target_hwnd, win32con.SW_SHOW)
                    time.sleep(0.1)
                    win32gui.SetForegroundWindow(target_hwnd)

                time.sleep(0.5)
                
                foreground_hwnd = win32gui.GetForegroundWindow()
                if foreground_hwnd == target_hwnd:
                    logger.info(f"窗口 HWND {target_hwnd} ('{title_to_match}') 已成功激活并置于前台。")
                    try:
                        window = pygetwindow.Win32Window(target_hwnd)
                        return window
                    except Exception as e_pyget:
                        logger.warning(f"创建 pygetwindow 对象时出错（但不影响激活）: {e_pyget}")
                        return None
                else:
                    current_fg_title = "未知标题"
                    try:
                        current_fg_title = win32gui.GetWindowText(foreground_hwnd)
                    except: pass
                    logger.warning(f"尝试激活窗口 HWND {target_hwnd} ('{title_to_match}')，但当前前台窗口是 HWND {foreground_hwnd} ('{current_fg_title}').")
                    # 继续尝试下一个标题 (如果还有)
            except Exception as e_activate_main:
                logger.error(f"激活窗口 HWND {target_hwnd} (标题 '{title_to_match}') 时发生意外错误: {e_activate_main}")
                # 继续尝试下一个标题 (如果还有)
        else: # 当前 title_to_match 未找到窗口
            logger.info(f"未找到标题为 '{title_to_match}' 的窗口。")

    # 如果遍历完所有 titles_to_try 都没有成功激活窗口
    logger.error(f"错误：尝试了所有指定/可能的标题 ({titles_to_try})，但未能找到并激活 '{target_process_name}' 的窗口。")
    return None

def process_image_to_webp(context, input_image_path: str, output_webp_dir: str, quality: int = 85, lossless: bool = False):
    """
    将指定的 PNG/JPG 图片转换为 WebP 格式。
    文件名将保持不变，只改变扩展名。

    参数:
        context: 应用上下文。
        input_image_path: 输入图片路径。
        output_webp_dir: WebP 图片的输出目录。
        quality: WebP 压缩质量 (1-100)，仅当 lossless=False 时有效。
        lossless: 是否使用无损压缩。
    """
    logger = getattr(context.shared, 'logger', logging)
    if check_stop_signal(context):
        logger.info("操作已取消 (process_image_to_webp)。")
        return None

    if not os.path.exists(input_image_path):
        logger.error(f"输入图片文件不存在: {input_image_path}")
        return None

    try:
        img = Image.open(input_image_path)
        base_filename = os.path.basename(input_image_path)
        name_without_ext = os.path.splitext(base_filename)[0]
        output_webp_filename = f"{name_without_ext}.webp"
        output_webp_path = os.path.join(output_webp_dir, output_webp_filename)

        os.makedirs(output_webp_dir, exist_ok=True)

        save_params = {'format': 'WEBP'}
        if lossless:
            save_params['lossless'] = True
            # Pillow 文档指出，当 lossless=True 时，quality 参数会被忽略，但一些版本可能仍接受它。
            # 为了清晰，可以只在有损压缩时明确传递 quality。
            # 或者，如果 Pillow 版本支持，可以同时传递 lossless=True 和 method=6 (最慢但压缩最好)
            # save_params['method'] = 6
        else:
            save_params['quality'] = quality
        
        # 处理透明度：如果图像有alpha通道 (RGBA)，转换为 RGB 以避免某些 WebP 查看器的问题
        # 或者，如果需要保留透明度，确保 Pillow 和 WebP 库支持
        if img.mode == 'RGBA' or img.mode == 'LA' or (img.mode == 'P' and 'transparency' in img.info):
            # 如果目标是无损且需要保留透明度
            if lossless:
                 logger.debug(f"图片 '{input_image_path}' (模式: {img.mode}) 包含透明度，将尝试无损保存以保留。")
            else:
            # 对于有损压缩，通常最好转换为RGB，除非明确需要带alpha的有损WebP
                 logger.debug(f"图片 '{input_image_path}' (模式: {img.mode}) 包含透明度，将转换为 RGB 后进行有损压缩。")
                 img = img.convert('RGB')
        
        img.save(output_webp_path, **save_params)
        logger.info(f"图片 '{input_image_path}' 已成功转换为 WebP (lossless={lossless}, quality={quality if not lossless else 'N/A'}) 并保存至 '{output_webp_path}'")
        img.close()
        return output_webp_path
    except FileNotFoundError:
        logger.error(f"打开图片失败，文件未找到: {input_image_path}")
        return None
    except Exception as e:
        logger.error(f"处理图片 '{input_image_path}' 到 WebP 时出错: {e}")
        if 'img' in locals() and hasattr(img, 'close'):
            img.close()
        return None

def create_zip_archive(context, source_dir_to_zip: str, zip_file_path: str):
    """
    将指定目录的内容打包成一个 ZIP 文件。
    """
    logger = getattr(context.shared, 'logger', logging)
    if check_stop_signal(context):
        logger.info("操作已取消 (create_zip_archive)。")
        return False

    if not os.path.isdir(source_dir_to_zip):
        logger.error(f"源目录不存在或不是一个目录: {source_dir_to_zip}")
        return False

    # 确保目标 ZIP 文件的目录存在
    zip_dir = os.path.dirname(zip_file_path)
    if zip_dir: # 如果 zip_file_path 包含目录
        os.makedirs(zip_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(source_dir_to_zip):
                if check_stop_signal(context):
                    logger.warning(f"打包操作在遍历目录 '{root}' 时被中断。")
                    # ZipFile 会在退出 with 块时自动关闭，部分写入的文件会保留。
                    # 如果需要，可以在这里尝试删除部分创建的 zip 文件。
                    # os.remove(zip_file_path) # 但这可能导致数据丢失，需谨慎
                    return False # 指示操作未完成
                for file in files:
                    if check_stop_signal(context):
                        logger.warning(f"打包操作在添加文件 '{file}' 时被中断。")
                        return False
                    file_path = os.path.join(root, file)
                    # arcname 是文件在 zip 包内的相对路径
                    arcname = os.path.relpath(file_path, source_dir_to_zip)
                    zipf.write(file_path, arcname)
                    logger.debug(f"已添加 '{file_path}' 到 ZIP 存档为 '{arcname}'")
        logger.info(f"目录 '{source_dir_to_zip}' 已成功打包到 '{zip_file_path}'")
        return True
    except Exception as e:
        logger.error(f"创建 ZIP 存档 '{zip_file_path}' 从目录 '{source_dir_to_zip}' 时出错: {e}")
        # 如果发生错误，可以考虑删除可能已创建的不完整 zip 文件
        if os.path.exists(zip_file_path):
            try:
                os.remove(zip_file_path)
                logger.info(f"已删除因错误而可能不完整的 ZIP 文件: {zip_file_path}")
            except Exception as e_remove:
                logger.warning(f"删除不完整的 ZIP 文件 '{zip_file_path}' 时失败: {e_remove}")
        return False

def stitch_images_horizontally(context, image_paths: list, output_path: str, alignment: str = 'center', spacing: int = 10, bg_color=(255, 255, 255)):
    """
    将一系列图片从左到右水平拼接成一张图片。

    参数:
        context: 应用上下文对象。
        image_paths: 要拼接的图片文件路径列表。
        output_path: 输出拼接图片的路径。
        alignment: 垂直对齐方式 ('top', 'center', 'bottom')。
        spacing: 图片之间的水平间距 (像素)。
        bg_color: 画布背景颜色 (RGB元组)。
    返回:
        bool: 成功返回 True, 失败返回 False。
    """
    logger = getattr(context.shared, 'logger', logging)
    logger.info(f"开始水平拼接图片到 '{output_path}' (对齐: {alignment}, 间距: {spacing})...")

    if check_stop_signal(context):
        logger.info("操作已取消 (stitch_images_horizontally)。")
        return False

    if not image_paths:
        logger.warning("没有提供用于水平拼接的图片路径。")
        return False

    images = []
    total_width = 0
    max_height = 0

    try:
        for i, path in enumerate(image_paths):
            if check_stop_signal(context):
                logger.info(f"水平拼接在加载图片 {i+1} ('{path}') 前被中断。")
                for img_obj in images: img_obj.close()
                return False
            if not os.path.exists(path):
                logger.warning(f"跳过拼接：找不到图片文件 '{path}'")
                continue
            img = Image.open(path)
            images.append(img)
            total_width += img.width
            if img.height > max_height:
                max_height = img.height
            logger.debug(f"读取图片 '{path}' 尺寸: {img.size}")

        if not images:
            logger.error("无法打开任何有效的图片进行水平拼接。")
            return False

        # 加上图片间的间距
        if len(images) > 1:
            total_width += spacing * (len(images) - 1)

        logger.debug(f"创建水平拼接画布，尺寸: ({total_width}, {max_height}), 背景色: {bg_color}")
        stitched_image = Image.new('RGB', (total_width, max_height), color=bg_color)

        current_x = 0
        for i, img in enumerate(images):
            if check_stop_signal(context):
                logger.info(f"水平拼接在粘贴图片 {i+1} ('{img.filename if hasattr(img, 'filename') else 'N/A'}') 前被中断。")
                for img_obj in images: img_obj.close() # 关闭所有已打开的
                # stitched_image.close() # Pillow Image 对象没有 close 方法
                return False

            paste_y = 0
            if alignment == 'center':
                paste_y = (max_height - img.height) // 2
            elif alignment == 'bottom':
                paste_y = max_height - img.height
            # 'top' alignment is paste_y = 0 (default)

            stitched_image.paste(img, (current_x, paste_y))
            current_x += img.width + spacing
            # img.close() # 在循环结束后统一关闭

        for img in images: # 确保所有图片都被关闭
            try:
                img.close()
            except Exception as e_close:
                logger.debug(f"关闭图片时出错 (正常结束 - 水平拼接): {e_close}")

        # 确保目录存在
        dir_name = os.path.dirname(output_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        stitched_image.save(output_path)
        logger.info(f"水平拼接完成，图片已保存为 '{output_path}'")
        return True
    except FileNotFoundError as e:
        logger.error(f"水平拼接时找不到文件：{e}")
        for img_obj in images: img_obj.close()
        return False
    except Exception as e:
        logger.error(f"水平拼接图片时出错: {e}")
        for img_obj in images: # 确保在异常情况下也尝试关闭图片
            try:
                img_obj.close()
            except:
                pass
        return False

def stitch_mode4_overview(context, image_paths: list, output_path: str, spacing_major: int = 60, spacing_minor: int = 30, background_color=(0, 0, 0)):
    """
    将8张图片分成两行（每行4张）并拼接成一张总览图。
    - 第1行: 图片 1, 2, 3, 4
    - 第2行: 图片 5, 6, 7, 8
    - 间距:
        - (1,2), (3,4), (5,6), (7,8) 之间为 spacing_minor
        - (2,3), (6,7) 之间为 spacing_major
        - 第1行和第2行之间为 spacing_major
    - 背景颜色由 background_color 指定。
    """
    logger = getattr(context.shared, 'logger', logging)
    logger.info(f"开始为模式4/5拼接总览图到 '{output_path}' (主间距: {spacing_major}, 次间距: {spacing_minor}, 背景: {background_color})...")
    
    if check_stop_signal(context):
        logger.info("操作已取消 (stitch_mode4_overview)。")
        return None # 返回 None 表示失败或未完成

    if not image_paths or len(image_paths) != 8:
        logger.error(f"需要8张图片进行模式4/5总览图拼接，但收到了 {len(image_paths) if image_paths else 0} 张。")
        return None

    images_opened = [] # 用于确保所有打开的图片都被关闭
    try:
        for i, path in enumerate(image_paths):
            if check_stop_signal(context):
                logger.info(f"拼接操作在加载图片 {i+1} ('{path}') 前被中断。")
                for img_obj in images_opened: img_obj.close()
                return None
            if not os.path.exists(path):
                logger.error(f"找不到图片文件 '{path}' (图片 {i+1})，无法进行拼接。")
                for img_obj in images_opened: img_obj.close()
                return None
            img = Image.open(path)
            images_opened.append(img)
        
        # 假设所有图片尺寸相同，基于第一张图片
        img_width, img_height = images_opened[0].size
        if img_width <= 0 or img_height <= 0:
            logger.error(f"图片尺寸无效: {img_width}x{img_height}。")
            for img_obj in images_opened: img_obj.close()
            return None

        # 计算画布尺寸
        row_width = (img_width * 4) + (spacing_minor * 2) + spacing_major
        canvas_height = (img_height * 2) + spacing_major
        canvas_width = row_width

        logger.debug(f"单张图片尺寸: {img_width}x{img_height}")
        logger.debug(f"画布尺寸: {canvas_width}x{canvas_height}")

        stitched_image = Image.new('RGB', (canvas_width, canvas_height), color=background_color)

        # 粘贴图片 - 第1行
        current_x_r1 = 0
        stitched_image.paste(images_opened[0], (current_x_r1, 0))
        current_x_r1 += img_width + spacing_minor
        stitched_image.paste(images_opened[1], (current_x_r1, 0))
        current_x_r1 += img_width + spacing_major
        stitched_image.paste(images_opened[2], (current_x_r1, 0))
        current_x_r1 += img_width + spacing_minor
        stitched_image.paste(images_opened[3], (current_x_r1, 0))

        # 粘贴图片 - 第2行
        row2_y_offset = img_height + spacing_major
        current_x_r2 = 0
        stitched_image.paste(images_opened[4], (current_x_r2, row2_y_offset))
        current_x_r2 += img_width + spacing_minor
        stitched_image.paste(images_opened[5], (current_x_r2, row2_y_offset))
        current_x_r2 += img_width + spacing_major
        stitched_image.paste(images_opened[6], (current_x_r2, row2_y_offset))
        current_x_r2 += img_width + spacing_minor
        stitched_image.paste(images_opened[7], (current_x_r2, row2_y_offset))

        # 调用者应确保 output_path 是唯一的，并且其目录已创建。
        # 此函数现在直接使用传入的 output_path。
        final_output_path_to_save = output_path # 直接使用传入的路径

        # 确保目录存在 (虽然调用者也可能已创建，但再次检查无害)
        dir_name = os.path.dirname(final_output_path_to_save)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        stitched_image.save(final_output_path_to_save)
        logger.info(f"模式4/5总览图拼接完成，图片已保存为 '{final_output_path_to_save}'")
        return final_output_path_to_save # 返回实际保存的路径

    except FileNotFoundError as e: # Should be caught by os.path.exists earlier
        logger.error(f"拼接模式4/5总览图时找不到文件：{e}")
        return None
    except Exception as e:
        logger.error(f"拼接模式4/5总览图时出错: {e}")
        # import traceback # 用于调试
        # traceback.print_exc()
        return None
    finally:
        for img_obj in images_opened: # 确保关闭所有图片对象
            try:
                img_obj.close()
            except: # nosec
                pass

def get_pixel_color_relative(context, window: pygetwindow.Win32Window, relative_coord: tuple):
    """
    获取指定窗口内相对坐标点的像素颜色。
    使用 win32gui 获取客户区坐标以提高准确性。
    """
    logger = getattr(context.shared, 'logger', logging)
    if not window:
        logger.error("get_pixel_color_relative: NIKKE 窗口对象无效。")
        return None

    try:
        hwnd = window._hWnd
        if not hwnd:
            logger.error("get_pixel_color_relative: 无法从 pygetwindow 对象获取窗口句柄 (HWND)。")
            return None

        client_left_rel, client_top_rel, client_right_rel, client_bottom_rel = win32gui.GetClientRect(hwnd)
        client_width = client_right_rel - client_left_rel
        client_height = client_bottom_rel - client_top_rel

        if client_width <= 0 or client_height <= 0:
            logger.error(f"get_pixel_color_relative: 获取到的窗口客户区尺寸无效 (Width={client_width}, Height={client_height})。")
            return None

        # 将客户区左上角转换为屏幕坐标
        screen_client_left, screen_client_top = win32gui.ClientToScreen(hwnd, (client_left_rel, client_top_rel))

        # 计算目标点在客户区内的绝对偏移量
        target_x_in_client = round(relative_coord[0] * client_width)
        target_y_in_client = round(relative_coord[1] * client_height)
        
        # 计算目标点在屏幕上的绝对坐标
        screen_x = screen_client_left + target_x_in_client
        screen_y = screen_client_top + target_y_in_client

        screen_w_pyautogui, screen_h_pyautogui = pyautogui.size()
        if 0 <= screen_x < screen_w_pyautogui and 0 <= screen_y < screen_h_pyautogui:
            color = pyautogui.pixel(screen_x, screen_y)
            logger.debug(f"get_pixel_color_relative: 颜色 @ rel {relative_coord} (abs client {target_x_in_client},{target_y_in_client}; abs screen {screen_x},{screen_y}) -> RGB: {color}")
            return color
        else:
            logger.error(f"get_pixel_color_relative: 计算的屏幕坐标 ({screen_x},{screen_y}) 超出屏幕范围 ({screen_w_pyautogui}x{screen_h_pyautogui})。")
            return None
    except Exception as e:
        logger.error(f"get_pixel_color_relative: 获取相对坐标 {relative_coord} 的像素颜色时出错: {e}")
        return None

def get_or_create_mode_output_subdir(context, mode_identifier, subdir_basename=None) -> str:
    """
    获取或创建指定模式的输出子目录路径。
    子目录将在 context.shared.base_output_dir 下创建。

    参数:
        context: 应用上下文。
        mode_identifier: 模式的标识符 (例如数字 1, 2, 或字符串 "mode1", "mode2_custom")。
        subdir_basename: 子目录的基础名称 (例如 "predictions", "reviews")。
                         如果为 None，则默认为 "modeX_output" (X是模式编号) 或 "mode_custom_output"。
    返回:
        成功则返回子目录的绝对路径，失败则返回 None。
    """
    logger = getattr(context.shared, 'logger', logging)
    base_output_dir = getattr(context.shared, 'base_output_dir', None)

    if not base_output_dir:
        logger.error("get_or_create_mode_output_subdir: context.shared.base_output_dir 未设置。")
        return None

    if subdir_basename:
        # 如果提供了 subdir_basename，我们通常会将其与模式标识符结合，或者直接使用它
        # 为保持与审查建议的一致性，这里允许 subdir_basename 直接作为子目录名的一部分
        # 例如 mode_identifier=1, subdir_basename="predictions" -> "mode1_predictions"
        # 或者，如果 subdir_basename 已经包含了模式信息，如 "mode1_specific_outputs"，也可以
        # 为了简单和明确，我们约定 mode_identifier 用于构建一个父级模式目录，subdir_basename 在其下
        # 或者，如果 subdir_basename 意图是完整的子目录名，则 mode_identifier 仅用于日志/区分
        
        # 按照审查建议的例子: core_utils.get_or_create_mode_output_subdir(context, 1, "predictions")
        # 这暗示最终目录可能是 base_output_dir / "mode1_predictions" 或 base_output_dir / "mode1" / "predictions"
        # 我们选择更简单的结构: base_output_dir / f"mode{mode_identifier}_{subdir_basename}"
        # 或者如果 subdir_basename 已经很具体，就直接用它，但加上模式前缀以防冲突
        if str(mode_identifier) not in subdir_basename: # 避免 "mode1_mode1_predictions"
            final_subdir_name = f"mode{mode_identifier}_{subdir_basename}"
        else:
            final_subdir_name = subdir_basename
    else:
        final_subdir_name = f"mode{mode_identifier}_output"

    mode_output_dir = os.path.join(base_output_dir, final_subdir_name)

    try:
        os.makedirs(mode_output_dir, exist_ok=True)
        logger.info(f"确保模式输出子目录 '{mode_output_dir}' 已创建。")
        return mode_output_dir
    except OSError as e:
        logger.error(f"创建模式输出子目录 '{mode_output_dir}' 失败: {e}")
        return None
    except Exception as e_unhandled:
        logger.error(f"创建模式输出子目录 '{mode_output_dir}' 时发生未预料的错误: {e_unhandled}")
        return None

def parse_color_string(color_str: str, logger_obj=None) -> tuple:
    """
    将逗号分隔的RGB颜色字符串 (例如 "255,0,0") 解析为RGB元组。
    如果解析失败，记录错误并返回默认颜色 (0,0,0)。
    """
    logger = logger_obj if logger_obj else logging.getLogger(__name__) # 使用传入的 logger 或默认 logger
    try:
        parts = list(map(int, color_str.split(',')))
        if len(parts) == 3:
            return tuple(parts)
        else:
            logger.warning(f"颜色字符串 '{color_str}' 格式不正确 (需要3个部分)，将使用默认颜色 (0,0,0)。")
            return (0, 0, 0)
    except ValueError:
        logger.warning(f"解析颜色字符串 '{color_str}' 时出错 (非整数值)，将使用默认颜色 (0,0,0)。")
        return (0, 0, 0)
    except Exception as e:
        logger.error(f"解析颜色字符串 '{color_str}' 时发生未知错误: {e}，将使用默认颜色 (0,0,0)。")
        return (0, 0, 0)

def generate_unique_filepath(output_dir: str, base_filename: str, logger_obj=None) -> str:
    """
    在指定的输出目录中为给定的基础文件名生成一个唯一的文件路径。
    如果原始路径已存在，则在文件名（扩展名前）附加 "_counter"。

    参数:
        output_dir: 文件将保存的目录。
        base_filename: 原始文件名 (例如 "image.png")。
        logger_obj: 可选的 logger 对象。

    返回:
        唯一的绝对文件路径。
    """
    logger = logger_obj if logger_obj else logging.getLogger(__name__)

    if not output_dir or not base_filename:
        logger.error("generate_unique_filepath: output_dir 和 base_filename 不能为空。")
        # 返回一个不太可能存在的路径，或者抛出异常
        return os.path.join(output_dir or ".", base_filename or "error_filename.err")

    filepath = os.path.join(output_dir, base_filename)
    
    if not os.path.exists(filepath):
        return filepath

    # 文件已存在，尝试生成唯一名称
    name_part, ext_part = os.path.splitext(base_filename)
    counter = 1
    while True:
        new_filename = f"{name_part}_{counter}{ext_part}"
        new_filepath = os.path.join(output_dir, new_filename)
        if not os.path.exists(new_filepath):
            logger.info(f"文件路径 '{filepath}' 已存在。将使用唯一路径 '{new_filepath}'。")
            return new_filepath
        counter += 1
        if counter > 1000: # 防止无限循环
            logger.error(f"尝试为 '{base_filename}' 生成唯一文件名失败次数过多。最后尝试: '{new_filepath}'。")
            return new_filepath # 或者抛出异常

def get_timestamp_for_filename():
    """返回当前时间的 YYYYMMDD_HHMMSS 格式字符串，用于文件名。"""
    return time.strftime("%Y%m%d_%H%M%S")
if __name__ == '__main__':
    print("core/utils.py 被直接运行 (通常作为模块导入)")
