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
import zipfile
import traceback

# --- 配置日志记录 ---
# 设置日志记录器
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()]) # 输出到控制台

# --- 全局变量和常量 ---
CURRENT_MODE = None # Will be set by run_selected_mode
stop_script_event = None # Will be a threading.Event passed from GUI
gui_logger_callback = None # Will be a callback from GUI to log messages

# [保留之前的常量...]
BASE_WIDTH = 3840
BASE_HEIGHT = 2160
# stop_script = False # Replaced by stop_script_event
WINDOW_TITLE = "NIKKE" # 严格匹配的窗口标题
# STOP_HOTKEY = "ctrl+1" # Hotkey will be handled by GUI or removed if not needed

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

# --- Coordinates for C_Arena Reviewer Modes (6, 7, 8) ---
# These are converted from c_arena_reviewer.py's COORDS_4K and COORDS_4K_MODE3
# Base resolution for conversion: BASE_WIDTH = 3840, BASE_HEIGHT = 2160

# For Modes 6 & 7 (derived from COORDS_4K in c_arena_reviewer.py)
C_ARENA_MODE67_COORDS_REL = {
    "group_1_click": calculate_relative_coords((270, 560), BASE_WIDTH, BASE_HEIGHT),
    "group_2_click": calculate_relative_coords((740, 560), BASE_WIDTH, BASE_HEIGHT),
    "group_3_click": calculate_relative_coords((1200, 560), BASE_WIDTH, BASE_HEIGHT),
    "group_4_click": calculate_relative_coords((1680, 560), BASE_WIDTH, BASE_HEIGHT),
    "group_5_click": calculate_relative_coords((2160, 560), BASE_WIDTH, BASE_HEIGHT),
    "group_6_click": calculate_relative_coords((2620, 560), BASE_WIDTH, BASE_HEIGHT),
    "group_7_click": calculate_relative_coords((3100, 560), BASE_WIDTH, BASE_HEIGHT),
    "group_8_click": calculate_relative_coords((3600, 560), BASE_WIDTH, BASE_HEIGHT),
    "8in4_1_click": calculate_relative_coords((1833, 896), BASE_WIDTH, BASE_HEIGHT),
    "8in4_2_click": calculate_relative_coords((2044, 896), BASE_WIDTH, BASE_HEIGHT),
    "8in4_3_click": calculate_relative_coords((1773, 1692), BASE_WIDTH, BASE_HEIGHT),
    "8in4_4_click": calculate_relative_coords((2132, 1703), BASE_WIDTH, BASE_HEIGHT),
    "4in2_1_color_check_coord": calculate_relative_coords((1923, 1160), BASE_WIDTH, BASE_HEIGHT), # Used for color check, and as a click target
    "4in2_2_color_check_coord": calculate_relative_coords((1923, 1410), BASE_WIDTH, BASE_HEIGHT), # Used for color check, and as a click target
    "4in2_2_real_click": calculate_relative_coords((2176, 1742), BASE_WIDTH, BASE_HEIGHT),
    "player1_click_carena": calculate_relative_coords((1534, 1096), BASE_WIDTH, BASE_HEIGHT),
    "player2_click_carena": calculate_relative_coords((2182, 1096), BASE_WIDTH, BASE_HEIGHT),
    "result_region_carena": (
        1607 / BASE_WIDTH, 968 / BASE_HEIGHT,
        (2116 - 1607) / BASE_WIDTH, (1642 - 968) / BASE_HEIGHT
    ),
    "close_result_click_carena": calculate_relative_coords((2369, 529), BASE_WIDTH, BASE_HEIGHT),
    # team1-5 clicks will use existing TEAM_COORDS_REL from main.py
    # close_teamview click will use existing EXIT_COORD_REL from main.py (original c_arena: (2370, 681))
    # team_region for screenshots will use existing SCREENSHOT_REGION_REL from main.py (original c_arena: (1433, 1134, 2417, 1530))
    # player_info region for screenshots will use existing PLAYER_INFO_REGION_REL from main.py (original c_arena: (1433, 768, 2417, 963))
    "player_detailinfo_2_click_carena": calculate_relative_coords((1560, 888), BASE_WIDTH, BASE_HEIGHT),
    "player_detailinfo_3_click_carena": calculate_relative_coords((2200, 1990), BASE_WIDTH, BASE_HEIGHT),
    "player_detailinfo_close_click_carena": calculate_relative_coords((2418, 202), BASE_WIDTH, BASE_HEIGHT),
    # player_info_2 region for screenshots will use existing PLAYER_INFO_2_REGION_REL from main.py (original c_arena: (1433, 1344, 2417, 1529))
    "player_info_3_region_carena": ( # Using c_arena's specific values due to slight difference
        1433 / BASE_WIDTH, 1768 / BASE_HEIGHT,
        (2417 - 1433) / BASE_WIDTH, (1842 - 1768) / BASE_HEIGHT
    ),
}

# For Mode 8 (derived from COORDS_4K_MODE3 in c_arena_reviewer.py)
C_ARENA_MODE8_COORDS_REL = {
    "mode3_8in4_1_click": calculate_relative_coords((1775, 827), BASE_WIDTH, BASE_HEIGHT),
    "mode3_8in4_2_click": calculate_relative_coords((2066, 827), BASE_WIDTH, BASE_HEIGHT),
    "mode3_8in4_3_click": calculate_relative_coords((1775, 1623), BASE_WIDTH, BASE_HEIGHT),
    "mode3_8in4_4_click": calculate_relative_coords((2066, 1623), BASE_WIDTH, BASE_HEIGHT),
    "mode3_4in2_1_color_check_coord": calculate_relative_coords((1907, 1065), BASE_WIDTH, BASE_HEIGHT), # Used for color check and click
    "mode3_4in2_2_color_check_coord": calculate_relative_coords((1910, 1340), BASE_WIDTH, BASE_HEIGHT), # Used for color check and click
    # Reused from C_ARENA_MODE67_COORDS_REL or main.py's existing relative coords where identical
    "player1_click_carena": C_ARENA_MODE67_COORDS_REL["player1_click_carena"],
    "player2_click_carena": C_ARENA_MODE67_COORDS_REL["player2_click_carena"],
    "result_region_carena": C_ARENA_MODE67_COORDS_REL["result_region_carena"],
    "close_result_click_carena": C_ARENA_MODE67_COORDS_REL["close_result_click_carena"],
    # player_info, team_region, close_teamview, player_detailinfo_2, player_info_2 etc. are reused
    "player_detailinfo_2_click_carena": C_ARENA_MODE67_COORDS_REL["player_detailinfo_2_click_carena"],
    "player_detailinfo_3_click_carena": C_ARENA_MODE67_COORDS_REL["player_detailinfo_3_click_carena"],
    "player_detailinfo_close_click_carena": C_ARENA_MODE67_COORDS_REL["player_detailinfo_close_click_carena"],
    "player_info_3_region_carena": C_ARENA_MODE67_COORDS_REL["player_info_3_region_carena"],
    "4in2_2_real_click": C_ARENA_MODE67_COORDS_REL["4in2_2_real_click"], # Explicitly used by mode 8 logic in c_arena
    # Match map for mode 8 (maps generic match names to mode8 specific click keys)
    # The values here are keys within this C_ARENA_MODE8_COORDS_REL dictionary or C_ARENA_MODE67_COORDS_REL
    "match_map": {
        "8in4_1": "mode3_8in4_1_click",
        "8in4_2": "mode3_8in4_2_click",
        "8in4_3": "mode3_8in4_3_click",
        "8in4_4": "mode3_8in4_4_click",
        "4in2_1": "mode3_4in2_1_color_check_coord", # Click target for 4in2_1 match
        "4in2_2_first_click_target_key": "mode3_4in2_2_color_check_coord", # Key for the first click in 4in2_2 logic
        # "2in1" will also use logic based on color_check_coords to pick a target
    },
    # Keys for color checking logic (values are names of other keys in this dict or C_ARENA_MODE67_COORDS_REL)
    "color_check_coord1_key": "mode3_4in2_1_color_check_coord",
    "color_check_coord2_key": "mode3_4in2_2_color_check_coord",
}
# Note: TEAM_COORDS_REL, EXIT_COORD_REL, SCREENSHOT_REGION_REL, PLAYER_INFO_REGION_REL, PLAYER_INFO_2_REGION_REL
# from main.py will be used directly by the ported c_arena functions where applicable and identical.
# The _carena suffixed coordinates are defined where c_arena_reviewer.py had different values or specific names.
# 统一文件目录和文件名前缀
TEMP_DIR = "temp_combined" # 统一临时文件目录
FINAL_OUTPUT_DIR = "final_output" # 统一最终图片输出目录 (模式1-8)
WEBP_OUTPUT_DIR = "output_webp"   # 模式9 WebP图片输出目录
ZIP_FILENAME = "output_archive.zip" # 模式9 ZIP压缩包文件名

