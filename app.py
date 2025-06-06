import sys
import os
import time
import logging
import shutil
import importlib
import ctypes
import keyboard
import json

# 尝试从 core 模块导入，如果 core.utils 或 core.constants 尚未按计划更新，
# app.py 在调用相关功能时可能会失败，这将在后续子阶段解决。
try:
    from core import constants as core_constants
    from core import utils as core_utils
except ImportError:
    print("警告: 无法从 core 模块导入部分内容。app.py 的某些功能可能受限。")
    print("请确保 core.constants 和 core.utils 按计划存在和更新。")
    # 提供临时的 core_constants 存根，以允许 AppContext 定义
    class TempConstants: pass
    core_constants = TempConstants()
    core_utils = None # 标记 core_utils 未成功导入

# --- 全局常量 ---
APP_NAME = "Nikke Champion Arena Cheerleading Tool"
APP_VERSION = "2.0.0-alpha" # 示例版本
MAIN_TEMP_DIR = "temp_app"
MAIN_OUTPUT_DIR = "output_app"
STOP_HOTKEY = "ctrl+1"
LOG_LEVEL = logging.INFO
NIKKE_PROCESS_NAME = "nikke.exe" # 假设 find_and_activate_window 使用此默认值

# --- AppContext 定义 ---
class SharedResources:
    def __init__(self):
        self.nikke_window = None
        self.constants = core_constants
        self.base_temp_dir = MAIN_TEMP_DIR       # 将由 app.py 初始化为绝对路径
        self.base_output_dir = MAIN_OUTPUT_DIR   # 将由 app.py 初始化为绝对路径
        self.stop_requested = False
        self.logger = logging.getLogger("AppLogger")
        self.app_config = None # 新增：持有解析后的完整 config.json 内容
        self.final_message = None # 用于模式执行后传递总结信息
        self.is_admin = False # GUI适配：添加is_admin属性
        self.available_modes = [] # GUI适配：存储从config.json加载的模式元数据

    def get_stitch_background_color(self):
        """
        从应用配置中获取并解析图像拼接的背景颜色。
        颜色在 config.json 的 global_settings.default_stitch_background_color 中定义为 "R,G,B" 字符串。
        如果未配置或格式错误，则返回默认颜色 (0,0,0)。
        """
        color_str = "0,0,0" # 默认值
        if self.app_config and 'global_settings' in self.app_config:
            color_str = self.app_config['global_settings'].get('default_stitch_background_color', "0,0,0")
        
        try:
            # 将 "R,G,B" 字符串转换为 (R, G, B) 元组
            color_tuple = tuple(map(int, color_str.split(',')))
            if len(color_tuple) == 3:
                return color_tuple
            else:
                self.logger.warning(f"背景颜色配置 '{color_str}' 格式不正确 (应为 R,G,B)，将使用默认颜色 (0,0,0)。")
                return (0,0,0)
        except ValueError:
            self.logger.warning(f"背景颜色配置 '{color_str}' 值无效 (无法转换为整数)，将使用默认颜色 (0,0,0)。")
            return (0,0,0)
        except Exception as e:
            self.logger.error(f"解析背景颜色时发生未知错误: {e}。配置: '{color_str}'。将使用默认颜色 (0,0,0)。")
            return (0,0,0)

