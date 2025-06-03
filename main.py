import ctypes
import sys
import os
import pygetwindow
import pyautogui
import time
from PIL import Image
import keyboard
import logging
import psutil
import win32gui
import win32process
import win32con
import shutil


# --- 配置日志记录 ---
# 设置日志记录器
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()]) # 输出到控制台

# --- 全局变量和常量 ---
# Mode will be selected by user input later
CURRENT_MODE = None 

# [保留之前的常量...]
BASE_WIDTH = 3840
BASE_HEIGHT = 2160
stop_script = False # 控制脚本停止的标志
WINDOW_TITLE = "NIKKE" # 严格匹配的窗口标题
STOP_HOTKEY = "ctrl+1" # 停止脚本的热键

# 绝对坐标定义 (基于 BASE_WIDTH, BASE_HEIGHT)
# 这些将不再直接使用，而是用来计算相对比例
_PLAYER1_COORD_ABS = (1671, 691)
_PLAYER2_COORD_ABS = (2175, 669)
_EXIT_COORD_ABS = (2370, 681)
_TEAM_COORDS_ABS = [
    (1515, 1064), # team1
    (1734, 1064), # team2
    (1928, 1064), # team3
    (2112, 1064), # team4
    (2303, 1064)  # team5
]
# 截图区域绝对坐标 (左上角 和 右下角)
_SCREENSHOT_LEFT_ABS = 1433
_SCREENSHOT_TOP_ABS = 1134
_SCREENSHOT_RIGHT_ABS = 2417
_SCREENSHOT_BOTTOM_ABS = 1530

# 新增：玩家信息截图区域绝对坐标
_PLAYER_INFO_LEFT_ABS = 1433
_PLAYER_INFO_TOP_ABS = 768
_PLAYER_INFO_RIGHT_ABS = 2417
_PLAYER_INFO_BOTTOM_ABS = 963

# 新增：详细信息点击坐标点
_PLAYER_DETAILINFO_2_ABS = (1560, 866)
_PLAYER_DETAILINFO_3_ABS = (2200, 2000)
_PLAYER_DETAILINFO_CLOSE_ABS = (3500, 200)

# 新增：玩家信息2截图区域绝对坐标
_PLAYER_INFO_2_LEFT_ABS = 1433
_PLAYER_INFO_2_TOP_ABS = 1344
_PLAYER_INFO_2_RIGHT_ABS = 2417
_PLAYER_INFO_2_BOTTOM_ABS = 1529

# 新增：玩家信息3截图区域绝对坐标
_PLAYER_INFO_3_LEFT_ABS = 1433
_PLAYER_INFO_3_TOP_ABS = 1768
_PLAYER_INFO_3_RIGHT_ABS = 2417
_PLAYER_INFO_3_BOTTOM_ABS = 1850

# 新增：People Vote 区域绝对坐标
_PEOPLE_VOTE_LEFT_ABS = 1395
_PEOPLE_VOTE_TOP_ABS = 285
_PEOPLE_VOTE_RIGHT_ABS = 2433
_PEOPLE_VOTE_BOTTOM_ABS = 1944

# Mode 2 Specific Absolute Coordinates
_PLAYER1_COORD_ABS_M2 = (1540, 1083)
_PLAYER2_COORD_ABS_M2 = (2176, 1083)
_RESULT_SCREENSHOT_LEFT_ABS = 1600
_RESULT_SCREENSHOT_TOP_ABS = 958
_RESULT_SCREENSHOT_RIGHT_ABS = 2109
_RESULT_SCREENSHOT_BOTTOM_ABS = 1651

# Mode 4 Specific Absolute Coordinates (64in8)
_64IN8_PLAYER1_COORD_ABS_M4 = (1430, 760)
_64IN8_PLAYER2_COORD_ABS_M4 = (1430, 1036)
_64IN8_PLAYER3_COORD_ABS_M4 = (2411, 760)
_64IN8_PLAYER4_COORD_ABS_M4 = (2411, 1036)
_64IN8_PLAYER5_COORD_ABS_M4 = (1430, 1555)
_64IN8_PLAYER6_COORD_ABS_M4 = (1430, 1825)
_64IN8_PLAYER7_COORD_ABS_M4 = (2411, 1555)
_64IN8_PLAYER8_COORD_ABS_M4 = (2411, 1825)

# Mode 5 Specific Absolute Coordinates (Champion Arena)
_CHAMPION_PLAYER1_COORD_ABS_M5 = (1428, 690)
_CHAMPION_PLAYER2_COORD_ABS_M5 = (1428, 960)
_CHAMPION_PLAYER3_COORD_ABS_M5 = (2408, 690)
_CHAMPION_PLAYER4_COORD_ABS_M5 = (2408, 960)
_CHAMPION_PLAYER5_COORD_ABS_M5 = (1428, 1480)
_CHAMPION_PLAYER6_COORD_ABS_M5 = (1428, 1750)
_CHAMPION_PLAYER7_COORD_ABS_M5 = (2408, 1480)
_CHAMPION_PLAYER8_COORD_ABS_M5 = (2408, 1750)
# --- 将绝对坐标转换为相对比例 ---
# 在脚本加载时计算一次相对比例
def calculate_relative_coords(abs_coords, base_w, base_h):
    """将绝对坐标列表或元组转换为相对比例列表或元组"""
    if isinstance(abs_coords, tuple): # 单个坐标
       return (abs_coords[0] / base_w, abs_coords[1] / base_h)
    elif isinstance(abs_coords, list): # 坐标列表
       return [(x / base_w, y / base_h) for x, y in abs_coords]
    else:
        raise TypeError("输入必须是元组或列表")

# 计算相对比例并存储（这些将在运行时使用）
PLAYER1_COORD_REL = calculate_relative_coords(_PLAYER1_COORD_ABS, BASE_WIDTH, BASE_HEIGHT)
PLAYER2_COORD_REL = calculate_relative_coords(_PLAYER2_COORD_ABS, BASE_WIDTH, BASE_HEIGHT)
EXIT_COORD_REL = calculate_relative_coords(_EXIT_COORD_ABS, BASE_WIDTH, BASE_HEIGHT)
TEAM_COORDS_REL = calculate_relative_coords(_TEAM_COORDS_ABS, BASE_WIDTH, BASE_HEIGHT)

# 计算截图区域的相对位置和大小
SCREENSHOT_REL_LEFT = _SCREENSHOT_LEFT_ABS / BASE_WIDTH
SCREENSHOT_REL_TOP = _SCREENSHOT_TOP_ABS / BASE_HEIGHT
SCREENSHOT_REL_WIDTH = (_SCREENSHOT_RIGHT_ABS - _SCREENSHOT_LEFT_ABS) / BASE_WIDTH
SCREENSHOT_REL_HEIGHT = (_SCREENSHOT_BOTTOM_ABS - _SCREENSHOT_TOP_ABS) / BASE_HEIGHT
SCREENSHOT_REGION_REL = (
    SCREENSHOT_REL_LEFT, 
    SCREENSHOT_REL_TOP, 
    SCREENSHOT_REL_WIDTH, 
    SCREENSHOT_REL_HEIGHT
)

# 计算玩家信息截图区域的相对位置和大小
PLAYER_INFO_REL_LEFT = _PLAYER_INFO_LEFT_ABS / BASE_WIDTH
PLAYER_INFO_REL_TOP = _PLAYER_INFO_TOP_ABS / BASE_HEIGHT
PLAYER_INFO_REL_WIDTH = (_PLAYER_INFO_RIGHT_ABS - _PLAYER_INFO_LEFT_ABS) / BASE_WIDTH
PLAYER_INFO_REL_HEIGHT = (_PLAYER_INFO_BOTTOM_ABS - _PLAYER_INFO_TOP_ABS) / BASE_HEIGHT
PLAYER_INFO_REGION_REL = (
    PLAYER_INFO_REL_LEFT,
    PLAYER_INFO_REL_TOP,
    PLAYER_INFO_REL_WIDTH,
    PLAYER_INFO_REL_HEIGHT
)

# 计算新增点击点的相对坐标
PLAYER_DETAILINFO_2_REL = calculate_relative_coords(_PLAYER_DETAILINFO_2_ABS, BASE_WIDTH, BASE_HEIGHT)
PLAYER_DETAILINFO_3_REL = calculate_relative_coords(_PLAYER_DETAILINFO_3_ABS, BASE_WIDTH, BASE_HEIGHT)
PLAYER_DETAILINFO_CLOSE_REL = calculate_relative_coords(_PLAYER_DETAILINFO_CLOSE_ABS, BASE_WIDTH, BASE_HEIGHT)

# 计算玩家信息2截图区域的相对位置和大小
PLAYER_INFO_2_REL_LEFT = _PLAYER_INFO_2_LEFT_ABS / BASE_WIDTH
PLAYER_INFO_2_REL_TOP = _PLAYER_INFO_2_TOP_ABS / BASE_HEIGHT
PLAYER_INFO_2_REL_WIDTH = (_PLAYER_INFO_2_RIGHT_ABS - _PLAYER_INFO_2_LEFT_ABS) / BASE_WIDTH
PLAYER_INFO_2_REL_HEIGHT = (_PLAYER_INFO_2_BOTTOM_ABS - _PLAYER_INFO_2_TOP_ABS) / BASE_HEIGHT
PLAYER_INFO_2_REGION_REL = (
    PLAYER_INFO_2_REL_LEFT,
    PLAYER_INFO_2_REL_TOP,
    PLAYER_INFO_2_REL_WIDTH,
    PLAYER_INFO_2_REL_HEIGHT
)

# 计算玩家信息3截图区域的相对位置和大小
# 使用修正后的 _PLAYER_INFO_3_BOTTOM_ABS
PLAYER_INFO_3_REL_LEFT = _PLAYER_INFO_3_LEFT_ABS / BASE_WIDTH
PLAYER_INFO_3_REL_TOP = _PLAYER_INFO_3_TOP_ABS / BASE_HEIGHT
PLAYER_INFO_3_REL_WIDTH = (_PLAYER_INFO_3_RIGHT_ABS - _PLAYER_INFO_3_LEFT_ABS) / BASE_WIDTH
PLAYER_INFO_3_REL_HEIGHT = (_PLAYER_INFO_3_BOTTOM_ABS - _PLAYER_INFO_3_TOP_ABS) / BASE_HEIGHT # 使用修正后的值
PLAYER_INFO_3_REGION_REL = (
    PLAYER_INFO_3_REL_LEFT,
    PLAYER_INFO_3_REL_TOP,
    PLAYER_INFO_3_REL_WIDTH,
    PLAYER_INFO_3_REL_HEIGHT
)

