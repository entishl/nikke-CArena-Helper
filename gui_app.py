import customtkinter as ctk
from customtkinter import filedialog #  GUI适配：为模式9导入目录选择对话框
import threading
import logging
from PIL import Image, ImageTk # Import ImageTk
import os # For path joining
import ctypes # For admin check
import sys # For exiting

# Function to check for admin rights and exit if not granted
def check_admin_and_exit_if_not():
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except AttributeError:
        # Fallback for environments where shell32 might not be available as expected
        # or IsUserAnAdmin is not found. Assume not admin to be safe.
        is_admin = False
        print("Warning: Could not determine admin status via ctypes.windll.shell32.IsUserAnAdmin().")

    if not is_admin:
        ctypes.windll.user32.MessageBoxW(
            0,
            "请以管理员权限运行此程序！\n\n程序即将退出。",
            "权限不足",
            0x00000010 | 0x00000000 # MB_ICONERROR | MB_OK
        )
        sys.exit(1)

# Assuming app.py is in the same directory or accessible via PYTHONPATH
try:
    from app import (
        initialize_app_context,
        setup_app_environment,
        execute_mode,
        cleanup_application,
        AppContext, # AppContext moved here
        # stop_script_callback # This might be handled differently or passed
    )
    from core.utils import get_asset_path # AppContext removed from here
    # APP_TITLE will be loaded from app_context.shared.app_config or a default if not found
    # MODE_CONFIGS will be replaced by app_context.shared.available_modes
    from core.constants import APP_TITLE # APP_TITLE can still be a fallback or defined here if not in config
except ImportError as e:
    print(f"Error importing from app.py or core modules: {e}")
    # Fallback or error handling if modules are not found
    # For now, let's define placeholders if imports fail, to allow GUI structure development
    class AppContext: pass
    def initialize_app_context(): return AppContext()
    def setup_app_environment(context): context.shared = type('Shared', (object,), {'nikke_window': None, 'logger': logging.getLogger(), 'stop_requested': False, 'is_admin': False, 'available_modes': []})()
    def execute_mode(context, mode, inputs): print(f"Executing mode {mode} with inputs {inputs}")
    def cleanup_application(logger): print("Cleaning up application")
    def get_asset_path(asset_name): return os.path.join("assets", asset_name) # Placeholder, assumes assets folder
    APP_TITLE = "Nikke Cheerleading Tool (Fallback)"
    # MODE_CONFIGS placeholder is no longer needed as it will be dynamically loaded


