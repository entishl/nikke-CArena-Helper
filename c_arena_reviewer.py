# -*- coding: utf-8 -*-
# 作者 Gemini
# Ctrl+C V by enty
import ctypes
import os
import sys
import time
import keyboard
import pyautogui
import psutil
import pygetwindow as gw # 保留导入，但查找逻辑会改变
from PIL import Image
import tkinter as tk
import threading
import zipfile
import math
# 检查并导入 pywin32
try:
    import win32gui
    import win32process
    import win32con
    import win32api # 用于获取屏幕缩放
except ImportError:
    print("错误：缺少 'pywin32' 库。")
    print("请在 PyCharm 的终端或命令行中运行： pip install pywin32")
    sys.exit(1)

# --- 配置区域 ---


# 模式 9 配置
OUTPUT_WEBP_DIR = "output" # 模式 9 的输出目录
ZIP_FILENAME = "output.zip" # 模式 9 生成的压缩包名称
TARGET_WIDTH = 1238
TARGET_HEIGHT = 990
WEBP_QUALITY = 90
WEBP_METHOD = 6 # 0 (fastest) to 6 (slowest, best compression)
# 模式 9 配置结束
BASE_WIDTH = 3840
BASE_HEIGHT = 2160
PROCESS_NAME = "nikke.exe" # 大小写敏感的进程名

OUTPUT_DIR = "final"
TEMP_DIR = "temp_screenshots" # 临时文件目录

# 4K 分辨率下的坐标和区域 (相对于游戏窗口客户区)
COORDS_4K = {
    # ... (坐标保持不变) ...
    "group_1": (270, 560), "group_2": (740, 560), "group_3": (1200, 560), "group_4": (1680, 560),
    "group_5": (2160, 560), "group_6": (2620, 560), "group_7": (3100, 560), "group_8": (3600, 560),
    "8in4_1": (1833, 896), "8in4_2": (2044, 896), "8in4_3": (1773, 1692), "8in4_4": (2132, 1703),
    "4in2_1": (1923, 1160), "4in2_2": (1923, 1410), # "2in1" 坐标点暂时移除，其值将在运行时动态确定
    "4in2_2_real": (2176, 1742), # 新增的实际点击坐标
    "player1": (1534, 1096), "player2": (2182, 1096),
    "result_region": (1607, 968, 2116, 1642),
    "close_result": (2369, 529),
    "team1": (1515, 1064), "team2": (1734, 1064), "team3": (1928, 1064),
    "team4": (2112, 1064), "team5": (2303, 1064),
    "close_teamview": (2370, 681),
    "team_region": (1433, 1134, 2417, 1530),
    # 新增玩家信息截图区域和坐标点
    "player_info": (1433, 768, 2417, 963), # 玩家信息区域1
    "player_detailinfo_2": (1560, 888),    # 玩家详情按钮2
    "player_detailinfo_3": (2200, 1990),   # 玩家详情按钮3 (注意：这个Y坐标 1990 看起来很大，请确认是否正确)
    "player_detailinfo_close": (2418, 202), # 关闭玩家详情按钮
    "player_info_2": (1433, 1344, 2417, 1529), # 玩家信息区域2
    "player_info_3": (1433, 1768, 2417, 1842), # 玩家信息区域3
}

# 新增：模式 3 (冠军争霸赛) 的坐标
COORDS_4K_MODE3 = {
    # 模式 3 特有坐标
    "mode3_8in4_1": (1775, 827),
    "mode3_8in4_2": (2066, 827),
    "mode3_8in4_3": (1775, 1623),
    "mode3_8in4_4": (2066, 1623),
    "mode3_4in2_1": (1907, 1065),
    "mode3_4in2_2": (1910, 1340),
    # 模式 3 需要沿用模式 1/2 的其他坐标 (如果名称相同)
    "player1": (1534, 1096), # 沿用
    "player2": (2182, 1096), # 沿用
    "result_region": (1607, 968, 2116, 1642), # 沿用
    "close_result": (2369, 529), # 沿用
    "team1": (1515, 1064), # 沿用
    "team2": (1734, 1064), # 沿用
    "team3": (1928, 1064), # 沿用
    "team4": (2112, 1064), # 沿用
    "team5": (2303, 1064), # 沿用
    "close_teamview": (2370, 681), # 沿用
    "team_region": (1433, 1134, 2417, 1530), # 沿用
    "player_info": (1433, 768, 2417, 963), # 沿用
    "player_detailinfo_2": (1560, 888), # 沿用
    "player_detailinfo_3": (2200, 1990), # 沿用
    "player_detailinfo_close": (2418, 202), # 沿用
    "player_info_2": (1433, 1344, 2417, 1529), # 沿用
    "player_info_3": (1433, 1768, 2417, 1842), # 沿用
    # 模式 3 的比赛名称映射 (将通用名称映射到模式 3 特定坐标名)
    "match_map": {
        "8in4_1": "mode3_8in4_1",
        "8in4_2": "mode3_8in4_2",
        "8in4_3": "mode3_8in4_3",
        "8in4_4": "mode3_8in4_4",
        "4in2_1": "mode3_4in2_1",
        "4in2_2": "mode3_4in2_2",
    },
    # 模式 3 的取色点
    "color_check_1": "mode3_4in2_1",
    "color_check_2": "mode3_4in2_2",
    # 修正：明确模式 3 也使用固定的 4in2_2_real 坐标
    "4in2_2_real": (2176, 1742),
}


MATCH_NAMES = ["8in4_1", "8in4_2", "8in4_3", "8in4_4", "4in2_1", "4in2_2", "2in1"]
GROUP_NAMES = [f"group_{i}" for i in range(1, 9)]
TEAM_NAMES = [f"team{i}" for i in range(1, 6)]

# --- 全局变量 ---
scale_x = 1.0
scale_y = 1.0
# 新增: 存储目标窗口信息
target_hwnd = None
window_left = 0
window_top = 0
window_width = 0
window_height = 0
# DPI缩放因子
dpi_scale = 1.0

# 修改：active_coords 将根据模式指向正确的坐标字典
active_coords = {} # 当前模式使用的基础坐标 (将被 COORDS_4K 或 COORDS_4K_MODE3 填充)
scaled_coords = {} # 存储缩放后的 *相对* 坐标
scaled_regions = {} # 存储缩放后的 *相对* 区域 (x, y, width, height)
stop_requested = False
script_running = False
run_mode = 7 # 6: 完整模式, 7: 单组模式, 8: 冠军赛模式, 9: 打包模式

# --- 辅助函数 ---

# is_admin, show_message 保持不变
# get_screen_resolution 不再需要，可以移除或注释掉
# def get_screen_resolution(): ...

# --- 修改后的核心函数 ---

def _get_dpi_scale():
    """获取主显示器的 DPI 缩放比例"""
    try:
        # 获取主显示器的设备上下文
        dc = win32gui.GetDC(0)
        # 获取水平和垂直方向的逻辑像素点数
        physical_width = win32api.GetDeviceCaps(dc, win32con.DESKTOPHORZRES)
        logical_width = win32api.GetDeviceCaps(dc, win32con.LOGPIXELSX)
        win32gui.ReleaseDC(0, dc)
        # 96 DPI 是 Windows 的标准 DPI（100% 缩放）
        scale = logical_width / 96.0
        print(f"检测到 DPI 缩放比例: {scale:.2f}")
        return scale
    except Exception as e:
        print(f"警告：无法检测 DPI 缩放，将使用默认值 1.0。错误: {e}")
        return 1.0

