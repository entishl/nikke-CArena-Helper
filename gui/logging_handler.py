import logging


class GUILogHandler(logging.Handler):
    """GUI日志处理器，将日志输出到GUI文本框"""

    def __init__(self, textbox_ref):
        super().__init__()
        self.textbox = textbox_ref  # 存储文本框引用，可能初始为None

    def set_textbox(self, textbox_ref):
        """设置文本框引用"""
        self.textbox = textbox_ref

    def _insert_text(self, msg):
        """在主线程中插入文本，确保线程安全"""
        if not self.textbox or not self.textbox.winfo_exists():
            # 如果文本框不可用，回退到控制台输出
            print(f"GUI Log (textbox not available): {msg}")
            return

        try:
            self.textbox.configure(state="normal")
            self.textbox.insert("end", msg + "\n")
            self.textbox.see("end")
            self.textbox.configure(state="disabled")
        except Exception as e:
            # 如果文本框操作失败，回退到控制台输出
            print(f"Error writing to GUI log textbox from _insert_text: {e}. Message: {msg}")

    def emit(self, record):
        """发出日志记录"""
        msg = self.format(record)

        # 如果文本框未设置或已销毁，无法使用'after'方法
        # 存在性检查将在调用的调用中进行
        if self.textbox:
            try:
                # 在主线程上调度UI更新以确保线程安全
                self.textbox.after(0, self._insert_text, msg)
            except Exception as e:
                # 如果在已销毁的widget上调用'after'时发生错误
                print(f"Error scheduling log message: {e}. Message: {msg}")
        else:
            print(f"GUILogHandler: Textbox not available. Log: {msg}")


class LoggingManager:
    """日志管理器"""

    def __init__(self, app_context):
        self.app_context = app_context
        self.gui_log_handler = None

    def setup_gui_logging(self, log_textbox=None):
        """设置GUI日志处理"""
        # 创建GUI日志处理器
        self.gui_log_handler = GUILogHandler(log_textbox)
        self.gui_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        # 将处理器添加到应用的日志记录器
        if self.app_context and hasattr(self.app_context, 'shared') and self.app_context.shared.logger:
            self.app_context.shared.logger.addHandler(self.gui_log_handler)
            self.gui_log_handler.setLevel(logging.INFO)  # 设置GUI文本框的处理器级别
            self.app_context.shared.logger.info("GUILogHandler added to AppLogger. Handler level: INFO.")
        else:
            # 如果应用上下文的日志记录器不可用，使用回退日志记录器
            fallback_logger = logging.getLogger("GuiFallbackLogger")
            fallback_logger.addHandler(self.gui_log_handler)
            fallback_logger.setLevel(logging.INFO)

            if self.app_context and hasattr(self.app_context, 'shared'):
                self.app_context.shared.logger = fallback_logger

            print("Warning: GUI using a fallback logger as app_context.shared.logger was not fully set up.")

    def update_log_handler_textbox(self, log_textbox):
        """更新日志处理器的文本框引用"""
        if self.gui_log_handler:
            self.gui_log_handler.set_textbox(log_textbox)

    def remove_gui_handler(self):
        """移除GUI日志处理器"""
        if (self.gui_log_handler and
            self.app_context and
            hasattr(self.app_context, 'shared') and
            self.app_context.shared.logger):

            self.app_context.shared.logger.removeHandler(self.gui_log_handler)
            self.gui_log_handler = None