class ModeSpecificConfig:
    def _load_mode1_config(self, mode_defaults):
        self.m1_output_suffix = mode_defaults.get('output_filename_suffix', '_prediction')
        self.m1_player1_name = mode_defaults.get('player1_name', 'P1')
        self.m1_player2_name = mode_defaults.get('player2_name', 'P2')

    def _load_mode2_config(self, mode_defaults):
        self.m2_output_suffix = mode_defaults.get('output_filename_suffix', '_review')
        self.m2_include_result = mode_defaults.get('include_result_image', True)
        self.m2_result_pos = mode_defaults.get('result_image_position', 'center')

    def _load_mode3_config(self, mode_defaults):
        self.m3_output_suffix = mode_defaults.get('output_filename_suffix', '_reverse')
        self.m3_include_vote = mode_defaults.get('include_vote_image', True)

    def _load_mode4_config(self, mode_defaults):
        default_suffix = '_64in8'
        self.m45_output_suffix = mode_defaults.get('output_filename_suffix', default_suffix)
        self.m45_num_players = mode_defaults.get('num_players', 8)
        self.m45_gen_overview = mode_defaults.get('generate_overview_image', True)
        self.m45_overview_rows = mode_defaults.get('overview_layout_rows', 2)
        self.m45_overview_cols = mode_defaults.get('overview_layout_cols', 4)
        self.m45_save_individual = mode_defaults.get('save_individual_images', False)

    def _load_mode5_config(self, mode_defaults):
        default_suffix = '_champ_pred'
        self.m45_output_suffix = mode_defaults.get('output_filename_suffix', default_suffix)
        self.m45_num_players = mode_defaults.get('num_players', 8) # 通常模式5也是8个? 或根据游戏调整
        self.m45_gen_overview = mode_defaults.get('generate_overview_image', True)
        self.m45_overview_rows = mode_defaults.get('overview_layout_rows', 2)
        self.m45_overview_cols = mode_defaults.get('overview_layout_cols', 4)
        self.m45_save_individual = mode_defaults.get('save_individual_images', False)

    def _load_mode6_config(self, mode_defaults):
        self.m6_group_prefix = mode_defaults.get('output_group_prefix', 'Group')
        self.m6_start_group = mode_defaults.get('start_group_index', 0)
        self.m6_end_group = mode_defaults.get('end_group_index', 7)

    def _load_mode7_config(self, mode_defaults):
        self.m7_group_prefix = mode_defaults.get('output_group_prefix', 'Group')
        self.m7_target_group = mode_defaults.get('target_group_index', 0) # app.py 会提示用户输入

    def _load_mode8_config(self, mode_defaults):
        self.m8_file_prefix = mode_defaults.get('file_prefix', 'champion_tournament') # 新增 file_prefix 加载
        self.m8_output_suffix = mode_defaults.get('output_filename_suffix', '_champ_matches')

    def _load_mode9_config(self, mode_defaults):
        self.m9_input_dir_relative = mode_defaults.get('input_dir_relative_to_main_output', True)
        self.m9_input_subdir = mode_defaults.get('input_subdir', '')
        self.m9_output_webp_subdir = mode_defaults.get('output_webp_subdir', 'm9_webp')
        self.m9_zip_filename = mode_defaults.get('zip_filename', 'mode9_archive.zip')
        self.m9_webp_quality = mode_defaults.get('webp_quality', 85)
        self.m9_webp_lossless = mode_defaults.get('webp_lossless', False) # 新增 webp_lossless 加载
        self.m9_del_orig_after_webp = mode_defaults.get('delete_originals_after_webp', False)
        self.m9_del_webp_after_zip = mode_defaults.get('delete_webp_after_zip', True)
        self.m9_configured_absolute_input_dir = mode_defaults.get('m9_configured_absolute_input_dir', None) # 新增配置项
        # 实际路径属性在 __init__ 中初始化为 None
        self.m9_actual_input_dir = None
        self.m9_actual_output_webp_dir = None
        self.m9_actual_zip_filepath = None

    def __init__(self, mode_number=None, app_config=None):
        # 通用配置项
        gs_defaults = app_config.get('global_settings', {}) if app_config else {}
        self.output_filename_prefix = gs_defaults.get('default_output_filename_prefix', 'NCA')
        self.temp_file_prefix = gs_defaults.get('default_temp_file_prefix', 'temp_')
        self.delete_temp_files_after_run = gs_defaults.get('default_delete_temp_files_after_run', True)
        self.image_spacing = gs_defaults.get('default_image_spacing', 20)
        self.stitch_background_color_str = gs_defaults.get('default_stitch_background_color', "0,0,0") # 新增背景颜色配置 (字符串形式)

        mode_loaders = {
            1: self._load_mode1_config,
            2: self._load_mode2_config,
            3: self._load_mode3_config,
            4: self._load_mode4_config,
            5: self._load_mode5_config,
            6: self._load_mode6_config,
            7: self._load_mode7_config,
            8: self._load_mode8_config,
            9: self._load_mode9_config,
        }

        if mode_number and app_config:
            mode_defaults = app_config.get('mode_specific_defaults', {}).get(f'mode{mode_number}', {})
            loader = mode_loaders.get(mode_number)
            if loader:
                loader(mode_defaults)
            # else: mode_number is None or invalid, or no specific config for it. Common attrs are set.

    def finalize_paths_for_mode9(self, base_output_dir, logger):
        # base_temp_dir is not used in the original logic from app.py for these paths
        # logger is needed for error messages if input is invalid
        success = True # Flag to indicate if path setup was successful
        # base_temp_dir is not used in the original logic from app.py for these paths
        # logger is needed for error messages if input is invalid
        success = True # Flag to indicate if path setup was successful
        if self.m9_input_dir_relative:
            if self.m9_input_subdir:
                self.m9_actual_input_dir = os.path.join(base_output_dir, self.m9_input_subdir)
            else:
                self.m9_actual_input_dir = base_output_dir
        else:
            # 如果不是相对路径，则优先尝试从配置的绝对路径读取
            configured_abs_dir = self.m9_configured_absolute_input_dir
            if configured_abs_dir and os.path.isdir(configured_abs_dir):
                logger.info(f"模式9: 使用配置文件中指定的绝对输入路径: '{configured_abs_dir}'")
                self.m9_actual_input_dir = configured_abs_dir
            else:
                if configured_abs_dir: # 配置了但路径无效
                    logger.warning(f"模式9: 配置文件中的绝对输入路径 '{configured_abs_dir}' 无效或不是一个目录。")
                
                # 提示用户输入绝对路径
                user_input_abs_dir = input(f"模式9配置为使用绝对输入路径。请输入完整输入目录路径: ").strip()
                if not user_input_abs_dir or not os.path.isdir(user_input_abs_dir):
                    logger.error(f"模式9的用户输入绝对路径无效或未提供: '{user_input_abs_dir}'。")
                    self.m9_actual_input_dir = None # 明确设为 None
                    success = False
                else:
                    self.m9_actual_input_dir = user_input_abs_dir
        
        if success: # 只有在输入路径有效时才继续设置其他路径
            self.m9_actual_output_webp_dir = os.path.join(base_output_dir, self.m9_output_webp_subdir)
            self.m9_actual_zip_filepath = os.path.join(base_output_dir, self.m9_zip_filename)
        else: # 如果输入路径无效，其他路径也应设为 None 或保持未设置状态
            self.m9_actual_output_webp_dir = None
            self.m9_actual_zip_filepath = None
            
        return success