def find_nikke_window_by_pid(pid):
    """使用 PID 查找 NIKKE 窗口句柄 (HWND)"""
    hwnd = None
    def callback(hwnd_enum, _):
        nonlocal hwnd
        # 检查窗口是否可见且拥有标题 (避免一些不可见的辅助窗口)
        if win32gui.IsWindowVisible(hwnd_enum) and win32gui.GetWindowText(hwnd_enum):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd_enum)
            if found_pid == pid:
                hwnd = hwnd_enum
                return False # 停止枚举
        return True # 继续枚举

    try:
        win32gui.EnumWindows(callback, None)
    except Exception as e:
        print(f"枚举窗口时出错: {e}")
    return hwnd

def check_and_activate_nikke():
    """检查 NIKKE 进程是否存在，找到其窗口，激活并获取窗口信息"""
    global target_hwnd, window_left, window_top, window_width, window_height, dpi_scale
    nikke_pid = None
    process_found = False
    for proc in psutil.process_iter(['pid', 'name']):
        # 规则 1: 精确、大小写敏感的进程名匹配
        if proc.info['name'] == PROCESS_NAME:
            nikke_pid = proc.info['pid']
            process_found = True
            print(f"找到 {PROCESS_NAME} 进程 (PID: {nikke_pid})")
            break

    if not process_found:
        show_message("错误", f"未找到 {PROCESS_NAME} 进程。\n请先运行 NIKKE 后再运行本脚本。")
        return False

    # 规则 2: 移除窗口标题检测，使用 PID 查找窗口
    target_hwnd = find_nikke_window_by_pid(nikke_pid)

    if not target_hwnd:
        show_message("错误", f"找到了 {PROCESS_NAME} 进程 (PID: {nikke_pid})，但未能找到其主窗口。\n请确保游戏窗口可见。")
        # 打印所有窗口标题以供调试（可选）
        print("当前所有可见窗口标题:")
        try:
            def enum_visible_windows_callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        print(f"- HWND: {hwnd}, PID: {pid}, Title: '{title}'")
                return True
            win32gui.EnumWindows(enum_visible_windows_callback, None)
        except Exception as e:
            print(f"调试: 枚举窗口时出错: {e}")
        return False

    print(f"找到 {PROCESS_NAME} 窗口句柄 (HWND): {target_hwnd}")

    try:
        # 规则 3: 获取窗口客户区大小和位置
        # 激活窗口前获取 DPI，因为激活可能触发 DPI 变化事件
        dpi_scale = _get_dpi_scale()

        # 尝试激活窗口
        if win32gui.IsIconic(target_hwnd): # 如果最小化则恢复
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            time.sleep(0.5)
        # 将窗口带到前台
        win32gui.SetForegroundWindow(target_hwnd)
        time.sleep(1) # 等待窗口激活

        # 获取客户区矩形 (相对于窗口左上角，通常是 0, 0, width, height)
        client_rect = win32gui.GetClientRect(target_hwnd)
        window_width = client_rect[2]
        window_height = client_rect[3]

        # 获取客户区左上角在屏幕上的坐标
        client_origin_screen = win32gui.ClientToScreen(target_hwnd, (0, 0))
        window_left = client_origin_screen[0]
        window_top = client_origin_screen[1]

        print(f"窗口客户区大小: {window_width} x {window_height}")
        print(f"窗口客户区屏幕位置 (左上角): ({window_left}, {window_top})")

        # 验证获取到的尺寸是否有效
        if window_width <= 0 or window_height <= 0:
             print(f"错误：获取到的窗口尺寸无效 ({window_width}x{window_height})。脚本无法继续。")
             show_message("错误", "无法获取有效的游戏窗口尺寸。")
             target_hwnd = None # 重置 hwnd
             return False

        print("NIKKE 窗口已激活并获取几何信息")
        return True

    except Exception as e:
        print(f"激活 NIKKE 窗口或获取几何信息时出错: {e}")
        # 尝试打印更多错误信息
        import traceback
        traceback.print_exc()
        show_message("错误", f"激活 NIKKE 窗口时出错: {e}")
        target_hwnd = None # 重置 hwnd
        return False

def calculate_scale():
    """计算并设置坐标缩放比例 (基于窗口客户区大小)"""
    global scale_x, scale_y, window_width, window_height
    if window_width == 0 or window_height == 0:
        print("错误：窗口尺寸未正确获取，无法计算缩放比例。")
        # 可以在这里选择退出或使用默认值，但最好是在 check_and_activate_nikke 中阻止执行
        return False # 表示计算失败

    print(f"根据窗口客户区计算缩放: {window_width} x {window_height}")
    scale_x = window_width / BASE_WIDTH
    scale_y = window_height / BASE_HEIGHT
    print(f"坐标缩放比例: x={scale_x:.4f}, y={scale_y:.4f}")
    return True # 表示计算成功

def scale_coord(coord_name, coords_dict):
    """获取指定字典中的基础坐标并缩放为 *相对于窗口客户区* 的坐标"""
    if coord_name not in coords_dict:
        print(f"错误：坐标名称 '{coord_name}' 未在当前模式的坐标字典中定义")
        return None
    base_coord = coords_dict[coord_name]
    # 确保获取到的是坐标元组 (x, y)
    if not isinstance(base_coord, tuple) or len(base_coord) != 2:
        print(f"错误：坐标 '{coord_name}' 在字典中的值无效: {base_coord}")
        return None
    base_x, base_y = base_coord
    # 直接缩放，不考虑 DPI，因为坐标是基于游戏内部渲染分辨率
    return int(base_x * scale_x), int(base_y * scale_y)

def scale_region(region_name, coords_dict):
    """获取指定字典中的基础区域并缩放为 *相对于窗口客户区* 的区域 (x, y, width, height)"""
    if region_name not in coords_dict:
        print(f"错误：区域名称 '{region_name}' 未在当前模式的坐标字典中定义")
        return None
    base_region = coords_dict[region_name]
    # 确保获取到的是区域元组 (x1, y1, x2, y2)
    if not isinstance(base_region, tuple) or len(base_region) != 4:
        print(f"错误：区域 '{region_name}' 在字典中的值无效: {base_region}")
        return None
    x1, y1, x2, y2 = base_region
    # 直接缩放，不考虑 DPI
    scaled_x1 = int(x1 * scale_x)
    scaled_y1 = int(y1 * scale_y)
    scaled_x2 = int(x2 * scale_x)
    scaled_y2 = int(y2 * scale_y)
    width = scaled_x2 - scaled_x1
    height = scaled_y2 - scaled_y1
    # 返回相对于窗口客户区的 (左上角x, 左上角y, 宽度, 高度)
    return scaled_x1, scaled_y1, width, height