# 计算 People Vote 截图区域的相对位置和大小
PEOPLE_VOTE_REL_LEFT = _PEOPLE_VOTE_LEFT_ABS / BASE_WIDTH
PEOPLE_VOTE_REL_TOP = _PEOPLE_VOTE_TOP_ABS / BASE_HEIGHT
PEOPLE_VOTE_REL_WIDTH = (_PEOPLE_VOTE_RIGHT_ABS - _PEOPLE_VOTE_LEFT_ABS) / BASE_WIDTH
PEOPLE_VOTE_REL_HEIGHT = (_PEOPLE_VOTE_BOTTOM_ABS - _PEOPLE_VOTE_TOP_ABS) / BASE_HEIGHT
PEOPLE_VOTE_REGION_REL = (
    PEOPLE_VOTE_REL_LEFT,
    PEOPLE_VOTE_REL_TOP,
    PEOPLE_VOTE_REL_WIDTH,
    PEOPLE_VOTE_REL_HEIGHT
)


# Calculate relative coords for Mode 2
PLAYER1_COORD_REL_M2 = calculate_relative_coords(_PLAYER1_COORD_ABS_M2, BASE_WIDTH, BASE_HEIGHT)
PLAYER2_COORD_REL_M2 = calculate_relative_coords(_PLAYER2_COORD_ABS_M2, BASE_WIDTH, BASE_HEIGHT)

# Calculate relative region for Mode 2 initial screenshot
RESULT_SCREENSHOT_REL_LEFT = _RESULT_SCREENSHOT_LEFT_ABS / BASE_WIDTH
RESULT_SCREENSHOT_REL_TOP = _RESULT_SCREENSHOT_TOP_ABS / BASE_HEIGHT
RESULT_SCREENSHOT_REL_WIDTH = (_RESULT_SCREENSHOT_RIGHT_ABS - _RESULT_SCREENSHOT_LEFT_ABS) / BASE_WIDTH
RESULT_SCREENSHOT_REL_HEIGHT = (_RESULT_SCREENSHOT_BOTTOM_ABS - _RESULT_SCREENSHOT_TOP_ABS) / BASE_HEIGHT
RESULT_SCREENSHOT_REGION_REL = (
    RESULT_SCREENSHOT_REL_LEFT,
    RESULT_SCREENSHOT_REL_TOP,
    RESULT_SCREENSHOT_REL_WIDTH,
    RESULT_SCREENSHOT_REL_HEIGHT
)

# Calculate relative coords for Mode 4 (64in8)
P64IN8_PLAYER1_COORD_REL_M4 = calculate_relative_coords(_64IN8_PLAYER1_COORD_ABS_M4, BASE_WIDTH, BASE_HEIGHT)
P64IN8_PLAYER2_COORD_REL_M4 = calculate_relative_coords(_64IN8_PLAYER2_COORD_ABS_M4, BASE_WIDTH, BASE_HEIGHT)
P64IN8_PLAYER3_COORD_REL_M4 = calculate_relative_coords(_64IN8_PLAYER3_COORD_ABS_M4, BASE_WIDTH, BASE_HEIGHT)
P64IN8_PLAYER4_COORD_REL_M4 = calculate_relative_coords(_64IN8_PLAYER4_COORD_ABS_M4, BASE_WIDTH, BASE_HEIGHT)
P64IN8_PLAYER5_COORD_REL_M4 = calculate_relative_coords(_64IN8_PLAYER5_COORD_ABS_M4, BASE_WIDTH, BASE_HEIGHT)
P64IN8_PLAYER6_COORD_REL_M4 = calculate_relative_coords(_64IN8_PLAYER6_COORD_ABS_M4, BASE_WIDTH, BASE_HEIGHT)
P64IN8_PLAYER7_COORD_REL_M4 = calculate_relative_coords(_64IN8_PLAYER7_COORD_ABS_M4, BASE_WIDTH, BASE_HEIGHT)
P64IN8_PLAYER8_COORD_REL_M4 = calculate_relative_coords(_64IN8_PLAYER8_COORD_ABS_M4, BASE_WIDTH, BASE_HEIGHT)

# Calculate relative coords for Mode 5 (Champion Arena)
CHAMPION_PLAYER1_COORD_REL_M5 = calculate_relative_coords(_CHAMPION_PLAYER1_COORD_ABS_M5, BASE_WIDTH, BASE_HEIGHT)
CHAMPION_PLAYER2_COORD_REL_M5 = calculate_relative_coords(_CHAMPION_PLAYER2_COORD_ABS_M5, BASE_WIDTH, BASE_HEIGHT)
CHAMPION_PLAYER3_COORD_REL_M5 = calculate_relative_coords(_CHAMPION_PLAYER3_COORD_ABS_M5, BASE_WIDTH, BASE_HEIGHT)
CHAMPION_PLAYER4_COORD_REL_M5 = calculate_relative_coords(_CHAMPION_PLAYER4_COORD_ABS_M5, BASE_WIDTH, BASE_HEIGHT)
CHAMPION_PLAYER5_COORD_REL_M5 = calculate_relative_coords(_CHAMPION_PLAYER5_COORD_ABS_M5, BASE_WIDTH, BASE_HEIGHT)
CHAMPION_PLAYER6_COORD_REL_M5 = calculate_relative_coords(_CHAMPION_PLAYER6_COORD_ABS_M5, BASE_WIDTH, BASE_HEIGHT)
CHAMPION_PLAYER7_COORD_REL_M5 = calculate_relative_coords(_CHAMPION_PLAYER7_COORD_ABS_M5, BASE_WIDTH, BASE_HEIGHT)
CHAMPION_PLAYER8_COORD_REL_M5 = calculate_relative_coords(_CHAMPION_PLAYER8_COORD_ABS_M5, BASE_WIDTH, BASE_HEIGHT)

# 临时文件目录和文件名前缀
TEMP_DIR = "temp" # <--- 新增：临时文件目录
TEMP_PREFIX_PLAYER_INFO = "playerinfo" # 玩家信息1
TEMP_PREFIX_PLAYER_INFO_2 = "playerinfo2" # 新增：玩家信息2
TEMP_PREFIX_PLAYER_INFO_3 = "playerinfo3" # 新增：玩家信息3
TEMP_PREFIX_P1 = "temp_pic" # 队伍截图 (Player 1)
TEMP_PREFIX_P2 = "temp_pic1" # 队伍截图 (Player 2)
PEOPLE_VOTE_TEMP_FILENAME = os.path.join(TEMP_DIR, "people_vote.png") # <--- 修改：加入目录
OUTPUT_P1 = "line_player1.png" # 中间拼接文件，也放入 temp
OUTPUT_P2 = "line_player2.png" # 中间拼接文件，也放入 temp
RESULT_TEMP_FILENAME = os.path.join(TEMP_DIR, "result.png") # <--- 修改：加入目录
FINAL_OUTPUT_M1 = "combined_prediction.png" # Mode 1 final output
FINAL_OUTPUT_M2 = "combined_review.png"     # Mode 2 final output
FINAL_OUTPUT_M3 = "combined_anti_buy.png"   # 新增：Mode 3 final output
FINAL_OUTPUT_M4_P1 = "mode4_player1_stitched.png"
FINAL_OUTPUT_M4_P2 = "mode4_player2_stitched.png"
FINAL_OUTPUT_M4_P3 = "mode4_player3_stitched.png"
FINAL_OUTPUT_M4_P4 = "mode4_player4_stitched.png"
FINAL_OUTPUT_M4_P5 = "mode4_player5_stitched.png"
FINAL_OUTPUT_M4_P6 = "mode4_player6_stitched.png"
FINAL_OUTPUT_M4_P7 = "mode4_player7_stitched.png"
FINAL_OUTPUT_M4_P8 = "mode4_player8_stitched.png"
FINAL_OUTPUT_M4_OVERVIEW = "64in8_overview.png" # <--- 新增：模式4总览图文件名
FINAL_OUTPUT_M5_P1 = "mode5_player1_stitched.png"
FINAL_OUTPUT_M5_P2 = "mode5_player2_stitched.png"
FINAL_OUTPUT_M5_P3 = "mode5_player3_stitched.png"
FINAL_OUTPUT_M5_P4 = "mode5_player4_stitched.png"
FINAL_OUTPUT_M5_P5 = "mode5_player5_stitched.png"
FINAL_OUTPUT_M5_P6 = "mode5_player6_stitched.png"
FINAL_OUTPUT_M5_P7 = "mode5_player7_stitched.png"
FINAL_OUTPUT_M5_P8 = "mode5_player8_stitched.png"
FINAL_OUTPUT_M5_OVERVIEW = "champion_overview.png"
HORIZONTAL_SPACING = 50 # 横向拼接的间隔像素

# 鼠标点击和截图之间的延迟（秒）
ACTION_DELAY = 1.2 # 增加延迟以确保UI响应

def is_admin():
    """
    检查当前脚本是否在 Windows 上以管理员权限运行。
    返回 True 如果是管理员，否则返回 False。
    """
    if sys.platform == 'win32': # 仅在 Windows 上执行检查
        try:
            # 调用 Windows API 函数 IsUserAnAdmin()
            # 它位于 shell32.dll 中
            # 如果用户是管理员组成员且进程已提升，则返回非零值
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except AttributeError:
            # 如果 ctypes.windll.shell32 不可用（非常罕见）
            logging.warning("无法访问 shell32.dll 来检查管理员权限。假定非管理员。")
            return False
        except Exception as e:
            logging.error(f"检查管理员权限时发生未知错误: {e}")
            return False
    else:
        # 在非 Windows 系统上，此检查不适用
        logging.info("非 Windows 平台，跳过管理员权限检查。")
        return True

