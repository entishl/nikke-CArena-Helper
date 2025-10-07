import customtkinter as ctk
import logging
from app import initialize_app_context, setup_app_environment, cleanup_application
from core.constants import APP_TITLE

# 导入重构后的组件
from gui.components import SidebarComponent, StatusComponent, ControlButtonComponent, AppearanceComponent
from gui.handlers import EventHandler, WindowStatusChecker
from gui.image_manager import ImageManager, LogComponent
from gui.script_runner import ScriptRunner, CompletionPopupManager
from gui.logging_handler import LoggingManager


class NikkeGuiApp(ctk.CTk):
    """重构后的Nikke GUI应用主类"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 基本窗口设置
        self.geometry("1000x700")
        ctk.set_default_color_theme("blue")

        # 应用上下文
        self.app_context = None
        self._initialize_app_context()

        # 当前模式
        self.current_mode_value = 1
        self._current_selected_button = None

        # 窗口引用
        self.settings_window = None

        # 初始化组件
        self._initialize_components()

        # 创建界面
        self.create_widgets()

        # 初始化设置
        self._apply_initial_settings()

        # 检查窗口状态
        self.window_checker.check_nikke_window_status()

        # 设置关闭事件
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _initialize_app_context(self):
        """初始化应用上下文"""
        # 获取/创建logger实例
        app_logger_instance = logging.getLogger("AppLogger")
        if not app_logger_instance.hasHandlers():
            app_logger_instance.setLevel(logging.DEBUG)
            console_h = logging.StreamHandler()
            console_h.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'))
            app_logger_instance.addHandler(console_h)
            app_logger_instance.info("Logger 'AppLogger' initialized by NikkeGuiApp with DEBUG level.")
        else:
            if app_logger_instance.level > logging.DEBUG or app_logger_instance.level == 0:
                effective_level_val = app_logger_instance.getEffectiveLevel()
                if effective_level_val > logging.DEBUG:
                    app_logger_instance.setLevel(logging.DEBUG)
                    app_logger_instance.info(f"NikkeGuiApp: Logger 'AppLogger' already existed, ensured level is DEBUG.")

        try:
            self.app_context = initialize_app_context(app_logger_instance)
            if not hasattr(self.app_context, 'shared'):
                # 确保共享对象存在
                self.app_context.shared = type('Shared', (object,), {
                    'logger': logging.getLogger("AppContextLogger"),
                    'stop_requested': False,
                    'is_admin': False,
                    'nikke_window': None,
                    'available_modes': [],
                    'app_config': {},
                    'selected_target_window_title': None
                })()
        except Exception as e:
            print(f"Error initializing AppContext: {e}")
            # 创建占位符
            from app import AppContext
            self.app_context = AppContext()
            self.app_context.shared = type('Shared', (object,), {
                'logger': logging.getLogger("FallbackAppContextLogger"),
                'stop_requested': False,
                'is_admin': False,
                'nikke_window': None,
                'available_modes': [],
                'app_config': {},
                'selected_target_window_title': None
            })()

        # 设置窗口标题
        app_title_from_config = APP_TITLE
        if hasattr(self.app_context, 'shared') and self.app_context.shared.app_config:
            app_title_from_config = self.app_context.shared.app_config.get(
                'global_settings', {}).get('app_display_name', APP_TITLE)
        self.title(app_title_from_config)

        # 设置外观模式
        self._set_appearance_mode()

        # 设置应用环境
        try:
            setup_app_environment(self.app_context)
        except Exception as e:
            print(f"Error setting up app environment: {e}")
            if self.app_context and hasattr(self.app_context, 'shared') and self.app_context.shared.logger:
                self.app_context.shared.logger.error(f"Error setting up app environment: {e}")

    def _initialize_components(self):
        """初始化所有组件"""
        # 事件处理器
        self.event_handler = EventHandler(self.app_context, self)

        # 日志管理器
        self.logging_manager = LoggingManager(self.app_context)

        # 图像管理器（稍后在create_widgets中设置display_area和image_label）
        self.image_manager = ImageManager(None, None, self.app_context)

        # 脚本运行器
        self.script_runner = ScriptRunner(self.app_context, self.on_script_finished)

        # 这些组件将在create_widgets中初始化，因为需要parent参数
        self.sidebar_component = None
        self.status_component = None
        self.control_buttons = None
        self.appearance_component = None
        self.log_component = None
        self.window_checker = None

    def create_widgets(self):
        """创建所有界面组件"""
        # 设置网格配置
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)  # 主内容行
        self.grid_rowconfigure(3, weight=0)  # 控制区域行

        # 创建侧边栏
        self.sidebar_component = SidebarComponent(
            self, self.app_context,
            self.event_handler.handle_mode_select,
            self.event_handler.handle_server_select
        )
        self.sidebar_component.get_frame().grid(row=0, column=0, rowspan=4, sticky="nsew")

        # 重写侧边栏的事件回调
        self.sidebar_component.on_image_toggle = self.event_handler.handle_image_toggle
        self.sidebar_component.on_settings_click = self.event_handler.handle_settings_click

        # 创建内容框架
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=20, pady=15)
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        # 创建显示区域
        display_area = ctk.CTkFrame(content_frame, fg_color="transparent")
        display_area.grid(row=0, column=0, sticky="nsew")
        display_area.grid_rowconfigure(0, weight=1)
        display_area.grid_columnconfigure(0, weight=1)
        display_area.bind("<Configure>", self.image_manager.display_image)

        # 创建图像标签
        image_label = ctk.CTkLabel(display_area, text="")
        image_label.grid(row=0, column=0, sticky="nsew")

        # 创建日志文本框
        log_textbox = ctk.CTkTextbox(display_area, wrap="word", state="disabled", height=250)

        # 设置图像管理器
        self.image_manager.set_display_area(display_area)
        self.image_manager.set_image_label(image_label)

        # 创建日志组件
        self.log_component = LogComponent(display_area, log_textbox)

        # 设置GUI日志处理
        self.logging_manager.setup_gui_logging(log_textbox)

        # 创建控制区域
        control_area = ctk.CTkFrame(self, height=100)
        control_area.grid(row=3, column=1, sticky="nsew", padx=20, pady=(0,20))
        control_area.grid_columnconfigure(0, weight=1)  # 状态标签
        control_area.grid_columnconfigure(1, weight=0)  # 按钮
        control_area.grid_columnconfigure(2, weight=1)  # 外观模式

        # 创建状态组件
        self.status_component = StatusComponent(control_area, self.event_handler.handle_retry_nikke)

        # 创建控制按钮组件
        self.control_buttons = ControlButtonComponent(
            control_area,
            self.event_handler.handle_start_script,
            self.event_handler.handle_stop_script
        )

        # 创建外观组件
        self.appearance_component = AppearanceComponent(
            control_area,
            self.event_handler.handle_appearance_change,
            self.event_handler.handle_settings_click
        )

        # 创建窗口状态检查器
        self.window_checker = WindowStatusChecker(self.app_context, self.status_component, self.control_buttons)

        # 设置图像显示开关变量
        self.sidebar_component.image_display_switch.configure(variable=ctk.BooleanVar(value=True))

        # 选择初始模式
        self._select_initial_mode()

    def _select_initial_mode(self):
        """选择初始模式"""
        if self.sidebar_component and hasattr(self.app_context, 'shared') and self.app_context.shared.available_modes:
            mode_buttons = self.sidebar_component.get_mode_buttons()
            if mode_buttons:
                # 选择第一个可用且启用的模式
                first_enabled_mode_id = None
                for mode_meta in sorted(self.app_context.shared.available_modes, key=lambda x: x.get('id', float('inf'))):
                    if mode_meta.get('enabled', True) and mode_meta['id'] in mode_buttons:
                        first_enabled_mode_id = mode_meta['id']
                        break

                if first_enabled_mode_id is not None:
                    self.event_handler.handle_mode_select(
                        first_enabled_mode_id,
                        mode_buttons.get(first_enabled_mode_id)
                    )
                else:
                    self.status_component.update_status("没有可选择的模式。")
                    self.image_manager.set_placeholder_text("请在配置文件中启用至少一个模式。")
                    self.control_buttons.set_start_enabled(False)
            else:
                self.status_component.update_status("模式加载失败或未配置。")
                self.image_manager.set_placeholder_text("请检查应用配置。")
                self.control_buttons.set_start_enabled(False)

    def _apply_initial_settings(self):
        """应用初始设置"""
        # 设置初始外观模式
        if hasattr(self.app_context, 'shared') and self.app_context.shared.app_config:
            initial_mode = self.app_context.shared.app_config.get('global_settings', {}).get('appearance_mode', 'System')
            self.appearance_component.set_initial_mode(initial_mode)

    def _set_appearance_mode(self):
        """设置外观模式"""
        initial_appearance_mode = "System"
        if hasattr(self.app_context, 'shared') and self.app_context.shared.app_config:
            initial_appearance_mode = self.app_context.shared.app_config.get(
                'global_settings', {}).get('appearance_mode', 'System')

        valid_modes = ["Light", "Dark", "System"]
        if initial_appearance_mode not in valid_modes:
            print(f"Warning: Invalid appearance_mode '{initial_appearance_mode}' in config. Falling back to 'System'.")
            initial_appearance_mode = "System"

        ctk.set_appearance_mode(initial_appearance_mode)

    def on_script_finished(self, status, message="脚本已结束。"):
        """脚本执行完成回调"""
        # 更新状态标签
        self.status_component.update_status(message)
        self.control_buttons.set_start_enabled(True)
        self.control_buttons.set_stop_enabled(False)

        # 显示完成弹窗
        CompletionPopupManager.show_completion_popup(status, message, self.app_context)

        # 重新检查窗口状态
        self.window_checker.check_nikke_window_status()

        # 根据开关状态恢复视图
        if self.sidebar_component.image_display_switch.get():
            self.image_manager.display_image()
        else:
            self.image_manager.hide_image()
            self.log_component.show_log()
            self.image_manager.set_placeholder_text("图片显示已关闭。\n日志将在此处显示。")

    def on_closing(self):
        """窗口关闭事件"""
        logger = self.app_context.shared.logger if self.app_context and hasattr(self.app_context, 'shared') else logging.getLogger("ClosingLogger")
        if self.script_runner.is_running():
            self.event_handler.handle_stop_script()

        try:
            cleanup_application(logger)
        except Exception as e:
            print(f"Error during cleanup: {e}")
        self.destroy()

    # 为了兼容性，保留一些原有属性
    @property
    def status_label(self):
        """兼容原有代码的status_label属性"""
        return self.status_component.status_label if self.status_component else None

    @property
    def nikke_window_status_label(self):
        """兼容原有代码的nikke_window_status_label属性"""
        return self.status_component.nikke_window_status_label if self.status_component else None

    @property
    def start_button(self):
        """兼容原有代码的start_button属性"""
        return self.control_buttons.start_button if self.control_buttons else None

    @property
    def stop_button(self):
        """兼容原有代码的stop_button属性"""
        return self.control_buttons.stop_button if self.control_buttons else None

    @property
    def log_textbox(self):
        """兼容原有代码的log_textbox属性"""
        return self.log_component.log_textbox if self.log_component else None

    @property
    def image_label(self):
        """兼容原有代码的image_label属性"""
        return self.image_manager.image_label if self.image_manager else None

    @property
    def mode_buttons(self):
        """兼容原有代码的mode_buttons属性"""
        return self.sidebar_component.get_mode_buttons() if self.sidebar_component else {}

    @property
    def server_options_map(self):
        """兼容原有代码的server_options_map属性"""
        return self.sidebar_component.get_server_options_map() if self.sidebar_component else {}

    @property
    def theme_manager(self):
        """兼容原有代码的theme_manager属性"""
        return ctk.ThemeManager