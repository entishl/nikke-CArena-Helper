# core/constants.py

# --- 基础配置 ---
BASE_WIDTH = 3840
BASE_HEIGHT = 2160

# --- 默认延迟时间 (可以被具体调用覆盖) ---
DEFAULT_INITIAL_DELAY_AFTER_ENTRY = 3.0
DEFAULT_DELAY_AFTER_TEAM_CLICK = 1.5
DEFAULT_DELAY_AFTER_INFO_ACTION = 0.5  # 用于 player_info_regions_config 中的动作
DEFAULT_DELAY_AFTER_CLOSE_VIEW = 1.0
# utils.py 中的 ACTION_DELAY 也会用到，最终应统一来源，暂时在此处也定义一个参考值
# 如果 utils.py 中的 ACTION_DELAY 被视为更通用，则此处可以不定义或引用它
UNIVERSAL_ACTION_DELAY = 1.2

# --- 目标窗口与进程 ---
APP_TITLE = "冠军竞技场截图工具" # GUI 应用标题
TARGET_PROCESS_NAME = "nikke.exe"
# TARGET_WINDOW_TITLE = "NIKKE" # 旧的单一标题，将被下面的列表取代
POSSIBLE_TARGET_WINDOW_TITLES = ["NIKKE", "勝利女神：妮姬", "胜利女神：新的希望"]
DEFAULT_TARGET_WINDOW_TITLE_INDEX = 0 # 默认使用列表中的第一个标题

# --- 临时文件与目录约定 (实际目录由调用方指定) ---
TEMP_DIR_NAME_DEFAULT = "temp_processing" # 默认临时目录名
PLAYER_INFO_SCREENSHOT_PREFIX = "player_info"
TEAM_SCREENSHOT_PREFIX = "team"
STITCHED_PLAYER_SUFFIX = "_stitched"

# --- 辅助函数 (用于在此模块内部转换坐标) ---
def _to_rel_coord(abs_coord, base_w=BASE_WIDTH, base_h=BASE_HEIGHT):
    """将绝对坐标 (x, y) 转换为相对比例。"""
    return (abs_coord[0] / base_w, abs_coord[1] / base_h)

def _to_rel_region(abs_region_x1y1x2y2, base_w=BASE_WIDTH, base_h=BASE_HEIGHT):
    """将绝对区域 (x1, y1, x2, y2) 转换为相对区域 (rel_x, rel_y, rel_w, rel_h)。"""
    x1, y1, x2, y2 = abs_region_x1y1x2y2
    rel_x = x1 / base_w
    rel_y = y1 / base_h
    rel_w = (x2 - x1) / base_w
    rel_h = (y2 - y1) / base_h
    if rel_w < 0: rel_w = 0
    if rel_h < 0: rel_h = 0
    return (rel_x, rel_y, rel_w, rel_h)

# === Constants from _backup/c_arena_predition.py (大多已转换为相对比例) ===
# 使用 PRED_ 前缀以区分来源，并与 reviewer 中的常量区分

# 原始绝对坐标 (仅作参考，实际使用下面的相对坐标)
_PRED_PLAYER1_COORD_ABS = (1671, 691)
_PRED_PLAYER2_COORD_ABS = (2175, 669)
_PRED_EXIT_COORD_ABS = (2370, 681)
_PRED_TEAM_COORDS_ABS = [
    (1515, 1064), (1734, 1064), (1928, 1064), (2112, 1064), (2303, 1064)
]
_PRED_SCREENSHOT_REGION_ABS = (1433, 1134, 2417, 1530) # team screenshot region
_PRED_PLAYER_INFO_REGION_ABS = (1433, 768, 2417, 963) # player info panel 1
_PRED_PLAYER_DETAILINFO_2_ABS = (1560, 866)
_PRED_PLAYER_INFO_2_REGION_ABS = (1433, 1344, 2417, 1529) # player info panel 2
_PRED_PLAYER_DETAILINFO_3_ABS = (2200, 2000)
_PRED_PLAYER_INFO_3_REGION_ABS = (1433, 1768, 2417, 1850) # player info panel 3
_PRED_PLAYER_DETAILINFO_CLOSE_ABS = (2418, 202) # 已根据用户反馈统一为X值较小的那个 (原为3500,200)