def setup_stop_hotkey():
    """设置停止脚本的热键。"""
    logging.info(f"按下 {STOP_HOTKEY} 可以随时停止脚本。")
    keyboard.add_hotkey(STOP_HOTKEY, stop_program)

def stop_program():
    """热键的回调函数，用于设置停止标志。"""
    global stop_script
    logging.warning(f"检测到停止热键 {STOP_HOTKEY}！正在尝试停止脚本...")
    stop_script = True

def check_stop_signal():
    """检查是否收到了停止信号，如果收到则退出脚本。"""
    if stop_script:
        logging.info("脚本已停止。")
        sys.exit(0) # 正常退出

def find_and_activate_window(process_name: str = "nikke.exe"):
    """
    查找与指定进程名称关联的主可见窗口并将其激活。
    只在 Windows 平台有效。
    """
    target_pid = None
    process_name_lower = process_name.lower()
    logging.info(f"正在查找进程名称为 '{process_name}' 的进程...")
    check_stop_signal()

    # 1. 查找进程 PID
    found_pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == process_name_lower:
                found_pids.append(proc.info['pid'])
                logging.debug(f"找到匹配进程: PID={proc.info['pid']}, 名称={proc.info['name']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as e:
             logging.warning(f"迭代进程时发生跳过错误: {e}")
             continue

    if not found_pids:
        logging.error(f"错误：未找到正在运行的进程 '{process_name}'。请确保游戏已启动。")
        sys.exit(1)

    if len(found_pids) > 1:
        logging.warning(f"警告：找到多个名为 '{process_name}' 的进程实例 (PIDs: {found_pids})。将尝试使用第一个找到的 PID ({found_pids[0]})。")
    target_pid = found_pids[0]
    logging.info(f"找到目标进程 PID: {target_pid}")
    check_stop_signal()

    # 2. 查找与 PID 关联的窗口句柄 (HWND)
    target_hwnd = None
    top_windows = []
    win32gui.EnumWindows(lambda hwnd, param: param.append(hwnd), top_windows)

    for hwnd in top_windows:
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid == target_pid:
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                    logging.info(f"找到与 PID {target_pid} 关联的窗口: HWND={hwnd}, 标题='{win32gui.GetWindowText(hwnd)}'")
                    target_hwnd = hwnd
                    break 
        except Exception:
             continue

    if target_hwnd is None:
        logging.error(f"错误：找到了 PID {target_pid} 的进程，但未能找到其关联的可见主窗口。")
        sys.exit(1)
    
    check_stop_signal()
    logging.info(f"将激活窗口 HWND: {target_hwnd}")

    # 3. 激活窗口
    try:
        # 使用 pygetwindow 获取窗口标题等信息，但主要通过 win32gui 操作
        window_title = win32gui.GetWindowText(target_hwnd) # 获取标题用于日志

        # 恢复窗口（如果最小化）
        if win32gui.IsIconic(target_hwnd): # IsIconic 检查是否最小化
            logging.info("窗口已最小化，正在恢复...")
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            time.sleep(1.5) # 等待窗口恢复

        # 激活窗口 (SetForegroundWindow 更可靠)
        logging.info("正在激活窗口...")
        try:
            win32gui.SetForegroundWindow(target_hwnd)
        except Exception as e: # pywintypes.error 可能发生
             logging.warning(f"SetForegroundWindow 失败({e})，尝试用 ShowWindow 激活...")
             # 作为备选方案，尝试ShowWindow激活
             win32gui.ShowWindow(target_hwnd, win32con.SW_SHOW)
             win32gui.SetForegroundWindow(target_hwnd) # 再次尝试

        # ---- 修改开始 ----
        # time.sleep(0.7) # 等待后台操作完成
        # 直接检查前台窗口句柄
        time.sleep(1) # 增加这里的延迟，给系统更多时间切换前台窗口
        foreground_hwnd = win32gui.GetForegroundWindow()

        if foreground_hwnd == target_hwnd:
              logging.info(f"窗口 HWND {target_hwnd} ('{window_title}') 已成功激活并置于前台。")
        else:
              logging.warning(f"尝试激活窗口 HWND {target_hwnd} ('{window_title}')，但当前前台窗口是 HWND {foreground_hwnd} ('{win32gui.GetWindowText(foreground_hwnd)}'). 脚本将继续，但可能操作错误窗口。")
              # 可以考虑在这里添加更严格的错误处理，例如退出脚本
              # sys.exit("无法确认目标窗口已激活。")

        # 返回一个 pygetwindow 对象（如果后续代码需要用到它的属性的话）
        try:
            window = pygetwindow.Win32Window(target_hwnd)
            return window
        except Exception as e:
             logging.warning(f"创建 pygetwindow 对象时出错（但不影响激活）: {e}")
             # 即使创建对象失败，也认为激活尝试已完成，返回 True 或 None
             # 这里选择返回 None 表示虽然尝试了，但对象创建失败
             return None 
        # ---- 修改结束 ----

    except Exception as e:
        # 处理 win32gui 可能引发的 pywintypes.error 等异常
        # import traceback # 取消注释以在调试时打印堆栈跟踪
        # traceback.print_exc()
        logging.error(f"激活窗口 HWND {target_hwnd} 时发生意外错误: {e}")
        sys.exit(1)

        
def click_coordinates(relative_coord: tuple, window: pygetwindow.Win32Window):
    """
    根据相对坐标和当前窗口尺寸/位置，计算实际屏幕坐标并模拟点击。
    相对坐标是 (比例X, 比例Y)，相对于窗口的客户区（内容区域）。
    """
    check_stop_signal()
    try:
        # --- 修改开始: 使用 win32gui 获取客户区信息 ---
        hwnd = window._hWnd # 获取窗口句柄
        if not hwnd:
             logging.error("错误：无法从 pygetwindow 对象获取窗口句柄 (HWND)。")
             return False

        # 获取客户区矩形（相对于窗口左上角）
        client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
        client_width = client_right - client_left
        client_height = client_bottom - client_top

        if client_width <= 0 or client_height <= 0:
             logging.error(f"错误：获取到的窗口客户区尺寸无效 (Width={client_width}, Height={client_height})。")
             return False

        # 将客户区的左上角坐标 (client_left, client_top) 转换为屏幕坐标
        screen_client_left, screen_client_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))
        # --- 修改结束 ---

        # --- 修改开始: 基于客户区计算屏幕坐标 ---
        # 屏幕X = 客户区左上角屏幕X + 相对X比例 * 客户区宽度
        # 屏幕Y = 客户区左上角屏幕Y + 相对Y比例 * 客户区高度
        screen_x = screen_client_left + round(relative_coord[0] * client_width)
        screen_y = screen_client_top + round(relative_coord[1] * client_height)
        # --- 修改结束 ---

        logging.info(f"相对坐标 {relative_coord} -> 屏幕坐标 ({screen_x}, {screen_y}) (基于窗口 '{window.title}' HWND:{hwnd} 的客户区 at [{screen_client_left},{screen_client_top}] size [{client_width}x{client_height}])")

        pyautogui.moveTo(screen_x, screen_y, duration=0.2) # 平滑移动
        pyautogui.click(screen_x, screen_y)
        time.sleep(ACTION_DELAY) # 点击后等待UI响应
        return True

    except Exception as e:
        logging.error(f"计算或点击相对坐标 {relative_coord} 时出错: {e}")
        return False
    

def take_screenshot(relative_region: tuple, window: pygetwindow.Win32Window, filename: str):
    """
    根据相对区域定义和当前窗口尺寸/位置，计算实际屏幕区域并截图保存。
    相对区域格式: (rel_left, rel_top, rel_width, rel_height)
    """
    if not all(isinstance(val, (int, float)) for val in relative_region) or len(relative_region) != 4:
        logging.error(f"无效的相对截图区域格式: {relative_region}. 需要 (rel_left, rel_top, rel_width, rel_height)。")
        return False
    
    check_stop_signal()
    try:
        # --- 修改开始: 使用 win32gui 获取客户区信息 ---
        hwnd = window._hWnd # 获取窗口句柄
        if not hwnd:
             logging.error("错误：无法从 pygetwindow 对象获取窗口句柄 (HWND)。")
             return False

        # 获取客户区矩形（相对于窗口左上角）
        client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
        client_width = client_right - client_left
        client_height = client_bottom - client_top

        if client_width <= 0 or client_height <= 0:
             logging.error(f"错误：获取到的窗口客户区尺寸无效 (Width={client_width}, Height={client_height})。")
             return False

        # 将客户区的左上角坐标 (client_left, client_top) 转换为屏幕坐标
        screen_client_left, screen_client_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))
        # --- 修改结束 ---

        # --- 修改开始: 基于客户区计算屏幕截图区域 ---
        region_left = screen_client_left + round(relative_region[0] * client_width)
        region_top = screen_client_top + round(relative_region[1] * client_height)
        region_width = round(relative_region[2] * client_width)
        region_height = round(relative_region[3] * client_height)
        # --- 修改结束 ---

        # 确保宽度和高度是正数
        if region_width <= 0 or region_height <= 0:
             logging.error(f"计算得到的截图区域尺寸无效: 宽度={region_width}, 高度={region_height} (基于客户区大小 {client_width}x{client_height} 和相对区域 {relative_region})。")
             return False

        actual_region = (region_left, region_top, region_width, region_height)

        logging.info(f"相对区域 {relative_region} -> 屏幕区域 {actual_region} (基于窗口 '{window.title}' HWND:{hwnd} 的客户区 at [{screen_client_left},{screen_client_top}] size [{client_width}x{client_height}])")
        logging.info(f"正在截取区域 {actual_region} 并保存为 '{filename}'...")

        screenshot = pyautogui.screenshot(region=actual_region)
        screenshot.save(filename)
        logging.info(f"截图已保存为 '{filename}'")
        time.sleep(0.2) # 保存后短暂等待
        return True
        
    except Exception as e:
        logging.error(f"截取或保存截图 '{filename}' (相对区域 {relative_region}) 时出错: {e}")
        return False
    

