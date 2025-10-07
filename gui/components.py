import customtkinter as ctk


class Tooltip:
    """
    Creates a tooltip for a given widget.
    """
    def __init__(self, widget, text, wraplength=250):
        self.widget = widget
        self.text = text
        self.wraplength = wraplength
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = ctk.CTkLabel(self.tooltip_window, text=self.text, wraplength=self.wraplength,
                               fg_color=("#F0F0F0", "#303030"), text_color=("#000000", "#FFFFFF"),
                               corner_radius=4, justify="left", padx=8, pady=4)
        label.pack(ipadx=1, ipady=1)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None


class SidebarComponent:
    """侧边栏组件，包含模式选择、服务器选择等"""

    def __init__(self, parent, app_context, on_mode_select, on_server_select):
        self.parent = parent
        self.app_context = app_context
        self.on_mode_select = on_mode_select
        self.on_server_select = on_server_select

        self.sidebar_frame = None
        self.mode_buttons = {}
        self.server_option_menu = None
        self.image_display_switch = None
        self.settings_button = None
        self.current_row = 0

        # 服务器选择配置
        self.server_options_map = {
            "自动": None,
            "国际服": "NIKKE",
            "港澳台": "勝利女神：妮姬",
            "大陆": "胜利女神：新的希望"
        }

        self.create_sidebar()

    def create_sidebar(self):
        """创建侧边栏"""
        self.sidebar_frame = ctk.CTkFrame(self.parent, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")

        # 标题
        sidebar_title = ctk.CTkLabel(self.sidebar_frame, text="NIKKE 应援工具", font=ctk.CTkFont(size=16, weight="bold"))
        sidebar_title.grid(row=self.current_row, column=0, padx=18, pady=(18, 10))
        self.current_row += 1

        # 创建模式按钮
        self.create_mode_buttons()

        # 创建服务器选择
        self.create_server_selection()

        # 创建图像显示开关
        self.create_image_switch()

        # 创建设置按钮
        self.create_settings_button()

        # 在所有组件之后设置权重，将空白区域推到底部
        self.sidebar_frame.grid_rowconfigure(self.current_row, weight=1)

    def create_mode_buttons(self):
        """创建模式选择按钮"""
        if hasattr(self.app_context, 'shared') and hasattr(self.app_context.shared, 'available_modes'):
            if self.app_context.shared.available_modes:
                all_enabled_modes = sorted(
                    [m for m in self.app_context.shared.available_modes if m.get('enabled', True)],
                    key=lambda x: x.get('id', float('inf'))
                )
                modes_map = {m['id']: m for m in all_enabled_modes}

                # 模式分组配置
                ordered_groups_config = [
                    {"name": "应援专用", "description": None, "ids": [1, 2, 3]},
                    {"name": "赛前总览用", "description": None, "ids": [41, 4, 5]},
                    {"name": "赛果分析用", "description": None, "ids": [6, 7, 8]},
                    {"name": "图片处理", "description": None, "ids": [9]}
                ]

                for group_config in ordered_groups_config:
                    group_name = group_config["name"]
                    description = group_config["description"]

                    modes_for_this_group_obj = []
                    for m_id in group_config["ids"]:
                        if m_id in modes_map:
                            modes_for_this_group_obj.append(modes_map[m_id])

                    if not modes_for_this_group_obj and not description:
                        continue

                    # 分组标签
                    group_label = ctk.CTkLabel(self.sidebar_frame, text=group_name, font=ctk.CTkFont(weight="bold"))
                    group_label.grid(row=self.current_row, column=0, padx=20, pady=(8, 5), sticky="w")
                    self.current_row += 1

                    if description:
                        desc_label = ctk.CTkLabel(self.sidebar_frame, text=description, font=ctk.CTkFont(size=11), anchor="w", justify="left")
                        desc_label.grid(row=self.current_row, column=0, padx=20, pady=(0, 4), sticky="w")
                        self.current_row += 1

                    # 模式按钮
                    if modes_for_this_group_obj:
                        for mode_meta in modes_for_this_group_obj:
                            mode_id = mode_meta['id']
                            btn_text = mode_meta.get('name', f"模式 {mode_id}")

                            btn = ctk.CTkButton(self.sidebar_frame, text=btn_text, height=16, font=ctk.CTkFont(size=12))
                            btn.grid(row=self.current_row, column=0, padx=20, pady=3, sticky="ew")
                            self.mode_buttons[mode_id] = btn
                            btn.configure(command=lambda m_id=mode_id: self.on_mode_select(m_id, self.mode_buttons.get(m_id)))
                            self.current_row += 1
            else:
                no_modes_label = ctk.CTkLabel(self.sidebar_frame, text="没有可用的模式。", font=ctk.CTkFont(slant="italic"))
                no_modes_label.grid(row=self.current_row, column=0, padx=20, pady=10)
                self.current_row += 1

    def create_server_selection(self):
        """创建服务器选择下拉菜单"""
        server_label = ctk.CTkLabel(self.sidebar_frame, text="服务器选择:", font=ctk.CTkFont(weight="bold"))
        server_label.grid(row=self.current_row, column=0, padx=20, pady=(10, 5), sticky="w")
        self.current_row += 1

        server_display_options = list(self.server_options_map.keys())
        server_selection_var = ctk.StringVar(value=server_display_options[0])

        self.server_option_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=server_display_options,
            variable=server_selection_var,
            command=self.on_server_select
        )
        self.server_option_menu.grid(row=self.current_row, column=0, padx=20, pady=5, sticky="ew")
        self.current_row += 1

    def create_image_switch(self):
        """创建图像显示开关"""
        switch_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        switch_frame.grid(row=self.current_row, column=0, padx=20, pady=(10, 5), sticky="ew")
        self.current_row += 1

        switch_frame.grid_columnconfigure(0, weight=0)
        switch_frame.grid_columnconfigure(1, weight=1)

        image_switch_label = ctk.CTkLabel(switch_frame, text="显示指引图像:", font=ctk.CTkFont(weight="bold"))
        image_switch_label.grid(row=0, column=0, sticky="w")

        self.image_display_switch = ctk.CTkSwitch(
            switch_frame,
            text="开/关",
            command=self.on_image_toggle
        )
        self.image_display_switch.grid(row=0, column=1, sticky="w")

    def create_settings_button(self):
        """创建设置按钮"""
        self.settings_button = ctk.CTkButton(self.sidebar_frame, text="延迟配置", command=self.on_settings_click)
        self.settings_button.grid(row=self.current_row, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.current_row += 1

    def on_image_toggle(self):
        """图像开关切换回调，由主应用重写"""
        pass

    def on_settings_click(self):
        """设置按钮点击回调，由主应用重写"""
        pass

    def get_frame(self):
        """获取侧边栏框架"""
        return self.sidebar_frame

    def get_mode_buttons(self):
        """获取模式按钮字典"""
        return self.mode_buttons

    def get_server_options_map(self):
        """获取服务器选项映射"""
        return self.server_options_map


class StatusComponent:
    """状态显示组件"""

    def __init__(self, parent, on_retry_nikke):
        self.parent = parent
        self.on_retry_nikke = on_retry_nikke

        self.status_label = None
        self.nikke_window_status_label = None
        self.shortcut_info_label = None
        self.retry_nikke_button = None

        self.create_status_widgets()

    def create_status_widgets(self):
        """创建状态显示组件"""
        status_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        status_frame.grid(row=0, column=0, sticky="ew", padx=(0,10))

        self.status_label = ctk.CTkLabel(status_frame, text="准备就绪", anchor="w")
        self.status_label.pack(pady=2, fill="x")

        self.nikke_window_status_label = ctk.CTkLabel(status_frame, text="NIKKE 窗口: 未连接", anchor="w")
        self.nikke_window_status_label.pack(pady=2, fill="x")

        self.shortcut_info_label = ctk.CTkLabel(status_frame, text="可随时按 Ctrl +1 强制中止脚本", anchor="w", text_color="gray")
        self.shortcut_info_label.pack(pady=2, fill="x")

        self.retry_nikke_button = ctk.CTkButton(status_frame, text="重试连接 NIKKE", command=self.on_retry_nikke, width=120)
        self.retry_nikke_button.pack(pady=(5,0), fill="x")

    def update_status(self, text, color=None):
        """更新状态标签"""
        if self.status_label:
            self.status_label.configure(text=text)
            if color:
                self.status_label.configure(text_color=color)

    def update_nikke_status(self, text, color=None):
        """更新NIKKE窗口状态"""
        if self.nikke_window_status_label:
            self.nikke_window_status_label.configure(text=text)
            if color:
                self.nikke_window_status_label.configure(text_color=color)


class ControlButtonComponent:
    """控制按钮组件"""

    def __init__(self, parent, on_start_script, on_stop_script):
        self.parent = parent
        self.on_start_script = on_start_script
        self.on_stop_script = on_stop_script

        self.start_button = None
        self.stop_button = None

        self.create_buttons()

    def create_buttons(self):
        """创建控制按钮"""
        button_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        button_frame.grid(row=0, column=1, sticky="e")

        self.start_button = ctk.CTkButton(
            button_frame,
            text="启动脚本",
            command=self.on_start_script,
            width=100,
            fg_color="green",
            font=ctk.CTkFont(weight="bold")
        )
        self.start_button.pack(side="left", padx=(0,10), pady=10)

        self.stop_button = ctk.CTkButton(
            button_frame,
            text="停止脚本",
            command=self.on_stop_script,
            state="disabled",
            width=100
        )
        self.stop_button.pack(side="left", pady=10)

    def set_start_enabled(self, enabled):
        """设置启动按钮状态"""
        if self.start_button:
            self.start_button.configure(state="normal" if enabled else "disabled")

    def set_stop_enabled(self, enabled):
        """设置停止按钮状态"""
        if self.stop_button:
            self.stop_button.configure(state="normal" if enabled else "disabled")


class AppearanceComponent:
    """外观设置组件"""

    def __init__(self, parent, on_appearance_change, on_settings_click):
        self.parent = parent
        self.on_appearance_change = on_appearance_change
        self.on_settings_click = on_settings_click

        self.settings_button = None
        self.appearance_mode_menu = None

        self.create_appearance_widgets()

    def create_appearance_widgets(self):
        """创建外观设置组件"""
        appearance_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        appearance_frame.grid(row=0, column=2, sticky="e", padx=(10, 0))

        self.settings_button = ctk.CTkButton(appearance_frame, text="延迟配置", command=self.on_settings_click, width=110)
        self.settings_button.pack(side="left", padx=(0, 10))

        appearance_label = ctk.CTkLabel(appearance_frame, text="外观模式:", anchor="w")
        appearance_label.pack(side="left", padx=(0, 5))

        appearance_mode_options = ["Light", "Dark", "System"]
        initial_mode = "System"

        self.appearance_mode_menu = ctk.CTkOptionMenu(
            appearance_frame,
            values=appearance_mode_options,
            command=self.on_appearance_change,
            width=110
        )
        self.appearance_mode_menu.set(initial_mode)
        self.appearance_mode_menu.pack(side="left")

    def set_initial_mode(self, mode):
        """设置初始外观模式"""
        if self.appearance_mode_menu:
            self.appearance_mode_menu.set(mode)