# 相对坐标 (这些是主要使用的)
PRED_PLAYER1_ENTRY_REL = _to_rel_coord(_PRED_PLAYER1_COORD_ABS)
PRED_PLAYER2_ENTRY_REL = _to_rel_coord(_PRED_PLAYER2_COORD_ABS)
PRED_EXIT_PLAYER_VIEW_REL = _to_rel_coord(_PRED_EXIT_COORD_ABS)
PRED_TEAM_BUTTONS_REL = [_to_rel_coord(coord) for coord in _PRED_TEAM_COORDS_ABS]
PRED_TEAM_SCREENSHOT_REGION_REL = _to_rel_region(_PRED_SCREENSHOT_REGION_ABS)

# 玩家信息面板的配置 (用于 collect_player_data 的 player_info_regions_config)
# 这是 c_arena_predition.py 中隐式定义的流程
PRED_PLAYER_INFO_CONFIG_SEQ = [
    {'type': 'screenshot', 'name': 'info_panel_1', 'region_rel': _to_rel_region(_PRED_PLAYER_INFO_REGION_ABS), 'delay_after': 0.5},
    {'type': 'click', 'name': 'click_detail_info_2', 'coord_rel': _to_rel_coord(_PRED_PLAYER_DETAILINFO_2_ABS), 'delay_after': 2.5},
    {'type': 'screenshot', 'name': 'info_panel_2', 'region_rel': _to_rel_region(_PRED_PLAYER_INFO_2_REGION_ABS), 'delay_after': 0.5},
    {'type': 'click', 'name': 'click_detail_info_3', 'coord_rel': _to_rel_coord(_PRED_PLAYER_DETAILINFO_3_ABS), 'delay_after': 1.0},
    {'type': 'screenshot', 'name': 'info_panel_3', 'region_rel': _to_rel_region(_PRED_PLAYER_INFO_3_REGION_ABS), 'delay_after': 0.5},
    {'type': 'click', 'name': 'click_close_detail_info', 'coord_rel': _to_rel_coord(_PRED_PLAYER_DETAILINFO_CLOSE_ABS), 'delay_after': 0.3} # 假设关闭按钮在此
]

# 为 PRED 模式下的 Player 2 定义独立的常量 (即使当前值与 P1 相同)
# 这主要是为了代码清晰性和未来的可维护性，如果 P2 的 UI 元素与 P1 不同
PRED_PLAYER2_INFO_CONFIG_SEQ = PRED_PLAYER_INFO_CONFIG_SEQ # 假设当前 P2 的信息面板流程与 P1 完全相同
PRED_PLAYER2_TEAM_BUTTONS_REL = PRED_TEAM_BUTTONS_REL # 假设当前 P2 的队伍按钮与 P1 完全相同
PRED_PLAYER2_TEAM_SCREENSHOT_REGION_REL = PRED_TEAM_SCREENSHOT_REGION_REL # 假设当前 P2 的队伍截图区域与 P1 完全相同
PRED_PLAYER2_EXIT_PLAYER_VIEW_REL = PRED_EXIT_PLAYER_VIEW_REL # 假设当前 P2 的关闭视图按钮与 P1 完全相同


# Mode 2 (复盘模式) 特有坐标 from predition.py
_PRED_PLAYER1_COORD_ABS_M2 = (1540, 1083)
_PRED_PLAYER2_COORD_ABS_M2 = (2176, 1083)
_PRED_RESULT_SCREENSHOT_ABS_M2 = (1600, 958, 2109, 1651)

PRED_PLAYER1_ENTRY_REL_M2 = _to_rel_coord(_PRED_PLAYER1_COORD_ABS_M2)
PRED_PLAYER2_ENTRY_REL_M2 = _to_rel_coord(_PRED_PLAYER2_COORD_ABS_M2)
PRED_RESULT_REGION_REL_M2 = _to_rel_region(_PRED_RESULT_SCREENSHOT_ABS_M2)