class NikkeGuiApp(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Title will be set after app_context is initialized, potentially from config
        # self.title(APP_TITLE) # Fallback title set during import if core.constants.APP_TITLE fails
        self.geometry("1000x700")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.app_context: AppContext = None
        self.script_thread = None
        self.stop_event = threading.Event()
        self.current_mode_value = 1 
        self._current_selected_button = None

        # 获取/创建 logger 实例，并进行基本配置以确保 DEBUG 日志能输出
        # 使用与 app.py 中一致的 logger 名称 "AppLogger"
        # 这样，如果 app.py 中的 setup_logging()（在命令行模式下）先运行，这里的 getLogger 会获取到已配置的 logger
        # 如果 gui_app.py 是主入口，这将是首次配置 "AppLogger"
        app_logger_instance = logging.getLogger("AppLogger")
        if not app_logger_instance.hasHandlers(): # 避免重复添加处理器
            app_logger_instance.setLevel(logging.DEBUG) # 设置为 DEBUG 以捕获所有级别的日志
            console_h = logging.StreamHandler() # 输出到控制台
            console_h.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'))
            app_logger_instance.addHandler(console_h)
            app_logger_instance.info("Logger 'AppLogger' initialized by NikkeGuiApp with DEBUG level.")
        else:
            # 如果 logger 已有处理器，确保其级别至少是 DEBUG，以便 app.py 中的 debug 日志能通过
            if app_logger_instance.level > logging.DEBUG or app_logger_instance.level == 0: # level 0 means NOTSET, effectively inherits from root
                 current_level = logging.getLevelName(app_logger_instance.level)
                 # Check effective level if current level is NOTSET
                 effective_level_val = app_logger_instance.getEffectiveLevel()
                 if effective_level_val > logging.DEBUG:
                    app_logger_instance.setLevel(logging.DEBUG)
                    app_logger_instance.info(f"NikkeGuiApp: Logger 'AppLogger' already existed (level {current_level}, effective {logging.getLevelName(effective_level_val)}), ensured level is DEBUG.")


        try:
            self.app_context = initialize_app_context(app_logger_instance) # 传递 logger
            if self.app_context and hasattr(self.app_context, 'shared'):
                print(f"DEBUG GUI: self.app_context.shared.available_modes in __init__ (try block): {getattr(self.app_context.shared, 'available_modes', 'N/A')}")
            else:
                print(f"DEBUG GUI: self.app_context or self.app_context.shared is not fully available in __init__ (try block) after initialize_app_context. AppContext: {self.app_context}")

            if not hasattr(self.app_context, 'shared'):
                # Ensure shared object and available_modes exist even if initialize_app_context fails partially
                self.app_context.shared = type('Shared', (object,), {
                    'logger': logging.getLogger("AppContextLogger"),
                    'stop_requested': False,
                    'is_admin': False,
                    'nikke_window': None,
                    'available_modes': [], # Ensure available_modes exists
                    'app_config': {}, # Ensure app_config exists
                    'selected_target_window_title': None # NEW: Default for "自动"
                })()
        except Exception as e:
            print(f"Error initializing AppContext: {e}")
            if self.app_context is None:
                self.app_context = AppContext() # Placeholder AppContext
                print(f"DEBUG GUI: AppContext created as placeholder in __init__ (except block).")
            # Ensure shared object and available_modes exist for fallback
            self.app_context.shared = type('Shared', (object,), {
                'logger': logging.getLogger("FallbackAppContextLogger"),
                'stop_requested': False,
                'is_admin': False,
                'nikke_window': None,
                'available_modes': [], # Ensure available_modes exists
                'app_config': {}, # Ensure app_config exists
                'selected_target_window_title': None # NEW: Default for "自动"
            })()
            if hasattr(self.app_context, 'shared'): # Log after fallback creation
                print(f"DEBUG GUI: self.app_context.shared.available_modes in __init__ (except block - fallback): {getattr(self.app_context.shared, 'available_modes', 'N/A')}")
        
        # Set title using app_config if available, otherwise use fallback APP_TITLE
        app_title_from_config = APP_TITLE # Fallback
        if hasattr(self.app_context, 'shared') and self.app_context.shared.app_config:
            app_title_from_config = self.app_context.shared.app_config.get(
                'global_settings', {}).get('app_display_name', APP_TITLE)
        self.title(app_title_from_config)

        self.log_textbox = None
        self.current_asset_image_name = None # Store the name of the current image
        self.show_image_var = ctk.BooleanVar(value=True) # NEW: Variable for image visibility switch
        self.setup_gui_logging()

        try:
            setup_app_environment(self.app_context)
        except Exception as e:
            print(f"Error setting up app environment: {e}")
            if self.app_context and hasattr(self.app_context, 'shared') and self.app_context.shared.logger:
                self.app_context.shared.logger.error(f"Error setting up app environment: {e}")


        # Server selection attributes
        self.server_options_map = {
            "自动": None,
            "国际服": "NIKKE",
            "港澳台": "勝利女神：妮姬",
            "大陆": "胜利女神：新的希望"
        }
        server_display_options = list(self.server_options_map.keys())
        self.server_selection_var = ctk.StringVar(value=server_display_options[0]) # Default "自动"

        # Set initial selected_target_window_title in app_context based on the dropdown's default
        if hasattr(self.app_context, 'shared'):
            # Ensure selected_target_window_title attribute exists if not set by default_shared_attrs
            if not hasattr(self.app_context.shared, 'selected_target_window_title'):
                 self.app_context.shared.selected_target_window_title = None # Fallback default
            
            initial_display_name = self.server_selection_var.get()
            self.app_context.shared.selected_target_window_title = self.server_options_map.get(initial_display_name)
            
            # Attempt to log this initialization
            logger_to_use = None
            if hasattr(self.app_context.shared, 'logger') and self.app_context.shared.logger:
                logger_to_use = self.app_context.shared.logger
            elif hasattr(self, 'app_logger_instance') and self.app_logger_instance: # Fallback to the instance logger if shared.logger isn't ready
                logger_to_use = self.app_logger_instance
            
            if logger_to_use:
                logger_to_use.info(
                    f"GUI Init: Default server set to '{initial_display_name}' "
                    f"(Title: {self.app_context.shared.selected_target_window_title})"
                )
            else: # Absolute fallback if no logger is available
                print(f"GUI Init (no logger): Default server set to '{initial_display_name}' (Title: {self.app_context.shared.selected_target_window_title})")

        self.nikke_window_status_label = None
        self.admin_status_label = None
        
        self.create_widgets() # Create widgets before checking status that updates them

        self.check_nikke_window_status()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1) # Main content rows
        self.grid_rowconfigure(3, weight=0) # Control area row

        # --- Sidebar Frame ---
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0) # Increased width slightly
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(20, weight=1) # Push appearance mode to bottom, ensure content is pushed up

        # Use the title set in __init__ which might come from app_config
        sidebar_title = ctk.CTkLabel(self.sidebar_frame, text=self.title(), font=ctk.CTkFont(size=20, weight="bold"))
        sidebar_title.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.mode_buttons = {}
        current_row = 1

        if hasattr(self.app_context, 'shared') and hasattr(self.app_context.shared, 'available_modes'):
            print(f"DEBUG GUI: available_modes in create_widgets before check: {self.app_context.shared.available_modes}")
            print(f"DEBUG GUI: Type of available_modes: {type(self.app_context.shared.available_modes)}")
            # The original condition `and self.app_context.shared.available_modes` implicitly checks if the list is non-empty.
            # We'll keep that, but the print above shows the actual content.
            print(f"DEBUG GUI: Condition check (bool(self.app_context.shared.available_modes)): {bool(self.app_context.shared.available_modes)}")
        else:
            print(f"DEBUG GUI: self.app_context.shared or self.app_context.shared.available_modes not available in create_widgets at the start.")

        if hasattr(self.app_context, 'shared') and self.app_context.shared.available_modes:
            all_enabled_modes = sorted(
                [m for m in self.app_context.shared.available_modes if m.get('enabled', True)],
                key=lambda x: x.get('id', float('inf'))
            )
            modes_map = {m['id']: m for m in all_enabled_modes}

            # 假设新模式“（赛果）查看赛果”在 config.json 中定义的 ID 为 10
            # 请确保 config.json 中有此模式的定义，包括 name: "（赛果）查看赛果"
            ID_CHECK_RESULT = 10

            ordered_groups_config = [
                {
                    "name": "应援专用",
                    "description": None,
                    "ids": [1, 2, 3]
                },
                {
                    "name": "赛前总览用",
                    "description": None,
                    "ids": [4, 41, 5]
                },
                {
                    "name": "赛果分析用",
                    "description": None,
                    "ids": [6, 7, 8]
                },
                {
                    "name": "图片处理",
                    "description": None,
                    "ids": [9]
                }
            ]

            for group_config in ordered_groups_config:
                group_name = group_config["name"]
                description = group_config["description"]
                
                modes_for_this_group_obj = []
                for m_id in group_config["ids"]:
                    if m_id in modes_map:
                        modes_for_this_group_obj.append(modes_map[m_id])
                    elif m_id == ID_CHECK_RESULT:
                        if hasattr(self.app_context, 'shared') and self.app_context.shared.logger:
                            self.app_context.shared.logger.warning(
                                f"GUI: 模式 '（赛果）查看赛果' (预期 ID {ID_CHECK_RESULT}) "
                                "在 available_modes 中未找到或未启用。该按钮将不会显示。"
                                "请确保其已在 config.json 中正确定义并启用。"
                            )
                
                if not modes_for_this_group_obj and not description:
                    continue

                group_label = ctk.CTkLabel(self.sidebar_frame, text=group_name, font=ctk.CTkFont(weight="bold"))
                group_label.grid(row=current_row, column=0, padx=20, pady=(10, 5), sticky="w")
                current_row += 1

                if description:
                    desc_label = ctk.CTkLabel(self.sidebar_frame, text=description, font=ctk.CTkFont(size=11), anchor="w", justify="left")
                    desc_label.grid(row=current_row, column=0, padx=25, pady=(0, 8), sticky="w")
                    current_row += 1
                
                if modes_for_this_group_obj:
                    for mode_meta in modes_for_this_group_obj:
                        mode_id = mode_meta['id']
                        # 按钮文本（btn_text）将从 mode_meta（源自 config.json）中的 'name' 字段获取
                        # 例如，对于 ID_CHECK_RESULT，如果配置正确，其 name 应为 "（赛果）查看赛果"
                        btn_text = mode_meta.get('name', f"模式 {mode_id}")
                        
                        btn = ctk.CTkButton(self.sidebar_frame, text=btn_text)
                        
                        btn.grid(row=current_row, column=0, padx=20, pady=5, sticky="ew")
                        self.mode_buttons[mode_id] = btn
                        btn.configure(command=lambda m_id=mode_id: self.select_mode(m_id, self.mode_buttons.get(m_id)))
                        current_row += 1
        else:
            no_modes_label = ctk.CTkLabel(self.sidebar_frame, text="没有可用的模式。", font=ctk.CTkFont(slant="italic"))
            no_modes_label.grid(row=current_row, column=0, padx=20, pady=10)
            current_row +=1
        
        # --- Server Selection ---
        server_label = ctk.CTkLabel(self.sidebar_frame, text="服务器选择:", font=ctk.CTkFont(weight="bold"))
        server_label.grid(row=current_row, column=0, padx=20, pady=(15, 5), sticky="w")
        current_row += 1

        server_display_options = list(self.server_options_map.keys()) # Defined in __init__
        # self.server_selection_var is also defined in __init__

        self.server_option_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=server_display_options,
            variable=self.server_selection_var,
            command=self.on_server_selected
        )
        self.server_option_menu.grid(row=current_row, column=0, padx=20, pady=5, sticky="ew")
        current_row += 1

        # --- Image Display Switch ---
        switch_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        switch_frame.grid(row=current_row, column=0, padx=20, pady=(15, 5), sticky="ew")
        current_row += 1
        
        switch_frame.grid_columnconfigure(0, weight=0) # Label
        switch_frame.grid_columnconfigure(1, weight=1) # Switch, allow it to expand if needed or align right

        image_switch_label = ctk.CTkLabel(switch_frame, text="显示指引图像:", font=ctk.CTkFont(weight="bold"))
        image_switch_label.grid(row=0, column=0, sticky="w", padx=(0, 10)) # Add some padding between label and switch

        self.image_display_switch = ctk.CTkSwitch(
            switch_frame,
            text="开/关", # Text for the switch itself
            variable=self.show_image_var,
            command=self.toggle_image_visibility
        )
        self.image_display_switch.grid(row=0, column=1, sticky="w") # Align switch to the left of its cell

        # --- Content Frame ---
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=20, pady=20)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.display_area = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.display_area.grid(row=0, column=0, sticky="nsew")
        self.display_area.grid_rowconfigure(0, weight=1)
        self.display_area.grid_columnconfigure(0, weight=1)
        self.display_area.bind("<Configure>", self._resize_and_display_image) # Bind resize event

        self.image_label = ctk.CTkLabel(self.display_area, text="")
        # Restore sticky="nsew" as it was in the reference and might work with ImageTk.PhotoImage
        self.image_label.grid(row=0, column=0, sticky="nsew")

        self.log_textbox = ctk.CTkTextbox(self.display_area, wrap="word", state="disabled", height=300)
        # self.log_textbox initially not packed/gridded, shown on demand

        # --- Control Area ---
        self.control_area = ctk.CTkFrame(self, height=100) 
        self.control_area.grid(row=3, column=1, sticky="nsew", padx=20, pady=(0,20))
        self.control_area.grid_columnconfigure(0, weight=1) # For status labels
        self.control_area.grid_columnconfigure(1, weight=0) # For buttons
        self.control_area.grid_columnconfigure(2, weight=0)

        status_frame = ctk.CTkFrame(self.control_area, fg_color="transparent")
        status_frame.grid(row=0, column=0, sticky="ew", padx=(0,10))

        self.status_label = ctk.CTkLabel(status_frame, text="准备就绪", anchor="w")
        self.status_label.pack(pady=2, fill="x")

        self.nikke_window_status_label = ctk.CTkLabel(status_frame, text="NIKKE 窗口: 未连接", anchor="w")
        self.nikke_window_status_label.pack(pady=2, fill="x")

        self.shortcut_info_label = ctk.CTkLabel(status_frame, text="可随时按 Ctrl +1 强制中止脚本", anchor="w", text_color="gray")
        self.shortcut_info_label.pack(pady=2, fill="x")
        
        self.retry_nikke_button = ctk.CTkButton(status_frame, text="重试连接NIKKE", command=lambda: self.check_nikke_window_status(from_retry=True), width=120)
        # self.retry_nikke_button initially not packed

        button_frame = ctk.CTkFrame(self.control_area, fg_color="transparent")
        button_frame.grid(row=0, column=1, sticky="e")

        self.start_button = ctk.CTkButton(button_frame, text="启动脚本", command=self.start_script, width=100)
        self.start_button.pack(side="left", padx=(0,10), pady=10)

        self.stop_button = ctk.CTkButton(button_frame, text="停止脚本", command=self.request_stop_script, state="disabled", width=100)
        self.stop_button.pack(side="left", pady=10)
        
        # Initial mode selection
        if self.mode_buttons and hasattr(self.app_context, 'shared') and self.app_context.shared.available_modes:
            # Select the first available and enabled mode
            first_enabled_mode_id = None
            for mode_meta in sorted(self.app_context.shared.available_modes, key=lambda x: x.get('id', float('inf'))):
                if mode_meta.get('enabled', True) and mode_meta['id'] in self.mode_buttons:
                    first_enabled_mode_id = mode_meta['id']
                    break
            
            if first_enabled_mode_id is not None:
                self.select_mode(first_enabled_mode_id, self.mode_buttons.get(first_enabled_mode_id))
            else: # No enabled modes with buttons found
                self.status_label.configure(text="没有可选择的模式。")
                self.image_label.configure(image=None, text="请在配置文件中启用至少一个模式。")
                if self.start_button: self.start_button.configure(state="disabled")
        else:
            # Fallback if no modes are loaded or no buttons created
            self.status_label.configure(text="模式加载失败或未配置。")
            self.image_label.configure(image=None, text="请检查应用配置。")
            if self.start_button: self.start_button.configure(state="disabled")

    def select_mode(self, mode_value, pressed_button):
        self.current_mode_value = mode_value
        
        selected_mode_name = f"模式 {mode_value}" # Fallback name
        asset_image_name = f"{mode_value}.png" # Fallback image name

        if hasattr(self.app_context, 'shared') and self.app_context.shared.available_modes:
            for mode_meta in self.app_context.shared.available_modes:
                if mode_meta.get('id') == mode_value:
                    selected_mode_name = mode_meta.get('name', selected_mode_name)
                    asset_image_name = mode_meta.get('asset_image', asset_image_name)
                    # If asset_image is not in meta, it defaults to f"{mode_value}.png"
                    break
        
        self.status_label.configure(text=f"已选择模式: {selected_mode_name}")

        if self._current_selected_button:
            self._current_selected_button.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        if pressed_button:
            pressed_button.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"])
            self._current_selected_button = pressed_button

        self.current_asset_image_name = asset_image_name # Store the selected image name
        
        if self.show_image_var.get():
            self._resize_and_display_image()
        else:
            self.image_label.grid_forget()
            self.log_textbox.grid(row=0, column=0, sticky="nsew")
            # Optionally, display a message in the log textbox or image_label if it's hidden
            self.image_label.configure(image=None, text="图片显示已关闭。\n日志将在此处显示。")

    def _resize_and_display_image(self, event=None):
        if not self.show_image_var.get():
            self.image_label.grid_forget()
            self.log_textbox.grid(row=0, column=0, sticky="nsew")
            # Ensure image_label doesn't show old image if switch is toggled off then on quickly
            self.image_label.configure(image=None, text="图片显示已关闭。")
            return

        if not self.current_asset_image_name:
            # No image selected yet, or called before selection
            self.image_label.configure(image=None, text="请选择一个模式")
            self.log_textbox.grid_forget() # Ensure log is hidden if no image and switch is on
            self.image_label.grid(row=0, column=0, sticky="nsew")
            return

        self.log_textbox.grid_forget()
        self.image_label.grid(row=0, column=0, sticky="nsew")

        try:
            logger = getattr(getattr(self.app_context, 'shared', None), 'logger', None)
            if not logger:
                logger = logging.getLogger("GuiAppImageResize")
                if not logger.hasHandlers():
                    ch_resize = logging.StreamHandler()
                    ch_resize.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'))
                    logger.addHandler(ch_resize)
                    logger.setLevel(logging.DEBUG)

            log_prefix = "_resize_and_display_image"
            if event: # Log if called from an event like <Configure>
                log_prefix += f" (event {event.type})"

            image_path = get_asset_path(self.current_asset_image_name)
            if os.path.exists(image_path):
                self.display_area.update_idletasks() # Ensure dimensions are current
                width = self.display_area.winfo_width()
                height = self.display_area.winfo_height()

                
                logger.debug(f"{log_prefix}: display_area current dimensions: width={width}, height={height}")

                padding = 20
                available_width = width - padding if width > padding else 1
                available_height = height - padding if height > padding else 1
                target_aspect_ratio = 5 / 4

                if available_width / available_height > target_aspect_ratio:
                    img_height = available_height
                    img_width = int(img_height * target_aspect_ratio)
                else:
                    img_width = available_width
                    img_height = int(img_width / target_aspect_ratio)

                if img_width < 50 or img_height < 40:
                    default_width_for_ratio = 400
                    img_width = default_width_for_ratio
                    img_height = int(default_width_for_ratio / target_aspect_ratio)
                    logger.debug(f"{log_prefix}: Calculated dimensions too small or display_area not ready ({available_width}x{available_height}), falling back to default {img_width}x{img_height}")
                
                logger.debug(f"{log_prefix}: Calculated image size for 5:4: img_width={img_width}, img_height={img_height}. Aspect ratio: {img_width/img_height if img_height > 0 else 'N/A'}")

                pil_image = Image.open(image_path)
                
                # Determine the resampling filter based on Pillow version
                try:
                    # Pillow 9.0.0+ uses Resampling enum
                    resample_filter = Image.Resampling.LANCZOS
                except AttributeError:
                    # Older versions use constants like Image.ANTIALIAS or Image.LANCZOS
                    resample_filter = Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS

                resized_pil_image = pil_image.resize((img_width, img_height), resample_filter)
                logger.debug(f"{log_prefix}: PIL image resized to: {resized_pil_image.size} using filter {resample_filter}")

                # Convert the resized PIL image to PhotoImage
                photo_image = ImageTk.PhotoImage(resized_pil_image)
                logger.debug(f"{log_prefix}: Resized PIL image converted to ImageTk.PhotoImage")

                # Configure the label with the PhotoImage
                self.image_label.configure(image=photo_image, text="")
                self.image_label.image = photo_image # Keep a reference!

                self.image_label.update_idletasks() # Ensure label dimensions are updated before query
                label_w = self.image_label.winfo_width()
                label_h = self.image_label.winfo_height()
                logger.debug(f"{log_prefix}: image_label actual dimensions after configure: width={label_w}, height={label_h}")
            else:
                self.image_label.configure(image=None, text=f"图片 {self.current_asset_image_name} 未找到\n路径: {image_path}")
                logger.warning(f"{log_prefix}: Image file not found: {image_path}")
        except Exception as e:
            self.image_label.configure(image=None, text=f"加载图片 {self.current_asset_image_name} 失败: {e}")
            logger.exception(f"{log_prefix}: Error loading image {self.current_asset_image_name}:")

    def setup_gui_logging(self):
        # Ensure log_textbox is created before calling this if it's needed for the handler
        # It's created in create_widgets, but self.log_textbox is None when this is first called in __init__
        # So, the GUILogHandler will be initialized with None. We need to update it.
        # Or, defer adding handler until log_textbox exists.
        # For now, GUILogHandler will store the textbox reference.
        
        self.gui_log_handler = GUILogHandler(self.log_textbox) # Pass reference
        self.gui_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        if self.app_context and hasattr(self.app_context, 'shared') and self.app_context.shared.logger:
            self.app_context.shared.logger.addHandler(self.gui_log_handler)
            # self.app_context.shared.logger.setLevel(logging.INFO) # Commented out to preserve DEBUG level set in __init__
            self.gui_log_handler.setLevel(logging.INFO) # Set handler level for GUI textbox
            self.app_context.shared.logger.info("GUILogHandler added to AppLogger. Handler level: INFO.") # Log this action
        else:
            # This case should be rare if app_context initialization is robust
            self.fallback_logger = logging.getLogger("GuiFallbackLogger")
            self.fallback_logger.addHandler(self.gui_log_handler)
            self.fallback_logger.setLevel(logging.INFO)
            if self.app_context and hasattr(self.app_context, 'shared'):
                 self.app_context.shared.logger = self.fallback_logger
            print("Warning: GUI using a fallback logger as app_context.shared.logger was not fully set up.")
    
    def _update_log_handler_textbox(self):
        # Call this after log_textbox is created in create_widgets
        if hasattr(self, 'gui_log_handler') and self.gui_log_handler:
            self.gui_log_handler.textbox = self.log_textbox


    def check_nikke_window_status(self, from_retry=False):
        if not self.nikke_window_status_label: return False # Widget not ready

        # Helper function for aspect ratio check to avoid code duplication
        def _check_and_warn_aspect_ratio(window_obj):
            if not window_obj: return
            try:
                # Attempt to get HWND, common attribute name is _hWnd
                hwnd = getattr(window_obj, '_hWnd', None)
                if not hwnd:
                    # Fallback to full window size if HWND is not available
                    width = window_obj.width
                    height = window_obj.height
                    logger = getattr(getattr(self.app_context, 'shared', None), 'logger', None)
                    if logger:
                        logger.warning("无法获取窗口句柄 (HWND)，将使用完整窗口尺寸进行宽高比检查。")
                else:
                    rect = ctypes.wintypes.RECT()
                    if ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect)):
                        width = rect.right - rect.left
                        height = rect.bottom - rect.top
                    else:
                        # Fallback if GetClientRect fails
                        width = window_obj.width
                        height = window_obj.height
                        logger = getattr(getattr(self.app_context, 'shared', None), 'logger', None)
                        if logger:
                            logger.warning("GetClientRect 调用失败，将使用完整窗口尺寸进行宽高比检查。")

                # Ensure logger exists for warnings/errors during this check
                logger = None
                if hasattr(self.app_context, 'shared') and hasattr(self.app_context.shared, 'logger'):
                    logger = self.app_context.shared.logger
                
                if height == 0:
                    if logger:
                        logger.warning("NIKKE 窗口高度为0，无法检查宽高比。")
                    return # Cannot check ratio if height is zero

                target_ratio = 16.0 / 9.0
                current_ratio = float(width) / height
                
                # Allow up to ~2% deviation from 16:9. You can adjust this tolerance.
                if abs(current_ratio - target_ratio) > 0.02:
                    ctypes.windll.user32.MessageBoxW(
                        0, # hwndOwner (0 for no owner window)
                        "当前 NIKKE 窗口非 16:9，截图可能错误。", # lpText
                        "窗口比例提示", # lpCaption
                        0x00000030 | 0x00000000  # uType: MB_ICONWARNING | MB_OK
                    )
            except AttributeError:
                if logger:
                    logger.warning("无法获取 NIKKE 窗口的 width/height 属性来检查宽高比。窗口对象可能不是预期的类型。")
            except Exception as e_ratio_check:
                if logger:
                    logger.error(f"检查 NIKKE 窗口宽高比时发生内部错误: {e_ratio_check}")

        # If already connected and not a retry, just confirm status and check ratio
        if not from_retry and self.app_context and hasattr(self.app_context, 'shared') and self.app_context.shared.nikke_window:
            _check_and_warn_aspect_ratio(self.app_context.shared.nikke_window) # Check ratio
            self.nikke_window_status_label.configure(text="NIKKE 窗口: 已连接", text_color="green")
            self.retry_nikke_button.pack_forget()
            if self.start_button: self.start_button.configure(state="normal")
            return True

        if self.app_context:
            try:
                current_logger = None
                if hasattr(self.app_context, 'shared') and hasattr(self.app_context.shared, 'logger'):
                    current_logger = self.app_context.shared.logger

                if from_retry:
                    if current_logger:
                        current_logger.info("尝试重新连接 NIKKE 窗口...")
                    else: # Fallback print if logger is not available
                        print("尝试重新连接 NIKKE 窗口...")
                    setup_app_environment(self.app_context) # Re-run to find window

                if hasattr(self.app_context.shared, 'nikke_window') and self.app_context.shared.nikke_window:
                    _check_and_warn_aspect_ratio(self.app_context.shared.nikke_window) # Check ratio
                    self.nikke_window_status_label.configure(text="NIKKE 窗口: 已连接", text_color="green")
                    self.retry_nikke_button.pack_forget()
                    if self.start_button: self.start_button.configure(state="normal")
                    return True
                else:
                    self.nikke_window_status_label.configure(text="NIKKE 窗口: 未找到! 请确保游戏运行且未最小化。", text_color="red")
                    self.retry_nikke_button.pack(pady=(5,0), fill="x")
                    if self.start_button: self.start_button.configure(state="disabled")
                    return False
            except Exception as e:
                self.nikke_window_status_label.configure(text=f"NIKKE 窗口: 连接出错", text_color="red")
                logger_for_error = None
                if hasattr(self.app_context, 'shared') and hasattr(self.app_context.shared, 'logger'):
                     logger_for_error = self.app_context.shared.logger
                
                if logger_for_error:
                    logger_for_error.error(f"Error checking NIKKE window: {e}")
                else: # Fallback print
                    print(f"Error checking NIKKE window: {e}")
                self.retry_nikke_button.pack(pady=(5,0), fill="x")
                if self.start_button: self.start_button.configure(state="disabled")
                return False
        return False


    def prompt_for_mode9_input_directory(self):
        """Prompts the user to select a directory for Mode 9 input."""
        if not (self.app_context and hasattr(self.app_context, 'shared') and self.app_context.shared.logger):
            # Fallback logger if app_context or its logger is not fully initialized
            temp_logger = logging.getLogger("GuiPromptLogger")
            temp_logger.warning("尝试提示模式9输入目录，但应用上下文或日志记录器不可用。")
        
        logger = getattr(getattr(self.app_context, 'shared', None), 'logger', logging.getLogger("GuiPromptLoggerFallback"))

        directory = filedialog.askdirectory(
            title="模式9 输入选择",
            initialdir=os.path.abspath(getattr(getattr(self.app_context, 'shared', None), 'base_output_dir', '.')), # 尝试从输出目录开始
            mustexist=True
        )
        if directory:
            logger.info(f"模式9输入目录已选择: {directory}")
            return directory
        else:
            logger.warning("模式9输入目录未选择。")
            return None

    def start_script(self):
        if self.script_thread and self.script_thread.is_alive():
            self.status_label.configure(text="脚本已在运行中。")
            return
        
        # Regardless of the switch, script execution shows logs

        self.image_label.grid_forget()
        self.log_textbox.grid(row=0, column=0, sticky="nsew")
        self._update_log_handler_textbox() # Ensure handler has the textbox
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

        self.status_label.configure(text=f"正在启动模式 {self.current_mode_value}...")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.retry_nikke_button.pack_forget() 

        self.stop_event.clear()
        if self.app_context and hasattr(self.app_context, 'shared'):
            self.app_context.shared.stop_requested = False

        mode_specific_inputs = {}
        
        # GUI适配：为模式9获取输入目录
        if self.current_mode_value == 9:
            # 确保在调用可能依赖 app_context 的方法前，app_context 是可用的
            if not self.app_context:
                self.status_label.configure(text="错误：应用上下文未初始化，无法启动模式9。")
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
                return

            input_dir = self.prompt_for_mode9_input_directory()
            if not input_dir:
                self.status_label.configure(text="模式9启动取消：未选择输入目录。")
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
                # Ensure log textbox is visible if it was hidden by a previous mode selection
                self.log_textbox.grid(row=0, column=0, sticky="nsew")
                self.image_label.grid_forget()
                if hasattr(self.app_context, 'shared') and self.app_context.shared.logger:
                     self.app_context.shared.logger.info("模式9启动取消：用户未选择输入目录。")
                return
            mode_specific_inputs['m9_actual_input_dir'] = input_dir
        
        # Add logic for other mode_specific_inputs if needed, e.g., for mode 7
        if self.current_mode_value == 7:
            # Placeholder: For Mode 7, GUI might need to prompt for target_group_index
            # For now, app.py handles this with input() if not in mode_specific_inputs
            # Example:
            # target_group = ctk.CTkInputDialog(text="请输入目标分组索引 (0-7):", title="模式7 输入").get_input()
            # if target_group is not None:
            #     try:
            #         mode_specific_inputs['target_group_index'] = int(target_group)
            #     except ValueError:
            #         self.status_label.configure(text="模式7错误：分组索引必须是数字。")
            #         self.start_button.configure(state="normal")
            #         self.stop_button.configure(state="disabled")
            #         return
            # else:
            #     self.status_label.configure(text="模式7启动取消：未提供分组索引。")
            #     self.start_button.configure(state="normal")
            #     self.stop_button.configure(state="disabled")
            #     return
            pass # Let app.py handle it for now if not provided by GUI

        self.script_thread = threading.Thread(target=self.execute_script_thread, args=(mode_specific_inputs,), daemon=True)
        self.script_thread.start()

    def execute_script_thread(self, mode_specific_inputs):
        logger = self.app_context.shared.logger if self.app_context and hasattr(self.app_context, 'shared') else logging.getLogger("ExecuteThreadLogger")
        try:
            if not (hasattr(self.app_context.shared, 'nikke_window') and self.app_context.shared.nikke_window):
                if not self.check_nikke_window_status(from_retry=True):
                    logger.error("无法执行脚本：NIKKE 窗口未连接。")
                    self.after(0, self.on_script_finished, "NIKKE 窗口连接失败")
                    return

            execute_mode(self.app_context, self.current_mode_value, mode_specific_inputs)
            final_message = getattr(self.app_context.shared, 'final_message', "脚本执行完成。")
            self.after(0, self.on_script_finished, final_message)
        except Exception as e:
            logger.exception("脚本执行过程中发生错误:")
            self.after(0, self.on_script_finished, f"脚本执行出错: {str(e)[:100]}")

    def on_server_selected(self, selected_display_name):
        selected_title = self.server_options_map.get(selected_display_name)
        logger = None
        if self.app_context and hasattr(self.app_context, 'shared'):
            self.app_context.shared.selected_target_window_title = selected_title
            if hasattr(self.app_context.shared, 'logger') and self.app_context.shared.logger:
                logger = self.app_context.shared.logger
            else: # Fallback logger if shared.logger is not available
                logger = logging.getLogger("ServerSelectLogger")
                # Basic config for fallback logger if it has no handlers
                if not logger.hasHandlers():
                    ch = logging.StreamHandler()
                    ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
                    logger.addHandler(ch)
                    logger.setLevel(logging.INFO)
            
            logger.info(f"服务器已选择: {selected_display_name} (对应标题: {selected_title})")
            # Re-check NIKKE window status as the target might have changed
            self.check_nikke_window_status(from_retry=True)
        else:
            # This case should be rare if __init__ is robust
            print(f"警告: AppContext 或 shared 对象不可用，无法设置服务器选择: {selected_display_name}")


    def request_stop_script(self):
        logger = self.app_context.shared.logger if self.app_context and hasattr(self.app_context, 'shared') else logging.getLogger("StopScriptLogger")
        if self.app_context and hasattr(self.app_context, 'shared'):
            self.app_context.shared.stop_requested = True
            logger.info("用户请求停止脚本...")
        self.stop_event.set() 
        self.status_label.configure(text="正在停止脚本...")
        self.stop_button.configure(state="disabled")

    def on_script_finished(self, message="脚本已结束。"):
        self.status_label.configure(text=message)
        self.start_button.configure(state="normal") # Re-enable start button
        self.stop_button.configure(state="disabled")
        self.script_thread = None

        self.check_nikke_window_status() # Re-check and update UI accordingly

        # After script finishes, restore view based on switch state
        if self.show_image_var.get():
            self._resize_and_display_image() # This will show image and hide log
        else:
            self.image_label.grid_forget() # Ensure image is hidden
            self.log_textbox.grid(row=0, column=0, sticky="nsew") # Ensure log is shown
            self.image_label.configure(image=None, text="图片显示已关闭。\n日志将在此处显示。") # Update text if needed


    def on_closing(self):
        logger = self.app_context.shared.logger if self.app_context and hasattr(self.app_context, 'shared') else logging.getLogger("ClosingLogger")
        if self.script_thread and self.script_thread.is_alive():
            self.request_stop_script()
            # Consider self.script_thread.join(timeout=...) if critical

        try:
            cleanup_application(logger)
        except Exception as e:
            print(f"Error during cleanup: {e}") # Use print if logger itself is problematic
        self.destroy()

    def toggle_image_visibility(self):
        if self.show_image_var.get():
            # Switch is ON, try to display image
            if self.current_asset_image_name: # Only if a mode (and thus image) is selected
                self._resize_and_display_image()
            else: # No mode selected, show placeholder text in image area
                self.log_textbox.grid_forget()
                self.image_label.grid(row=0, column=0, sticky="nsew")
                self.image_label.configure(image=None, text="请选择一个模式以显示图片。")
        else:
            # Switch is OFF, display log area
            self.image_label.grid_forget()
            self.log_textbox.grid(row=0, column=0, sticky="nsew")
            # Update image_label text to indicate it's hidden, even if it's not visible
            self.image_label.configure(image=None, text="图片显示已关闭。\n日志将在此处显示。")
            # If log_textbox is empty, you might want to add a placeholder or ensure it's clear
            # For now, just showing it is enough.
        
        # Log the action
        logger = getattr(getattr(self.app_context, 'shared', None), 'logger', logging.getLogger("GUIToggleLogger"))
        status = "开启" if self.show_image_var.get() else "关闭"
        logger.info(f"用户切换图片显示为: {status}")


class GUILogHandler(logging.Handler):
    def __init__(self, textbox_ref):
        super().__init__()
        self.textbox = textbox_ref # Store the reference, even if initially None

    def emit(self, record):
        if not self.textbox: # Don't try to log if textbox isn't set yet
            print(f"GUILogHandler: Textbox not available. Log: {self.format(record)}")
            return
        
        msg = self.format(record)
        # Ensure operations are thread-safe if emit is called from other threads
        # customtkinter widgets should generally be updated from the main thread.
        # self.textbox.after(0, self._insert_text, msg) # Alternative for thread safety
        
        try:
            self.textbox.configure(state="normal")
            self.textbox.insert("end", msg + "\n")
            self.textbox.see("end") 
            self.textbox.configure(state="disabled")
        except Exception as e:
            # Fallback if textbox operations fail (e.g., widget destroyed)
            print(f"Error writing to GUI log textbox: {e}. Message: {msg}")


if __name__ == '__main__':
    check_admin_and_exit_if_not() # Check for admin rights before starting the app
    app = NikkeGuiApp()
    # Call this after create_widgets has run and self.log_textbox is initialized
    app._update_log_handler_textbox()
    app.mainloop()