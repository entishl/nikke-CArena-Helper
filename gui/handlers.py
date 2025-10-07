import json
import os
import ctypes
import logging
from core.utils import get_base_path


class EventHandler:
    """事件处理器类"""

    def __init__(self, app_context, app_instance):
        self.app_context = app_context
        self.app_instance = app_instance

    def handle_mode_select(self, mode_value, pressed_button):
        """处理模式选择事件"""
        self.app_instance.current_mode_value = mode_value

        selected_mode_name = f"模式 {mode_value}"
        asset_image_name = f"{mode_value}.png"

        if hasattr(self.app_context, 'shared') and self.app_context.shared.available_modes:
            for mode_meta in self.app_context.shared.available_modes:
                if mode_meta.get('id') == mode_value:
                    selected_mode_name = mode_meta.get('name', selected_mode_name)
                    asset_image_name = mode_meta.get('asset_image', asset_image_name)
                    break

        # 更新状态标签
        self.app_instance.status_component.update_status(f"已选择模式: {selected_mode_name}")

        # 更新按钮状态
        if hasattr(self.app_instance, '_current_selected_button') and self.app_instance._current_selected_button:
            self.app_instance._current_selected_button.configure(
                fg_color=self.app_instance.theme_manager.theme["CTkButton"]["fg_color"]
            )
        if pressed_button:
            pressed_button.configure(
                fg_color=self.app_instance.theme_manager.theme["CTkButton"]["hover_color"]
            )
            self.app_instance._current_selected_button = pressed_button

        # 设置当前图像名称并显示
        self.app_instance.image_manager.set_current_image_name(asset_image_name)
        if self.app_instance.sidebar_component.image_display_switch.get():
            self.app_instance.image_manager.display_image()
        else:
            self.app_instance.image_manager.hide_image()
            self.app_instance.log_component.show_log()

    def handle_server_select(self, selected_display_name):
        """处理服务器选择事件"""
        server_options_map = self.app_instance.sidebar_component.get_server_options_map()
        selected_title = server_options_map.get(selected_display_name)

        logger = self._get_logger()
        if self.app_context and hasattr(self.app_context, 'shared'):
            self.app_context.shared.selected_target_window_title = selected_title

            if logger:
                logger.info(f"服务器已选择: {selected_display_name} (对应标题: {selected_title})")
            # 重新检查NIKKE窗口状态
            self.app_instance.window_checker.check_nikke_window_status(from_retry=True)
        else:
            print(f"警告: AppContext 或 shared 对象不可用，无法设置服务器选择: {selected_display_name}")

    def handle_appearance_change(self, new_appearance_mode: str):
        """处理外观模式变更事件"""
        logger = self._get_logger()

        try:
            import customtkinter as ctk
            ctk.set_appearance_mode(new_appearance_mode)

            if logger:
                logger.info(f"外观模式已切换为: {new_appearance_mode}")

            # 保存新设置到配置文件
            if hasattr(self.app_context, 'shared') and self.app_context.shared.app_config:
                if 'global_settings' not in self.app_context.shared.app_config:
                    self.app_context.shared.app_config['global_settings'] = {}

                self.app_context.shared.app_config['global_settings']['appearance_mode'] = new_appearance_mode

                config_filepath = os.path.join(get_base_path(), "config.json")
                with open(config_filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.app_context.shared.app_config, f, indent=2, ensure_ascii=False)

                if logger:
                    logger.info(f"外观模式设置已保存到 {config_filepath}")

                self.app_instance.status_component.update_status(
                    f"外观模式已切换为 {new_appearance_mode} 并保存。",
                    "green"
                )
            else:
                if logger:
                    logger.warning("无法保存外观模式：app_context 或 app_config 不可用。")
                self.app_instance.status_component.update_status("外观模式已切换，但无法保存。", "orange")

        except Exception as e:
            if logger:
                logger.exception("切换外观模式时发生错误:")
            self.app_instance.status_component.update_status(f"切换外观模式失败: {e}", "red")

    def handle_settings_click(self):
        """处理设置按钮点击事件"""
        if not hasattr(self.app_instance, 'settings_window') or \
           not self.app_instance.settings_window or \
           not self.app_instance.settings_window.winfo_exists():
            from gui.windows import SettingsWindow
            self.app_instance.settings_window = SettingsWindow(self.app_instance, self.app_context)
        else:
            self.app_instance.settings_window.focus()

    def handle_image_toggle(self):
        """处理图像显示开关事件"""
        if self.app_instance.sidebar_component.image_display_switch.get():
            # 开关为ON，显示图像
            if self.app_instance.image_manager.has_current_image():
                self.app_instance.image_manager.display_image()
            else:
                self.app_instance.image_manager.hide_image()
                self.app_instance.log_component.show_log()
                self.app_instance.image_manager.set_placeholder_text("请选择一个模式以显示图片。")
        else:
            # 开关为OFF，显示日志区域
            self.app_instance.image_manager.hide_image()
            self.app_instance.log_component.show_log()
            self.app_instance.image_manager.set_placeholder_text("图片显示已关闭。\n日志将在此处显示。")

        logger = self._get_logger()
        status = "开启" if self.app_instance.sidebar_component.image_display_switch.get() else "关闭"
        if logger:
            logger.info(f"用户切换图片显示为: {status}")

    def handle_retry_nikke(self):
        """处理重试连接NIKKE事件"""
        self.app_instance.window_checker.check_nikke_window_status(from_retry=True)

    def handle_start_script(self):
        """处理启动脚本事件"""
        if self.app_instance.script_runner.is_running():
            self.app_instance.status_component.update_status("脚本已在运行中。")
            return

        # 显示日志区域
        self.app_instance.image_manager.hide_image()
        self.app_instance.log_component.show_log()
        self.app_instance.log_component.clear_log()

        self.app_instance.status_component.update_status(f"正在启动模式 {self.app_instance.current_mode_value}...")
        self.app_instance.control_buttons.set_start_enabled(False)
        self.app_instance.control_buttons.set_stop_enabled(True)

        # 重置停止标志
        self.app_instance.script_runner.reset_stop_flag()

        # 获取模式特定输入
        mode_specific_inputs = self._get_mode_specific_inputs()
        if mode_specific_inputs is None:  # 用户取消
            self._cancel_script_start()
            return

        # 启动脚本
        self.app_instance.script_runner.start_script(
            self.app_instance.current_mode_value,
            mode_specific_inputs
        )

    def handle_stop_script(self):
        """处理停止脚本事件"""
        logger = self._get_logger()
        if self.app_context and hasattr(self.app_context, 'shared'):
            self.app_context.shared.stop_requested = True
            if logger:
                logger.info("用户请求停止脚本...")

        self.app_instance.script_runner.set_stop_flag()
        self.app_instance.status_component.update_status("正在停止脚本...")
        self.app_instance.control_buttons.set_stop_enabled(False)

    def _get_logger(self):
        """获取日志记录器"""
        if self.app_context and hasattr(self.app_context, 'shared') and self.app_context.shared.logger:
            return self.app_context.shared.logger
        return logging.getLogger("EventHandlerLogger")

    def _get_mode_specific_inputs(self):
        """获取模式特定输入"""
        mode_specific_inputs = {}

        # 模式9：输入目录
        if self.app_instance.current_mode_value == 9:
            if not self.app_context:
                self.app_instance.status_component.update_status("错误：应用上下文未初始化，无法启动模式9。")
                self._cancel_script_start()
                return None

            input_dir = self.app_instance.script_runner.prompt_for_mode9_input_directory()
            if not input_dir:
                self.app_instance.status_component.update_status("模式9启动取消：未选择输入目录。")
                self._cancel_script_start()

                logger = self._get_logger()
                if logger:
                    logger.info("模式9启动取消：用户未选择输入目录。")
                return None

            mode_specific_inputs['m9_actual_input_dir'] = input_dir

        # 模式7：目标分组索引（预留，目前由app.py处理）
        if self.app_instance.current_mode_value == 7:
            # 预留：可以在这里添加GUI输入对话框
            pass

        return mode_specific_inputs

    def _cancel_script_start(self):
        """取消脚本启动"""
        self.app_instance.control_buttons.set_start_enabled(True)
        self.app_instance.control_buttons.set_stop_enabled(False)

        # 确保日志文本框可见
        self.app_instance.log_component.show_log()
        self.app_instance.image_manager.hide_image()