# --- Mode 2 (复盘模式) 特有配置常量 ---
# 模式2的截图和交互流程通常基于预测模式的元素
# PRED_PLAYER1_ENTRY_REL_M2 和 PRED_PLAYER2_ENTRY_REL_M2 已定义 (用于入口点击)
# PRED_RESULT_REGION_REL_M2 已定义 (用于赛果截图)
M2_PLAYER_INFO_CONFIG_SEQ = PRED_PLAYER_INFO_CONFIG_SEQ
M2_TEAM_BUTTONS_REL = PRED_TEAM_BUTTONS_REL
M2_TEAM_SCREENSHOT_REGION_REL = PRED_TEAM_SCREENSHOT_REGION_REL
M2_EXIT_PLAYER_VIEW_REL = PRED_EXIT_PLAYER_VIEW_REL

# Mode 3 (反买模式) 特有坐标 from predition.py
_PRED_PEOPLE_VOTE_REGION_ABS_M3 = (1395, 285, 2433, 1944)
PRED_PEOPLE_VOTE_REGION_REL_M3 = _to_rel_region(_PRED_PEOPLE_VOTE_REGION_ABS_M3)

# --- Mode 3 (反买模式) 特有配置常量 ---
# 模式3的截图和交互流程通常也基于预测模式的元素
M3_PLAYER1_ENTRY_REL = PRED_PLAYER1_ENTRY_REL
M3_PLAYER2_ENTRY_REL = PRED_PLAYER2_ENTRY_REL
M3_PLAYER_INFO_CONFIG_SEQ = PRED_PLAYER_INFO_CONFIG_SEQ
M3_TEAM_BUTTONS_REL = PRED_TEAM_BUTTONS_REL
M3_TEAM_SCREENSHOT_REGION_REL = PRED_TEAM_SCREENSHOT_REGION_REL
M3_EXIT_PLAYER_VIEW_REL = PRED_EXIT_PLAYER_VIEW_REL
M3_PEOPLE_VOTE_REGION_REL = PRED_PEOPLE_VOTE_REGION_REL_M3 # 民意调查区域

# --- Mode 4 (64进8) 特有入口坐标 ---
_P64IN8_PLAYER1_COORD_ABS_M4 = (1430, 760)
_P64IN8_PLAYER2_COORD_ABS_M4 = (1430, 1036)
_P64IN8_PLAYER3_COORD_ABS_M4 = (2411, 760)
_P64IN8_PLAYER4_COORD_ABS_M4 = (2411, 1036)
_P64IN8_PLAYER5_COORD_ABS_M4 = (1430, 1555)
_P64IN8_PLAYER6_COORD_ABS_M4 = (1430, 1825)
_P64IN8_PLAYER7_COORD_ABS_M4 = (2411, 1555)
_P64IN8_PLAYER8_COORD_ABS_M4 = (2411, 1825)

P64IN8_PLAYER1_COORD_REL_M4 = _to_rel_coord(_P64IN8_PLAYER1_COORD_ABS_M4)
P64IN8_PLAYER2_COORD_REL_M4 = _to_rel_coord(_P64IN8_PLAYER2_COORD_ABS_M4)
P64IN8_PLAYER3_COORD_REL_M4 = _to_rel_coord(_P64IN8_PLAYER3_COORD_ABS_M4)
P64IN8_PLAYER4_COORD_REL_M4 = _to_rel_coord(_P64IN8_PLAYER4_COORD_ABS_M4)
P64IN8_PLAYER5_COORD_REL_M4 = _to_rel_coord(_P64IN8_PLAYER5_COORD_ABS_M4)
P64IN8_PLAYER6_COORD_REL_M4 = _to_rel_coord(_P64IN8_PLAYER6_COORD_ABS_M4)
P64IN8_PLAYER7_COORD_REL_M4 = _to_rel_coord(_P64IN8_PLAYER7_COORD_ABS_M4)
P64IN8_PLAYER8_COORD_REL_M4 = _to_rel_coord(_P64IN8_PLAYER8_COORD_ABS_M4)