def load_app_config(logger):
    config_filepath = "config.json"
    default_config = { # 硬编码的后备默认值
        "global_settings": {"default_output_filename_prefix": "FallbackNCA"},
        "mode_specific_defaults": {}
    }
    try:
        if os.path.exists(config_filepath):
            with open(config_filepath, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                logger.info(f"成功从 '{config_filepath}' 加载应用配置。")
                return config_data
        else:
            logger.warning(f"配置文件 '{config_filepath}' 未找到。")
            try:
                with open(config_filepath, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                logger.info(f"已在 '{os.path.abspath(config_filepath)}' 创建默认配置文件。建议查看并根据需要修改。")
                # 即使创建成功，第一次运行时也返回 default_config，
                # 或者可以选择再次读取刚创建的文件 (return load_app_config(logger))
                # 为简单起见，此处返回内存中的默认配置，下次启动时将加载文件。
                return default_config
            except Exception as e_create:
                logger.error(f"创建默认配置文件 '{config_filepath}' 失败: {e_create}。将使用内部硬编码的默认配置。")
                return default_config
    except json.JSONDecodeError:
        logger.error(f"解析配置文件 '{config_filepath}' 失败。请检查JSON格式。将使用内部默认配置。")
        return default_config
    except Exception as e:
        logger.error(f"加载配置文件时发生错误: {e}。将使用内部默认配置。")
        return default_config

class AppContext:
    def __init__(self, mode_number=None, app_config_data=None): # mode_number 和 app_config_data 用于初始化 ModeSpecificConfig
        self.shared = SharedResources()
        # 将 app_config_data 存入 shared，以便 ModeSpecificConfig 和其他地方访问
        self.shared.app_config = app_config_data
        self.mode_config = ModeSpecificConfig(mode_number=mode_number, app_config=app_config_data)

# --- 核心业务逻辑函数 ---
def initialize_app_context(logger):
    """
    创建并初始化 AppContext。
    - 加载应用配置。
    - 创建 AppContext 实例。
    - 设置共享资源的基本路径和 logger。
    - 加载模式元数据。
    """
    logger.info("Initializing AppContext...")
    app_config_data = load_app_config(logger)
    logger.debug(f"DEBUG app.py: Loaded app_config_data, modes_meta content: {app_config_data.get('modes_meta')}")

    # AppContext 初始化时传入 app_config_data，但不传入 mode_number
    # mode_config 将在用户选择模式后，根据选定模式再具体化
    context = AppContext(app_config_data=app_config_data)
    context.shared.logger = logger  # 确保 context 使用的是主程序创建的 logger
    context.shared.constants = core_constants
    context.shared.base_temp_dir = os.path.abspath(MAIN_TEMP_DIR)
    context.shared.base_output_dir = os.path.abspath(MAIN_OUTPUT_DIR)

    # GUI适配：加载模式元数据
    if app_config_data and isinstance(app_config_data.get("modes_meta"), list):
        raw_modes_meta = app_config_data["modes_meta"]
        valid_modes = []
        for mode_meta in raw_modes_meta:
            if isinstance(mode_meta, dict) and \
               'id' in mode_meta and isinstance(mode_meta['id'], int) and \
               'name' in mode_meta and isinstance(mode_meta['name'], str) and \
               'desc' in mode_meta and isinstance(mode_meta['desc'], str):
                # enabled 和 asset_image 是可选的，但如果存在，最好也检查类型
                if 'enabled' in mode_meta and not isinstance(mode_meta['enabled'], bool):
                    logger.warning(f"模式元数据条目 {mode_meta.get('id', 'N/A')} 的 'enabled' 字段类型无效，应为布尔型。已跳过此条目。")
                    continue
                if 'asset_image' in mode_meta and not isinstance(mode_meta['asset_image'], str):
                    logger.warning(f"模式元数据条目 {mode_meta.get('id', 'N/A')} 的 'asset_image' 字段类型无效，应为字符串。已跳过此条目。")
                    continue
                valid_modes.append(mode_meta)
            else:
                logger.warning(f"在 config.json 的 'modes_meta' 中发现无效或不完整的模式条目: {mode_meta}。已跳过。")
        
        context.shared.available_modes = valid_modes
        logger.debug(f"DEBUG app.py: Valid modes after validation loop: {valid_modes}")
        logger.debug(f"DEBUG app.py: context.shared.available_modes finally set to: {context.shared.available_modes}")
        if valid_modes:
            logger.info(f"成功加载并验证了 {len(valid_modes)} 个模式的元数据。")
        elif raw_modes_meta: # 原始列表不为空但验证后为空
             logger.warning("config.json 中的 'modes_meta' 列表不包含任何有效的模式定义。")
        # else: raw_modes_meta 为空或不存在，下面会处理
            
    if not hasattr(context.shared, 'available_modes') or not context.shared.available_modes: # 再次检查，以防上面逻辑未赋值或赋值为空
        logger.warning("未能从 config.json 加载有效的模式元数据 ('modes_meta' 未找到、为空或所有条目均无效)。GUI模式列表可能为空。")
        context.shared.available_modes = [] # 确保属性存在且为空列表

    logger.info("AppContext initialized with basic settings and mode metadata.")
    return context

def setup_app_environment(context: AppContext):
    """
    设置应用运行环境。
    - 创建应用目录。
    - 查找并激活 NIKKE 窗口。
    - 设置全局热键。
    - 检查管理员权限并设置到context。
    返回:
        bool: True 如果 NIKKE 窗口成功找到并激活，否则 False。
    """
    logger = context.shared.logger
    logger.info("Setting up app environment...")

    # 0. 检查并设置管理员权限 (在其他操作之前，因为某些操作可能需要)
    context.shared.is_admin = is_admin() # GUI适配：设置is_admin状态
    if sys.platform == 'win32' and not context.shared.is_admin:
        logger.warning("当前用户非管理员。部分功能（如窗口激活、全局热键）可能受限或失败。")
    else:
        logger.info(f"管理员权限状态: {context.shared.is_admin}")

    # 1. 创建应用目录
    try:
        create_app_directories(logger)
    except Exception as e:
        logger.error(f"Failed to create app directories during environment setup: {e}")
        # 根据 GUI 计划，这里应该能让调用者知道失败了
        # 对于命令行版本，main 函数会处理异常并退出
        raise # 重新抛出，让 main 处理或 GUI 捕获

    # 2. 检查 core_utils 并查找激活 NIKKE 窗口
    if not core_utils or not hasattr(core_utils, 'find_and_activate_window'):
        logger.critical("Core utilities (core.utils) or find_and_activate_window function is missing.")
        # 此处错误比较严重，命令行版本会在 main 中提示并退出
        # GUI 版本需要能获取这个状态
        return False # 表示环境设置失败

    logger.info(f"Attempting to find and activate '{NIKKE_PROCESS_NAME}' window...")
    # 修改调用以匹配新的 find_and_activate_window 签名
    nikke_window = core_utils.find_and_activate_window(context)
    if nikke_window:
        context.shared.nikke_window = nikke_window
        logger.info(f"Successfully obtained NIKKE window: {nikke_window.title}")
    else:
        logger.error(f"Failed to find or activate '{NIKKE_PROCESS_NAME}' window. Ensure the game is running and visible.")
        # GUI 需要知道这个结果
        return False # 表示窗口未找到

    # 3. 设置全局热键
    setup_global_hotkeys(context, logger)
    
    logger.info("App environment setup complete.")
    return True # 环境设置成功（窗口也找到了）

def execute_mode(context: AppContext, mode_number: int, mode_specific_inputs: dict = None):
    """
    执行指定的模式。
    - 加载模式特定配置。
    - 处理模式特定输入 (如果 mode_specific_inputs 未提供，则可能退化为命令行输入)。
    - 导入并运行模式模块。
    - 处理 final_message。
    """
    logger = context.shared.logger
    logger.info(f"Executing mode {mode_number}...")
    context.shared.stop_requested = False # 重置停止请求标志，确保每个模式开始时都是可运行的
    context.shared.final_message = None # 重置 final_message

    # 1. 根据选定模式，重新初始化/更新 context.mode_config
    context.mode_config = ModeSpecificConfig(mode_number=mode_number, app_config=context.shared.app_config)
    logger.info(f"Loaded specific configuration for mode {mode_number}.")

    # 2. 特定模式的用户输入和路径处理
    # GUI 版本将通过 mode_specific_inputs 传递这些值
    # 命令行版本将在此处提示输入
    if mode_number == 7:
        target_group_idx = context.mode_config.m7_target_group # 默认值
        if mode_specific_inputs and 'target_group_index' in mode_specific_inputs:
            target_group_idx = mode_specific_inputs['target_group_index']
            logger.info(f"Mode 7: Using target_group_index from inputs: {target_group_idx}")
        else: # 命令行回退或默认
            try:
                val_str = input(f"请输入目标分组索引 (0-7, 默认为 {target_group_idx}): ").strip()
                if val_str: # 仅当用户输入了内容时才尝试转换
                    val_int = int(val_str)
                    if not (0 <= val_int <= 7):
                        raise ValueError("索引超出范围，请输入0-7之间的数字。")
                    target_group_idx = val_int
            except ValueError as ve:
                logger.warning(f"无效输入或未输入，将使用默认/已配置的目标分组索引 {target_group_idx}: {ve}")
        context.mode_config.m7_target_group = target_group_idx
        logger.info(f"Mode 7: Target group index set to {context.mode_config.m7_target_group}.")

    elif mode_number == 9:
        # 模式9的路径最终确定逻辑
        # GUI 版本可能需要预先收集 m9_configured_absolute_input_dir (如果 m9_input_dir_relative=False)
        # 或者，如果 GUI 总是提供绝对路径，则这里的逻辑需要调整
        # 当前假设 mode_specific_inputs 可能包含 'm9_actual_input_dir'
        if mode_specific_inputs and 'm9_actual_input_dir' in mode_specific_inputs:
            # 如果 GUI 直接提供了最终的 m9_actual_input_dir
            context.mode_config.m9_actual_input_dir = mode_specific_inputs['m9_actual_input_dir']
            # 还需要设置其他相关路径
            context.mode_config.m9_actual_output_webp_dir = os.path.join(context.shared.base_output_dir, context.mode_config.m9_output_webp_subdir)
            context.mode_config.m9_actual_zip_filepath = os.path.join(context.shared.base_output_dir, context.mode_config.m9_zip_filename)
            logger.info(f"Mode 9: Using actual_input_dir from inputs: {context.mode_config.m9_actual_input_dir}")
            if not os.path.isdir(context.mode_config.m9_actual_input_dir):
                logger.error(f"Mode 9: Provided actual_input_dir '{context.mode_config.m9_actual_input_dir}' is not a valid directory.")
                return # 无法继续
        else:
            # 命令行回退或基于 config.json 的配置
            if not context.mode_config.finalize_paths_for_mode9(context.shared.base_output_dir, logger):
                logger.error(f"Mode 9 path initialization failed. Aborting mode 9.")
                return # 无法继续

        logger.info(f"Mode 9 Input directory: {getattr(context.mode_config, 'm9_actual_input_dir', 'Not set')}")
        logger.info(f"Mode 9 WebP output directory: {getattr(context.mode_config, 'm9_actual_output_webp_dir', 'Not set')}")
        logger.info(f"Mode 9 ZIP file path: {getattr(context.mode_config, 'm9_actual_zip_filepath', 'Not set')}")
        
        if context.mode_config.m9_actual_output_webp_dir:
            os.makedirs(context.mode_config.m9_actual_output_webp_dir, exist_ok=True)
        elif context.mode_config.m9_actual_input_dir: # 确保如果输入有效但输出目录创建失败，也应记录
             logger.warning("Mode 9: WebP output directory is not set, cannot create it.")


    # 3. 模式调度
    module_name = f"modes.mode{mode_number}"
    try:
        mode_module = importlib.import_module(module_name)
        if hasattr(mode_module, 'run'):
            logger.info(f"Starting execution of mode {mode_number} ({module_name})...")
            mode_module.run(context) # 传递更新后的 context
            logger.info(f"Mode {mode_number} execution finished.")
            
            # 检查并处理 final_message
            if context.shared.final_message:
                logger.info(f"Mode {mode_number} summary: {context.shared.final_message}")
                # 在命令行版本中，可以直接打印
                # GUI 版本会从 context.shared.final_message 中读取
                print(f"\n--- Mode {mode_number} Result ---")
                print(context.shared.final_message)
                print("--------------------")
                # GUI 可能希望保留 final_message 直到下一次执行，或由 GUI 清理
                # 此处暂时不清空，以便 GUI 读取
            else:
                logger.info(f"Mode {mode_number} did not provide a final_message.")
        else:
            logger.error(f"Mode module {module_name} does not have a run function.")
    except ImportError:
        logger.error(f"Could not import mode module {module_name}. Ensure 'modes/mode{mode_number}.py' exists and is correct.")
    except Exception as mode_exc:
        logger.exception(f"An error occurred while executing mode {mode_number} ({module_name}): {mode_exc}")

# --- 辅助函数 ---
def is_admin():
    if sys.platform == 'win32':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    return True # 非 Windows 平台假定有足够权限

def setup_logging():
    """配置日志系统"""
    logger = logging.getLogger("AppLogger")
    logger.setLevel(LOG_LEVEL)
    # 清除已存在的 handlers，防止重复添加
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    
    # 控制台输出
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(LOG_LEVEL)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # 可选：文件输出 (如果需要)
    # log_file_path = os.path.join(MAIN_OUTPUT_DIR, "app.log")
    # fh = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    # fh.setLevel(LOG_LEVEL)
    # fh.setFormatter(formatter)
    # logger.addHandler(fh)
    
    logger.info(f"{APP_NAME} v{APP_VERSION} 日志系统初始化完成。")

def create_app_directories(logger):
    """创建应用所需的主临时目录和输出目录"""
    try:
        os.makedirs(MAIN_TEMP_DIR, exist_ok=True)
        logger.info(f"确保临时目录 '{os.path.abspath(MAIN_TEMP_DIR)}' 已创建。")
        os.makedirs(MAIN_OUTPUT_DIR, exist_ok=True)
        logger.info(f"确保输出目录 '{os.path.abspath(MAIN_OUTPUT_DIR)}' 已创建。")
    except OSError as e:
        logger.error(f"创建应用目录失败: {e}")
        raise # 重新抛出异常，让主程序处理

def stop_script_callback(context_ref: AppContext):
    """热键回调，设置停止标志"""
    if not context_ref.shared.stop_requested:
        context_ref.shared.stop_requested = True
        context_ref.shared.logger.warning(f"检测到停止热键 ({STOP_HOTKEY})！请求停止当前操作...")

def setup_global_hotkeys(context: AppContext, logger):
    """设置全局热键"""
    try:
        # 使用 lambda 确保传递当前的 context 实例
        keyboard.add_hotkey(STOP_HOTKEY, lambda: stop_script_callback(context))
        logger.info(f"全局停止热键 '{STOP_HOTKEY}' 已设置。在模式运行时按下可请求停止。")
    except Exception as e:
        logger.error(f"设置全局热键失败: {e}")
        logger.warning("脚本将无法通过热键停止。")

def cleanup_application(logger):
    """应用退出前的清理工作"""
    logger.info("开始应用清理...")
    try:
        keyboard.remove_all_hotkeys()
        logger.info("已移除所有全局热key。")
    except Exception as e:
        logger.warning(f"移除热键时发生错误: {e}")

    # 可选：清理临时目录 (根据需求决定是否默认清理)
    try:
        if os.path.exists(MAIN_TEMP_DIR):
            shutil.rmtree(MAIN_TEMP_DIR)
            logger.info(f"主临时目录 '{MAIN_TEMP_DIR}' 已清理。")
    except Exception as e:
        logger.error(f"清理主临时目录 '{MAIN_TEMP_DIR}' 失败: {e}")
    logger.info("应用清理完成。")

# --- 主应用逻辑 ---
def main():
    # 1. 初始化日志 (尽早进行)
    # setup_logging() 应该在 AppContext 创建之前被调用，
    # 并且 AppContext.shared.logger 应该被设置为这个 logger 实例。
    # 或者，AppContext 初始化时创建自己的 logger，然后 setup_logging 配置它。
    # 根据计划，AppContext 初始化时会获得 logger。
    
    # 临时性的早期日志，直到 context.shared.logger 可用
    temp_logger = logging.getLogger("PreInitLogger")
    temp_logger.addHandler(logging.StreamHandler(sys.stdout)) # 简单输出到控制台
    temp_logger.setLevel(logging.INFO)

    # 实际的日志配置由 setup_logging 完成，它会配置 AppLogger
    setup_logging() # 配置 AppLogger
    logger = logging.getLogger("AppLogger") # 获取已配置的 logger
    logger.info(f"正在启动 {APP_NAME} v{APP_VERSION}...")

    # 2. 检查管理员权限 (Windows)
    if sys.platform == 'win32' and not is_admin():
        logger.error("错误：此脚本需要管理员权限才能在 Windows 上正常运行。")
        ctypes.windll.user32.MessageBoxW(None, "请以管理员身份运行此脚本。", "权限不足", 0x10 | 0x1000)
        return

    context = None
    try:
        # 3. 初始化 AppContext
        context = initialize_app_context(logger)
        # logger 现在是 context.shared.logger，后续可以直接使用 context.shared.logger
        context.shared.logger.info("应用上下文核心初始化完成。")

        # 4. 设置应用环境 (包括目录创建、窗口激活、热键)
        if not setup_app_environment(context):
            # setup_app_environment 内部会记录具体错误
            # 对于命令行版本，如果窗口查找失败，会提示并退出
            context.shared.logger.error("应用环境设置失败 (例如，未能找到 NIKKE 窗口)。程序将退出。")
            if not context.shared.nikke_window : # 更具体的检查
                 ctypes.windll.user32.MessageBoxW(None, f"未能找到或激活 '{NIKKE_PROCESS_NAME}' 窗口。\n请确保游戏正在运行且可见。", "错误", 0x10 | 0x1000)
            # 如果是其他环境设置问题，例如 core.utils 加载失败，setup_app_environment 返回 False
            elif not core_utils or not hasattr(core_utils, 'find_and_activate_window'):
                 ctypes.windll.user32.MessageBoxW(
                    None,
                    "核心工具模块加载失败。\n\n"
                    "应用无法正常激活游戏窗口，后续功能将受限。\n"
                    "请检查日志获取详细信息，并确认 core/utils.py 文件完好。\n\n"
                    "程序即将退出。",
                    f"{APP_NAME} - 严重错误",
                    0x10 | 0x1000
                )
            return # 退出主函数

        context.shared.logger.info("应用环境设置成功。")

        # 5. 用户模式选择循环 (命令行界面)
        while True: # 主循环由内部的 stop_requested 或 break 控制
            if context.shared.stop_requested: # 检查是否由热键或其他方式请求停止整个应用
                context.shared.logger.info("主循环检测到应用停止请求。")
                break

            print("\n" + "="*30)
            print(f"欢迎使用 {APP_NAME}!")
            print("请选择要运行的模式:")
            print("  1: 买马预测")
            print("  2: 复盘模式")
            print("  3: 反买存档")
            print("  4: 64进8")
            print("  5: 冠军争霸预测")
            print("  6: Reviewer 完整分组赛")
            print("  7: Reviewer 单组分组赛")
            print("  8: Reviewer 冠军赛截图")
            print("  9: 图片处理与打包")
            print("  0: 退出程序")
            print("="*30)

            try:
                choice = input("请输入模式编号 (0-9): ").strip()
                if not choice: continue

                selected_mode_num = int(choice)

                if selected_mode_num == 0:
                    context.shared.logger.info("用户选择退出程序。")
                    break # 退出模式选择循环

                if 1 <= selected_mode_num <= 9:
                    context.shared.logger.info(f"用户选择了模式 {selected_mode_num}。")
                    # 对于命令行版本，mode_specific_inputs 通常为 None 或空字典，
                    # execute_mode 内部会处理 input() 获取。
                    # GUI 版本会填充 mode_specific_inputs。
                    execute_mode(context, selected_mode_num, mode_specific_inputs=None)
                    
                    # 检查在 execute_mode 内部是否通过热键请求了停止
                    if context.shared.stop_requested:
                        context.shared.logger.info(f"模式 {selected_mode_num} 执行期间检测到停止请求。返回主菜单。")
                        # execute_mode 开始时会重置 stop_requested，这里不需要再次重置为 False
                        # continue 会回到主循环顶部，再次检查全局 stop_requested
                        continue
                else:
                    context.shared.logger.warning(f"无效的模式编号: {selected_mode_num}。请输入0-9之间的数字。")

            except ValueError:
                context.shared.logger.warning("输入无效，请输入数字。")
            except KeyboardInterrupt:
                context.shared.logger.info("\n检测到用户中断 (Ctrl+C)。正在退出...")
                context.shared.stop_requested = True # 确保 finally 会执行清理
                break # 退出模式选择循环
            except Exception as e:
                context.shared.logger.exception(f"主模式选择循环中发生未预料的错误: {e}")
                # 可以选择继续循环或中断
                # break # 或者让用户重试

    except Exception as e:
        # 捕获 initialize_app_context 或 setup_app_environment 中可能抛出的未处理异常
        if context and hasattr(context, 'shared') and context.shared.logger: # 尝试使用已有的 logger
            context.shared.logger.exception(f"应用程序在初始化或环境设置阶段发生严重错误: {e}")
        else: # 如果 logger 自身初始化失败
            # 使用最初获取的 logger 实例，如果 context.shared.logger 不可用
            logger.exception(f"应用程序在初始化或环境设置阶段发生严重错误 (logger 可能未完全配置): {e}")
            print(f"应用程序发生严重错误: {e}", file=sys.stderr) # Fallback
        
        # 尝试显示消息框
        try:
            ctypes.windll.user32.MessageBoxW(None, f"应用程序发生严重错误，请查看日志。\n错误详情: {str(e)[:200]}...", f"{APP_NAME} - 严重错误", 0x10 | 0x1000)
        except Exception as mb_e:
            # 如果 context.shared.logger 可用，用它记录；否则用最初的 logger
            log_ref = context.shared.logger if context and hasattr(context, 'shared') and context.shared.logger else logger
            log_ref.error(f"显示错误消息框也失败了: {mb_e}")
            
    finally:
        # 确保使用一个有效的 logger 进行清理日志记录
        final_logger = None
        if context and hasattr(context, 'shared') and context.shared.logger:
            final_logger = context.shared.logger
        elif 'logger' in locals() and logger: # 'logger' 是 main 函数开始时定义的
            final_logger = logger
        
        if final_logger:
            cleanup_application(final_logger)
            final_logger.info(f"{APP_NAME} 已关闭。")
        else:
            # 如果 context 或其 logger 未能成功初始化，并且最初的 logger 也不可用
            print(f"{APP_NAME} 已关闭 (可能在早期初始化阶段失败，且无法访问 logger)。")


if __name__ == "__main__":
    main()
