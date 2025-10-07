# core/automation_utils.py
import os
import time
import logging
import pyautogui
import pygetwindow
import win32gui
import win32con
import win32process
import psutil
from . import constants as core_constants


def check_stop_signal(context):
    """检查是否收到了停止信号，如果收到则记录并返回 True，否则返回 False。"""
    if hasattr(context, 'shared') and hasattr(context.shared, 'stop_requested') and context.shared.stop_requested:
        if hasattr(context, 'shared') and hasattr(context.shared, 'logger'):
            context.shared.logger.warning("检测到停止信号。")
        else:
            logging.warning("检测到停止信号 (context.shared.logger 不可用)。")
        return True
    return False


def _get_window_client_info(hwnd):
    """
    获取窗口客户区的几何信息。

    参数:
        hwnd: 窗口句柄

    返回:
        dict: 包含客户区信息的字典 {
            'left': 客户区左边界,
            'top': 客户区上边界,
            'width': 客户区宽度,
            'height': 客户区高度,
            'screen_left': 客户区左边界在屏幕上的坐标,
            'screen_top': 客户区上边界在屏幕上的坐标
        }
        如果获取失败返回 None
    """
    try:
        client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
        client_width = client_right - client_left
        client_height = client_bottom - client_top

        if client_width <= 0 or client_height <= 0:
            return None

        screen_client_left, screen_client_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))

        return {
            'left': client_left,
            'top': client_top,
            'width': client_width,
            'height': client_height,
            'screen_left': screen_client_left,
            'screen_top': screen_client_top
        }
    except Exception:
        return None


def _relative_to_screen(relative_coord, client_info):
    """
    将相对坐标转换为屏幕坐标。

    参数:
        relative_coord: 相对坐标 (x, y) 比例
        client_info: 从 _get_window_client_info 获取的客户区信息

    返回:
        tuple: (screen_x, screen_y) 屏幕坐标
    """
    screen_x = client_info['screen_left'] + round(relative_coord[0] * client_info['width'])
    screen_y = client_info['screen_top'] + round(relative_coord[1] * client_info['height'])
    return (screen_x, screen_y)


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

        client_info = _get_window_client_info(hwnd)
        if not client_info:
            logger.error("错误：无法获取窗口客户区信息。")
            return False

        screen_x, screen_y = _relative_to_screen(relative_coord, client_info)

        logger.info(f"相对坐标 {relative_coord} -> 屏幕坐标 ({screen_x}, {screen_y}) (基于窗口 '{window.title}' HWND:{hwnd} 的客户区 at [{client_info['screen_left']},{client_info['screen_top']}] size [{client_info['width']}x{client_info['height']}])")

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

        client_info = _get_window_client_info(hwnd)
        if not client_info:
            logger.error("错误：无法获取窗口客户区信息。")
            return False

        region_left = client_info['screen_left'] + round(relative_region[0] * client_info['width'])
        region_top = client_info['screen_top'] + round(relative_region[1] * client_info['height'])
        region_width = round(relative_region[2] * client_info['width'])
        region_height = round(relative_region[3] * client_info['height'])

        if region_width <= 0 or region_height <= 0:
             logger.error(f"计算得到的截图区域尺寸无效: 宽度={region_width}, 高度={region_height} (基于客户区大小 {client_info['width']}x{client_info['height']} 和相对区域 {relative_region})。")
             return False

        actual_region = (region_left, region_top, region_width, region_height)

        logger.info(f"相对区域 {relative_region} -> 屏幕区域 {actual_region} (基于窗口 '{window.title}' HWND:{hwnd} 的客户区 at [{client_info['screen_left']},{client_info['screen_top']}] size [{client_info['width']}x{client_info['height']}])")
        logger.info(f"正在截取区域 {actual_region} 并保存为 '{filename}'...")

        # 确保目录存在
        # 如果 filename 是绝对路径，os.path.dirname 可能返回空，所以需要检查
        dir_name = os.path.dirname(filename)
        if dir_name: # 只有当 dirname 不是空（即 filename 不是只有文件名）时才创建目录
            os.makedirs(dir_name, exist_ok=True)

        screenshot = pyautogui.screenshot(region=actual_region)
        screenshot.save(filename)
        logger.info(f"截图已保存为 '{filename}'")
        time.sleep(core_constants.POST_SCREENSHOT_DELAY)
        return True

    except Exception as e:
        logger.error(f"截取或保存截图 '{filename}' (相对区域 {relative_region}) 时出错: {e}")
        return False