# --- Mode 5 (冠军争霸预测) 特有入口坐标 ---
_CHAMPION_PLAYER1_COORD_ABS_M5 = (1428, 690)
_CHAMPION_PLAYER2_COORD_ABS_M5 = (1428, 960)
_CHAMPION_PLAYER3_COORD_ABS_M5 = (2408, 690)
_CHAMPION_PLAYER4_COORD_ABS_M5 = (2408, 960)
_CHAMPION_PLAYER5_COORD_ABS_M5 = (1428, 1480)
_CHAMPION_PLAYER6_COORD_ABS_M5 = (1428, 1750)
_CHAMPION_PLAYER7_COORD_ABS_M5 = (2408, 1480)
_CHAMPION_PLAYER8_COORD_ABS_M5 = (2408, 1750)

CHAMPION_PLAYER1_COORD_REL_M5 = _to_rel_coord(_CHAMPION_PLAYER1_COORD_ABS_M5)
CHAMPION_PLAYER2_COORD_REL_M5 = _to_rel_coord(_CHAMPION_PLAYER2_COORD_ABS_M5)
CHAMPION_PLAYER3_COORD_REL_M5 = _to_rel_coord(_CHAMPION_PLAYER3_COORD_ABS_M5)
CHAMPION_PLAYER4_COORD_REL_M5 = _to_rel_coord(_CHAMPION_PLAYER4_COORD_ABS_M5)
CHAMPION_PLAYER5_COORD_REL_M5 = _to_rel_coord(_CHAMPION_PLAYER5_COORD_ABS_M5)
CHAMPION_PLAYER6_COORD_REL_M5 = _to_rel_coord(_CHAMPION_PLAYER6_COORD_ABS_M5)
CHAMPION_PLAYER7_COORD_REL_M5 = _to_rel_coord(_CHAMPION_PLAYER7_COORD_ABS_M5)
CHAMPION_PLAYER8_COORD_REL_M5 = _to_rel_coord(_CHAMPION_PLAYER8_COORD_ABS_M5)

# --- Mode 4/5 (64进8 / 冠军争霸预测) 共享的 collect_player_data 相关常量 ---
# 初始化为 PRED_ 系列的值，因为模式4/5当前代码使用它们
# 如果模式4/5有独特的UI元素，这些常量的值将来可以独立修改
M45_PLAYER_INFO_CONFIG_SEQ = PRED_PLAYER_INFO_CONFIG_SEQ
M45_TEAM_BUTTONS_REL = PRED_TEAM_BUTTONS_REL
M45_TEAM_SCREENSHOT_REGION_REL = PRED_TEAM_SCREENSHOT_REGION_REL
M45_EXIT_PLAYER_VIEW_REL = PRED_EXIT_PLAYER_VIEW_REL

# === Constants from _backup/c_arena_reviewer.py (COORDS_4K and COORDS_4K_MODE3) ===
# 使用 R_ 前缀 (Reviewer)

# --- R_COORDS_4K (常规赛/分组赛模式: reviewer 模式 6, 7) ---
R_GROUP_BUTTONS_REL = {
    f"group_{i}": _to_rel_coord(coord) for i, coord in enumerate([
        (270, 560), (740, 560), (1200, 560), (1680, 560),
        (2160, 560), (2620, 560), (3100, 560), (3600, 560)
    ], 1)
}

R_MATCH_8IN4_ENTRIES_REL = { # 8进4比赛入口
    "8in4_1": _to_rel_coord((1833, 896)), "8in4_2": _to_rel_coord((2044, 896)),
    "8in4_3": _to_rel_coord((1773, 1692)), "8in4_4": _to_rel_coord((2132, 1703)),
}
R_MATCH_4IN2_ENTRIES_REL = { # 4进2比赛入口 (颜色判断前的基础点)
    "4in2_1": _to_rel_coord((1923, 1160)), # 用于颜色判断点1
    "4in2_2_color_check": _to_rel_coord((1923, 1410)), # 用于颜色判断点2 (原4in2_2)
    "4in2_2_actual_click": _to_rel_coord((2176, 1742)), # 实际第二个点击目标 (原4in2_2_real)
}
# 2in1 的入口点会根据颜色判断从 R_MATCH_4IN2_ENTRIES_REL 中选择

