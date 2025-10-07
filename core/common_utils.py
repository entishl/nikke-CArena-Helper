# core/common_utils.py
import logging


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