TEMP_PREFIX_PLAYER_INFO = "playerinfo" # 玩家信息1
TEMP_PREFIX_PLAYER_INFO_2 = "playerinfo2" # 新增：玩家信息2
TEMP_PREFIX_PLAYER_INFO_3 = "playerinfo3" # 新增：玩家信息3
TEMP_PREFIX_P1 = "temp_pic" # 队伍截图 (Player 1)
TEMP_PREFIX_P2 = "temp_pic1" # 队伍截图 (Player 2)
PEOPLE_VOTE_TEMP_FILENAME = os.path.join(TEMP_DIR, "people_vote.png")
OUTPUT_P1 = "line_player1.png" # 中间拼接文件，也放入 temp
OUTPUT_P2 = "line_player2.png" # 中间拼接文件，也放入 temp
RESULT_TEMP_FILENAME = os.path.join(TEMP_DIR, "result.png")

# 模式 1-5 最终输出文件名 (指向 FINAL_OUTPUT_DIR)
FINAL_OUTPUT_M1 = os.path.join(FINAL_OUTPUT_DIR, "combined_prediction.png")
FINAL_OUTPUT_M2 = os.path.join(FINAL_OUTPUT_DIR, "combined_review.png")
FINAL_OUTPUT_M3 = os.path.join(FINAL_OUTPUT_DIR, "combined_anti_buy.png")
FINAL_OUTPUT_M4_P1 = os.path.join(FINAL_OUTPUT_DIR, "mode4_player1_stitched.png")
FINAL_OUTPUT_M4_P2 = os.path.join(FINAL_OUTPUT_DIR, "mode4_player2_stitched.png")
FINAL_OUTPUT_M4_P3 = os.path.join(FINAL_OUTPUT_DIR, "mode4_player3_stitched.png")
FINAL_OUTPUT_M4_P4 = os.path.join(FINAL_OUTPUT_DIR, "mode4_player4_stitched.png")
FINAL_OUTPUT_M4_P5 = os.path.join(FINAL_OUTPUT_DIR, "mode4_player5_stitched.png")
FINAL_OUTPUT_M4_P6 = os.path.join(FINAL_OUTPUT_DIR, "mode4_player6_stitched.png")
FINAL_OUTPUT_M4_P7 = os.path.join(FINAL_OUTPUT_DIR, "mode4_player7_stitched.png")
FINAL_OUTPUT_M4_P8 = os.path.join(FINAL_OUTPUT_DIR, "mode4_player8_stitched.png")
FINAL_OUTPUT_M4_OVERVIEW = os.path.join(FINAL_OUTPUT_DIR, "64in8_overview.png")
FINAL_OUTPUT_M5_P1 = os.path.join(FINAL_OUTPUT_DIR, "mode5_player1_stitched.png")
FINAL_OUTPUT_M5_P2 = os.path.join(FINAL_OUTPUT_DIR, "mode5_player2_stitched.png")
FINAL_OUTPUT_M5_P3 = os.path.join(FINAL_OUTPUT_DIR, "mode5_player3_stitched.png")
FINAL_OUTPUT_M5_P4 = os.path.join(FINAL_OUTPUT_DIR, "mode5_player4_stitched.png")
FINAL_OUTPUT_M5_P5 = os.path.join(FINAL_OUTPUT_DIR, "mode5_player5_stitched.png")
FINAL_OUTPUT_M5_P6 = os.path.join(FINAL_OUTPUT_DIR, "mode5_player6_stitched.png")
FINAL_OUTPUT_M5_P7 = os.path.join(FINAL_OUTPUT_DIR, "mode5_player7_stitched.png")
FINAL_OUTPUT_M5_P8 = os.path.join(FINAL_OUTPUT_DIR, "mode5_player8_stitched.png")
FINAL_OUTPUT_M5_OVERVIEW = os.path.join(FINAL_OUTPUT_DIR, "champion_overview.png")

HORIZONTAL_SPACING = 50 # 横向拼接的间隔像素

# 鼠标点击和截图之间的延迟（秒）
ACTION_DELAY = 1.2 # 增加延迟以确保UI响应

# Constants for Mode 9 (C_Arena Image Processing and Packaging)
TARGET_WIDTH_M9 = 1238
WEBP_QUALITY_M9 = 90
WEBP_METHOD_M9 = 6

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

# def setup_stop_hotkey(): # GUI will handle stop signals
#     """设置停止脚本的热键。"""
#     # logging.info(f"按下 {STOP_HOTKEY} 可以随时停止脚本。")
#     # keyboard.add_hotkey(STOP_HOTKEY, stop_program)

# def stop_program(): # GUI will handle stop signals
#     """热键的回调函数，用于设置停止标志。"""
#     # global stop_script
#     # logging.warning(f"检测到停止热键 {STOP_HOTKEY}！正在尝试停止脚本...")
#     # stop_script = True # Replaced by stop_script_event.set()

def check_stop_signal():
    """检查是否收到了停止信号，如果收到则退出脚本。"""
    if stop_script_event and stop_script_event.is_set():
        logging.info("GUI请求停止脚本。正在退出...")
        # Instead of sys.exit, we should allow the function to return
        # so the thread can terminate gracefully.
        # sys.exit(0)
        raise InterruptedError("Script stopped by GUI request") # Raise an exception to unwind

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