def stitch_images_vertically(image_paths: list, output_path: str):
    """
    将一系列图片从上到下垂直拼接成一张图片。
    """
    logging.info(f"开始垂直拼接图片到 '{output_path}'...")
    check_stop_signal()
    if not image_paths:
        logging.warning("没有提供用于垂直拼接的图片路径。")
        return False

    images = []
    total_height = 0
    max_width = 0

    # 打开所有图片并计算尺寸
    try:
        for path in image_paths:
            if not os.path.exists(path):
                logging.warning(f"跳过拼接：找不到图片文件 '{path}'")
                continue
            img = Image.open(path)
            images.append(img)
            total_height += img.height
            if img.width > max_width:
                max_width = img.width
            logging.debug(f"读取图片 '{path}' 尺寸: {img.size}")

        if not images:
             logging.error("无法打开任何有效的图片进行垂直拼接。")
             return False

        # 创建新的空白图片
        logging.debug(f"创建垂直拼接画布，尺寸: ({max_width}, {total_height})")
        stitched_image = Image.new('RGB', (max_width, total_height))

        # 逐个粘贴图片
        current_y = 0
        for img in images:
            check_stop_signal()
            # 如果图片宽度小于最大宽度，居中粘贴（可选）
            paste_x = (max_width - img.width) // 2
            stitched_image.paste(img, (paste_x, current_y))
            current_y += img.height
            img.close() # 及时关闭文件句柄

        # 保存拼接后的图片
        stitched_image.save(output_path)
        logging.info(f"垂直拼接完成，图片已保存为 '{output_path}'")
        return True
    except FileNotFoundError as e:
        logging.error(f"垂直拼接时找不到文件：{e}")
        return False
    except Exception as e:
        logging.error(f"垂直拼接图片时出错: {e}")
        # 清理已打开的图片
        for img in images:
            try:
                img.close()
            except: # nosec
                pass # 如果关闭失败就算了
        return False

def stitch_images_horizontally(image_paths: list, output_path: str, spacing: int = 0, background_color=(0, 0, 0)):
    """
    将一系列图片从左到右水平拼接成一张图片，并在图片间加入指定间隔。
    新增 background_color 参数用于设置画布背景色。
    """
    logging.info(f"开始水平拼接图片到 '{output_path}' (间隔: {spacing}px, 背景色: {background_color})...")
    check_stop_signal()
    if not image_paths:
        logging.warning("没有提供用于水平拼接的图片路径。")
        return False

    images = []
    total_width = 0
    max_height = 0

    # 打开所有图片并计算尺寸
    try:
        num_images = 0
        for path in image_paths:
            if not os.path.exists(path):
                logging.warning(f"跳过拼接：找不到图片文件 '{path}'")
                continue
            img = Image.open(path)
            images.append(img)
            total_width += img.width
            if img.height > max_height:
                max_height = img.height
            num_images += 1
            logging.debug(f"读取图片 '{path}' 尺寸: {img.size}")

        if not images:
            logging.error("无法打开任何有效的图片进行水平拼接。")
            return False

        # 加上间隔的总宽度
        total_width += spacing * (num_images - 1) if num_images > 1 else 0

        # 创建新的空白图片，使用指定的背景色
        logging.debug(f"创建水平拼接画布，尺寸: ({total_width}, {max_height}), 背景色: {background_color}")
        stitched_image = Image.new('RGB', (total_width, max_height), color=background_color)

        # 逐个粘贴图片
        current_x = 0
        for img in images:
            check_stop_signal()
            # 如果图片高度小于最大高度，顶部对齐粘贴（或居中）
            paste_y = 0 # (max_height - img.height) // 2 # 居中对齐
            stitched_image.paste(img, (current_x, paste_y))
            current_x += img.width + spacing # 移动到下一个位置（包括间隔）
            img.close() # 及时关闭文件句柄

        # --- 新增：检查文件名冲突并生成新文件名 ---
        final_output_path = output_path
        base, ext = os.path.splitext(output_path)
        counter = 1
        while os.path.exists(final_output_path):
            final_output_path = f"{base}_{counter}{ext}"
            counter += 1
            if counter > 100: # 防止无限循环
                 logging.error(f"尝试生成唯一文件名失败，已尝试到 '{final_output_path}'")
                 # 清理已打开的图片
                 for img in images:
                     try: img.close()
                     except: pass
                 return None # 返回 None 表示失败

        if final_output_path != output_path:
             logging.info(f"目标文件 '{output_path}' 已存在，将保存为 '{final_output_path}'")
        # --- 文件名冲突处理结束 ---

        # 保存拼接后的图片
        stitched_image.save(final_output_path)
        logging.info(f"水平拼接完成，图片已保存为 '{final_output_path}'")
        return final_output_path # 返回实际保存的文件路径
    except FileNotFoundError as e:
        logging.error(f"水平拼接时找不到文件：{e}")
        return False
    except Exception as e:
        logging.error(f"水平拼接图片时出错: {e}")
        # 清理已打开的图片
        for img in images:
            try:
                img.close()
            except: # nosec
                pass # 如果关闭失败就算了
        return False
def stitch_mode4_overview(image_paths: list, output_path: str, spacing_major: int = 60, spacing_minor: int = 30, background_color=(0, 0, 0)):
    """
    将8张图片分成两行（每行4张）并拼接成一张总览图。
    - 第1行: 图片 1, 2, 3, 4
    - 第2行: 图片 5, 6, 7, 8
    - 间距:
        - (1,2), (3,4), (5,6), (7,8) 之间为 30px (spacing_minor)
        - (2,3), (6,7) 之间为 60px (spacing_major)
        - 第1行和第2行之间为 60px (spacing_major)
    - 背景为黑色。
    """
    logging.info(f"开始为模式4拼接总览图到 '{output_path}'...")
    check_stop_signal()

    if not image_paths or len(image_paths) != 8:
        logging.error(f"需要8张图片进行模式4总览图拼接，但收到了 {len(image_paths) if image_paths else 0} 张。")
        return None # 返回 None 表示失败

    images = []
    try:
        for i, path in enumerate(image_paths):
            if not os.path.exists(path):
                logging.error(f"找不到图片文件 '{path}' (图片 {i+1})，无法进行拼接。")
                for img_obj in images: # 清理已打开的图片
                    img_obj.close()
                return None
            img = Image.open(path)
            images.append(img)
        
        img_width, img_height = images[0].size # 假设所有图片尺寸相同
        if img_width <= 0 or img_height <= 0:
            logging.error(f"图片尺寸无效: {img_width}x{img_height}。")
            for img_obj in images:
                img_obj.close()
            return None

        # 计算画布尺寸
        row_width = (img_width * 4) + (spacing_minor * 2) + spacing_major
        canvas_height = (img_height * 2) + spacing_major
        canvas_width = row_width

        logging.debug(f"单张图片尺寸: {img_width}x{img_height}")
        logging.debug(f"画布尺寸: {canvas_width}x{canvas_height}")

        stitched_image = Image.new('RGB', (canvas_width, canvas_height), color=background_color)

        # 粘贴图片 - 第1行
        current_x_r1 = 0
        stitched_image.paste(images[0], (current_x_r1, 0))
        current_x_r1 += img_width + spacing_minor
        stitched_image.paste(images[1], (current_x_r1, 0))
        current_x_r1 += img_width + spacing_major
        stitched_image.paste(images[2], (current_x_r1, 0))
        current_x_r1 += img_width + spacing_minor
        stitched_image.paste(images[3], (current_x_r1, 0))

        # 粘贴图片 - 第2行
        row2_y_offset = img_height + spacing_major
        current_x_r2 = 0
        stitched_image.paste(images[4], (current_x_r2, row2_y_offset))
        current_x_r2 += img_width + spacing_minor
        stitched_image.paste(images[5], (current_x_r2, row2_y_offset))
        current_x_r2 += img_width + spacing_major
        stitched_image.paste(images[6], (current_x_r2, row2_y_offset))
        current_x_r2 += img_width + spacing_minor
        stitched_image.paste(images[7], (current_x_r2, row2_y_offset))

        # 处理文件名冲突
        final_output_path = output_path
        base, ext = os.path.splitext(output_path)
        counter = 1
        while os.path.exists(final_output_path):
            final_output_path = f"{base}_{counter}{ext}"
            counter += 1
            if counter > 100: # 安全中止
                 logging.error(f"尝试为模式4总览图生成唯一文件名失败，已尝试到 '{final_output_path}'")
                 for img_obj in images:
                     img_obj.close()
                 return None

        if final_output_path != output_path:
             logging.info(f"目标文件 '{output_path}' 已存在，模式4总览图将保存为 '{final_output_path}'")
        
        stitched_image.save(final_output_path)
        logging.info(f"模式4总览图拼接完成，图片已保存为 '{final_output_path}'")
        return final_output_path

    except FileNotFoundError as e:
        logging.error(f"拼接模式4总览图时找不到文件：{e}")
        return None
    except Exception as e:
        logging.error(f"拼接模式4总览图时出错: {e}")
        # import traceback # 用于调试
        # traceback.print_exc()
        return None
    finally:
        for img_obj in images: # 确保关闭所有图片对象
            try:
                img_obj.close()
            except: # nosec
                pass

