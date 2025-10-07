import threading
import time
import logging
import os
from customtkinter import filedialog
from app import execute_mode, setup_app_environment
from core.automation_utils import activate_nikke_window_if_needed


class ScriptRunner:
    """脚本运行管理器"""

    def __init__(self, app_context, on_script_finished):
        self.app_context = app_context
        self.on_script_finished = on_script_finished

        self.script_thread = None
        self.stop_event = threading.Event()

    def is_running(self):
        """检查脚本是否正在运行"""
        return self.script_thread and self.script_thread.is_alive()

    def start_script(self, mode_value, mode_specific_inputs):
        """启动脚本执行"""
        self.script_thread = threading.Thread(
            target=self.execute_script_thread,
            args=(mode_value, mode_specific_inputs),
            daemon=True
        )
        self.script_thread.start()

    def execute_script_thread(self, mode_value, mode_specific_inputs):
        """脚本执行线程"""
        logger = self._get_logger()
        status = 'unknown'
        final_message_or_error = "脚本执行完毕，但状态未知。"

        try:
            # 首先确保窗口已连接
            if not (hasattr(self.app_context.shared, 'nikke_window') and self.app_context.shared.nikke_window):
                # 需要检查窗口状态，但这需要主应用的方法
                # 这里我们假设主应用会传递检查结果
                logger.error("无法执行脚本：NIKKE 窗口未连接。")
                status = 'error'
                final_message_or_error = "NIKKE 窗口连接失败"
                self._notify_script_finished(status, final_message_or_error)
                return

            # 如果不是模式9，尝试激活窗口
            if mode_value != 9:
                logger.info(f"模式 {mode_value} 即将执行，尝试激活 NIKKE 窗口...")
                if hasattr(self.app_context, 'shared') and self.app_context.shared.nikke_window:
                    if activate_nikke_window_if_needed(self.app_context):
                        logger.info("NIKKE 窗口已成功激活或已处于前台。")
                    else:
                        logger.warning("尝试激活 NIKKE 窗口失败或窗口未处于前台。脚本仍将继续执行。")
                else:
                    logger.warning("无法激活窗口：app_context.shared.nikke_window 不存在。")

            # 等待启动延迟
            gui_startup_delay = self.app_context.shared.delay_config.get('gui_startup', 5.0)
            logger.info(f"准备执行模式 {mode_value}，等待 {gui_startup_delay} 秒...")
            time.sleep(gui_startup_delay)
            logger.info("等待结束，开始执行模式。")

            # 执行模式
            execute_mode(self.app_context, mode_value, mode_specific_inputs)
            status = 'success'
            final_message_or_error = getattr(self.app_context.shared, 'final_message', "脚本执行完成。")

        except Exception as e:
            logger.exception("脚本执行过程中发生错误:")
            status = 'error'
            final_message_or_error = f"{str(e)[:100]}"

        finally:
            # 检查是否是用户请求停止
            if self.app_context and hasattr(self.app_context, 'shared') and self.app_context.shared.stop_requested:
                status = 'stopped'
                final_message_or_error = "脚本已由用户停止。"

            # 通知主线程脚本已完成
            self._notify_script_finished(status, final_message_or_error)

    def _notify_script_finished(self, status, message):
        """通知主线程脚本已完成"""
        # 这里需要通过回调函数通知主线程
        if self.on_script_finished:
            self.on_script_finished(status, message)

    def stop_script(self):
        """停止脚本执行"""
        logger = self._get_logger()
        if self.app_context and hasattr(self.app_context, 'shared'):
            self.app_context.shared.stop_requested = True
            if logger:
                logger.info("用户请求停止脚本...")
        self.stop_event.set()

    def set_stop_flag(self):
        """设置停止标志"""
        self.stop_event.set()

    def reset_stop_flag(self):
        """重置停止标志"""
        self.stop_event.clear()
        if self.app_context and hasattr(self.app_context, 'shared'):
            self.app_context.shared.stop_requested = False

    def prompt_for_mode9_input_directory(self):
        """提示用户选择模式9的输入目录"""
        logger = self._get_logger()

        if not (self.app_context and hasattr(self.app_context, 'shared') and self.app_context.shared.logger):
            temp_logger = logging.getLogger("GuiPromptLogger")
            temp_logger.warning("尝试提示模式9输入目录，但应用上下文或日志记录器不可用。")

        logger = self._get_logger()

        directory = filedialog.askdirectory(
            title="模式9 输入选择",
            initialdir=os.path.abspath(getattr(getattr(self.app_context, 'shared', None), 'base_output_dir', '.')),
            mustexist=True
        )
        if directory:
            logger.info(f"模式9输入目录已选择: {directory}")
            return directory
        else:
            logger.warning("模式9输入目录未选择。")
            return None

    def _get_logger(self):
        """获取日志记录器"""
        if self.app_context and hasattr(self.app_context, 'shared') and self.app_context.shared.logger:
            return self.app_context.shared.logger
        return logging.getLogger("ScriptRunnerLogger")


class CompletionPopupManager:
    """完成弹窗管理器"""

    @staticmethod
    def show_completion_popup(status, message, app_context=None):
        """根据脚本执行状态显示不同的弹窗"""
        import ctypes

        popup_title = "提示"
        popup_text = ""
        icon_flag = 0x00000000  # MB_OK

        if status == 'success':
            popup_text = "任务完成！"
            icon_flag |= 0x00000040  # MB_ICONINFORMATION
        elif status == 'error':
            popup_text = f"脚本执行出错:\n\n{message}"
            icon_flag |= 0x00000010  # MB_ICONERROR
        elif status == 'stopped':
            popup_text = "脚本已由用户停止。"
            icon_flag |= 0x00000030  # MB_ICONWARNING
        else:  # unknown or other status
            popup_text = f"脚本执行完毕，但状态未知。\n\n消息: {message}"
            icon_flag |= 0x00000030  # MB_ICONWARNING

        # 添加 MB_TOPMOST 标志，确保弹窗总在最前
        icon_flag |= 0x00040000  # MB_TOPMOST

        # 使用 ctypes 显示 Windows 消息框
        try:
            ctypes.windll.user32.MessageBoxW(0, popup_text, popup_title, icon_flag)
        except Exception as e:
            logger = None
            if app_context and hasattr(app_context, 'shared') and app_context.shared.logger:
                logger = app_context.shared.logger
            else:
                logger = logging.getLogger("PopupLogger")
            logger.error(f"显示完成弹窗时出错: {e}")