class WindowStatusChecker:
    """窗口状态检查器"""

    def __init__(self, app_context, status_component, control_buttons):
        self.app_context = app_context
        self.status_component = status_component
        self.control_buttons = control_buttons

    def check_nikke_window_status(self, from_retry=False):
        """检查NIKKE窗口状态"""
        if not self.status_component.nikke_window_status_label:
            return False

        # 检查窗口宽高比的辅助函数
        def _check_and_warn_aspect_ratio(window_obj):
            if not window_obj:
                return

            try:
                # 尝试获取窗口句柄
                import ctypes.wintypes
                hwnd = getattr(window_obj, '_hWnd', None)
                if not hwnd:
                    width = window_obj.width
                    height = window_obj.height
                    logger = self._get_logger()
                    if logger:
                        logger.warning("无法获取窗口句柄 (HWND)，将使用完整窗口尺寸进行宽高比检查。")
                else:
                    rect = ctypes.wintypes.RECT()
                    if ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect)):
                        width = rect.right - rect.left
                        height = rect.bottom - rect.top
                    else:
                        width = window_obj.width
                        height = window_obj.height
                        logger = self._get_logger()
                        if logger:
                            logger.warning("GetClientRect 调用失败，将使用完整窗口尺寸进行宽高比检查。")

                logger = self._get_logger()
                if height == 0:
                    if logger:
                        logger.warning("NIKKE 窗口高度为0，无法检查宽高比。")
                    return

                target_ratio = 16.0 / 9.0
                current_ratio = float(width) / height

                # 允许约2%的偏差
                if abs(current_ratio - target_ratio) > 0.02:
                    ctypes.windll.user32.MessageBoxW(
                        0,
                        "当前 NIKKE 窗口非 16:9，截图可能错误。",
                        "窗口比例提示",
                        0x00000030 | 0x00000000
                    )
            except AttributeError:
                logger = self._get_logger()
                if logger:
                    logger.warning("无法获取 NIKKE 窗口的 width/height 属性来检查宽高比。")
            except Exception as e_ratio_check:
                logger = self._get_logger()
                if logger:
                    logger.error(f"检查 NIKKE 窗口宽高比时发生内部错误: {e_ratio_check}")

        # 如果已经连接且不是重试，确认状态并检查比例
        if not from_retry and self.app_context and hasattr(self.app_context, 'shared') and self.app_context.shared.nikke_window:
            _check_and_warn_aspect_ratio(self.app_context.shared.nikke_window)
            self.status_component.update_nikke_status("NIKKE 窗口: 已连接", "green")
            if self.control_buttons:
                self.control_buttons.set_start_enabled(True)
            return True

        if self.app_context:
            try:
                logger = self._get_logger()

                if from_retry:
                    if logger:
                        logger.info("尝试重新连接 NIKKE 窗口...")
                    else:
                        print("尝试重新连接 NIKKE 窗口...")

                    # 重新运行应用环境设置以查找窗口
                    from app import setup_app_environment
                    setup_app_environment(self.app_context)

                if hasattr(self.app_context.shared, 'nikke_window') and self.app_context.shared.nikke_window:
                    _check_and_warn_aspect_ratio(self.app_context.shared.nikke_window)
                    self.status_component.update_nikke_status("NIKKE 窗口: 已连接", "green")
                    if self.control_buttons:
                        self.control_buttons.set_start_enabled(True)
                    return True
                else:
                    self.status_component.update_nikke_status(
                        "NIKKE 窗口: 未找到! 请确保游戏运行且未最小化。",
                        "red"
                    )
                    if self.control_buttons:
                        self.control_buttons.set_start_enabled(False)
                    return False
            except Exception as e:
                self.status_component.update_nikke_status("NIKKE 窗口: 连接出错", "red")
                logger = self._get_logger()
                if logger:
                    logger.error(f"Error checking NIKKE window: {e}")
                else:
                    print(f"Error checking NIKKE window: {e}")
                if self.control_buttons:
                    self.control_buttons.set_start_enabled(False)
                return False
        return False

    def _get_logger(self):
        """获取日志记录器"""
        if self.app_context and hasattr(self.app_context, 'shared') and self.app_context.shared.logger:
            return self.app_context.shared.logger
        return logging.getLogger("WindowCheckerLogger")