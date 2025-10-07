# core/file_utils.py
import os
import sys
import time
import logging
import zipfile


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


def check_stop_signal(context):
    """检查是否收到了停止信号，如果收到则记录并返回 True，否则返回 False。"""
    if hasattr(context, 'shared') and hasattr(context.shared, 'stop_requested') and context.shared.stop_requested:
        if hasattr(context, 'shared') and hasattr(context.shared, 'logger'):
            context.shared.logger.warning("检测到停止信号。")
        else:
            logging.warning("检测到停止信号 (context.shared.logger 不可用)。")
        return True
    return False


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


def get_base_path():
   """ 获取应用程序的基础路径，用于查找资源文件。"""
   if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
       # PyInstaller one-file bundle in temporary _MEIPASS directory
       # For data files placed next to the executable (like in one-dir),
       # we need the directory of the executable itself.
       return os.path.dirname(sys.executable)
   elif getattr(sys, 'frozen', False):
       # PyInstaller one-dir bundle or other frozen environment
       return os.path.dirname(sys.executable)
   else:
       # Running as a standard Python script
       # Running as a standard Python script
       # __file__ is core/utils.py, so dirname is core/. We need its parent.
       return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))