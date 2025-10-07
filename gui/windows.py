import customtkinter as ctk  # type: ignore
import ctypes
import json
import os
import logging
from core.file_utils import get_base_path


class SettingsWindow(ctk.CTkToplevel):
    """延迟设置窗口"""

    def __init__(self, master, app_context):
        super().__init__(master)
        self.app_context = app_context
        self.transient(master)
        self.title("延迟设置")
        self.geometry("450x280")
        self.grab_set()

        # 为延迟设置创建 StringVar
        self.delay_gui_startup_var = ctk.StringVar()
        self.delay_after_player_entry_var = ctk.StringVar()
        self.delay_after_team_click_var = ctk.StringVar()
        self.delay_after_click_player_details_var = ctk.StringVar()

        self.create_widgets()
        self.load_delay_settings_to_gui()

    def create_widgets(self):
        """创建设置窗口的组件"""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(2, weight=0)

        # --- Row 0: 脚本启动延迟 ---
        ctk.CTkLabel(main_frame, text="脚本启动延迟(秒):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        info_icon0 = ctk.CTkLabel(main_frame, text=" (?)", text_color="gray", cursor="hand2")
        info_icon0.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="w")
        from gui.components import Tooltip
        Tooltip(info_icon0, "从点击[启动脚本]到激活游戏的等待时间\n用于给你时间进入正确的界面\n如果你习惯先进入正确界面再启动可以设置得很小\n默认值5")
        self.delay_gui_startup_entry = ctk.CTkEntry(main_frame, textvariable=self.delay_gui_startup_var, width=80)
        self.delay_gui_startup_entry.grid(row=0, column=2, padx=5, pady=5, sticky="e")

        # --- Row 1: 点击玩家头像延迟 ---
        ctk.CTkLabel(main_frame, text="点击玩家头像延迟(秒):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        info_icon1 = ctk.CTkLabel(main_frame, text=" (?)", text_color="gray", cursor="hand2")
        info_icon1.grid(row=1, column=1, padx=(0, 5), pady=5, sticky="w")
        Tooltip(info_icon1, "在对阵表中点击玩家头像后的等待时间\n用于等待玩家队伍面板的加载\n程序内置保护时间，理论上可以设置为0，默认值1.5")
        self.delay_after_player_entry_entry = ctk.CTkEntry(main_frame, textvariable=self.delay_after_player_entry_var, width=80)
        self.delay_after_player_entry_entry.grid(row=1, column=2, padx=5, pady=5, sticky="e")

        # --- Row 2: 队伍切换延迟 ---
        ctk.CTkLabel(main_frame, text="队伍切换延迟(秒):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        info_icon2 = ctk.CTkLabel(main_frame, text=" (?)", text_color="gray", cursor="hand2")
        info_icon2.grid(row=2, column=1, padx=(0, 5), pady=5, sticky="w")
        Tooltip(info_icon2, "在玩家队伍界面，切换队伍的时间\n用于等待队伍信息刷新\n内置保护时间，理论上可以设置为0，默认值0.5")
        self.delay_after_team_click_entry = ctk.CTkEntry(main_frame, textvariable=self.delay_after_team_click_var, width=80)
        self.delay_after_team_click_entry.grid(row=2, column=2, padx=5, pady=5, sticky="e")

        # --- Row 3: 玩家详情面板延迟 ---
        ctk.CTkLabel(main_frame, text="玩家详情面板延迟(秒):").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        info_icon3 = ctk.CTkLabel(main_frame, text=" (?)", text_color="gray", cursor="hand2")
        info_icon3.grid(row=3, column=1, padx=(0, 5), pady=5, sticky="w")
        Tooltip(info_icon3, "进入玩家详情面板的等待时间\n需要加载大量数据，网络环境差的可以设置得再大一些\n理论上可以设置为0，但严重不建议\n默认值3")
        self.delay_after_click_player_details_entry = ctk.CTkEntry(main_frame, textvariable=self.delay_after_click_player_details_var, width=80)
        self.delay_after_click_player_details_entry.grid(row=3, column=2, padx=5, pady=5, sticky="e")

        # --- Buttons ---
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=4, column=0, columnspan=3, pady=(20, 0))

        self.save_button = ctk.CTkButton(button_frame, text="保存并关闭", command=self.save_and_close)
        self.save_button.pack(side="left", padx=10)

        self.cancel_button = ctk.CTkButton(button_frame, text="取消", command=self.destroy)
        self.cancel_button.pack(side="left", padx=10)

    def load_delay_settings_to_gui(self):
        """从配置中加载延迟设置到界面"""
        if self.app_context and hasattr(self.app_context, 'shared') and hasattr(self.app_context.shared, 'delay_config'):
            delay_config = self.app_context.shared.delay_config
            self.delay_gui_startup_var.set(str(delay_config.get('gui_startup', 5.0)))
            self.delay_after_player_entry_var.set(str(delay_config.get('after_player_entry', 3.0)))
            self.delay_after_team_click_var.set(str(delay_config.get('after_team_click', 1.5)))
            self.delay_after_click_player_details_var.set(str(delay_config.get('after_click_player_details', 2.5)))

    def save_and_close(self):
        """保存设置并关闭窗口"""
        logger = self.app_context.shared.logger
        try:
            new_gui_startup = float(self.delay_gui_startup_var.get())
            new_after_player_entry = float(self.delay_after_player_entry_var.get())
            new_after_team_click = float(self.delay_after_team_click_var.get())
            new_after_click_player_details = float(self.delay_after_click_player_details_var.get())

            delay_config = self.app_context.shared.delay_config
            delay_config['gui_startup'] = new_gui_startup
            delay_config['after_player_entry'] = new_after_player_entry
            delay_config['after_team_click'] = new_after_team_click
            delay_config['after_click_player_details'] = new_after_click_player_details

            self.app_context.shared.app_config['delay_settings'] = delay_config

            config_filepath = os.path.join(get_base_path(), "config.json")
            with open(config_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.app_context.shared.app_config, f, indent=2, ensure_ascii=False)

            logger.info(f"延迟设置已成功保存到 {config_filepath}")
            self.master.status_label.configure(text="延迟设置已保存！", text_color="green")
            self.destroy()

        except ValueError:
            logger.error("保存延迟设置失败：输入值无效，请输入有效的数字。")
            ctypes.windll.user32.MessageBoxW(self.winfo_id(), "保存失败！\n\n所有延迟值都必须是有效的数字 (例如 3.0 或 5)。", "输入错误", 0x00000010)
        except Exception as e:
            logger.exception("保存延迟设置时发生未知错误:")
            ctypes.windll.user32.MessageBoxW(self.winfo_id(), f"保存延迟设置时发生未知错误:\n\n{e}", "严重错误", 0x00000010)