R_PLAYER1_ENTRY_REL = _to_rel_coord((1534, 1096)) # reviewer 中 player1 头像
R_PLAYER2_ENTRY_REL = _to_rel_coord((2182, 1096)) # reviewer 中 player2 头像

R_RESULT_REGION_REL = _to_rel_region((1607, 968, 2116, 1642))
R_CLOSE_RESULT_REL = _to_rel_coord((2369, 529))

R_TEAM_BUTTONS_REL = [ # reviewer 中的队伍按钮顺序
    _to_rel_coord((1515, 1064)), _to_rel_coord((1734, 1064)),
    _to_rel_coord((1928, 1064)), _to_rel_coord((2112, 1064)),
    _to_rel_coord((2303, 1064))
]

# --- Reviewer (Mode 6, 7, 8) 相关延迟和配置 ---
R_DELAY_AFTER_GROUP_CLICK = 3.0  # 默认延迟，原在 mode6 中用 getattr 获取
R_DELAY_BETWEEN_GROUPS = 5.0     # 默认延迟，原在 mode6 中用 getattr 获取
R_DELAY_DEFAULT_AFTER_MATCH_ENTRY = 1.0 # mode8 中已用，这里也明确一下 (mode6 中 R_DELAY_AFTER_MATCH_ENTRY 字典也用此做默认)
R_DELAY_AFTER_SECOND_MATCH_ENTRY = 0.5 # mode6 中已用，这里明确
R_DELAY_BETWEEN_MATCHES_IN_GROUP = 1.0 # mode6 中已用 (cc.R_DELAY_BETWEEN_MATCHES_IN_GROUP)，这里明确

R_NUM_TOTAL_GROUPS = 8 # 假设总组数 (用于 mode6)

# 模式6/7/8 颜色判断逻辑的结构化常量 (针对4in2阶段)
# R_MATCH_NAMES = ["8in4_1", "8in4_2", "8in4_3", "8in4_4", "4in2_1", "4in2_2", "2in1"] # 假设的比赛名称顺序
R_MATCH_NAMES = ["8in4_1", "8in4_2", "8in4_3", "8in4_4", "4in2_1", "4in2_2", "2in1"] # 确保这个列表存在且正确

R_4IN2_COLOR_LOGIC_CONFIG = {
    'check_point1': R_MATCH_4IN2_ENTRIES_REL["4in2_1"],
    'check_point2': R_MATCH_4IN2_ENTRIES_REL["4in2_2_color_check"],
    'click_targets_default': { # 当 point1 颜色占优或相等时
        '4in2_1': R_MATCH_4IN2_ENTRIES_REL["4in2_1"],
        '4in2_2_first': R_MATCH_4IN2_ENTRIES_REL["4in2_1"], # 原代码逻辑
        '2in1': R_MATCH_4IN2_ENTRIES_REL["4in2_1"]          # 原代码逻辑
    },
    'click_targets_color2_dominant': { # 当 point2 颜色占优时
        '4in2_1': R_MATCH_4IN2_ENTRIES_REL["4in2_1"], # 原代码逻辑
        '4in2_2_first': R_MATCH_4IN2_ENTRIES_REL["4in2_2_color_check"],
        '2in1': R_MATCH_4IN2_ENTRIES_REL["4in2_2_color_check"]
    },
    '4in2_2_second_click': R_MATCH_4IN2_ENTRIES_REL["4in2_2_actual_click"] # 固定点击
}
# 模式8 可能需要类似的 R_M8_4IN2_COLOR_LOGIC_CONFIG，如果其键名不同 (例如使用 R_M8_MATCH_4IN2_ENTRIES_REL)
# R_DELAY_AFTER_MATCH_ENTRY 应该是一个字典，如 mode8 所用，这里定义一个默认值供 mode6 使用
R_DELAY_AFTER_MATCH_ENTRY = {
    "8in4_1": 1.5, "8in4_2": 1.5, "8in4_3": 1.5, "8in4_4": 1.5,
    "4in2_1": 1.5, "4in2_2": 1.5, # 4in2_2 在第二次点击后还有 R_DELAY_AFTER_SECOND_MATCH_ENTRY
    "2in1": 1.5
}
R_CLOSE_TEAMVIEW_REL = _to_rel_coord((2370, 681))
R_TEAM_SCREENSHOT_REGION_REL = _to_rel_region((1433, 1134, 2417, 1530))