def safe_click(coord_name, delay_after=0.5):
    """带错误检查和延迟的点击操作 (计算绝对屏幕坐标)"""
    global stop_requested, window_left, window_top
    if stop_requested: return False # 如果请求停止，则不执行

    # 获取相对于窗口客户区的缩放后坐标
    relative_coord = scaled_coords.get(coord_name)
    if relative_coord:
        # 计算绝对屏幕坐标
        abs_x = window_left + relative_coord[0]
        abs_y = window_top + relative_coord[1]
        try:
            print(f"  点击: {coord_name} at screen ({abs_x}, {abs_y}) [relative: {relative_coord}]")
            pyautogui.click(abs_x, abs_y)
            time.sleep(delay_after) # 点击后短暂等待
            return True
        except Exception as e:
            print(f"错误：点击 {coord_name} 在屏幕坐标 ({abs_x}, {abs_y}) 失败: {e}")
            return False
    else:
        print(f"错误：无法获取缩放后的相对坐标 '{coord_name}'")
        return False

def safe_screenshot(region_name, filename):
    """带错误检查的截图操作 (计算绝对屏幕区域)"""
    global stop_requested, window_left, window_top
    if stop_requested: return False # 如果请求停止，则不执行

    # 获取相对于窗口客户区的缩放后区域 (x, y, width, height)
    relative_region = scaled_regions.get(region_name)
    if relative_region:
        rel_x, rel_y, rel_w, rel_h = relative_region
        # 计算绝对屏幕区域
        abs_x = window_left + rel_x
        abs_y = window_top + rel_y
        # 确保宽度和高度大于0
        if rel_w <= 0 or rel_h <= 0:
            print(f"错误: 截图区域 '{region_name}' 的计算尺寸无效 ({rel_w}x{rel_h})。跳过截图。")
            return False
        abs_region = (abs_x, abs_y, rel_w, rel_h)

        try:
            print(f"  截图: {region_name} from screen region {abs_region} to {filename} [relative: {relative_region}]")
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            screenshot = pyautogui.screenshot(region=abs_region)
            screenshot.save(filename)
            return True
        except Exception as e:
            print(f"错误：截图 {region_name} (区域: {abs_region}) 失败: {e}")
            # 尝试捕获屏幕权限错误 (macOS - 虽然我们现在是Windows, 但保留检查无妨)
            if "Quartz" in str(e) or "NSRunningApplication" in str(e):
                 print("截图权限错误：请确保您的操作系统允许Python或终端进行屏幕录制。")
                 show_message("权限错误", "截图失败，请检查屏幕录制权限！")
                 request_stop() # 停止脚本
            elif "access is denied" in str(e).lower() or "error code 5" in str(e):
                 print("权限错误：可能是由于管理员权限不足或屏幕保护软件阻止。")
                 show_message("权限错误", "截图失败，可能是权限不足或安全软件阻止。请尝试以管理员身份运行。")
                 # 不自动停止，给用户时间查看
            return False
    else:
        print(f"错误：无法获取缩放后的相对区域 '{region_name}'")
        return False

def get_pixel_color(coord_name):
    """获取指定坐标名称处的屏幕像素 RGB 颜色"""
    global window_left, window_top, scaled_coords
    relative_coord = scaled_coords.get(coord_name)
    if relative_coord:
        abs_x = window_left + relative_coord[0]
        abs_y = window_top + relative_coord[1]
        try:
            # 确保坐标在屏幕范围内
            screen_width, screen_height = pyautogui.size()
            if 0 <= abs_x < screen_width and 0 <= abs_y < screen_height:
                color = pyautogui.pixel(abs_x, abs_y)
                print(f"  取色: {coord_name} at screen ({abs_x}, {abs_y}) -> RGB: {color}")
                return color
            else:
                print(f"错误：计算出的绝对坐标 ({abs_x}, {abs_y}) 超出屏幕范围 ({screen_width}x{screen_height})。")
                return None
        except Exception as e:
            print(f"错误：获取坐标 {coord_name} ({abs_x}, {abs_y}) 的像素颜色失败: {e}")
            return None
    else:
        print(f"错误：无法获取缩放后的相对坐标 '{coord_name}' 用于取色。")
        return None

# --- 主自动化逻辑函数 ---

