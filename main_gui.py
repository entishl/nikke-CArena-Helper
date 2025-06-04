import logging
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import threading
import time
import sys
import os

# Placeholder for main.py's main logic function and other components
# These will be properly imported and used after main.py is refactored.
# For example:
# import main as nikke_script

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NIKKE 脚本 GUI")
        self.geometry("600x500") # Increased height for admin status and logs
        ctk.set_appearance_mode("System") 
        ctk.set_default_color_theme("blue")

        self.script_thread = None
        self.stop_event = threading.Event()
        self.nikke_script_module = None # To store imported main.py module

        # Frame for mode selection
        self.mode_frame = ctk.CTkFrame(self)
        self.mode_frame.pack(pady=10, padx=20, fill="x")

        self.mode_label = ctk.CTkLabel(self.mode_frame, text="选择运行模式:")
        self.mode_label.pack(side="left", padx=10)

        self.modes = {
            "1: 买马预测模式": 1,
            "2: 复盘模式": 2,
            "3: 反买存档模式": 3,
            "4: 64进8专用模式": 4,
            "5: 冠军争霸模式": 5,
            "6: C_Arena - 完整分组赛": 6,
            "7: C_Arena - 单一分组赛": 7,
            "8: C_Arena - 冠军锦标赛": 8,
            "9: 图片处理与打包": 9,
        }
        self.mode_var = tk.StringVar(value=list(self.modes.keys())[0])
        self.mode_dropdown = ctk.CTkOptionMenu(self.mode_frame, variable=self.mode_var, values=list(self.modes.keys()))
        self.mode_dropdown.pack(side="left", expand=True, fill="x", padx=10)

        # Frame for buttons
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(pady=10, padx=20, fill="x")

        self.start_button = ctk.CTkButton(self.button_frame, text="启动脚本", command=self.start_script)
        self.start_button.pack(side="left", expand=True, padx=5)

        self.stop_button = ctk.CTkButton(self.button_frame, text="停止脚本", command=self.request_stop_script, state="disabled")
        self.stop_button.pack(side="left", expand=True, padx=5)
        
        # Log Text Area
        self.log_textbox = ctk.CTkTextbox(self, height=250, state="disabled", wrap="word")
        self.log_textbox.pack(pady=10, padx=20, fill="both", expand=True)

        # Admin status
        self.admin_status_label = ctk.CTkLabel(self, text="管理员权限: 正在检查...")
        self.admin_status_label.pack(pady=(5, 10))
        
        self.load_nikke_script_module()
        if self.nikke_script_module:
            self.check_admin_status()
            # Setup logging to redirect to GUI
            self.setup_gui_logging()


    def load_nikke_script_module(self):
        try:
            import main as nikke_script
            self.nikke_script_module = nikke_script
            self.log_message("成功加载 main.py 模块。\n")
        except ImportError as e:
            self.log_message(f"错误: 无法加载 main.py 模块: {e}\n请确保 main.py 在同一目录下且无导入错误。\n")
        except Exception as e:
            self.log_message(f"加载 main.py 时发生未知错误: {e}\n")

    def log_message(self, message):
        if not self.log_textbox.winfo_exists(): return # Avoid error if widget is destroyed
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", str(message))
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def setup_gui_logging(self):
        if not self.nikke_script_module:
            return
        
        # Get the root logger from main.py (or the logger it uses)
        # This assumes main.py's logging is accessible and can have handlers added.
        # A more robust way would be for main.py to provide a function to add a log handler.
        logger = self.nikke_script_module.logging.getLogger() # Get root logger used by main.py
        
        # Remove existing StreamHandlers to avoid duplicate console output if main.py also logs to console
        for handler in logger.handlers[:]:
            if isinstance(handler, self.nikke_script_module.logging.StreamHandler) and handler.stream == sys.stdout: # or sys.stderr
                 logger.removeHandler(handler)

        gui_log_handler = GUILogHandler(self.log_message)
        # You might want to set a specific format for the GUI logger
        formatter = self.nikke_script_module.logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        gui_log_handler.setFormatter(formatter)
        
        logger.addHandler(gui_log_handler)
        logger.setLevel(self.nikke_script_module.logging.INFO) # Ensure logger level is appropriate
        self.log_message("GUI 日志记录器已设置。\n")


    def start_script(self):
        if not self.nikke_script_module:
            self.log_message("错误: main.py 模块未加载，无法启动脚本。\n")
            return

        if self.script_thread and self.script_thread.is_alive():
            self.log_message("脚本已在运行中。\n")
            return

        selected_mode_text = self.mode_var.get()
        selected_mode_value = self.modes[selected_mode_text]
        
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end") 
        self.log_textbox.configure(state="disabled")

        self.log_message(f"准备启动模式 {selected_mode_value}: {selected_mode_text}\n")
        
        # 5秒倒计时
        self.log_message("脚本将在5秒后启动... 请准备好 NIKKE 窗口。\n")
        self.start_button.configure(state="disabled")
        self.mode_dropdown.configure(state="disabled")
        
        self.after(1000, lambda: self.countdown(4)) # Start countdown from 4

    def countdown(self, count):
        if count > 0:
            self.log_message(f"...{count}\n")
            self.after(1000, lambda: self.countdown(count - 1))
        else:
            self.log_message("启动脚本...\n")
            self.execute_script_thread()

    def execute_script_thread(self):
        selected_mode_text = self.mode_var.get()
        selected_mode_value = self.modes[selected_mode_text]

        self.stop_event.clear()
        # start_button and mode_dropdown are already disabled
        self.stop_button.configure(state="normal")

        self.script_thread = threading.Thread(target=self.run_script_target, args=(selected_mode_value,))
        self.script_thread.daemon = True 
        self.script_thread.start()
        
        self.after(100, self.check_script_thread_status)

    def run_script_target(self, mode_value):
        try:
            # This is where the refactored main.py logic is called
            self.nikke_script_module.run_selected_mode(mode_value, self.stop_event, self.log_message)
        except AttributeError:
             self.log_message("错误: 'run_selected_mode' 函数未在 main.py 中定义或 main.py 未正确加载。\n请确保 main.py 已按要求修改。\n")
        except Exception as e:
            self.log_message(f"脚本执行出错: {e}\n")
            import traceback
            self.log_message(traceback.format_exc() + "\n")
        finally:
            self.after(0, self.on_script_finished)


    def check_script_thread_status(self):
        if self.script_thread and self.script_thread.is_alive():
            self.after(100, self.check_script_thread_status)
        # No explicit else needed, on_script_finished handles UI update

    def on_script_finished(self):
        """Called when the script thread finishes."""
        if not self.stop_event.is_set() and (not self.script_thread or not self.script_thread.is_alive()):
             # Only log "完毕" if not stopped by user and thread is actually done
             # The script itself should log its completion status.
             pass
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.mode_dropdown.configure(state="normal")
        self.stop_event.clear() # Clear event for next run

    def request_stop_script(self):
        if self.script_thread and self.script_thread.is_alive():
            self.log_message("正在发送停止信号...\n")
            self.stop_event.set() 
            # The script thread should detect this and stop.
            # UI updates will happen in on_script_finished when thread actually exits.
        else:
            self.log_message("没有正在运行的脚本。\n")
            self.stop_button.configure(state="disabled") # Ensure it's disabled if no script

    def check_admin_status(self):
        if not self.nikke_script_module:
            self.admin_status_label.configure(text="管理员权限: main.py 未加载")
            return
        try:
            if self.nikke_script_module.is_admin():
                self.admin_status_label.configure(text="管理员权限: 是", text_color="green")
            else:
                self.admin_status_label.configure(text="管理员权限: 否 (脚本可能无法正常工作!)", text_color="red")
                self.log_message("警告: 脚本未以管理员权限运行，可能导致功能异常。\n")
        except AttributeError:
            self.admin_status_label.configure(text="管理员权限: 检查函数未找到")
            self.log_message("错误: is_admin 函数未在 main.py 中定义。\n")
        except Exception as e:
            self.admin_status_label.configure(text=f"管理员权限: 检查出错 {e}")


# Custom Log Handler for redirecting logs to GUI
class GUILogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        msg = self.format(record)
        self.callback(msg + "\n")


if __name__ == "__main__":
    # This check should ideally be in main.py if it's run directly,
    # but for GUI, it's better to inform within the GUI.
    # For now, main.py's own admin check will run if it's refactored correctly.
    app = App()
    app.mainloop()