# Reviewer 中的玩家信息面板配置 (与 Predition 结构类似，但坐标不同)
R_PLAYER_INFO_CONFIG_SEQ = [
    {'type': 'screenshot', 'name': 'info_panel_1', 'region_rel': _to_rel_region((1433, 768, 2417, 963)), 'delay_after': 0.5},
    {'type': 'click', 'name': 'click_detail_info_2', 'coord_rel': _to_rel_coord((1560, 888)), 'delay_after': 2.5},
    {'type': 'screenshot', 'name': 'info_panel_2', 'region_rel': _to_rel_region((1433, 1344, 2417, 1529)), 'delay_after': 0.5},
    {'type': 'click', 'name': 'click_detail_info_3', 'coord_rel': _to_rel_coord((2200, 1990)), 'delay_after': 1.0},
    {'type': 'screenshot', 'name': 'info_panel_3', 'region_rel': _to_rel_region((1433, 1768, 2417, 1842)), 'delay_after': 0.5},
    {'type': 'click', 'name': 'click_close_detail_info', 'coord_rel': _to_rel_coord((2418, 202)), 'delay_after': 0.5}
]


# --- R_COORDS_4K_MODE8 (冠军赛模式: reviewer 模式 8) ---
# 很多坐标沿用 R_COORDS_4K (模式 6,7 的常量)，这里只定义不同的或模式8特有的
R_M8_MATCH_8IN4_ENTRIES_REL = {
    "mode8_8in4_1": _to_rel_coord((1775, 827)), "mode8_8in4_2": _to_rel_coord((2066, 827)),
    "mode8_8in4_3": _to_rel_coord((1775, 1623)), "mode8_8in4_4": _to_rel_coord((2066, 1623)),
}
R_M8_MATCH_4IN2_ENTRIES_REL = { # 颜色判断前的基础点
    "mode8_4in2_1": _to_rel_coord((1907, 1065)), # 用于颜色判断点1
    "mode8_4in2_2_color_check": _to_rel_coord((1910, 1340)), # 用于颜色判断点2
    # 模式8 也使用固定的 R_MATCH_4IN2_ENTRIES_REL["4in2_2_actual_click"]
}
# R_M8_COLOR_CHECK_1_KEY = "mode8_4in2_1" (用于取色逻辑的键名)
# R_M8_COLOR_CHECK_2_KEY = "mode8_4in2_2_color_check"

# 模式8的比赛名称到实际坐标键的映射 (用于简化逻辑)
R_M8_MATCH_KEY_MAP = {
    "8in4_1": "mode8_8in4_1", "8in4_2": "mode8_8in4_2",
    "8in4_3": "mode8_8in4_3", "8in4_4": "mode8_8in4_4",
    "4in2_1": "mode8_4in2_1", "4in2_2": "mode8_4in2_2_color_check", # 4in2_2 指向颜色检查点
}