def run_automation():
    """执行自动化主逻辑"""
    global script_running, stop_requested, run_mode
    # 修改：现在操作 active_coords, scaled_coords, scaled_regions
    global active_coords, scaled_coords, scaled_regions

    script_running = True
    stop_requested = False
    print("\n自动化脚本启动...")

    # 1. 检查并激活 NIKKE，获取窗口信息
    if not check_and_activate_nikke():
        script_running = False
        print("无法找到或激活 NIKKE 窗口，脚本退出。")
        return

    # 2. 计算缩放比例
    if not calculate_scale():
        script_running = False
        print("无法计算坐标缩放比例，脚本退出。")
        return

    # 3. 选择当前模式使用的坐标字典
    if run_mode == 8:
        active_coords = COORDS_4K_MODE3
        print("使用模式 8 (冠军赛) 坐标系")
    else: # 模式 6 和 7 使用默认坐标系
        active_coords = COORDS_4K
        print("使用模式 6/7 (常规赛) 坐标系")

    # 4. 预先计算所有缩放后的相对坐标和区域 (使用 active_coords)
    # 清空旧数据
    scaled_coords.clear()
    scaled_regions.clear()

    print("正在计算缩放后的坐标和区域...")
    calculation_ok = True
    for name, value in active_coords.items():
        if isinstance(value, tuple):
            if len(value) == 2: # 是坐标
                scaled = scale_coord(name, active_coords)
                if scaled:
                    scaled_coords[name] = scaled
                else:
                    print(f"  - 坐标缩放失败: {name}")
                    calculation_ok = False
            elif len(value) == 4: # 是区域
                scaled = scale_region(name, active_coords)
                if scaled:
                    scaled_regions[name] = scaled
                else:
                    print(f"  - 区域缩放失败: {name}")
                    calculation_ok = False
            # 忽略其他类型的值，如 "match_map"
        # else: # 忽略非元组项，例如 match_map
        #    print(f"  - 忽略非坐标/区域项: {name}")

    # 验证计算结果是否有效
    # (检查 calculation_ok 标志)
    if not calculation_ok:
        print("错误：部分或全部坐标/区域无法正确缩放。请检查坐标定义和窗口尺寸。")
        script_running = False
        return

    # 5. 创建输出和临时目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    print(f"最终结果将保存在: {os.path.abspath(OUTPUT_DIR)}")
    print(f"临时文件将保存在: {os.path.abspath(TEMP_DIR)}")

    # 6. 执行模式选择和主循环
    file_prefix_base = "group" # 默认前缀基础
    if run_mode == 6: # 完整模式
        print("\n选择模式：完整模式 (处理所有8个组)")
        groups_to_process = range(1, 9)
    elif run_mode == 7: # 单组模式
        print("\n选择模式：单组模式 (仅处理当前组，文件名前缀为 group1)")
        groups_to_process = [1] # 只处理一次
        file_prefix_base = "group1" # 固定前缀
    elif run_mode == 8: # 冠军赛模式
        print("\n选择模式：冠军赛模式 (处理当前界面，文件名前缀为 champain)")
        groups_to_process = [1] # 只处理一次
        file_prefix_base = "champain" # 固定前缀
    else:
        print(f"错误：未知的运行模式 {run_mode} 无法执行自动化。")
        script_running = False
        return

    total_matches = len(MATCH_NAMES) * len(groups_to_process)
    completed_matches = 0
    start_time = time.time()

    # 主循环
    for group_index in groups_to_process: # 对于模式 2 和 3，这个循环只执行一次 (group_index=1)
        if stop_requested: break

        # 确定当前循环的文件名前缀
        if run_mode == 6:
            current_file_prefix = f"group{group_index}"
            print(f"\n====== 开始处理组别 {group_index} (前缀: {current_file_prefix}) ======")
        else: # 模式 7 或 8
            current_file_prefix = file_prefix_base # 使用固定的 "group1" 或 "champain"
            print(f"\n====== 开始处理当前界面 (前缀: {current_file_prefix}) ======")


        # --- 为 4in2 和 2in1 确定点击目标 (根据当前模式和取色) ---
        # 确定用于取色的坐标名称
        color_check_coord1_name = active_coords.get("color_check_1", "4in2_1" if run_mode != 8 else "mode3_4in2_1")
        color_check_coord2_name = active_coords.get("color_check_2", "4in2_2" if run_mode != 8 else "mode3_4in2_2")

        # 修正：始终使用 "4in2_2_real" 作为第二次点击的目标名称
        # 确保 "4in2_2_real" 在 active_coords 中存在
        second_target_for_4in2_2_match = "4in2_2_real"
        if "4in2_2_real" not in active_coords:
             print(f"错误：坐标 '4in2_2_real' 未在当前模式 ({run_mode}) 的坐标字典中定义！脚本无法继续。")
             script_running = False
             return # 关键坐标缺失，无法继续

        # 初始化点击目标变量 (使用取色点的名称作为默认值)
        target_for_4in2_1_match = color_check_coord1_name # 默认 B 小的点
        target_for_2in1_match = color_check_coord1_name   # 默认 B 大的点
        first_target_for_4in2_2_match = color_check_coord1_name # 默认 B 大的点

        print(f"  正在确定 4in2 和 2in1 的点击目标 (基于 {color_check_coord1_name} 和 {color_check_coord2_name})...")
        color1 = get_pixel_color(color_check_coord1_name)
        color2 = get_pixel_color(color_check_coord2_name)

        if color1 and color2:
            b1 = color1[2] # RGB 的 B 分量
            b2 = color2[2]
            print(f"  颜色比较: {color_check_coord1_name} B={b1}, {color_check_coord2_name} B={b2}")
            if b2 > b1:
                target_for_2in1_match = color_check_coord2_name # B 大的
                first_target_for_4in2_2_match = color_check_coord2_name # B 大的
                target_for_4in2_1_match = color_check_coord1_name # B 小的
                print(f"  判定: {color_check_coord2_name} 的 B 值更大。")
            else:
                target_for_2in1_match = color_check_coord1_name # B 大的 (或相等)
                first_target_for_4in2_2_match = color_check_coord1_name # B 大的 (或相等)
                target_for_4in2_1_match = color_check_coord2_name # B 小的
                print(f"  判定: {color_check_coord1_name} 的 B 值更大或相等。")
        else:
            print(f"  警告：无法获取 {color_check_coord1_name} 或 {color_check_coord2_name} 的颜色，将使用默认点击目标。")
            # 保持上面基于模式设置的默认值

        print(f"  最终点击目标: 4in2_1 使用 '{target_for_4in2_1_match}', 4in2_2 先点 '{first_target_for_4in2_2_match}' 再点 '{second_target_for_4in2_2_match}', 2in1 使用 '{target_for_2in1_match}'")
        # --- 结束取色判断逻辑 ---


        # 只有在完整模式(模式1)下才点击分组按钮
        if run_mode == 6:
            group_coord_name = f"group_{group_index}" # 仅模式 1 需要
            if not safe_click(group_coord_name, delay_after=6): # 点击分组按钮，等待加载
                 print(f"错误：点击组别 {group_index} 失败，跳过该组")
                 continue # 跳到下一个组
            if stop_requested: break
            # time.sleep(1) # 可选：额外等待，确保UI稳定

        # 循环处理该组/当前界面的7场比赛
        for match_name in MATCH_NAMES:
            if stop_requested: break

            # 修正：确保传递正确的参数给 process_single_match
            if process_single_match(current_file_prefix, match_name,
                                    target_for_4in2_1_match,
                                    first_target_for_4in2_2_match,
                                    second_target_for_4in2_2_match,
                                    target_for_2in1_match):
                completed_matches += 1
                print(f"进度: {completed_matches}/{total_matches} ({completed_matches/total_matches:.1%})")
            else:
                print(f"处理 {current_file_prefix} - {match_name} 时出错或被中断。")
                if stop_requested:
                    print("检测到停止请求，正在尝试安全退出...")
                    break # 跳出内部比赛循环
                else:
                    print("尝试继续处理下一场比赛...")

            if stop_requested:
                 print("检测到停止请求，正在中断...")
                 break

        if stop_requested:
            print("脚本执行被中断。")
            break # 跳出外部组别循环

        print(f"====== 完成处理组别 {group_index} ======")
        # ---

    # 结束逻辑 (不变)
    end_time = time.time()
    duration = end_time - start_time
    print("\n====== 自动化任务执行完毕 ======")
    print(f"总耗时: {duration:.2f} 秒")
    # 统计 final 目录中符合命名规则的文件数
    # 修改：根据模式判断前缀
    expected_prefix = "group" if run_mode in [6, 7] else "champain"
    try:
        final_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(expected_prefix) and f.endswith(".png")]
        print(f"成功处理并保存的最终图片数量: {len(final_files)}")
    except FileNotFoundError:
        print(f"警告：输出目录 '{OUTPUT_DIR}' 未找到，无法统计最终文件。")
        final_files = [] # 避免后续错误

    if stop_requested:
        print("任务被人为中断。")

    # 根据模式调整完成消息
    mode_desc = {6: "完整模式", 7: "单组模式", 8: "冠军赛模式"}
    completion_msg = (
        f"脚本执行完毕 (模式: {mode_desc.get(run_mode, '未知')})。\n"
        f"总耗时: {duration:.2f} 秒。\n"
        f"结果已保存至 '{OUTPUT_DIR}' 文件夹，文件名前缀为 '{expected_prefix}'。"
    )
    show_message("完成", completion_msg)

    script_running = False
    # 清理临时文件的逻辑可以保留或按需启用
    # cleanup_all_temp_files() # 如果需要全局清理

# --- 其他函数 (比如 is_admin, show_message, stitch*, cleanup*, process_single_match, 热键处理, main) ---
# 这些函数不需要修改，因为它们的内部逻辑要么与窗口/坐标无关，
# 要么依赖于已经被修改的 safe_click/safe_screenshot/scaled_coords/scaled_regions。
# 为确保完整性，我会将它们也包含在下面，但标记为“无需修改”。