# --- 主程序逻辑 (将被 run_selected_mode 调用) ---
def execute_main_logic(): # Renamed from main to avoid conflict if this file is run directly
    # global stop_script # Replaced by stop_script_event
    logging.info("脚本核心逻辑启动。")
    
    # Hotkey setup is removed, GUI handles stop.
    # setup_stop_hotkey()
    check_stop_signal()

    # 2. 创建所需目录
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
        logging.info(f"已确保临时目录 '{TEMP_DIR}' 存在。")
        os.makedirs(FINAL_OUTPUT_DIR, exist_ok=True)
        logging.info(f"已确保最终输出目录 '{FINAL_OUTPUT_DIR}' 存在。")
        os.makedirs(WEBP_OUTPUT_DIR, exist_ok=True)
        logging.info(f"已确保WebP输出目录 '{WEBP_OUTPUT_DIR}' 存在。")
    except OSError as e:
        logging.error(f"创建目录失败: {e}")
        return # 无法创建目录则退出

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
            player1_output = process_player(
                PLAYER1_COORD_REL, TEAM_COORDS_REL, TEMP_PREFIX_P1, OUTPUT_P1,
                SCREENSHOT_REGION_REL, nikke_window
            )
            if player1_output: logging.info("===== Player 1 处理完成 =====")
            else: logging.error("处理 Player 1 失败。")
            check_stop_signal()
            if click_coordinates(EXIT_COORD_REL, nikke_window): time.sleep(1.0)
            else: logging.warning("未能点击退出坐标。")
            check_stop_signal()
            player2_output = process_player(
                PLAYER2_COORD_REL, TEAM_COORDS_REL, TEMP_PREFIX_P2, OUTPUT_P2,
                SCREENSHOT_REGION_REL, nikke_window
            )
            if player2_output: logging.info("===== Player 2 处理完成 =====")
            else: logging.error("处理 Player 2 失败。")
            check_stop_signal()
            
            final_images_to_stitch_m1 = [p for p in [player1_output, player2_output] if p and os.path.exists(p)]
            if len(final_images_to_stitch_m1) >= 1:
                actual_final_output_path = stitch_images_horizontally(final_images_to_stitch_m1, FINAL_OUTPUT_M1, HORIZONTAL_SPACING, background_color=(0,0,0))
                if actual_final_output_path: logging.info(f"成功生成最终拼接图片 (模式 1): '{actual_final_output_path}'")
                else: logging.error("未能成功生成最终拼接图片 (模式 1)。")
            else:
                logging.error("没有可用于最终横向拼接的有效图片 (模式 1)。")

        elif CURRENT_MODE == 2:
            logging.info("===== 运行模式 2: 复盘模式 =====")
            if take_screenshot(RESULT_SCREENSHOT_REGION_REL, nikke_window, RESULT_TEMP_FILENAME):
                result_screenshot_path = RESULT_TEMP_FILENAME
                logging.info(f"初始结果图已保存为 '{result_screenshot_path}'")
            else: logging.error("未能截取初始结果图。")
            check_stop_signal()
            time.sleep(0.5)
            
            player1_output = process_player(
                PLAYER1_COORD_REL_M2, TEAM_COORDS_REL, TEMP_PREFIX_P1, OUTPUT_P1,
                SCREENSHOT_REGION_REL, nikke_window
            )
            if player1_output: logging.info("===== Player 1 (模式 2) 处理完成 =====")
            else: logging.error("处理 Player 1 (模式 2) 失败。")
            check_stop_signal()
            if click_coordinates(EXIT_COORD_REL, nikke_window): time.sleep(1.0)
            else: logging.warning("未能点击退出坐标。")
            check_stop_signal()
            player2_output = process_player(
                PLAYER2_COORD_REL_M2, TEAM_COORDS_REL, TEMP_PREFIX_P2, OUTPUT_P2,
                SCREENSHOT_REGION_REL, nikke_window
            )
            if player2_output: logging.info("===== Player 2 (模式 2) 处理完成 =====")
            else: logging.error("处理 Player 2 (模式 2) 失败。")
            check_stop_signal()

            final_images_to_stitch_m2 = [p for p in [player1_output, result_screenshot_path, player2_output] if p and os.path.exists(p)]
            if len(final_images_to_stitch_m2) >= 1:
                actual_final_output_path = stitch_images_horizontally(final_images_to_stitch_m2, FINAL_OUTPUT_M2, spacing=0, background_color=(255,255,255))
                if actual_final_output_path: logging.info(f"成功生成最终拼接图片 (模式 2): '{actual_final_output_path}'")
                else: logging.error("未能成功生成最终拼接图片 (模式 2)。")
            else:
                logging.error("没有可用于最终横向拼接的有效图片 (模式 2)。")

        elif CURRENT_MODE == 3:
            logging.info("===== 运行模式 3: 反买模式 =====")
            if take_screenshot(PEOPLE_VOTE_REGION_REL, nikke_window, PEOPLE_VOTE_TEMP_FILENAME):
                people_vote_screenshot_path = PEOPLE_VOTE_TEMP_FILENAME
                logging.info(f"民意区域截图已保存为 '{people_vote_screenshot_path}'")
            else: logging.error("未能截取民意区域截图。")
            check_stop_signal()
            time.sleep(0.5)

            player1_output = process_player(
                PLAYER1_COORD_REL, TEAM_COORDS_REL, TEMP_PREFIX_P1, OUTPUT_P1,
                SCREENSHOT_REGION_REL, nikke_window
            )
            if player1_output: logging.info("===== Player 1 (模式 3) 处理完成 =====")
            else: logging.error("处理 Player 1 (模式 3) 失败。")
            check_stop_signal()
            if click_coordinates(EXIT_COORD_REL, nikke_window): time.sleep(1.0)
            else: logging.warning("未能点击退出坐标。")
            check_stop_signal()
            player2_output = process_player(
                PLAYER2_COORD_REL, TEAM_COORDS_REL, TEMP_PREFIX_P2, OUTPUT_P2,
                SCREENSHOT_REGION_REL, nikke_window
            )
            if player2_output: logging.info("===== Player 2 (模式 3) 处理完成 =====")
            else: logging.error("处理 Player 2 (模式 3) 失败。")
            check_stop_signal()

            final_images_to_stitch_m3 = [p for p in [player1_output, people_vote_screenshot_path, player2_output] if p and os.path.exists(p)]
            if len(final_images_to_stitch_m3) >= 1:
                actual_final_output_path = stitch_images_horizontally(final_images_to_stitch_m3, FINAL_OUTPUT_M3, spacing=0, background_color=(255,255,255))
                if actual_final_output_path: logging.info(f"成功生成最终拼接图片 (模式 3): '{actual_final_output_path}'")
                else: logging.error("未能成功生成最终拼接图片 (模式 3)。")
            else:
                logging.error("没有可用于最终横向拼接的有效图片 (模式 3)。")

        elif CURRENT_MODE == 4:
            logging.info("===== 运行模式 4: 64进8专用模式 =====")
            mode4_player_coords_rel = [
                P64IN8_PLAYER1_COORD_REL_M4, P64IN8_PLAYER2_COORD_REL_M4,
                P64IN8_PLAYER3_COORD_REL_M4, P64IN8_PLAYER4_COORD_REL_M4,
                P64IN8_PLAYER5_COORD_REL_M4, P64IN8_PLAYER6_COORD_REL_M4,
                P64IN8_PLAYER7_COORD_REL_M4, P64IN8_PLAYER8_COORD_REL_M4
            ]
            mode4_final_output_names = [
                FINAL_OUTPUT_M4_P1, FINAL_OUTPUT_M4_P2, FINAL_OUTPUT_M4_P3, FINAL_OUTPUT_M4_P4,
                FINAL_OUTPUT_M4_P5, FINAL_OUTPUT_M4_P6, FINAL_OUTPUT_M4_P7, FINAL_OUTPUT_M4_P8
            ]
            mode4_generated_files = []
            for i, player_coord_rel in enumerate(mode4_player_coords_rel, 1):
                check_stop_signal() # MODIFIED
                logging.info(f"===== 开始处理模式4 - Player {i} =====")
                player_stitched_temp_path = process_player(
                    player_coord_rel, TEAM_COORDS_REL, f"m4_p{i}_teams", f"line_m4_p{i}.png",
                    SCREENSHOT_REGION_REL, nikke_window, initial_delay=3.0
                )
                if player_stitched_temp_path and os.path.exists(player_stitched_temp_path):
                    unique_final_output_name = mode4_final_output_names[i-1]
                    # Simplified: Assume no filename conflict for this diff, directly copy
                    try:
                        shutil.copy2(player_stitched_temp_path, unique_final_output_name)
                        logging.info(f"模式4 - Player {i} 的截图已成功保存为 '{unique_final_output_name}'")
                        mode4_generated_files.append(unique_final_output_name)
                    except Exception as e:
                        logging.error(f"复制模式4 - Player {i} 的截图到根目录失败: {e}")
                else: logging.error(f"处理模式4 - Player {i} 失败。")
                if i < len(mode4_player_coords_rel): # MODIFIED
                    if click_coordinates(EXIT_COORD_REL, nikke_window): time.sleep(1.0)
                    else: logging.warning(f"模式4 - Player {i} 后未能点击退出坐标。")
                check_stop_signal()
            
            if mode4_generated_files and len(mode4_generated_files) == 8: # MODIFIED
                overview_path = stitch_mode4_overview(mode4_generated_files, FINAL_OUTPUT_M4_OVERVIEW)
                if overview_path:
                    actual_final_output_path = overview_path
                    logging.info(f"模式4总览图已成功生成: '{actual_final_output_path}'")
                    for file_path in mode4_generated_files: # Cleanup individual files
                        try:
                            if os.path.exists(file_path): os.remove(file_path)
                        except OSError as e: logging.warning(f"无法删除模式4独立截图 '{file_path}': {e}")
                else:
                    logging.error("模式4总览图拼接失败。")
                    actual_final_output_path = f"Mode 4 generated {len(mode4_generated_files)} separate files. Overview stitching failed." # For notification
            elif mode4_generated_files:
                 actual_final_output_path = f"Mode 4 generated {len(mode4_generated_files)} separate files. Not enough for overview."
            else:
                 actual_final_output_path = None


        elif CURRENT_MODE == 5:
            logging.info("===== 运行模式 5: 冠军争霸模式 =====")
            mode5_player_coords_rel = [
                CHAMPION_PLAYER1_COORD_REL_M5, CHAMPION_PLAYER2_COORD_REL_M5,
                CHAMPION_PLAYER3_COORD_REL_M5, CHAMPION_PLAYER4_COORD_REL_M5,
                CHAMPION_PLAYER5_COORD_REL_M5, CHAMPION_PLAYER6_COORD_REL_M5,
                CHAMPION_PLAYER7_COORD_REL_M5, CHAMPION_PLAYER8_COORD_REL_M5
            ]
            mode5_final_output_names = [
                FINAL_OUTPUT_M5_P1, FINAL_OUTPUT_M5_P2, FINAL_OUTPUT_M5_P3, FINAL_OUTPUT_M5_P4,
                FINAL_OUTPUT_M5_P5, FINAL_OUTPUT_M5_P6, FINAL_OUTPUT_M5_P7, FINAL_OUTPUT_M5_P8
            ]
            mode5_generated_files = []
            for i, player_coord_rel in enumerate(mode5_player_coords_rel, 1):
                check_stop_signal() # MODIFIED
                logging.info(f"===== 开始处理模式5 - Player {i} =====")
                player_stitched_temp_path = process_player(
                    player_coord_rel, TEAM_COORDS_REL, f"m5_p{i}_teams", f"line_m5_p{i}.png",
                    SCREENSHOT_REGION_REL, nikke_window, initial_delay=3.0
                )
                if player_stitched_temp_path and os.path.exists(player_stitched_temp_path):
                    unique_final_output_name = mode5_final_output_names[i-1]
                    # Simplified: Assume no filename conflict for this diff, directly copy
                    try:
                        shutil.copy2(player_stitched_temp_path, unique_final_output_name)
                        logging.info(f"模式5 - Player {i} 的截图已成功保存为 '{unique_final_output_name}'")
                        mode5_generated_files.append(unique_final_output_name)
                    except Exception as e:
                        logging.error(f"复制模式5 - Player {i} 的截图到根目录失败: {e}")
                else: logging.error(f"处理模式5 - Player {i} 失败。")
                if i < len(mode5_player_coords_rel): # MODIFIED
                    if click_coordinates(EXIT_COORD_REL, nikke_window): time.sleep(1.0)
                    else: logging.warning(f"模式5 - Player {i} 后未能点击退出坐标。")
                check_stop_signal()

            if mode5_generated_files and len(mode5_generated_files) == 8: # MODIFIED
                overview_path = stitch_mode4_overview(mode5_generated_files, FINAL_OUTPUT_M5_OVERVIEW) # Reuses mode 4 stitching logic
                if overview_path:
                    actual_final_output_path = overview_path
                    logging.info(f"模式5总览图已成功生成: '{actual_final_output_path}'")
                    for file_path in mode5_generated_files: # Cleanup individual files
                        try:
                            if os.path.exists(file_path): os.remove(file_path)
                        except OSError as e: logging.warning(f"无法删除模式5独立截图 '{file_path}': {e}")
                else:
                    logging.error("模式5总览图拼接失败。")
                    actual_final_output_path = f"Mode 5 generated {len(mode5_generated_files)} separate files. Overview stitching failed."
            elif mode5_generated_files:
                actual_final_output_path = f"Mode 5 generated {len(mode5_generated_files)} separate files. Not enough for overview."
            else:
                actual_final_output_path = None
        
        elif CURRENT_MODE in [6, 7, 8]: # C_Arena Reviewer Modes
            logging.info(f"===== 调用C_Arena模式 {CURRENT_MODE} 逻辑 =====")
            if not run_carena_mode_logic(nikke_window, CURRENT_MODE):
                logging.error(f"C_Arena模式 {CURRENT_MODE} 执行失败或被中断。")
            # For modes 6, 7, 8, actual_final_output_path is not set here for the main notification logic
            # as run_carena_mode_logic handles its own notifications/output.
            # We set a placeholder to prevent generic popup if not specifically handled by run_carena_mode_logic.
            actual_final_output_path = f"C_Arena Mode {CURRENT_MODE} operations handled by its logic."


        elif CURRENT_MODE == 9: # Image Processing and Packaging
            logging.info("===== 运行模式 9: 图片处理与打包 =====")
            if run_mode_9_logic(): # This function handles its own notifications
                logging.info("模式9处理和打包成功完成。")
            else:
                logging.error("模式9处理或打包失败。")
            actual_final_output_path = "Mode 9 processing handled." # Prevents generic popup
        
        else:
            logging.error(f"未知的 CURRENT_MODE: {CURRENT_MODE}")

        # --- 任务完成后的弹窗 (Adjusted for new modes) ---
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
            # try: # GUI will handle notifications
            #     ctypes.windll.user32.MessageBoxW(None, notification_message, notification_title, MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND | MB_TOPMOST)
            #     logging.info("通知弹窗已显示。")
            # except Exception as mb_err:
            #     logging.error(f"显示通知消息框时出错: {mb_err}")
            if gui_logger_callback and notification_message: # Send to GUI log
                gui_logger_callback(f"{notification_title}: {notification_message}")

        # --- 弹窗结束 ---

    except InterruptedError: # Raised by check_stop_signal()
        logging.info("脚本执行被 GUI 中断。")
    except Exception as e:
        logging.exception(f"脚本执行过程中发生意外错误: {e}")
        if gui_logger_callback:
            gui_logger_callback(f"脚本执行过程中发生意外错误: {e}\n{traceback.format_exc()}")
    finally:
        # --- 新增：清理临时目录 ---
        if os.path.exists(TEMP_DIR):
            try:
                shutil.rmtree(TEMP_DIR)
                logging.info(f"已成功删除临时目录 '{TEMP_DIR}' 及其内容。")
            except Exception as clean_err:
                logging.error(f"清理临时目录 '{TEMP_DIR}' 时发生错误: {clean_err}")
        # --- 清理结束 ---
        # keyboard.remove_hotkey(STOP_HOTKEY) # Hotkey removed
        logging.info("脚本核心逻辑执行完毕或已停止。")