# 模式8 的颜色判断逻辑结构化常量
R_M8_4IN2_COLOR_LOGIC_CONFIG = {
    'check_point1': R_M8_MATCH_4IN2_ENTRIES_REL["mode8_4in2_1"],
    'check_point2': R_M8_MATCH_4IN2_ENTRIES_REL["mode8_4in2_2_color_check"],
    'click_targets_default': { # 当 point1 颜色占优或相等时
        '4in2_1': R_M8_MATCH_4IN2_ENTRIES_REL["mode8_4in2_1"],
        '4in2_2_first': R_M8_MATCH_4IN2_ENTRIES_REL["mode8_4in2_1"], # 沿用原代码逻辑
        '2in1': R_M8_MATCH_4IN2_ENTRIES_REL["mode8_4in2_1"]          # 沿用原代码逻辑
    },
    'click_targets_color2_dominant': { # 当 point2 颜色占优时
        '4in2_1': R_M8_MATCH_4IN2_ENTRIES_REL["mode8_4in2_1"], # 沿用原代码逻辑
        '4in2_2_first': R_M8_MATCH_4IN2_ENTRIES_REL["mode8_4in2_2_color_check"],
        '2in1': R_M8_MATCH_4IN2_ENTRIES_REL["mode8_4in2_2_color_check"]
    },
    # 模式8的 R_M8_MATCH_4IN2_ENTRIES_REL 中没有 "mode8_4in2_2_actual_click"
    # 它使用的是通用的 R_MATCH_4IN2_ENTRIES_REL["4in2_2_actual_click"]
    # 因此这里也引用通用的
    '4in2_2_second_click': R_MATCH_4IN2_ENTRIES_REL["4in2_2_actual_click"]
}

# 模式8 特定延迟常量
R_M8_DELAY_AFTER_MATCH_ENTRY = { # 字典，键是 R_M8_MATCH_KEY_MAP 中的值
    "mode8_8in4_1": 1.5, "mode8_8in4_2": 1.5,
    "mode8_8in4_3": 1.5, "mode8_8in4_4": 1.5,
    "mode8_4in2_1": 1.5, "mode8_4in2_2_color_check": 1.5, # 对应 4in2_2 的第一次点击后
    # "2in1" 在模式8中会映射到 "mode8_4in2_1" 或 "mode8_4in2_2_color_check"
    # 所以这里不需要单独为 "2in1" 定义，它会使用上面映射键的延迟
}
R_M8_DELAY_BETWEEN_MATCHES = 1.0 # 比赛之间的延迟
R_M8_DELAY_AFTER_SECOND_MATCH_ENTRY = 0.5 # 针对 4in2_2 第二次点击后的延迟 (如果适用)


# 模式9 (打包模式) 相关常量 from reviewer
R_M9_OUTPUT_WEBP_DIR = "output_webp_reviewer" # 避免与 main.py 中的冲突
R_M9_ZIP_FILENAME = "output_reviewer.zip"
R_M9_TARGET_WIDTH = 1238
# R_M9_TARGET_HEIGHT = 990 # 此项在 reviewer 中已改为按比例缩放，不再强制高度
R_M9_WEBP_QUALITY = 90
R_M9_WEBP_METHOD = 6


# --- 关于 collect_player_data 函数参数与常量使用的说明 ---
# 1. 玩家信息配置 (`player_info_regions_config`):
#    - 调用 `collect_player_data` 时，应根据具体场景（原 reviewer 逻辑或原 predition 逻辑）
#      传入 `R_PLAYER_INFO_CONFIG_SEQ` 或 `PRED_PLAYER_INFO_CONFIG_SEQ`。
#    - `PRED_PLAYER_INFO_CONFIG_SEQ` 内部的关闭详细信息步骤 (`click_close_detail_info`)
#      已更新为使用与 `R_PLAYER_INFO_CONFIG_SEQ` 相同的、X值较小的关闭坐标
#      (即 `_to_rel_coord((2418, 202))`)。
#
# 2. 关闭5队阵容视图 (`close_player_view_coord_rel` 参数):
#    - `PRED_EXIT_PLAYER_VIEW_REL` (源自 predition.py) 和
#      `R_CLOSE_TEAMVIEW_REL` (源自 reviewer.py)
#      均由相同的绝对坐标 (2370, 681) 转换而来，因此它们是等效的。
#    - `collect_player_data` 函数接收此参数，并负责执行此最终的关闭动作。
#      调用时，根据上下文选择 `PRED_EXIT_PLAYER_VIEW_REL` 或 `R_CLOSE_TEAMVIEW_REL` 均可。