# --- 无需修改的辅助函数 ---

def is_admin():
    """检查当前脚本是否以管理员权限运行 (仅限 Windows)"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def show_message(title, text):
    """显示一个简单的消息弹窗"""
    # 使用 ctypes.windll.user32.MessageBoxW 来避免编码问题
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x40 | 0x1000) # MB_ICONINFORMATION | MB_SYSTEMMODAL

def stitch_images_vertically(image_paths, output_path):
    """垂直拼接图片"""
    global stop_requested
    if stop_requested: return False

    images = []
    valid_paths = []
    for p in image_paths:
        if os.path.exists(p):
            try:
                img = Image.open(p)
                images.append(img)
                valid_paths.append(p)
            except Exception as e:
                print(f"警告: 加载图片 {p} 失败，将跳过: {e}")
        else:
            print(f"警告: 拼接图片路径不存在，将跳过: {p}")

    if not images:
        print(f"错误：无法加载任何有效图片用于垂直拼接: {image_paths}")
        return False

    widths, heights = zip(*(i.size for i in images))
    total_height = sum(heights)
    max_width = max(widths)

    # 创建白色背景画布
    new_im = Image.new('RGB', (max_width, total_height), (255, 255, 255))

    y_offset = 0
    for im in images:
        # 如果图片宽度小于最大宽度，可以考虑居中粘贴
        x_offset = (max_width - im.size[0]) // 2
        new_im.paste(im, (x_offset, y_offset))
        y_offset += im.size[1]
        im.close() # 关闭图片释放内存

    try:
        print(f"  垂直拼接: {len(images)} 张图片 ({valid_paths}) -> {output_path}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        new_im.save(output_path)
        return True
    except Exception as e:
        print(f"错误：保存垂直拼接图片失败 {output_path}: {e}")
        return False
    finally:
        if 'new_im' in locals():
            new_im.close()

def stitch_images_horizontally(image_paths, output_path):
    """水平拼接图片 (调整为更灵活地处理图片数量)"""
    global stop_requested
    if stop_requested: return False

    images = []
    valid_paths = []
    for p in image_paths:
        if p and os.path.exists(p): # 检查路径是否有效且存在
            try:
                img = Image.open(p)
                images.append(img)
                valid_paths.append(p)
            except Exception as e:
                print(f"警告: 加载图片 {p} 失败，将跳过: {e}")
        else:
             # 如果路径本身就是 None 或空字符串，静默跳过
             if p:
                 print(f"警告: 拼接图片路径不存在或无效，将跳过: {p}")

    if not images:
        print(f"错误：无法加载任何有效图片用于水平拼接: {image_paths}")
        return False
    elif len(images) != 3:
         print(f"警告: 水平拼接期望3张图片，实际加载 {len(images)} 张: {valid_paths}。将继续拼接。")
         # 可以根据需要调整此处的行为，例如如果少于3张则失败

    widths, heights = zip(*(i.size for i in images))
    total_width = sum(widths)
    max_height = max(heights)

    # 创建白色背景画布
    new_im = Image.new('RGB', (total_width, max_height), (255, 255, 255))

    x_offset = 0
    for im in images:
        # 垂直居中粘贴
        y_offset = (max_height - im.size[1]) // 2
        new_im.paste(im, (x_offset, y_offset))
        x_offset += im.size[0]
        im.close() # 关闭图片释放内存

    try:
        print(f"  水平拼接: {len(images)} 张图片 ({valid_paths}) -> {output_path}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        new_im.save(output_path)
        return True
    except Exception as e:
        print(f"错误：保存水平拼接图片失败 {output_path}: {e}")
        return False
    finally:
        if 'new_im' in locals():
             new_im.close()

def cleanup_temp_files(file_prefix, match_name):
    """清理指定赛事的临时截图文件 (使用传入的文件前缀)"""
    print(f"  清理临时文件 for {file_prefix}_{match_name}...")
    files_to_remove = []
    # 队伍截图
    for player_num in [1, 2]:
        player_coord_name = f"player{player_num}" # 获取 player 坐标名
        for team_index in range(1, 6):
            files_to_remove.append(os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_{player_coord_name}_team{team_index}.png"))
        # 新增：玩家信息截图
        files_to_remove.append(os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_{player_coord_name}_playerinfo.png"))
        files_to_remove.append(os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_{player_coord_name}_player_info_2.png"))
        files_to_remove.append(os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_{player_coord_name}_player_info_3.png"))
        # 拼接的玩家完整图 (现在包含信息和队伍)
        files_to_remove.append(os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_{player_coord_name}.png"))

    # 赛果截图
    files_to_remove.append(os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_result.png"))

    removed_count = 0
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                removed_count += 1
            except OSError as e:
                print(f"警告：无法删除临时文件 {file_path}: {e}")
    print(f"  已尝试清理，找到并删除 {removed_count} 个临时文件。")

# 修正：确保函数签名正确
def process_single_match(file_prefix, match_name,
                         target_for_4in2_1_match,
                         first_target_for_4in2_2_match,
                         second_target_for_4in2_2_match,
                         target_for_2in1_match):
    """处理单个赛事的完整流程 (使用传入的文件前缀和明确的点击目标)"""
    global stop_requested, run_mode, active_coords # 需要访问 run_mode 和 active_coords
    if stop_requested: return False

    print(f"\n--- 开始处理 {file_prefix} - {match_name} ---")

    # A-1: 根据比赛类型执行不同的点击操作进入赛果界面
    print(f"  执行初始点击操作 for {match_name}...")
    click_success = False
    # 获取当前模式下的实际点击坐标名称 (用于 8in4)
    actual_match_coord_name = match_name # 默认使用通用名称
    if run_mode == 8 and "match_map" in active_coords:
        actual_match_coord_name = active_coords["match_map"].get(match_name, match_name)
        print(f"  模式 8 映射: {match_name} -> {actual_match_coord_name}")

    if match_name.startswith("8in4"):
        # 8进4: 点击映射后的坐标名
        click_success = safe_click(actual_match_coord_name, delay_after=3)
    elif match_name == "4in2_1":
        # 4进2 第一场: 点击 B 值较小的坐标 (target_for_4in2_1_match)
        click_success = safe_click(target_for_4in2_1_match, delay_after=1.5)
    elif match_name == "4in2_2":
        # 4进2 第二场: 先点 B 值大的 (first_target_for_4in2_2_match)，再点 _real 坐标 (second_target_for_4in2_2_match)
        if safe_click(first_target_for_4in2_2_match, delay_after=1.0): # 点击 B 值大的
            click_success = safe_click(second_target_for_4in2_2_match, delay_after=1.5) # 再点击 _real 坐标
        else:
            click_success = False # 第一次点击失败
    elif match_name == "2in1":
        # 2进1: 点击 B 值较大的坐标 (target_for_2in1_match)
        click_success = safe_click(target_for_2in1_match, delay_after=1.5)
    else:
        print(f"错误：未知的 match_name '{match_name}'，无法执行初始点击。")
        return False # 未知比赛类型

    if not click_success:
        # 提供更详细的错误信息
        click_info = actual_match_coord_name if match_name.startswith('8in4') else f"基于取色判断的目标 (4in2_1: {target_for_4in2_1_match}, 4in2_2_first: {first_target_for_4in2_2_match}, 4in2_2_second: {second_target_for_4in2_2_match}, 2in1: {target_for_2in1_match})"
        print(f"错误：执行 {match_name} 的初始点击操作失败 (目标: {click_info})。")
        return False
    if stop_requested: return False

    # A-2: 截图赛果区域 (使用 file_prefix)
    result_img_path = os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_result.png")
    if not safe_screenshot("result_region", result_img_path): return False
    if stop_requested: return False

    player_stitched_paths = {} # 存储两个玩家拼接好的队伍图路径
    # 新增：存储玩家信息截图路径
    player_info_paths = {} # {1: [info1_path, info2_path, info3_path], 2: [...]}

    # 处理两个玩家
    for player_num in [1, 2]:
        player_coord_name = f"player{player_num}"
        if stop_requested: return False

        print(f"-- 处理 {player_coord_name} --")
        # A-3 / A-7: 点击玩家头像
        if not safe_click(player_coord_name, delay_after=3): return False # 等待队伍界面加载
        if stop_requested: return False

        # --- 新增：截图玩家信息区域 1, 2, 3 (使用 file_prefix) ---
        current_player_info_paths = []
        # 截图 player_info
        player_info_filename = f"{file_prefix}_{match_name}_{player_coord_name}_playerinfo.png"
        player_info_path = os.path.join(TEMP_DIR, player_info_filename)
        if not safe_screenshot("player_info", player_info_path): return False
        current_player_info_paths.append(player_info_path)
        if stop_requested: return False

        # 点击 player_detailinfo_2, 等待, 截图 player_info_2
        if not safe_click("player_detailinfo_2", delay_after=2.5): return False
        player_info_2_filename = f"{file_prefix}_{match_name}_{player_coord_name}_player_info_2.png"
        player_info_2_path = os.path.join(TEMP_DIR, player_info_2_filename)
        if not safe_screenshot("player_info_2", player_info_2_path): return False
        current_player_info_paths.append(player_info_2_path)
        if stop_requested: return False

        # 点击 player_detailinfo_3, 等待, 截图 player_info_3
        if not safe_click("player_detailinfo_3", delay_after=1.0): return False
        player_info_3_filename = f"{file_prefix}_{match_name}_{player_coord_name}_player_info_3.png"
        player_info_3_path = os.path.join(TEMP_DIR, player_info_3_filename)
        if not safe_screenshot("player_info_3", player_info_3_path): return False
        current_player_info_paths.append(player_info_3_path)
        if stop_requested: return False

        # 点击 player_detailinfo_close
        if not safe_click("player_detailinfo_close", delay_after=0.5): return False
        if stop_requested: return False

        player_info_paths[player_num] = current_player_info_paths # 存储当前玩家的三个信息截图路径
        # --- 新增结束 ---

        team_img_paths = []
        # A-4 / A-8: 循环点击5个队伍并截图 (使用 file_prefix)
        for i, team_coord_name in enumerate(TEAM_NAMES, 1):
            if stop_requested: return False
            # A-4-1: 点击队伍
            if not safe_click(team_coord_name, delay_after=1.5): return False # 增加队伍切换等待
            if stop_requested: return False

            # A-4-2: 截图队伍区域
            team_img_filename = f"{file_prefix}_{match_name}_{player_coord_name}_team{i}.png"
            team_img_path = os.path.join(TEMP_DIR, team_img_filename)
            # 添加截图重试机制 (可选)
            attempts = 0
            max_attempts = 2
            screenshot_success = False
            while attempts < max_attempts and not screenshot_success:
                 screenshot_success = safe_screenshot("team_region", team_img_path)
                 if not screenshot_success:
                      attempts += 1
                      print(f"  截图失败，尝试重新截图 ({attempts}/{max_attempts})...")
                      time.sleep(0.5)
                 if stop_requested: return False # 每次尝试后检查
            if not screenshot_success:
                print(f"错误: 多次尝试截图 team_region 失败 for {team_coord_name}。")
                return False # 截图失败则中止当前比赛处理

            team_img_paths.append(team_img_path)
            if stop_requested: return False

        # A-5 / A-8 (cont.): 垂直拼接玩家信息截图和队伍截图 (共 8 张) (使用 file_prefix)
        player_stitched_filename = f"{file_prefix}_{match_name}_{player_coord_name}.png"
        player_stitched_path = os.path.join(TEMP_DIR, player_stitched_filename)
        # 准备拼接列表：先放3张信息图，再放5张队伍图
        images_to_stitch_vertically = player_info_paths.get(player_num, []) + team_img_paths
        if len(images_to_stitch_vertically) != 8:
             print(f"警告：期望为 {player_coord_name} 垂直拼接 8 张图片，实际找到 {len(images_to_stitch_vertically)} 张。")
             # 可以选择是否继续拼接，这里选择继续，但标记可能不完整

        if not stitch_images_vertically(images_to_stitch_vertically, player_stitched_path):
            print(f"错误：{player_coord_name} 的截图垂直拼接失败")
            # 记录失败，但尝试继续关闭界面
            player_stitched_paths[player_num] = None # 标记失败
        else:
            player_stitched_paths[player_num] = player_stitched_path # 存储成功拼接的路径
        if stop_requested: return False

        # A-6 / A-9: 点击队伍界面关闭
        if not safe_click("close_teamview", delay_after=1): return False # 增加关闭后延时
        if stop_requested: return False

    # A-10: 水平拼接 Player1, Result, Player2 (使用 file_prefix)
    final_img_filename = f"{file_prefix}_{match_name}.png"
    final_img_path = os.path.join(OUTPUT_DIR, final_img_filename)

    # 获取两个玩家的拼接图路径 (可能是 None)
    player1_img = player_stitched_paths.get(1)
    player2_img = player_stitched_paths.get(2)

    # 确保赛果图存在
    if not os.path.exists(result_img_path):
        print(f"错误: 赛果截图文件丢失: {result_img_path}")
        result_img_path = None # 标记丢失

    # 参与拼接的图片列表 (过滤掉 None 或不存在的路径)
    images_to_stitch = [p for p in [player1_img, result_img_path, player2_img] if p and os.path.exists(p)]

    if len(images_to_stitch) == 3: # 仅在三张图都有效时执行拼接
        if not stitch_images_horizontally(images_to_stitch, final_img_path):
            print(f"错误：最终图像水平拼接失败 for {file_prefix}_{match_name}")
            # 即使拼接失败，也尝试关闭赛果界面
    else:
        print(f"警告：缺少用于最终水平拼接的图片 for {file_prefix}_{match_name}。跳过拼接。")
        print(f"  Player1: {player1_img}, Result: {result_img_path}, Player2: {player2_img}")
        # 如果你想即使缺少图片也尝试拼接（例如只有赛果），可以在这里调整逻辑

    if stop_requested: return False

    # A-11: 点击赛果界面关闭
    if not safe_click("close_result", delay_after=1.5): return False # 增加关闭后延时

    # 清理本次赛事的临时文件 (使用 file_prefix)
    cleanup_temp_files(file_prefix, match_name)

    print(f"--- 完成处理 {file_prefix} - {match_name} ---")
    return True


def process_and_save_image(input_path, output_dir):
    """
    将单个图像宽度调整至 TARGET_WIDTH (1238px)，高度按原始比例计算，然后转换为 WebP 并保存。

    Args:
        input_path (str): 输入图像文件的路径 (应位于 final 目录)。
        output_dir (str): 保存 WebP 图像的目录。

    Returns:
        bool: 处理成功返回 True，否则返回 False。
    """
    global TARGET_WIDTH, TARGET_HEIGHT, WEBP_QUALITY, WEBP_METHOD
    try:
        print(f"  处理图片: {os.path.basename(input_path)}")
        img = Image.open(input_path)
        orig_width, orig_height = img.size

        if orig_width <= 0 or orig_height <= 0:
            print(f"    错误: 图片 '{os.path.basename(input_path)}' 尺寸无效 ({orig_width}x{orig_height})，跳过。")
            img.close()
            return False

        # --- 调整大小逻辑 (保持宽高比) ---
        # TARGET_HEIGHT 将不再用于强制设定输出高度

        new_processing_width = TARGET_WIDTH
        
        # 根据原始宽高比计算新的目标高度
        if orig_width == 0: # 防止除以零错误
            print(f"    错误: 图片 '{os.path.basename(input_path)}' 原始宽度为0，无法计算比例，跳过。")
            img.close()
            return False
        
        new_processing_height = int(round(orig_height * (new_processing_width / orig_width)))

        print(f"    按原始比例缩放至 ({new_processing_width}x{new_processing_height})...")
        # 直接缩放，不进行裁剪
        final_img = img.resize((new_processing_width, new_processing_height), Image.Resampling.LANCZOS)
        # resized_img 变量不再需要，img 直接 resize 给 final_img

        # --- 保存为 WebP ---
        base_filename = os.path.splitext(os.path.basename(input_path))[0]
        output_filename = f"{base_filename}.webp"
        output_path = os.path.join(output_dir, output_filename)

        print(f"    保存为 WebP: {output_path} (Quality: {WEBP_QUALITY}, Method: {WEBP_METHOD})")
        final_img.save(output_path, 'WEBP', quality=WEBP_QUALITY, method=WEBP_METHOD, lossless=False)

        # --- 清理 ---
        final_img.close()
        img.close()
        return True

    except FileNotFoundError:
        print(f"错误：找不到输入文件 '{input_path}'")
        return False
    except Exception as e:
        print(f"错误：处理图片 '{input_path}' 失败: {e}")
        import traceback
        traceback.print_exc()
        # 尝试关闭可能打开的图像对象
        if 'img' in locals() and hasattr(img, 'close'): img.close()
        if 'resized_img' in locals() and hasattr(resized_img, 'close'): resized_img.close()
        if 'final_img' in locals() and hasattr(final_img, 'close'): final_img.close()
        return False

def create_output_zip(source_dir, zip_filename):
    """
    将指定目录的内容打包成 ZIP 文件 (仅存储，不压缩)。

    Args:
        source_dir (str): 要打包的源目录。
        zip_filename (str): 输出的 ZIP 文件名（包含路径）。

    Returns:
        bool: 打包成功返回 True，否则返回 False。
    """
    if not os.path.isdir(source_dir):
        print(f"错误：源目录 '{source_dir}' 不存在或不是一个目录，无法打包。")
        return False

    try:
        print(f"\n开始打包目录 '{source_dir}' 到 '{zip_filename}'...")
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_STORED) as zipf:
            item_count = 0
            for root, _, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # arcname 是文件在 zip 文件中的相对路径
                    arcname = os.path.relpath(file_path, source_dir)
                    print(f"  添加: {arcname}")
                    zipf.write(file_path, arcname=arcname)
                    item_count += 1
        print(f"打包完成，共添加 {item_count} 个文件到 {zip_filename}")
        return True
    except Exception as e:
        print(f"错误：创建 ZIP 文件 '{zip_filename}' 失败: {e}")
        import traceback
        traceback.print_exc()
        # 如果打包失败，尝试删除可能已创建的不完整 zip 文件
        if os.path.exists(zip_filename):
            try:
                os.remove(zip_filename)
                print(f"已删除不完整的 ZIP 文件: {zip_filename}")
            except OSError as remove_err:
                print(f"警告：无法删除不完整的 ZIP 文件 '{zip_filename}': {remove_err}")
        return False

def run_mode_9_processing():
    """执行模式 9 的逻辑：处理图片并打包"""
    global OUTPUT_DIR, OUTPUT_WEBP_DIR, ZIP_FILENAME
    print("\n====== 开始执行模式 9：图片处理与打包 ======")
    script_running = True # 标记模式9开始

    # 1. 定义输入和输出目录
    input_dir = OUTPUT_DIR # 使用模式1/2的最终输出目录作为输入
    output_dir = OUTPUT_WEBP_DIR

    print(f"输入图片目录 (来源): {os.path.abspath(input_dir)}")
    print(f"输出 WebP 目录: {os.path.abspath(output_dir)}")
    print(f"最终压缩包名: {ZIP_FILENAME}")

    # 2. 检查输入目录是否存在
    if not os.path.isdir(input_dir):
        show_message("错误", f"输入目录 '{input_dir}' 不存在。\n请先运行模式 1 或 2 生成图片。")
        print(f"错误: 输入目录 '{input_dir}' 不存在。")
        return # 模式 9 无法继续

    # 3. 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 4. 获取要处理的图片文件列表 (假设是 png)
    try:
        # 只处理 final 目录下的 png 文件
        image_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.png') and os.path.isfile(os.path.join(input_dir, f))]
    except Exception as e:
        show_message("错误", f"无法读取输入目录 '{input_dir}': {e}")
        print(f"错误: 无法读取输入目录 '{input_dir}': {e}")
        return

    if not image_files:
        show_message("信息", f"输入目录 '{input_dir}' 中没有找到 .png 图片文件。")
        print(f"警告: 输入目录 '{input_dir}' 中没有找到 .png 图片文件。")
        return # 没有文件可处理

    print(f"找到 {len(image_files)} 个 .png 文件准备处理...")

    # 5. 循环处理每张图片
    success_count = 0
    fail_count = 0
    start_time = time.time()

    for filename in image_files:
        input_path = os.path.join(input_dir, filename)
        if process_and_save_image(input_path, output_dir):
            success_count += 1
        else:
            fail_count += 1
            # 可以选择如果一张失败是否停止，目前设置为继续处理其他图片

    end_time_process = time.time()
    print(f"\n图片处理完成。成功: {success_count}, 失败: {fail_count}. 耗时: {end_time_process - start_time:.2f} 秒")

    if success_count == 0:
        show_message("错误", f"未能成功处理任何图片。请检查控制台日志。")
        print("错误：未能成功处理任何图片。")
        return # 没有成功处理的文件，不进行打包

    # 6. 打包输出目录
    zip_file_path = ZIP_FILENAME # 直接在当前目录创建 zip
    if create_output_zip(output_dir, zip_file_path):
        # 7. 显示成功消息
        completion_message = (
            "图片已标准化并打包。\n\n"
            f"压缩包 '{zip_file_path}' 已创建。\n\n"
            "你可以将压缩包名改为\"服务器名_第一组左上角玩家的uid\" ，\n"
            "如 \"jp_04501689.zip\" （避免和同一大区的玩家重复）\n\n"
            "再分享到QQ群 437983122 或者其他地方"
        )
        show_message("模式 9 完成", completion_message)
        print("\n模式 9 执行完毕。")
    else:
        # 打包失败的消息
        show_message("错误", f"图片处理完成，但打包到 '{zip_file_path}' 失败。\n请检查控制台日志。")
        print(f"错误：打包目录 '{output_dir}' 失败。")

    script_running = False # 标记模式9结束

# --- 热键处理 (不变) ---
def start_script():
    """Ctrl+8 热键回调"""
    global script_running
    if not script_running:
        print("\n收到启动请求 (Ctrl+8)...")
        # 在新线程中运行自动化，避免阻塞热键监听
        automation_thread = threading.Thread(target=run_automation, daemon=True)
        automation_thread.start()
    else:
        print("脚本已在运行中，请勿重复启动。")

def request_stop():
    """Ctrl+1 热键回调"""
    global stop_requested, script_running
    if script_running:
        if not stop_requested:
            print("\n接收到停止请求 (Ctrl+1)... 请稍候，脚本将在当前操作完成后安全停止。")
            stop_requested = True
            # 注意：立即终止可能导致文件损坏或状态不一致
    else:
        print("脚本未在运行，无需停止。(按 Ctrl+C 可退出监听)")
        # 如果希望按 Ctrl+1 退出等待状态，可以在这里添加 sys.exit() 或其他逻辑
        # 例如，设置一个标志让主循环退出
        # global exit_requested; exit_requested = True

# --- 主程序入口 (添加 pywin32 依赖检查 和 模式 9) ---
if __name__ == "__main__":
    # 0. 检查 pywin32 是否已导入 (在顶部完成)

    # 1. 检查管理员权限
    if sys.platform == 'win32' and not is_admin():
        try:
            show_message("需要管理员权限", "脚本需要管理员权限来控制其他程序和进行截图。\n请右键点击脚本或快捷方式，选择“以管理员身份运行”。")
        except Exception as e:
            print(f"显示消息框失败: {e}")
            print("错误：请以管理员身份运行本程序！")
        sys.exit(1)

    # 2. 选择运行模式 (增加模式 9)
    while True:
        try:
            # 更新提示信息
            prompt = (
                "请选择运行模式:\n"
                " 6: 完整模式 (自动截取8个分组, 前缀 groupX)\n"
                " 7: 单组模式 (自动截取当前组, 前缀 group1)\n"
                " 8: 冠军赛模式 (自动截取当前界面, 前缀 champain)\n"
                " 9: 图片处理和打包 (处理 'final' 目录图片并压缩)\n"
                "请输入数字 (6, 7, 8 或 9): "
            )
            mode_choice = input(prompt)
            run_mode = int(mode_choice)
            # 更新有效选项
            if run_mode in [6, 7, 8, 9]:
                break
            else:
                print("输入无效，请输入 6, 7, 8 或 9。")
        except ValueError:
            print("输入无效，请输入数字 6, 7, 8 或 9。")
        except EOFError:
             print("无法获取用户输入，程序退出。")
             sys.exit(1)
        except KeyboardInterrupt:
             print("\n操作取消。")
             sys.exit(0)

    # --- 根据模式执行 ---
    if run_mode in [6, 7, 8]: # 修改：模式 6, 7, 8 都需要热键监听
        # 模式 1, 2, 3 需要热键监听
        exit_requested_main = False # 用于通过 Ctrl+C 或其他方式退出主循环
        try:
            keyboard.add_hotkey('ctrl+8', start_script) # start_script 调用 run_automation
            keyboard.add_hotkey('ctrl+1', request_stop)
            print("\n--- NIKKE 竞技场截图工具 ---") # 通用标题
            print("\n--- 加入 NIKKE PVP讨论群 437983122 ---")
            print("\n--- 分享你大区的数据 ---")
            # 更新模式显示
            mode_text = {6: "完整模式 (分组赛)", 7: "单组模式 (分组赛)", 8: "冠军赛模式"}
            print(f"当前模式: {mode_text.get(run_mode, '未知')}")
            print("依赖检查: pywin32 已加载。")
            print(f"目标进程: {PROCESS_NAME}")
            print("\n准备就绪:")
            print(" 1. 请确保 NIKKE 游戏已运行并且窗口可见。")
            print("    - 如果全屏模式，需保证你的屏幕为16：9，否则请使用16：9窗口化。")
            # 根据模式调整导航提示
            if run_mode == 6 or run_mode == 7:
                print(" 2. 返回游戏，导航到【竞技场】-【新秀竞技场】的【晋级赛】界面（顶部有8个小组可选择）。")
            elif run_mode == 8:
                print(" 2. 返回游戏，导航到【竞技场】-【冠军竞技场】的【锦标赛】界面（显示对阵图）。")
            print(" 3. 按 Ctrl+8 开始运行脚本。")
            print("\n运行期间:")
            print(" - 请勿移动鼠标或操作键盘，避免干扰自动化。")
            print(" - 如需停止，请按 Ctrl+1 (脚本将在当前步骤完成后停止)。")
            print(" - 脚本日志会显示在当前控制台窗口。")
            print("-------------------------------------------------")
            print("正在监听热键... (按 Ctrl+C 退出监听)")

            # 保持脚本运行以监听热键
            while not exit_requested_main:
                time.sleep(1) # 减少CPU占用

        except ImportError as e:
             # keyboard 库的 ImportError
             print(f"错误：缺少 '{e.name}' 库。请使用 'pip install {e.name}' 安装。")
             input("按 Enter 退出...")
             sys.exit(1)
        except Exception as e:
             print(f"\n发生意外错误: {e}")
             import traceback
             traceback.print_exc() # 打印详细错误信息
        except KeyboardInterrupt: # 捕获 Ctrl+C
             print("\n收到退出信号 (Ctrl+C)，正在关闭...")
             exit_requested_main = True
        finally:
            # 程序结束前尝试清理热键
            try:
                keyboard.remove_all_hotkeys()
                print("热键已移除。")
            except Exception:
                pass # 忽略移除错误
            print("脚本退出。")

    elif run_mode == 9:
        # 模式 9 直接运行，不需要热键
        try:
            run_mode_9_processing()
        except Exception as e:
            print(f"\n模式 9 执行期间发生意外错误: {e}")
            import traceback
            traceback.print_exc()
            show_message("致命错误", f"模式 9 发生严重错误，请查看控制台。\n{e}")
        finally:
            print("脚本退出。")
            # input("按 Enter 键退出...") # 可以取消注释，以便用户查看控制台日志
    else:
        # 这个分支理论上不会执行，因为上面已经校验了 run_mode
        print("错误：未知的运行模式。")
        sys.exit(1)