def process_player(player_coord_rel: tuple, team_coords_rel: list, temp_prefix: str, output_image: str, screenshot_region_rel: tuple, window: pygetwindow.Win32Window, initial_delay: float = 3.0):
    """
    处理单个玩家的点击、截图和垂直拼接流程，使用相对坐标。
    在点击初始玩家坐标后会等待 'initial_delay' 秒。
    需要传入目标窗口对象。
    返回生成的垂直拼接图片的路径，如果成功的话。
    """
    logging.info(f"开始处理玩家，点击初始相对坐标: {player_coord_rel}")
    # 初始点击
    if not click_coordinates(player_coord_rel, window):
        logging.error("未能点击玩家初始坐标。")
        return None # 如果初始点击失败，则无法继续
    
    # --- 新增：在初始点击后添加等待 ---
    logging.info(f"在初始点击后等待 {initial_delay} 秒...")
    check_stop_signal() # 等待前检查
    time.sleep(initial_delay)
    check_stop_signal() # 等待后检查
    logging.info("等待结束。")
    # --- 新增结束 ---

    temp_image_paths = [] # 初始化截图路径列表
    success = True

    # --- 新增：截取 Player Info 区域 ---
    player_info_temp_filename = os.path.join(TEMP_DIR, f"{TEMP_PREFIX_PLAYER_INFO}_{temp_prefix}.png") # <--- 修改：加入目录
    logging.info(f"正在截取玩家信息区域并保存为 '{player_info_temp_filename}'...")
    try:
        # 确保窗口激活
        window.activate()
        time.sleep(0.2)
    except Exception as e:
        logging.warning(f"重新激活窗口以截取玩家信息时出错: {e}")

    if take_screenshot(PLAYER_INFO_REGION_REL, window, player_info_temp_filename):
        temp_image_paths.append(player_info_temp_filename) # 将玩家信息截图放在列表最前面
        logging.info("玩家信息截图成功。")
    else:
        logging.warning(f"未能截取玩家信息区域 '{player_info_temp_filename}'。")
        # 即使玩家信息截图失败，也继续尝试截取队伍信息
    check_stop_signal()
    time.sleep(0.5) # 截图后短暂等待
    # --- 玩家信息1截图结束 ---

    # --- 新增：处理玩家详细信息2和3 ---
    # 点击 player_detailinfo_2
    logging.info(f"点击玩家详细信息坐标2 (相对): {PLAYER_DETAILINFO_2_REL}")
    if click_coordinates(PLAYER_DETAILINFO_2_REL, window):
        logging.info("等待 2.5 秒...")
        check_stop_signal()
        time.sleep(2.5)
        check_stop_signal()

        # 截图 player_info_2
        player_info_2_temp_filename = os.path.join(TEMP_DIR, f"{TEMP_PREFIX_PLAYER_INFO_2}_{temp_prefix}.png") # <--- 修改：加入目录
        logging.info(f"正在截取玩家信息区域2 并保存为 '{player_info_2_temp_filename}'...")
        try:
            window.activate()
            time.sleep(0.2)
        except Exception as e:
            logging.warning(f"重新激活窗口以截取玩家信息2时出错: {e}")

        if take_screenshot(PLAYER_INFO_2_REGION_REL, window, player_info_2_temp_filename):
            temp_image_paths.append(player_info_2_temp_filename) # 添加到列表第二位
            logging.info("玩家信息2截图成功。")
        else:
            logging.warning(f"未能截取玩家信息区域2 '{player_info_2_temp_filename}'。")
        check_stop_signal()
        time.sleep(0.5) # 截图后短暂等待

        # 点击 player_detailinfo_3
        logging.info(f"点击玩家详细信息坐标3 (相对): {PLAYER_DETAILINFO_3_REL}")
        if click_coordinates(PLAYER_DETAILINFO_3_REL, window):
            logging.info("等待 1 秒...")
            check_stop_signal()
            time.sleep(1.0)
            check_stop_signal()

            # 截图 player_info_3
            player_info_3_temp_filename = os.path.join(TEMP_DIR, f"{TEMP_PREFIX_PLAYER_INFO_3}_{temp_prefix}.png") # <--- 修改：加入目录
            logging.info(f"正在截取玩家信息区域3 并保存为 '{player_info_3_temp_filename}'...")
            try:
                window.activate()
                time.sleep(0.2)
            except Exception as e:
                logging.warning(f"重新激活窗口以截取玩家信息3时出错: {e}")

            # 检查 PLAYER_INFO_3_REGION_REL 的高度是否有效
            if PLAYER_INFO_3_REGION_REL[3] <= 0:
                 logging.error(f"错误：玩家信息区域3的高度无效 ({PLAYER_INFO_3_REGION_REL[3]})。请检查绝对坐标 _PLAYER_INFO_3_TOP_ABS 和 _PLAYER_INFO_3_BOTTOM_ABS。跳过截图。")
            elif take_screenshot(PLAYER_INFO_3_REGION_REL, window, player_info_3_temp_filename):
                temp_image_paths.append(player_info_3_temp_filename) # 添加到列表第三位
                logging.info("玩家信息3截图成功。")
            else:
                logging.warning(f"未能截取玩家信息区域3 '{player_info_3_temp_filename}'。")
            check_stop_signal()
            time.sleep(0.5) # 截图后短暂等待

            # 点击 player_detailinfo_close
            logging.info(f"点击关闭详细信息坐标 (相对): {PLAYER_DETAILINFO_CLOSE_REL}")
            if click_coordinates(PLAYER_DETAILINFO_CLOSE_REL, window):
                logging.info("等待 0.3 秒...")
                check_stop_signal()
                time.sleep(0.3)
                check_stop_signal()
            else:
                logging.warning("未能点击关闭详细信息坐标。")

        else:
            logging.warning("未能点击玩家详细信息坐标3，跳过后续截图和关闭操作。")
    else:
        logging.warning("未能点击玩家详细信息坐标2，跳过详细信息截图流程。")
    # --- 详细信息处理结束 ---


    logging.info("开始处理队伍...")
    # 现在 temp_image_paths 应该包含 player_info, player_info_2, player_info_3 (如果成功的话)
    for i, team_coord_rel in enumerate(team_coords_rel, 1):
        check_stop_signal()
        logging.info(f"--- 处理 Team {i} (相对坐标: {team_coord_rel}) ---")
        
        # 1. 点击队伍相对坐标
        if not click_coordinates(team_coord_rel, window):
            logging.warning(f"未能点击 Team {i} 的相对坐标 {team_coord_rel}，跳过此队伍。")
            continue # 跳到下一个队伍
        check_stop_signal() 

        # 2. 截图并保存（使用相对区域）
        temp_filename = os.path.join(TEMP_DIR, f"{temp_prefix}{i}.png") # <--- 修改：加入目录
        try:
             # 确保窗口激活，并给UI一点反应时间
             window.activate() 
             time.sleep(0.2) # 短暂等待激活生效
        except Exception as e:
             logging.warning(f"重新激活窗口时出错: {e}")
             # 即使激活失败也继续尝试截图
             
        if not take_screenshot(screenshot_region_rel, window, temp_filename):
            logging.warning(f"未能为 Team {i} 创建截图 '{temp_filename}'，将跳过此图片。")
            continue # 继续处理下一个队伍
        else:
             temp_image_paths.append(temp_filename)
             
        time.sleep(ACTION_DELAY) # 在截图或点击队伍后的小延迟（原有的）

    # 3. 垂直拼接所有成功的截图
    if not temp_image_paths:
         logging.error(f"没有成功截取任何位于 '{TEMP_DIR}' 目录下的 {temp_prefix}* 图片，无法进行垂直拼接。")
         return None

    # --- 修改：将垂直拼接的中间结果也放入 temp 目录 ---
    output_image_in_temp = os.path.join(TEMP_DIR, output_image)
    if not stitch_images_vertically(temp_image_paths, output_image_in_temp):
        logging.error(f"垂直拼接图片到 '{output_image_in_temp}' 失败。")
        return None
    # --- 修改结束 ---

    # 清理单个截图临时文件 (playerinfo*, temp_pic*, temp_pic1*)
    # 这些文件现在都在 temp_image_paths 里，并且路径已包含 TEMP_DIR
    cleanup_individual_screenshots = True
    if cleanup_individual_screenshots:
        logging.info(f"正在清理 '{TEMP_DIR}' 目录中的单个截图文件...")
        for path in temp_image_paths:
             try:
                 if os.path.exists(path):
                     os.remove(path)
                     logging.debug(f"已删除临时截图文件: {path}")
             except OSError as e:
                 logging.warning(f"无法删除临时截图文件 '{path}': {e}")

    return output_image_in_temp # 返回在 temp 目录中的中间拼接文件路径