# This new function will be called by the GUI
def run_selected_mode(mode_value, stop_event_from_gui, gui_log_cb):
    global CURRENT_MODE, stop_script_event, gui_logger_callback
    CURRENT_MODE = mode_value
    stop_script_event = stop_event_from_gui
    gui_logger_callback = gui_log_cb # Store the callback

    # Configure logging to use the GUI callback if provided
    # This is a simplified approach. A more robust solution might involve
    # a custom logging handler that calls gui_logger_callback.
    # For now, critical messages can use gui_logger_callback directly.
    
    # Basic logging setup if not already configured by GUI
    # This ensures that if main.py is somehow run in a context without GUI's logger,
    # it still logs to console. GUI's setup should ideally take precedence.
    if not any(isinstance(h, logging.StreamHandler) for h in logging.getLogger().handlers):
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            handlers=[logging.StreamHandler()])


    logging.info(f"run_selected_mode 调用，模式: {CURRENT_MODE}")
    if gui_logger_callback:
        gui_logger_callback(f"主脚本: run_selected_mode 调用，模式: {CURRENT_MODE}\n")

    # Admin check (can be done here or GUI can call is_admin directly)
    if sys.platform == 'win32':
        if not is_admin():
            err_msg = "错误: 脚本需要管理员权限才能运行。"
            logging.error(err_msg)
            if gui_logger_callback: gui_logger_callback(err_msg + "\n")
            # GUI should ideally prevent starting if not admin, or show a persistent warning.
            # For now, the script will proceed but might fail.
            # return # Optionally, prevent execution if not admin

    try:
        execute_main_logic() # Call the original main logic
        if gui_logger_callback:
             gui_logger_callback("主脚本: 任务执行完成。\n")
    except Exception as e:
        err_msg = f"主脚本: 执行模式 {CURRENT_MODE} 时发生顶层错误: {e}"
        logging.exception(err_msg)
        if gui_logger_callback:
            import traceback
            gui_logger_callback(err_msg + f"\n{traceback.format_exc()}\n")
    finally:
        logging.info(f"主脚本: 模式 {CURRENT_MODE} 执行流程结束。")
        if gui_logger_callback:
            gui_logger_callback(f"主脚本: 模式 {CURRENT_MODE} 执行流程结束。\n")