def find_and_activate_window(context, selected_window_title_override: str = None, activate_now: bool = True):
    """
    查找与 core_constants.TARGET_PROCESS_NAME 关联且窗口标题匹配的窗口。
    如果 activate_now 为 True (默认)，则激活找到的窗口。
    优先使用 context.shared.selected_target_window_title (如果非 None)。
    如果 context.shared.selected_target_window_title 为 None (自动选择)，
    或提供了 selected_window_title_override，则按以下顺序确定目标标题：
    1. selected_window_title_override (如果提供)
    2. (如果上述都为 None) 遍历 core_constants.POSSIBLE_TARGET_WINDOW_TITLES 尝试查找。

    参数:
        context: 应用上下文。
        selected_window_title_override: 可选的窗口标题覆盖。
        activate_now: 布尔值，指示是否在找到窗口后立即激活它。默认为 True。
    返回:
        pygetwindow.Win32Window 对象如果找到窗口 (且如果 activate_now=True 则已激活)，否则返回 None。
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
    else: # GUI选择了"自动"或上下文标题不可用
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
        logger.info(f"正在尝试查找进程 '{target_process_name}' 且窗口标题为 '{title_to_match}' 的窗口 (激活: {activate_now})...")

        target_hwnd = None
        # 遍历找到的PID，查找与 PID 关联且标题匹配的窗口句柄 (HWND)
        for pid_to_check in found_pids:
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
                                break
                except Exception:
                    continue
            if target_hwnd:
                break

        if target_hwnd:
            if activate_now:
                logger.info(f"将激活窗口 HWND: {target_hwnd} (标题: '{title_to_match}')")
                try:
                    if win32gui.IsIconic(target_hwnd):
                        logger.info("窗口已最小化，正在恢复...")
                        win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                        time.sleep(core_constants.WINDOW_RESTORE_DELAY)

                    logger.info("正在激活窗口...")
                    try:
                        win32gui.SetForegroundWindow(target_hwnd)
                    except Exception as e_set_fg:
                        logger.warning(f"SetForegroundWindow 失败({e_set_fg})，尝试用 ShowWindow 激活...")
                        win32gui.ShowWindow(target_hwnd, win32con.SW_SHOW)
                        time.sleep(core_constants.POST_SHOW_WINDOW_DELAY)
                        win32gui.SetForegroundWindow(target_hwnd)

                    time.sleep(core_constants.POST_WINDOW_ACTIVATION_DELAY)

                    foreground_hwnd = win32gui.GetForegroundWindow()
                    if foreground_hwnd == target_hwnd:
                        logger.info(f"窗口 HWND {target_hwnd} ('{title_to_match}') 已成功激活并置于前台。")
                        try:
                            window = pygetwindow.Win32Window(target_hwnd)
                            return window
                        except Exception as e_pyget:
                            logger.warning(f"创建 pygetwindow 对象时出错（但不影响激活）: {e_pyget}")
                            # 即使创建 pygetwindow 对象失败，如果激活成功，也应该认为窗口已找到并激活
                            # 但为了返回一致的类型，这里可能还是返回 None，或者一个标记对象
                            return None # 或者返回一个特殊的标记表示激活成功但对象创建失败
                    else:
                        current_fg_title = "未知标题"
                        try:
                            current_fg_title = win32gui.GetWindowText(foreground_hwnd)
                        except: pass
                        logger.warning(f"尝试激活窗口 HWND {target_hwnd} ('{title_to_match}')，但当前前台窗口是 HWND {foreground_hwnd} ('{current_fg_title}')。")
                        # 激活失败，继续尝试下一个标题 (如果还有)
                except Exception as e_activate_main:
                    logger.error(f"激活窗口 HWND {target_hwnd} (标题 '{title_to_match}') 时发生意外错误: {e_activate_main}")
                    # 激活失败，继续尝试下一个标题 (如果还有)
            else: # activate_now is False
                logger.info(f"找到窗口 HWND: {target_hwnd} (标题: '{title_to_match}')，但不执行激活操作。")
                try:
                    window = pygetwindow.Win32Window(target_hwnd)
                    return window
                except Exception as e_pyget_no_activate:
                    logger.error(f"创建 pygetwindow 对象时出错 (未激活模式): {e_pyget_no_activate}")
                    return None
        else:
            logger.info(f"未找到标题为 '{title_to_match}' 的窗口。")

    logger.error(f"错误：尝试了所有指定/可能的标题 ({titles_to_try})，但未能找到 '{target_process_name}' 的窗口 (激活状态: {activate_now})。")
    return None


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

        client_info = _get_window_client_info(hwnd)
        if not client_info:
            logger.error(f"get_pixel_color_relative: 获取到的窗口客户区尺寸无效。")
            return None

        # 计算目标点在客户区内的绝对偏移量
        target_x_in_client = round(relative_coord[0] * client_info['width'])
        target_y_in_client = round(relative_coord[1] * client_info['height'])

        # 计算目标点在屏幕上的绝对坐标
        screen_x = client_info['screen_left'] + target_x_in_client
        screen_y = client_info['screen_top'] + target_y_in_client

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


def activate_nikke_window_if_needed(context):
    """
    如果 context.shared.nikke_window 存在且未激活，则尝试激活它。
    """
    logger = getattr(context.shared, 'logger', logging)
    nikke_window_obj = getattr(context.shared, 'nikke_window', None)

    if not nikke_window_obj:
        logger.info("activate_nikke_window_if_needed: NIKKE 窗口对象不存在于上下文中，无法激活。")
        return False

    try:
        target_hwnd = nikke_window_obj._hWnd
        if not target_hwnd:
            logger.error("activate_nikke_window_if_needed: 无法从 NIKKE 窗口对象获取 HWND。")
            return False

        foreground_hwnd = win32gui.GetForegroundWindow()
        if foreground_hwnd == target_hwnd:
            logger.info(f"activate_nikke_window_if_needed: NIKKE 窗口 (HWND {target_hwnd}) 已是前台窗口。")
            return True

        logger.info(f"activate_nikke_window_if_needed: 正在尝试激活 NIKKE 窗口 (HWND {target_hwnd}, Title: '{nikke_window_obj.title}')...")
        if win32gui.IsIconic(target_hwnd):
            logger.info("窗口已最小化，正在恢复...")
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            time.sleep(core_constants.WINDOW_RESTORE_DELAY) # 等待窗口恢复

        try:
            win32gui.SetForegroundWindow(target_hwnd)
        except Exception as e_set_fg: # pywintypes.error 可能发生
            logger.warning(f"SetForegroundWindow 失败({e_set_fg})，尝试用 ShowWindow 激活...")
            win32gui.ShowWindow(target_hwnd, win32con.SW_SHOW) # 尝试另一种方式显示
            time.sleep(core_constants.POST_SHOW_WINDOW_DELAY) # 短暂等待
            win32gui.SetForegroundWindow(target_hwnd) # 再次尝试置顶

        time.sleep(core_constants.POST_WINDOW_ACTIVATION_DELAY) # 等待激活操作生效

        final_foreground_hwnd = win32gui.GetForegroundWindow()
        if final_foreground_hwnd == target_hwnd:
            logger.info(f"NIKKE 窗口 (HWND {target_hwnd}) 已成功激活。")
            return True
        else:
            current_fg_title = "未知标题"
            try:
                current_fg_title = win32gui.GetWindowText(final_foreground_hwnd)
            except: pass
            logger.warning(f"尝试激活 NIKKE 窗口 (HWND {target_hwnd}) 后，当前前台窗口仍为 HWND {final_foreground_hwnd} ('{current_fg_title}')。")
            return False

    except AttributeError:
        logger.error("activate_nikke_window_if_needed: NIKKE 窗口对象无效或没有 _hWnd 属性。")
        return False
    except Exception as e:
        logger.error(f"activate_nikke_window_if_needed: 激活 NIKKE 窗口时发生错误: {e}")
        return False