# --- 主程序逻辑 ---
def main():
    global stop_script
    logging.info("脚本启动。")
    
    # 1. 设置停止热键
    setup_stop_hotkey()
    check_stop_signal() 

    # 2. 创建临时目录
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
        logging.info(f"已确保临时目录 '{TEMP_DIR}' 存在。")
    except OSError as e:
        logging.error(f"创建临时目录 '{TEMP_DIR}' 失败: {e}")
        return # 无法创建临时目录则退出

    # 3. 查找并激活 NIKKE 窗口
    nikke_window = find_and_activate_window()
    if nikke_window is None:
        # 在退出前尝试清理可能已创建的目录
        if os.path.exists(TEMP_DIR):
             try: shutil.rmtree(TEMP_DIR)
             except Exception as clean_err: logging.warning(f"退出前清理临时目录失败: {clean_err}")
        return
    check_stop_signal()
    
    # 关键：获取窗口对象后，我们将在后续操作中使用它来计算坐标
    logging.info(f"获取到窗口对象: Title='{nikke_window.title}', Pos=({nikke_window.left},{nikke_window.top}), Size=({nikke_window.width}x{nikke_window.height})")
    time.sleep(0.5) # 等待窗口信息稳定

    # 定义处理任务需要的文件和路径
    player1_output = None # Path to line_player1.png if successful
    player2_output = None # Path to line_player2.png if successful
    result_screenshot_path = None # Mode 2: Path to result.png
    people_vote_screenshot_path = None # Mode 3: Path to people_vote.png
    actual_final_output_path = None # Stores the final path returned by stitch_images_horizontally

    try:
        if CURRENT_MODE == 1:
            logging.info("===== 运行模式 1: 预测模式 =====")
            # --- 处理 Player 1 ---
            logging.info("===== 开始处理 Player 1 =====")
            # process_player 现在返回 temp 目录中的路径
            player1_output = process_player(
                PLAYER1_COORD_REL,
                TEAM_COORDS_REL,
                TEMP_PREFIX_P1,
                OUTPUT_P1, # 这是中间文件的基础名
                SCREENSHOT_REGION_REL,
                nikke_window
            )
            if player1_output is None:
                logging.error("处理 Player 1 失败。")
            else:
                logging.info("===== Player 1 处理完成 =====")
            check_stop_signal()

            # --- 点击退出按钮 ---
            logging.info("正在点击退出坐标 (相对)...")
            if not click_coordinates(EXIT_COORD_REL, nikke_window):
                 logging.warning("未能点击退出坐标。")
            check_stop_signal()
            time.sleep(1.0) 

            # --- 处理 Player 2 ---
            logging.info("===== 开始处理 Player 2 =====")
            # process_player 现在返回 temp 目录中的路径
            player2_output = process_player(
                PLAYER2_COORD_REL,
                TEAM_COORDS_REL,
                TEMP_PREFIX_P2,
                OUTPUT_P2, # 这是中间文件的基础名
                SCREENSHOT_REGION_REL,
                nikke_window
            )
            if player2_output is None:
                logging.error("处理 Player 2 失败。")
            else:
                logging.info("===== Player 2 处理完成 =====")
            check_stop_signal()

            # --- 横向拼接 Player 1 和 Player 2 的结果 ---
            final_images_to_stitch_m1 = []
            # player1_output 和 player2_output 现在是 temp 目录中的路径
            if player1_output and os.path.exists(player1_output):
                final_images_to_stitch_m1.append(player1_output)
            else:
                 # 使用 os.path.join 获取预期的临时文件路径用于日志
                 expected_path = os.path.join(TEMP_DIR, OUTPUT_P1)
                 logging.warning(f"Player 1 的中间拼接图片 '{expected_path}' 不存在或未生成，无法用于最终拼接。")

            if player2_output and os.path.exists(player2_output):
                final_images_to_stitch_m1.append(player2_output)
            else:
                 expected_path = os.path.join(TEMP_DIR, OUTPUT_P2)
                 logging.warning(f"Player 2 的中间拼接图片 '{expected_path}' 不存在或未生成，无法用于最终拼接。")

            if len(final_images_to_stitch_m1) >= 1:
                logging.info("开始最终的横向拼接 (模式 1)...")
                # 捕获 stitch_images_horizontally 返回的实际路径
                actual_final_output_path = stitch_images_horizontally(final_images_to_stitch_m1, FINAL_OUTPUT_M1, HORIZONTAL_SPACING, background_color=(0,0,0)) # 默认黑色背景
                if not actual_final_output_path:
                    logging.error(f"未能成功生成最终拼接图片 (模式 1)。")
                else:
                     logging.info(f"成功生成最终拼接图片: '{actual_final_output_path}'")
                     # 中间文件 (line_player1.png, line_player2.png in temp/) 会在 finally 块中随 temp 目录一起删除
            else:
                logging.error("没有可用于最终横向拼接的有效图片 (模式 1)。")

        elif CURRENT_MODE == 2:
            logging.info("===== 运行模式 2: 复盘模式 =====")
            
            # --- 初始截图 ---
            logging.info("正在截取初始结果图 (result.png)...")
            if take_screenshot(RESULT_SCREENSHOT_REGION_REL, nikke_window, RESULT_TEMP_FILENAME):
                result_screenshot_path = RESULT_TEMP_FILENAME
                logging.info(f"初始结果图已保存为 '{result_screenshot_path}'")
            else:
                logging.error("未能截取初始结果图。")
            check_stop_signal()
            time.sleep(0.5) # 短暂等待

            # --- 处理 Player 1 (使用 Mode 2 坐标) ---
            logging.info("===== 开始处理 Player 1 (模式 2) =====")
            player1_output = process_player(
                PLAYER1_COORD_REL_M2, # 使用 Mode 2 坐标
                TEAM_COORDS_REL,
                TEMP_PREFIX_P1,
                OUTPUT_P1, # 中间文件名
                SCREENSHOT_REGION_REL, # 截图区域保持不变
                nikke_window
            )
            if player1_output is None:
                logging.error("处理 Player 1 (模式 2) 失败。")
            else:
                logging.info("===== Player 1 (模式 2) 处理完成 =====")
            check_stop_signal()
            
            # --- 点击退出按钮 (模式 2) ---
            logging.info("正在点击退出坐标 (相对)...")
            if not click_coordinates(EXIT_COORD_REL, nikke_window):
                 logging.warning("未能点击退出坐标。")
            check_stop_signal()
            time.sleep(1.0) 

            # --- 处理 Player 2 (使用 Mode 2 坐标) ---
            logging.info("===== 开始处理 Player 2 (模式 2) =====")
            player2_output = process_player(
                PLAYER2_COORD_REL_M2, # 使用 Mode 2 坐标
                TEAM_COORDS_REL,
                TEMP_PREFIX_P2,
                OUTPUT_P2, # 中间文件名
                SCREENSHOT_REGION_REL, # 截图区域保持不变
                nikke_window
            )
            if player2_output is None:
                logging.error("处理 Player 2 (模式 2) 失败。")
            else:
                logging.info("===== Player 2 (模式 2) 处理完成 =====")
            check_stop_signal()

            # --- 横向拼接 Player 1, Result, Player 2 的结果 (白色背景) ---
            final_images_to_stitch_m2 = []
            # player1_output, result_screenshot_path, player2_output 都是 temp/ 目录中的路径
            if player1_output and os.path.exists(player1_output):
                final_images_to_stitch_m2.append(player1_output)
            else:
                 expected_path = os.path.join(TEMP_DIR, OUTPUT_P1)
                 logging.warning(f"Player 1 的中间拼接图片 '{expected_path}' 不存在或未生成，无法用于最终拼接 (模式 2)。")

            if result_screenshot_path and os.path.exists(result_screenshot_path):
                 final_images_to_stitch_m2.append(result_screenshot_path)
            else:
                 # RESULT_TEMP_FILENAME 已经包含 TEMP_DIR
                 logging.warning(f"初始结果截图 '{RESULT_TEMP_FILENAME}' 不存在或未生成，无法用于最终拼接 (模式 2)。")

            if player2_output and os.path.exists(player2_output):
                final_images_to_stitch_m2.append(player2_output)
            else:
                 expected_path = os.path.join(TEMP_DIR, OUTPUT_P2)
                 logging.warning(f"Player 2 的中间拼接图片 '{expected_path}' 不存在或未生成，无法用于最终拼接 (模式 2)。")

            if len(final_images_to_stitch_m2) >= 1: # 至少需要一张图才能拼接
                logging.info("开始最终的横向拼接 (模式 2)...")
                # 捕获 stitch_images_horizontally 返回的实际路径
                # --- 修改：移除模式2的水平间距 ---
                actual_final_output_path = stitch_images_horizontally(final_images_to_stitch_m2, FINAL_OUTPUT_M2, spacing=0, background_color=(255, 255, 255)) # 白色背景, spacing=0
                if not actual_final_output_path:
                    logging.error(f"未能成功生成最终拼接图片 (模式 2)。")
                else:
                     logging.info(f"成功生成最终拼接图片: '{actual_final_output_path}'")
                     # 中间文件 (line_player1.png, result.png, line_player2.png in temp/) 会在 finally 块中删除
            else:
                logging.error("没有可用于最终横向拼接的有效图片 (模式 2)。")

            # 不再需要单独清理 result.png，它会在 finally 中随 temp 目录一起删除

        elif CURRENT_MODE == 3:
            logging.info("===== 运行模式 3: 反买模式 =====")

            # --- 初始截图 (People Vote) ---
            logging.info(f"正在截取民意区域 ({PEOPLE_VOTE_TEMP_FILENAME})...")
            if take_screenshot(PEOPLE_VOTE_REGION_REL, nikke_window, PEOPLE_VOTE_TEMP_FILENAME):
                people_vote_screenshot_path = PEOPLE_VOTE_TEMP_FILENAME
                logging.info(f"民意区域截图已保存为 '{people_vote_screenshot_path}'")
            else:
                logging.error("未能截取民意区域截图。")
            check_stop_signal()
            time.sleep(0.5) # 短暂等待

            # --- 处理 Player 1 (使用 Mode 1 坐标) ---
            logging.info("===== 开始处理 Player 1 (模式 3) =====")
            player1_output = process_player(
                PLAYER1_COORD_REL, # 使用 Mode 1 坐标
                TEAM_COORDS_REL,
                TEMP_PREFIX_P1,
                OUTPUT_P1, # 中间文件名
                SCREENSHOT_REGION_REL,
                nikke_window
            )
            if player1_output is None:
                logging.error("处理 Player 1 (模式 3) 失败。")
            else:
                logging.info("===== Player 1 (模式 3) 处理完成 =====")
            check_stop_signal()

            # --- 点击退出按钮 ---
            logging.info("正在点击退出坐标 (相对)...")
            if not click_coordinates(EXIT_COORD_REL, nikke_window):
                 logging.warning("未能点击退出坐标。")
            check_stop_signal()
            time.sleep(1.0)

            # --- 处理 Player 2 (使用 Mode 1 坐标) ---
            logging.info("===== 开始处理 Player 2 (模式 3) =====")
            player2_output = process_player(
                PLAYER2_COORD_REL, # 使用 Mode 1 坐标
                TEAM_COORDS_REL,
                TEMP_PREFIX_P2,
                OUTPUT_P2, # 中间文件名
                SCREENSHOT_REGION_REL,
                nikke_window
            )
            if player2_output is None:
                logging.error("处理 Player 2 (模式 3) 失败。")
            else:
                logging.info("===== Player 2 (模式 3) 处理完成 =====")
            check_stop_signal()

            # --- 横向拼接 Player 1, People Vote, Player 2 的结果 (白色背景) ---
            final_images_to_stitch_m3 = []
            # player1_output, people_vote_screenshot_path, player2_output 都是 temp/ 目录中的路径
            if player1_output and os.path.exists(player1_output):
                final_images_to_stitch_m3.append(player1_output)
            else:
                 expected_path = os.path.join(TEMP_DIR, OUTPUT_P1)
                 logging.warning(f"Player 1 的中间拼接图片 '{expected_path}' 不存在或未生成，无法用于最终拼接 (模式 3)。")

            if people_vote_screenshot_path and os.path.exists(people_vote_screenshot_path):
                 final_images_to_stitch_m3.append(people_vote_screenshot_path)
            else:
                 # PEOPLE_VOTE_TEMP_FILENAME 已经包含 TEMP_DIR
                 logging.warning(f"民意截图 '{PEOPLE_VOTE_TEMP_FILENAME}' 不存在或未生成，无法用于最终拼接 (模式 3)。")

            if player2_output and os.path.exists(player2_output):
                final_images_to_stitch_m3.append(player2_output)
            else:
                 expected_path = os.path.join(TEMP_DIR, OUTPUT_P2)
                 logging.warning(f"Player 2 的中间拼接图片 '{expected_path}' 不存在或未生成，无法用于最终拼接 (模式 3)。")

            if len(final_images_to_stitch_m3) >= 1: # 至少需要一张图才能拼接
                logging.info("开始最终的横向拼接 (模式 3)...")
                # 捕获 stitch_images_horizontally 返回的实际路径
                # --- 修改：移除模式3的水平间距 ---
                actual_final_output_path = stitch_images_horizontally(final_images_to_stitch_m3, FINAL_OUTPUT_M3, spacing=0, background_color=(255, 255, 255)) # 白色背景, spacing=0
                if not actual_final_output_path:
                    logging.error(f"未能成功生成最终拼接图片 (模式 3)。")
                else:
                     logging.info(f"成功生成最终拼接图片: '{actual_final_output_path}'")
                     # 中间文件 (line_player1.png, people_vote.png, line_player2.png in temp/) 会在 finally 块中删除
            else:
                logging.error("没有可用于最终横向拼接的有效图片 (模式 3)。")

            # 不再需要单独清理 people_vote.png，它会在 finally 中随 temp 目录一起删除

        elif CURRENT_MODE == 4:
            logging.info("===== 运行模式 4: 64进8专用模式 =====")
            mode4_player_coords_rel = [
                P64IN8_PLAYER1_COORD_REL_M4, P64IN8_PLAYER2_COORD_REL_M4,
                P64IN8_PLAYER3_COORD_REL_M4, P64IN8_PLAYER4_COORD_REL_M4,
                P64IN8_PLAYER5_COORD_REL_M4, P64IN8_PLAYER6_COORD_REL_M4,
                P64IN8_PLAYER7_COORD_REL_M4, P64IN8_PLAYER8_COORD_REL_M4
            ]
            mode4_final_output_names = [
                FINAL_OUTPUT_M4_P1, FINAL_OUTPUT_M4_P2,
                FINAL_OUTPUT_M4_P3, FINAL_OUTPUT_M4_P4,
                FINAL_OUTPUT_M4_P5, FINAL_OUTPUT_M4_P6,
                FINAL_OUTPUT_M4_P7, FINAL_OUTPUT_M4_P8
            ]
            mode4_generated_files = []
            actual_final_output_path = None # Initialize for mode 4

            for i, player_coord_rel in enumerate(mode4_player_coords_rel, 1):
                check_stop_signal()
                logging.info(f"===== 开始处理模式4 - Player {i} =====")
                temp_prefix = f"m4_p{i}_teams"
                output_image_base_name = f"line_m4_p{i}.png"

                player_stitched_temp_path = process_player(
                    player_coord_rel=player_coord_rel,
                    team_coords_rel=TEAM_COORDS_REL,
                    temp_prefix=temp_prefix,
                    output_image=output_image_base_name,
                    screenshot_region_rel=SCREENSHOT_REGION_REL,
                    window=nikke_window,
                    initial_delay=3.0
                )
                check_stop_signal()

                if player_stitched_temp_path and os.path.exists(player_stitched_temp_path):
                    final_output_name_base = mode4_final_output_names[i-1]
                    
                    # Handle filename conflicts for final output
                    unique_final_output_name = final_output_name_base
                    counter = 1
                    # Ensure base and ext are correctly derived for os.path.join later if needed
                    # For now, direct string manipulation is fine as it's just for the current directory
                    base_fn, ext_fn = os.path.splitext(final_output_name_base)
                    while os.path.exists(unique_final_output_name):
                        unique_final_output_name = f"{base_fn}_{counter}{ext_fn}"
                        counter += 1
                        if counter > 100: # Safety break
                            logging.error(f"无法为模式4 Player {i} 生成唯一最终文件名，已尝试到 '{unique_final_output_name}'")
                            unique_final_output_name = None # Indicate failure
                            break
                    
                    if unique_final_output_name:
                        try:
                            shutil.copy2(player_stitched_temp_path, unique_final_output_name)
                            logging.info(f"模式4 - Player {i} 的截图已成功保存为 '{unique_final_output_name}'")
                            mode4_generated_files.append(unique_final_output_name)
                        except Exception as e:
                            logging.error(f"复制模式4 - Player {i} 的截图到根目录失败: {e}")
                else:
                    logging.error(f"处理模式4 - Player {i} 失败，未生成临时拼接图。")

                check_stop_signal()
                if i < len(mode4_player_coords_rel): # If not the last player
                    logging.info(f"模式4 - Player {i} 处理完毕，点击退出...")
                    if not click_coordinates(EXIT_COORD_REL, nikke_window):
                        logging.warning(f"模式4 - Player {i} 后未能点击退出坐标。")
                    time.sleep(1.0) # Wait for UI to return
                check_stop_signal()
            
            # --- 新增：模式4总览图拼接 ---
            if mode4_generated_files and len(mode4_generated_files) == 8:
                logging.info(f"模式4已生成 {len(mode4_generated_files)} 个独立的玩家截图，尝试拼接总览图...")
                # 调用新的拼接函数，传入已生成的8个文件路径列表
                # FINAL_OUTPUT_M4_OVERVIEW 是新定义的常量 "64in8_overview.png"
                overview_path = stitch_mode4_overview(mode4_generated_files, FINAL_OUTPUT_M4_OVERVIEW)
                
                if overview_path:
                    logging.info(f"模式4总览图已成功生成: '{overview_path}'")
                    actual_final_output_path = overview_path
                    # 删除独立的玩家截图
                    logging.info("正在删除模式4的独立玩家截图...")
                    for file_path in mode4_generated_files:
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                logging.debug(f"已删除模式4独立截图: {file_path}")
                        except OSError as e:
                            logging.warning(f"无法删除模式4独立截图 '{file_path}': {e}")
                    mode4_generated_files = [] # 清空列表，因为文件已被删除
                else:
                    logging.error("模式4总览图拼接失败。将仅保留独立的8张玩家截图。")
                    actual_final_output_path = f"Mode 4 generated {len(mode4_generated_files)} separate files. Overview stitching failed."
            elif mode4_generated_files: # 如果生成了文件，但不足8个
                logging.warning(f"模式4生成了 {len(mode4_generated_files)} 个文件，但不足8个，无法拼接总览图。")
                actual_final_output_path = f"Mode 4 generated {len(mode4_generated_files)} separate files. Not enough files for overview."
            else: # 没有生成任何文件
                logging.error("模式4未能生成任何独立的玩家截图。")
                actual_final_output_path = None
            # --- 总览图拼接结束 ---
        elif CURRENT_MODE == 5:
            logging.info("===== 运行模式 5: 冠军争霸模式 =====")
            mode5_player_coords_rel = [
                CHAMPION_PLAYER1_COORD_REL_M5, CHAMPION_PLAYER2_COORD_REL_M5,
                CHAMPION_PLAYER3_COORD_REL_M5, CHAMPION_PLAYER4_COORD_REL_M5,
                CHAMPION_PLAYER5_COORD_REL_M5, CHAMPION_PLAYER6_COORD_REL_M5,
                CHAMPION_PLAYER7_COORD_REL_M5, CHAMPION_PLAYER8_COORD_REL_M5
            ]
            mode5_final_output_names = [
                FINAL_OUTPUT_M5_P1, FINAL_OUTPUT_M5_P2,
                FINAL_OUTPUT_M5_P3, FINAL_OUTPUT_M5_P4,
                FINAL_OUTPUT_M5_P5, FINAL_OUTPUT_M5_P6,
                FINAL_OUTPUT_M5_P7, FINAL_OUTPUT_M5_P8
            ]
            mode5_generated_files = []
            actual_final_output_path = None # Initialize for mode 5

            for i, player_coord_rel in enumerate(mode5_player_coords_rel, 1):
                check_stop_signal()
                logging.info(f"===== 开始处理模式5 - Player {i} =====")
                temp_prefix = f"m5_p{i}_teams"
                output_image_base_name = f"line_m5_p{i}.png"

                player_stitched_temp_path = process_player(
                    player_coord_rel=player_coord_rel,
                    team_coords_rel=TEAM_COORDS_REL, # Reuses TEAM_COORDS_REL as per plan
                    temp_prefix=temp_prefix,
                    output_image=output_image_base_name,
                    screenshot_region_rel=SCREENSHOT_REGION_REL, # Reuses SCREENSHOT_REGION_REL
                    window=nikke_window,
                    initial_delay=3.0
                )
                check_stop_signal()

                if player_stitched_temp_path and os.path.exists(player_stitched_temp_path):
                    final_output_name_base = mode5_final_output_names[i-1]
                    
                    unique_final_output_name = final_output_name_base
                    counter = 1
                    base_fn, ext_fn = os.path.splitext(final_output_name_base)
                    while os.path.exists(unique_final_output_name):
                        unique_final_output_name = f"{base_fn}_{counter}{ext_fn}"
                        counter += 1
                        if counter > 100:
                            logging.error(f"无法为模式5 Player {i} 生成唯一最终文件名，已尝试到 '{unique_final_output_name}'")
                            unique_final_output_name = None
                            break
                    
                    if unique_final_output_name:
                        try:
                            shutil.copy2(player_stitched_temp_path, unique_final_output_name)
                            logging.info(f"模式5 - Player {i} 的截图已成功保存为 '{unique_final_output_name}'")
                            mode5_generated_files.append(unique_final_output_name)
                        except Exception as e:
                            logging.error(f"复制模式5 - Player {i} 的截图到根目录失败: {e}")
                else:
                    logging.error(f"处理模式5 - Player {i} 失败，未生成临时拼接图。")

                check_stop_signal()
                if i < len(mode5_player_coords_rel): # If not the last player
                    logging.info(f"模式5 - Player {i} 处理完毕，点击退出...")
                    if not click_coordinates(EXIT_COORD_REL, nikke_window):
                        logging.warning(f"模式5 - Player {i} 后未能点击退出坐标。")
                    time.sleep(1.0)
                check_stop_signal()
            
            if mode5_generated_files and len(mode5_generated_files) == 8:
                logging.info(f"模式5已生成 {len(mode5_generated_files)} 个独立的玩家截图，尝试拼接总览图...")
                # Reuses stitch_mode4_overview as the logic is identical
                overview_path = stitch_mode4_overview(mode5_generated_files, FINAL_OUTPUT_M5_OVERVIEW)
                
                if overview_path:
                    logging.info(f"模式5总览图已成功生成: '{overview_path}'")
                    actual_final_output_path = overview_path
                    # 删除独立的玩家截图
                    logging.info("正在删除模式5的独立玩家截图...")
                    for file_path in mode5_generated_files:
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                logging.debug(f"已删除模式5独立截图: {file_path}")
                        except OSError as e:
                            logging.warning(f"无法删除模式5独立截图 '{file_path}': {e}")
                    mode5_generated_files = [] # 清空列表，因为文件已被删除
                else:
                    logging.error("模式5总览图拼接失败。将仅保留独立的8张玩家截图。")
                    actual_final_output_path = f"Mode 5 generated {len(mode5_generated_files)} separate files. Overview stitching failed."
            elif mode5_generated_files:
                logging.warning(f"模式5生成了 {len(mode5_generated_files)} 个文件，但不足8个，无法拼接总览图。")
                actual_final_output_path = f"Mode 5 generated {len(mode5_generated_files)} separate files. Not enough files for overview."
            else:
                logging.error("模式5未能生成任何独立的玩家截图。")
                actual_final_output_path = None
            # --- 总览图拼接结束 ---
        else:
            logging.error(f"未知的 CURRENT_MODE: {CURRENT_MODE}")

        # --- 任务完成后的弹窗 ---
        # 对于模式1,2,3, actual_final_output_path 是文件名。
        # 对于模式4, actual_final_output_path 是 "Mode 4 generated X files." 或 None,
        # mode4_generated_files 列表包含实际文件名。

        notification_message = None
        notification_title = None

        if CURRENT_MODE == 4:
            notification_title = "模式4完成"
            if actual_final_output_path and isinstance(actual_final_output_path, str) and os.path.exists(actual_final_output_path):
                notification_message = f"模式4操作完成！\n\n总览图已保存为: {os.path.basename(actual_final_output_path)}"
            elif actual_final_output_path and isinstance(actual_final_output_path, str) and "separate files" in actual_final_output_path:
                # This case implies overview stitching failed or not enough files, but some individual files might exist
                # if mode4_generated_files is not empty (meaning they weren't deleted due to successful overview)
                if "Overview stitching failed" in actual_final_output_path and mode4_generated_files:
                     num_files = len(mode4_generated_files)
                     notification_message = f"模式4操作完成。\n\n成功生成 {num_files} 张独立截图。\n总览图拼接失败。"
                elif "Not enough files for overview" in actual_final_output_path and mode4_generated_files:
                     num_files = len(mode4_generated_files)
                     notification_message = f"模式4操作完成。\n\n成功生成 {num_files} 张独立截图。\n文件不足，无法拼接总览图。"
                else: # Fallback or if mode4_generated_files was empty
                    notification_message = "模式4操作失败或未生成预期的总览图。"
            elif not actual_final_output_path and mode4_generated_files: # Overview failed, but individual files exist
                 notification_message = f"模式4操作完成！\n\n成功生成 {len(mode4_generated_files)} 张独立截图。\n总览图拼接失败或未执行。"
            elif not actual_final_output_path and not mode4_generated_files : # Complete failure
                notification_message = "模式4操作失败。\n\n未能生成任何截图文件。"
                logging.warning("模式4未能生成任何截图文件 (用于弹窗)。")
        elif CURRENT_MODE == 5:
            notification_title = "模式5完成"
            if actual_final_output_path and isinstance(actual_final_output_path, str) and os.path.exists(actual_final_output_path):
                notification_message = f"模式5操作完成！\n\n总览图已保存为: {os.path.basename(actual_final_output_path)}"
            elif actual_final_output_path and isinstance(actual_final_output_path, str) and "separate files" in actual_final_output_path:
                if "Overview stitching failed" in actual_final_output_path and mode5_generated_files:
                     num_files = len(mode5_generated_files)
                     notification_message = f"模式5操作完成。\n\n成功生成 {num_files} 张独立截图。\n总览图拼接失败。"
                elif "Not enough files for overview" in actual_final_output_path and mode5_generated_files:
                     num_files = len(mode5_generated_files)
                     notification_message = f"模式5操作完成。\n\n成功生成 {num_files} 张独立截图。\n文件不足，无法拼接总览图。"
                else: # Fallback
                    notification_message = "模式5操作失败或未生成预期的总览图。"
            elif not actual_final_output_path and mode5_generated_files: # Overview failed, but individual files exist
                 notification_message = f"模式5操作完成！\n\n成功生成 {len(mode5_generated_files)} 张独立截图。\n总览图拼接失败或未执行。"
            elif not actual_final_output_path and not mode5_generated_files: # Complete failure
                notification_message = "模式5操作失败。\n\n未能生成任何截图文件。"
                logging.warning("模式5未能生成任何截图文件 (用于弹窗)。")
        elif actual_final_output_path and isinstance(actual_final_output_path, str) and os.path.exists(actual_final_output_path):
            notification_message = f"截图完成！\n\n文件已保存为: {os.path.basename(actual_final_output_path)}"
            notification_title = "操作完成"
        else:
            if CURRENT_MODE not in [4, 5] :
                logging.warning("未找到最终输出文件或操作未成功完成，无法提供打开选项。")

        if notification_message and notification_title:
            logging.info("任务完成，准备显示通知弹窗...")
            # MessageBoxW constants
            MB_OK = 0x00000000
            MB_ICONINFORMATION = 0x00000040
            MB_SETFOREGROUND = 0x00010000
            MB_TOPMOST = 0x00040000

            time.sleep(0.5)
            try:
                ctypes.windll.user32.MessageBoxW(None, notification_message, notification_title, MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND | MB_TOPMOST)
                logging.info("通知弹窗已显示。")
            except Exception as mb_err:
                logging.error(f"显示通知消息框时出错: {mb_err}")
        # --- 弹窗结束 ---

    except Exception as e:
        logging.exception(f"脚本执行过程中发生意外错误: {e}")
    finally:
        # --- 新增：清理临时目录 ---
        if os.path.exists(TEMP_DIR):
            try:
                shutil.rmtree(TEMP_DIR)
                logging.info(f"已成功删除临时目录 '{TEMP_DIR}' 及其内容。")
            except Exception as clean_err:
                logging.error(f"清理临时目录 '{TEMP_DIR}' 时发生错误: {clean_err}")
        # --- 清理结束 ---
        keyboard.remove_hotkey(STOP_HOTKEY)
        logging.info("脚本执行完毕或已停止。")