if __name__ == "__main__":
    # This block is for direct execution of main.py (e.g., for testing without GUI)
    # It will retain the original command-line mode selection.
    # The GUI will call run_selected_mode directly.

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()])

    if sys.platform == 'win32':
        if not is_admin():
            logging.error("脚本需要管理员权限才能运行。")
            ctypes.windll.user32.MessageBoxW(None, "请以管理员身份运行此脚本。", "权限不足", 0x30)
            sys.exit(1)
        else:
            logging.info("脚本以管理员权限运行 (直接执行)。")

    local_stop_event = threading.Event() # For direct execution, create a dummy event

    def cli_log(message): # Dummy logger for CLI
        print(message.strip())

    valid_modes = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    selected_cli_mode = None
    while selected_cli_mode not in valid_modes:
        try:
            prompt = (
                "请选择运行模式 (直接运行 main.py):\n"
                "  1: 买马预测模式\n  2: 复盘模式\n  3: 反买存档模式\n"
                "  4: 64进8专用模式\n  5: 冠军争霸模式\n"
                "  6: C_Arena - 完整分组赛\n  7: C_Arena - 单一分组赛\n"
                "  8: C_Arena - 冠军锦标赛\n  9: 图片处理与打包\n"
                "请输入你的选择 (1-9): "
            )
            mode_input = input(prompt)
            mode_int = int(mode_input)
            if mode_int in valid_modes:
                selected_cli_mode = mode_int
            else:
                logging.warning(f"输入无效，请输入 {', '.join(map(str, valid_modes))} 中的一个。")
        except ValueError:
            logging.warning(f"输入无效，请输入数字 {', '.join(map(str, valid_modes))} 中的一个。")
        except EOFError:
            logging.error("无法读取输入。退出。")
            sys.exit(1)
        except KeyboardInterrupt:
            logging.info("用户中断输入。退出。")
            sys.exit(0)
    
    logging.info(f"直接运行模式 {selected_cli_mode}...")
    # Simulate the 5s delay for CLI execution as well
    start_delay = 5
    logging.info(f"脚本将在 {start_delay} 秒后开始... 请准备好 NIKKE 窗口。")
    try:
        for i in range(start_delay, 0, -1):
             logging.info(f"...{i}")
             time.sleep(1)
             # No stop event check here for CLI simplicity during countdown
    except KeyboardInterrupt:
        logging.info("脚本在启动倒计时期间被中断。")
        sys.exit(0)

    run_selected_mode(selected_cli_mode, local_stop_event, cli_log)

def get_pixel_color_from_rel(relative_coord: tuple, window: pygetwindow.Win32Window):
    """
    根据相对坐标和当前窗口客户区，计算实际屏幕坐标并获取该点的像素RGB颜色。
    相对坐标是 (比例X, 比例Y)，相对于窗口的客户区。
    """
    check_stop_signal()
    if not isinstance(relative_coord, tuple) or len(relative_coord) != 2:
        logging.error(f"无效的相对坐标格式: {relative_coord}. 需要 (rel_x, rel_y)。")
        return None

    try:
        hwnd = window._hWnd
        if not hwnd:
            logging.error("错误：无法从 pygetwindow 对象获取窗口句柄 (HWND) for pixel color。")
            return None

        # 获取客户区矩形（相对于窗口左上角）
        client_rect_left, client_rect_top, client_rect_right, client_rect_bottom = win32gui.GetClientRect(hwnd)
        client_width = client_rect_right - client_rect_left
        client_height = client_rect_bottom - client_rect_top

        if client_width <= 0 or client_height <= 0:
            logging.error(f"错误：获取到的窗口客户区尺寸无效 (Width={client_width}, Height={client_height}) for pixel color。")
            return None

        # 将客户区的左上角坐标 (通常是0,0) 转换为屏幕坐标
        screen_client_origin_x, screen_client_origin_y = win32gui.ClientToScreen(hwnd, (client_rect_left, client_rect_top))

        # 基于客户区计算实际的屏幕坐标
        screen_x = screen_client_origin_x + round(relative_coord[0] * client_width)
        screen_y = screen_client_origin_y + round(relative_coord[1] * client_height)

        logging.info(f"相对坐标 {relative_coord} -> 屏幕坐标 ({screen_x}, {screen_y}) for pixel color (基于窗口 '{window.title}' HWND:{hwnd} 客户区尺寸 {client_width}x{client_height} @ ({screen_client_origin_x},{screen_client_origin_y}))")
        
        # pyautogui.pixel() 需要绝对屏幕坐标
        color = pyautogui.pixel(screen_x, screen_y)
        logging.info(f"颜色拾取成功 at ({screen_x}, {screen_y}): RGB {color}")
        return color

    except Exception as e:
        logging.error(f"获取相对坐标 {relative_coord} 的像素颜色时出错: {e}")
        return None
    time.sleep(0.5) # 截图后短暂等待