if __name__ == "__main__":
    # --- 新增：管理员权限检查 ---
    if sys.platform == 'win32': # 再次确认是 Windows
        if not is_admin():
            logging.error("脚本需要管理员权限才能运行。")
            # 显示一个 Windows 弹窗消息
            # MessageBoxW(hWnd, lpText, lpCaption, uType)
            # hWnd=None: 使消息框成为应用程序模态
            # lpText: 消息内容 (使用 Unicode)
            # lpCaption: 标题 (使用 Unicode)
            # uType: 消息框样式 (0x30 = MB_OK | MB_ICONWARNING)
            ctypes.windll.user32.MessageBoxW(None, "请以管理员身份运行此脚本。", "权限不足", 0x30) 
            sys.exit(1) # 退出脚本
        else:
            logging.info("脚本以管理员权限运行。")
    # --- 管理员检查结束 ---

    # --- 获取用户选择的模式 ---
    valid_modes = [1, 2, 3, 4, 5] # 新增：包含模式3、模式4和模式5
    while CURRENT_MODE not in valid_modes:
        try:
            mode_input = input(f"请选择运行模式（如果不知道选什么那就是选1）\n 1: 买马预测模式（请提前进入【投注】页面）\n 2: 复盘模式（请提前进入应援结果【显示5队胜负】的页面）\n 3: 我就要反买立此存档坐等装逼（或装死）- 请提前进入投注页面\n 4: 64进8专用模式 (请提前进入64进8的玩家列表页面)\n 5: 冠军争霸模式 (请提前进入冠军争霸的玩家列表页面)\n 请输入你的选择： ") # 更新提示信息
            mode_int = int(mode_input)
            if mode_int in valid_modes:
                CURRENT_MODE = mode_int
                logging.info(f"已选择模式 {CURRENT_MODE}")
            else:
                logging.warning(f"输入无效，请输入 {', '.join(map(str, valid_modes))} 中的一个。") # 动态提示有效模式
        except ValueError:
            logging.warning(f"输入无效，请输入数字 {', '.join(map(str, valid_modes))} 中的一个。") # 动态提示有效模式
        except EOFError: # Handle case where input stream is closed (e.g., piping)
             logging.error("无法读取输入。退出。")
             sys.exit(1)
        except KeyboardInterrupt: # Handle Ctrl+C during input
             logging.info("用户中断输入。退出。")
             sys.exit(0)
    # --- 模式选择结束 ---

    # 添加一个启动5s延迟，给用户时间切换到目标窗口或准备
    start_delay = 5 
    logging.info(f"脚本将在 {start_delay} 秒后开始... 请准备好 NIKKE 窗口。")
    
    # --- 关键点：确保 stop_script = False 在此循环之前已在全局定义 ---
    try:
        for i in range(start_delay, 0, -1):
             logging.info(f"...{i}")
             time.sleep(1)
             # 在setup_stop_hotkey之前可能无法停止，但检查无害
             # 或者在 setup_stop_hotkey 之后再检查
             # 为了安全，每次循环都检查全局标志
             if stop_script: # 访问全局变量 stop_script
                  logging.info("脚本在启动前被停止。")
                  sys.exit(0)
        
        # 在调用 main 之前设置热键似乎更合理，
        # 但当前结构是在 main 内部设置。
        # 如果希望延迟期间也能用热键停止，需要提前设置。
        # 目前维持原状，仅确保 stop_script 定义存在。
        
        main()
        
    except NameError as e:
         logging.error(f"发生 NameError: {e}。请确保所有全局变量（如 'stop_script'）已在脚本顶部正确定义。")
         sys.exit(1)
    except Exception as e:
         logging.exception(f"脚本启动或执行 main 时发生未处理的错误: {e}")
         sys.exit(1)