def cleanup_temp_files_carena(file_prefix: str, match_name: str):
    """
    清理指定C_Arena赛事的临时截图文件 (使用传入的文件前缀)。
    路径基于 main.py 的 TEMP_DIR。
    """
    logging.info(f"  清理C_Arena临时文件 for {file_prefix}_{match_name}...")
    files_to_remove = []
    # 队伍截图
    for player_num_suffix in ["player1_click_carena", "player2_click_carena"]: # 使用 main.py 中的坐标键作为参考
        # 玩家相关的队伍截图 (5个队伍)
        for team_index in range(1, 6): # team1 to team5
            files_to_remove.append(os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_{player_num_suffix}_team{team_index}.png"))
        
        # 玩家信息截图 (3个)
        files_to_remove.append(os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_{player_num_suffix}_playerinfo.png"))
        files_to_remove.append(os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_{player_num_suffix}_player_info_2.png"))
        files_to_remove.append(os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_{player_num_suffix}_player_info_3.png"))
        
        # 垂直拼接的该玩家的完整图 (包含信息和队伍)
        files_to_remove.append(os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_{player_num_suffix}.png"))

    # 赛果截图
    files_to_remove.append(os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_result.png"))

    removed_count = 0
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                removed_count += 1
                logging.debug(f"    已删除C_Arena临时文件: {file_path}")
            except OSError as e:
                logging.warning(f"    警告：无法删除C_Arena临时文件 {file_path}: {e}")
    logging.info(f"  C_Arena临时文件清理完成，尝试删除 {len(files_to_remove)} 个文件，实际删除 {removed_count} 个。")

def process_single_match_carena(
    nikke_window: pygetwindow.Win32Window,
    current_mode: int, # 6, 7, or 8
    file_prefix: str,
    match_name: str,
    target_for_4in2_1_match_key: str,
    first_target_for_4in2_2_match_key: str,
    second_target_for_4in2_2_match_key: str, # This should be the key for the "_real_click"
    target_for_2in1_match_key: str
):
    """
    处理单个C_Arena赛事的完整流程。
    使用 main.py 的函数和常量。
    """
    # global stop_script # Replaced by stop_script_event
    
    logging.info(f"\n--- 开始处理C_Arena赛事 {file_prefix} - {match_name} (模式 {current_mode}) ---")
    if stop_script_event and stop_script_event.is_set():
        logging.info(f"C_Arena赛事 {file_prefix} - {match_name} 在开始前被中断。")
        return False

    # 根据当前模式选择坐标字典
    active_coords_dict = C_ARENA_MODE67_COORDS_REL if current_mode in [6, 7] else C_ARENA_MODE8_COORDS_REL

    # A-1: 根据比赛类型执行不同的点击操作进入赛果界面
    logging.info(f"  执行初始点击操作 for {match_name}...")
    click_success = False
    
    actual_match_coord_key_to_click = match_name # Default for 8in4 in mode 6/7
    if current_mode == 8 and "match_map" in active_coords_dict:
        actual_match_coord_key_to_click = active_coords_dict["match_map"].get(match_name, match_name)
        logging.info(f"  模式 8 映射: {match_name} -> {actual_match_coord_key_to_click}")

    if match_name.startswith("8in4"):
        key_to_use_for_8in4 = actual_match_coord_key_to_click
        if current_mode != 8: # For mode 6 and 7, add suffix
            key_to_use_for_8in4 = f"{actual_match_coord_key_to_click}_click"
        click_success = click_coordinates(active_coords_dict[key_to_use_for_8in4], nikke_window)
        if click_success: time.sleep(3) # c_arena_reviewer had delay_after=3
    elif match_name == "4in2_1":
        click_success = click_coordinates(active_coords_dict[target_for_4in2_1_match_key], nikke_window)
        if click_success: time.sleep(1.5)
    elif match_name == "4in2_2":
        if click_coordinates(active_coords_dict[first_target_for_4in2_2_match_key], nikke_window):
            time.sleep(1.0)
            click_success = click_coordinates(active_coords_dict[second_target_for_4in2_2_match_key], nikke_window)
            if click_success: time.sleep(1.5)
        else:
            click_success = False
    elif match_name == "2in1":
        click_success = click_coordinates(active_coords_dict[target_for_2in1_match_key], nikke_window)
        if click_success: time.sleep(1.5)
    else:
        logging.error(f"错误：未知的 match_name '{match_name}'，无法执行初始点击。")
        return False

    if not click_success:
        logging.error(f"错误：执行 {match_name} 的初始点击操作失败。")
        return False
    if stop_script_event and stop_script_event.is_set(): return False

    # A-2: 截图赛果区域
    result_img_path = os.path.join(TEMP_DIR, f"{file_prefix}_{match_name}_result.png")
    if not take_screenshot(active_coords_dict["result_region_carena"], nikke_window, result_img_path):
        logging.error(f"未能截取赛果图 for {match_name}")
        return False
    if stop_script_event and stop_script_event.is_set(): return False

    player_stitched_paths = {} 
    player_info_and_teams_screenshot_paths = {} 

    # 处理两个玩家
    for player_num_idx, player_key_suffix in enumerate(["player1_click_carena", "player2_click_carena"], 1):
        if stop_script_event and stop_script_event.is_set(): return False
        logging.info(f"-- 处理C_Arena玩家 {player_num_idx} ({player_key_suffix}) --")
        
        # A-3 / A-7: 点击玩家头像
        if not click_coordinates(active_coords_dict[player_key_suffix], nikke_window):
            logging.error(f"未能点击玩家 {player_num_idx} 头像")
            return False
        time.sleep(3) # 等待队伍界面加载
        if stop_script_event and stop_script_event.is_set(): return False

        current_player_screenshots = []
        
        # 截图玩家信息区域 1 (使用 main.py 的 PLAYER_INFO_REGION_REL)
        p_info1_fname = f"{file_prefix}_{match_name}_{player_key_suffix}_playerinfo.png"
        p_info1_fpath = os.path.join(TEMP_DIR, p_info1_fname)
        if not take_screenshot(PLAYER_INFO_REGION_REL, nikke_window, p_info1_fpath): return False
        current_player_screenshots.append(p_info1_fpath)
        if stop_script_event and stop_script_event.is_set(): return False

        # 点击 player_detailinfo_2, 等待, 截图 player_info_2 (使用 main.py 的 PLAYER_INFO_2_REGION_REL)
        if not click_coordinates(active_coords_dict["player_detailinfo_2_click_carena"], nikke_window): return False
        time.sleep(2.5)
        p_info2_fname = f"{file_prefix}_{match_name}_{player_key_suffix}_player_info_2.png"
        p_info2_fpath = os.path.join(TEMP_DIR, p_info2_fname)
        if not take_screenshot(PLAYER_INFO_2_REGION_REL, nikke_window, p_info2_fpath): return False
        current_player_screenshots.append(p_info2_fpath)
        if stop_script_event and stop_script_event.is_set(): return False
        
        # 点击 player_detailinfo_3, 等待, 截图 player_info_3 (使用 C_ARENA_MODE67_COORDS_REL["player_info_3_region_carena"])
        if not click_coordinates(active_coords_dict["player_detailinfo_3_click_carena"], nikke_window): return False
        time.sleep(1.0)
        p_info3_fname = f"{file_prefix}_{match_name}_{player_key_suffix}_player_info_3.png"
        p_info3_fpath = os.path.join(TEMP_DIR, p_info3_fname)
        if not take_screenshot(active_coords_dict["player_info_3_region_carena"], nikke_window, p_info3_fpath): return False
        current_player_screenshots.append(p_info3_fpath)
        if stop_script_event and stop_script_event.is_set(): return False

        # 点击 player_detailinfo_close
        if not click_coordinates(active_coords_dict["player_detailinfo_close_click_carena"], nikke_window): return False
        time.sleep(0.5)
        if stop_script_event and stop_script_event.is_set(): return False

        # 循环点击5个队伍并截图 (使用 main.py 的 TEAM_COORDS_REL 和 SCREENSHOT_REGION_REL)
        for i, team_coord_rel in enumerate(TEAM_COORDS_REL, 1):
            if stop_script_event and stop_script_event.is_set(): return False
            if not click_coordinates(team_coord_rel, nikke_window):
                logging.error(f"未能点击玩家 {player_num_idx} 的队伍 {i}")
                return False
            time.sleep(1.5) # 增加队伍切换等待 (原c_arena有此延迟)
            if stop_script_event and stop_script_event.is_set(): return False

            team_img_fname = f"{file_prefix}_{match_name}_{player_key_suffix}_team{i}.png"
            team_img_fpath = os.path.join(TEMP_DIR, team_img_fname)
            if not take_screenshot(SCREENSHOT_REGION_REL, nikke_window, team_img_fpath): 
                logging.error(f"未能截取玩家 {player_num_idx} 的队伍 {i} 截图")
                return False
            current_player_screenshots.append(team_img_fpath)
            if stop_script_event and stop_script_event.is_set(): return False
        
        player_info_and_teams_screenshot_paths[player_num_idx] = current_player_screenshots

        # 垂直拼接玩家信息截图和队伍截图 (共 3+5=8 张)
        player_stitched_fname = f"{file_prefix}_{match_name}_{player_key_suffix}.png" # Stitched file for this player
        player_stitched_fpath = os.path.join(TEMP_DIR, player_stitched_fname)
        
        if not stitch_images_vertically(current_player_screenshots, player_stitched_fpath):
            logging.error(f"玩家 {player_num_idx} 的截图垂直拼接失败")
            player_stitched_paths[player_num_idx] = None
        else:
            player_stitched_paths[player_num_idx] = player_stitched_fpath
        if stop_script_event and stop_script_event.is_set(): return False

        # 点击队伍界面关闭 (使用 main.py 的 EXIT_COORD_REL)
        if not click_coordinates(EXIT_COORD_REL, nikke_window): 
            logging.error(f"未能为玩家 {player_num_idx} 点击关闭队伍界面")
            return False
        time.sleep(1.0)
        if stop_script_event and stop_script_event.is_set(): return False

    # A-10: 水平拼接 Player1, Result, Player2
    final_img_fname = f"{file_prefix}_{match_name}.png"
    final_img_fpath = os.path.join(FINAL_OUTPUT_DIR, final_img_fname) # Save to new FINAL_OUTPUT_DIR

    player1_stitched_img = player_stitched_paths.get(1)
    player2_stitched_img = player_stitched_paths.get(2)

    images_to_stitch_horizontally = []
    if player1_stitched_img and os.path.exists(player1_stitched_img):
        images_to_stitch_horizontally.append(player1_stitched_img)
    else:
        logging.warning(f"玩家1的拼接图丢失 for {match_name}")
    
    if os.path.exists(result_img_path):
        images_to_stitch_horizontally.append(result_img_path)
    else:
        logging.warning(f"赛果图丢失 for {match_name}")

    if player2_stitched_img and os.path.exists(player2_stitched_img):
        images_to_stitch_horizontally.append(player2_stitched_img)
    else:
        logging.warning(f"玩家2的拼接图丢失 for {match_name}")

    if len(images_to_stitch_horizontally) == 3:
        if not stitch_images_horizontally(images_to_stitch_horizontally, final_img_fpath, spacing=0, background_color=(255,255,255)): # c_arena uses white bg, no spacing
            logging.error(f"最终图像水平拼接失败 for {file_prefix}_{match_name}")
            # Continue to close result even if stitching fails
    else:
        logging.warning(f"缺少用于最终水平拼接的图片 for {file_prefix}_{match_name}。需要3张，实际{len(images_to_stitch_horizontally)}张。跳过拼接。")

    if stop_script_event and stop_script_event.is_set(): return False

    # A-11: 点击赛果界面关闭
    if not click_coordinates(active_coords_dict["close_result_click_carena"], nikke_window): 
        logging.error(f"未能点击关闭赛果界面 for {match_name}")
        return False
    time.sleep(1.5)
    if stop_script_event and stop_script_event.is_set(): return False

    # 清理本次赛事的临时文件
    cleanup_temp_files_carena(file_prefix, match_name)

    logging.info(f"--- 完成处理C_Arena赛事 {file_prefix} - {match_name} ---")
    return True
# --- C_Arena Reviewer Mode Logics (Modes 6, 7, 8) ---

MATCH_NAMES_CARENA = ["8in4_1", "8in4_2", "8in4_3", "8in4_4", "4in2_1", "4in2_2", "2in1"] # From c_arena_reviewer

def run_carena_mode_logic(nikke_window: pygetwindow.Win32Window, mode: int):
    """
    处理C_Arena截图模式 (模式 6, 7, 8) 的核心逻辑。
    mode 6: 完整模式 (8个组)
    mode 7: 单组模式 (当前组)
    mode 8: 冠军赛模式 (当前界面)
    """
    # global stop_script # Replaced by stop_script_event
    logging.info(f"===== 运行C_Arena模式 {mode} =====")

    active_coords_dict = C_ARENA_MODE67_COORDS_REL if mode in [6, 7] else C_ARENA_MODE8_COORDS_REL
    
    groups_to_process = []
    file_prefix_base = ""

    if mode == 6: # 完整模式
        logging.info("模式 6: 完整模式 (处理所有8个组)")
        groups_to_process = range(1, 9) # group_1 to group_8
        # file_prefix_base will be set inside the loop
    elif mode == 7: # 单组模式
        logging.info("模式 7: 单组模式 (仅处理当前组)")
        groups_to_process = [1] # Placeholder for single run
        file_prefix_base = "group1_current" # Fixed prefix for current group
    elif mode == 8: # 冠军赛模式
        logging.info("模式 8: 冠军赛模式 (处理当前界面)")
        groups_to_process = [1] # Placeholder for single run
        file_prefix_base = "champain_current" # Fixed prefix for champion mode
    else:
        logging.error(f"未知的C_Arena模式: {mode}")
        return

    total_matches_overall = len(MATCH_NAMES_CARENA) * len(groups_to_process)
    completed_matches_overall = 0
    
    # --- 确定 4in2 和 2in1 的点击目标 (基于颜色拾取) ---
    # 这些键名需要与 C_ARENA_MODE67_COORDS_REL 和 C_ARENA_MODE8_COORDS_REL 中的定义对应
    # For Mode 6/7
    color_check_coord1_key_m67 = "4in2_1_color_check_coord"
    color_check_coord2_key_m67 = "4in2_2_color_check_coord"
    second_target_4in2_2_m67 = "4in2_2_real_click"
    # For Mode 8
    color_check_coord1_key_m8 = active_coords_dict.get("color_check_coord1_key", "mode3_4in2_1_color_check_coord")
    color_check_coord2_key_m8 = active_coords_dict.get("color_check_coord2_key", "mode3_4in2_2_color_check_coord")
    second_target_4in2_2_m8 = "4in2_2_real_click" # Mode 8 also uses the "_real_click"

    target_4in2_1_key = ""
    first_target_4in2_2_key = ""
    second_target_4in2_2_key_final = "" # This will be the "_real_click" key
    target_2in1_key = ""

    # Select appropriate keys based on mode
    current_color_check_coord1_key = color_check_coord1_key_m8 if mode == 8 else color_check_coord1_key_m67
    current_color_check_coord2_key = color_check_coord2_key_m8 if mode == 8 else color_check_coord2_key_m67
    second_target_4in2_2_key_final = second_target_4in2_2_m8 if mode == 8 else second_target_4in2_2_m67


    logging.info(f"  正在确定 4in2 和 2in1 的点击目标 (基于 {current_color_check_coord1_key} 和 {current_color_check_coord2_key})...")
    color1_rel_coord = active_coords_dict.get(current_color_check_coord1_key)
    color2_rel_coord = active_coords_dict.get(current_color_check_coord2_key)

    if not color1_rel_coord or not color2_rel_coord:
        logging.error(f"错误：无法在坐标字典中找到颜色检查点: {current_color_check_coord1_key} 或 {current_color_check_coord2_key}")
        return

    color1_rgb = get_pixel_color_from_rel(color1_rel_coord, nikke_window)
    color2_rgb = get_pixel_color_from_rel(color2_rel_coord, nikke_window)

    if color1_rgb and color2_rgb:
        b1 = color1_rgb[2]
        b2 = color2_rgb[2]
        logging.info(f"  颜色比较: {current_color_check_coord1_key} B={b1}, {current_color_check_coord2_key} B={b2}")
        if b2 > b1:
            target_2in1_key = current_color_check_coord2_key
            first_target_4in2_2_key = current_color_check_coord2_key
            target_4in2_1_key = current_color_check_coord1_key
            logging.info(f"  判定: {current_color_check_coord2_key} (B={b2}) 的 B 值更大。")
        else:
            target_2in1_key = current_color_check_coord1_key
            first_target_4in2_2_key = current_color_check_coord1_key
            target_4in2_1_key = current_color_check_coord2_key
            logging.info(f"  判定: {current_color_check_coord1_key} (B={b1}) 的 B 值更大或相等。")
    else:
        logging.warning(f"  警告：无法获取颜色，将使用默认点击目标。4in2_1 点击 {current_color_check_coord1_key}, 4in2_2 先点 {current_color_check_coord1_key} 再点 {second_target_4in2_2_key_final}, 2in1 点击 {current_color_check_coord1_key}")
        target_4in2_1_key = current_color_check_coord1_key
        first_target_4in2_2_key = current_color_check_coord1_key
        # second_target_4in2_2_key_final is already set
        target_2in1_key = current_color_check_coord1_key
        
    logging.info(f"  最终点击目标键: 4in2_1 使用 '{target_4in2_1_key}', 4in2_2 先点 '{first_target_4in2_2_key}' 再点 '{second_target_4in2_2_key_final}', 2in1 使用 '{target_2in1_key}'")
    # --- 颜色拾取逻辑结束 ---

    for group_idx_enum, group_num_placeholder in enumerate(groups_to_process): # group_num_placeholder is 1 for mode 7/8
        if stop_script_event and stop_script_event.is_set(): break
        
        current_file_prefix = f"group{group_idx_enum + 1}" if mode == 6 else file_prefix_base
        
        if mode == 6: # 完整模式下，点击分组按钮
            group_click_key = f"group_{group_idx_enum + 1}_click"
            logging.info(f"\n====== 开始处理C_Arena组别 {group_idx_enum + 1} (前缀: {current_file_prefix}) ======")
            if not click_coordinates(active_coords_dict[group_click_key], nikke_window):
                logging.error(f"错误：点击组别 {group_idx_enum + 1} 失败，跳过该组")
                continue
            time.sleep(6) # 等待加载
            if stop_script_event and stop_script_event.is_set(): break
        else: # 单组或冠军赛模式
             logging.info(f"\n====== 开始处理C_Arena当前界面 (前缀: {current_file_prefix}) ======")


        for match_name in MATCH_NAMES_CARENA:
            if stop_script_event and stop_script_event.is_set(): break
            
            success = process_single_match_carena(
                nikke_window,
                mode, # Pass the overall mode (6, 7, or 8)
                current_file_prefix,
                match_name,
                target_for_4in2_1_match_key,
                first_target_for_4in2_2_match_key,
                second_target_4in2_2_key_final, # Pass the key for the "_real_click"
                target_2in1_key
            )
            if success:
                completed_matches_overall += 1
                logging.info(f"C_Arena进度: {completed_matches_overall}/{total_matches_overall} ({completed_matches_overall/total_matches_overall:.1%})")
            else:
                logging.error(f"处理C_Arena赛事 {current_file_prefix} - {match_name} 时出错或被中断。")
                if stop_script_event and stop_script_event.is_set():
                    logging.info(f"C_Arena赛事 {current_file_prefix} - {match_name} 中断。")
                    break # Break from MATCH_NAMES_CARENA loop
        # This is the end of the "for match_name in MATCH_NAMES_CARENA:" loop

        if stop_script_event and stop_script_event.is_set(): # Check if inner loop was broken due to stop_script_event
            logging.info(f"C_Arena组别 {group_idx_enum + 1 if mode == 6 else 'current'} 处理中断。")
            break # Break from groups_to_process loop
            
        if mode == 6: # 完整模式下，每组处理完后
            logging.info(f"====== 完成处理C_Arena组别 {group_idx_enum + 1} ======")
        else: # 单组或冠军赛模式完成
            logging.info(f"====== 完成处理C_Arena当前界面 (模式 {mode}) ======")
    # This is the end of the "for group_idx_enum..." loop

    if stop_script_event and stop_script_event.is_set():
        logging.warning("C_Arena模式执行被人为中断。")
    else:
        logging.info(f"===== C_Arena模式 {mode} 执行完毕 =====")
    
    return not (stop_script_event and stop_script_event.is_set())

# --- Mode 9: Image Processing and Packaging Logic ---

def process_and_save_image_carena(input_path: str, output_dir: str):
    """
    将单个图像宽度调整至预设宽度，高度按原始比例计算，然后转换为 WebP 并保存。
    使用 main.py 中定义的常量。
    """
    # Constants TARGET_WIDTH_M9, WEBP_QUALITY_M9, WEBP_METHOD_M9 are global
    try:
        logging.info(f"  模式9处理图片: {os.path.basename(input_path)}")
        img = Image.open(input_path)
        orig_width, orig_height = img.size

        if orig_width <= 0 or orig_height <= 0:
            logging.error(f"    错误: 图片 '{os.path.basename(input_path)}' 尺寸无效 ({orig_width}x{orig_height})，跳过。")
            img.close()
            return False

        new_processing_width = TARGET_WIDTH_M9
        if orig_width == 0:
            logging.error(f"    错误: 图片 '{os.path.basename(input_path)}' 原始宽度为0，无法计算比例，跳过。")
            img.close()
            return False
        
        new_processing_height = int(round(orig_height * (new_processing_width / orig_width)))

        logging.info(f"    按原始比例缩放至 ({new_processing_width}x{new_processing_height})...")
        final_img = img.resize((new_processing_width, new_processing_height), Image.Resampling.LANCZOS)

        base_filename = os.path.splitext(os.path.basename(input_path))[0]
        output_filename = f"{base_filename}.webp"
        output_path = os.path.join(output_dir, output_filename) # output_dir is WEBP_OUTPUT_DIR

        logging.info(f"    保存为 WebP: {output_path} (Quality: {WEBP_QUALITY_M9}, Method: {WEBP_METHOD_M9})")
        final_img.save(output_path, 'WEBP', quality=WEBP_QUALITY_M9, method=WEBP_METHOD_M9, lossless=False)

        final_img.close()
        img.close()
        return True
    except FileNotFoundError:
        logging.error(f"错误：模式9找不到输入文件 '{input_path}'")
        return False
    except Exception as e:
        logging.error(f"错误：模式9处理图片 '{input_path}' 失败: {e}")
        # import traceback; traceback.print_exc() # Uncomment for debug
        return False

def create_output_zip_carena(source_dir: str, zip_filename_with_path: str):
    """
    将指定目录的内容打包成 ZIP 文件 (仅存储，不压缩)。
    zip_filename_with_path 是包含路径的完整zip文件名。
    """
    if not os.path.isdir(source_dir):
        logging.error(f"错误：模式9源目录 '{source_dir}' 不存在或不是一个目录，无法打包。")
        return False
    try:
        logging.info(f"\n模式9开始打包目录 '{source_dir}' 到 '{zip_filename_with_path}'...")
        with zipfile.ZipFile(zip_filename_with_path, 'w', zipfile.ZIP_STORED) as zipf:
            item_count = 0
            for root, _, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    logging.info(f"  添加: {arcname}")
                    zipf.write(file_path, arcname=arcname)
                    item_count += 1
        logging.info(f"模式9打包完成，共添加 {item_count} 个文件到 {zip_filename_with_path}")
        return True
    except Exception as e:
        logging.error(f"错误：模式9创建 ZIP 文件 '{zip_filename_with_path}' 失败: {e}")
        # import traceback; traceback.print_exc() # Uncomment for debug
        if os.path.exists(zip_filename_with_path):
            try:
                os.remove(zip_filename_with_path)
                logging.info(f"已删除不完整的 ZIP 文件: {zip_filename_with_path}")
            except OSError as remove_err:
                logging.warning(f"警告：无法删除不完整的 ZIP 文件 '{zip_filename_with_path}': {remove_err}")
        return False

def run_mode_9_logic():
    """执行模式 9 的逻辑：处理图片并打包"""
    global FINAL_OUTPUT_DIR, WEBP_OUTPUT_DIR, ZIP_FILENAME # Use constants from main.py
    
    logging.info("\n====== 开始执行模式 9：图片处理与打包 ======")
    
    input_dir_m9 = FINAL_OUTPUT_DIR
    output_dir_m9_webp = WEBP_OUTPUT_DIR
    zip_file_path_m9 = ZIP_FILENAME # This is just the filename, will be in current dir

    logging.info(f"模式9输入图片目录 (来源): {os.path.abspath(input_dir_m9)}")
    logging.info(f"模式9输出 WebP 目录: {os.path.abspath(output_dir_m9_webp)}")
    logging.info(f"模式9最终压缩包名: {zip_file_path_m9}")

    if not os.path.isdir(input_dir_m9):
        logging.error(f"错误: 模式9输入目录 '{input_dir_m9}' 不存在。请先运行模式 1-8 生成图片。")
        # Consider using ctypes.windll.user32.MessageBoxW for GUI error if needed
        return False

    # os.makedirs(output_dir_m9_webp, exist_ok=True) # Already created in main()

    try:
        image_files = [f for f in os.listdir(input_dir_m9) if f.lower().endswith('.png') and os.path.isfile(os.path.join(input_dir_m9, f))]
    except Exception as e:
        logging.error(f"错误: 模式9无法读取输入目录 '{input_dir_m9}': {e}")
        return False

    if not image_files:
        logging.warning(f"警告: 模式9输入目录 '{input_dir_m9}' 中没有找到 .png 图片文件。")
        return False

    logging.info(f"模式9找到 {len(image_files)} 个 .png 文件准备处理...")
    success_count = 0
    fail_count = 0
    start_time = time.time()

    for filename in image_files:
        if stop_script_event and stop_script_event.is_set():
            logging.warning("模式9在图片处理中被中断。")
            return False
        input_path = os.path.join(input_dir_m9, filename)
        if process_and_save_image_carena(input_path, output_dir_m9_webp):
            success_count += 1
        else:
            fail_count += 1
            
    end_time_process = time.time()
    logging.info(f"\n模式9图片处理完成。成功: {success_count}, 失败: {fail_count}. 耗时: {end_time_process - start_time:.2f} 秒")

    if success_count == 0 and fail_count > 0 : # Only show error if all failed
        logging.error("模式9未能成功处理任何图片。")
        return False
    if success_count == 0 and fail_count == 0: # No files processed (e.g. list was empty after all)
        logging.info("模式9没有文件被处理。")
        return True # Not an error, just nothing to do.

    if stop_script_event and stop_script_event.is_set():
        logging.warning("模式9在打包前被中断。")
        return False
        
    if create_output_zip_carena(output_dir_m9_webp, zip_file_path_m9):
        completion_message = (
            "模式9：图片已标准化并打包。\n\n"
            f"压缩包 '{zip_file_path_m9}' 已创建在脚本运行目录下。\n\n"
            "你可以将压缩包名改为\"服务器名_第一组左上角玩家的uid\" ，\n"
            "如 \"jp_04501689.zip\" （避免和同一大区的玩家重复）\n\n"
            "再分享到QQ群 437983122 或者其他地方"
        )
        logging.info(completion_message)
        # GUI will handle notifications
        # try:
        #     ctypes.windll.user32.MessageBoxW(None, completion_message, "模式 9 完成", 0x40 | 0x1000)
        # except Exception as e:
        #     logging.warning(f"显示模式9完成消息框失败: {e}")
        if gui_logger_callback:
            gui_logger_callback(completion_message) # Send to GUI log
        return True
    else:
        logging.error(f"错误：模式9打包目录 '{output_dir_m9_webp}' 失败。")
        return False
