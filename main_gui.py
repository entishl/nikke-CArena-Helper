import logging
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import threading
import time
import sys
import os
import keyboard
from PIL import Image, ImageTk

def resource_path(relative_path_to_join):
    """
    获取资源的绝对路径，适用于开发环境和 PyInstaller 打包后。
    relative_path_to_join 应该是像 "assets/image.png" 这样的路径。
    """
    if hasattr(sys, 'frozen'):  # Bundled by PyInstaller
        if hasattr(sys, '_MEIPASS'):
            # --onefile mode: base_path is the temp extraction folder
            base_path = sys._MEIPASS
        else:
            # Directory mode: base_path is the directory of the executable
            base_path = os.path.dirname(sys.executable)
    else:
        # Development mode: base_path is the script's current working directory (os.abspath("."))
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path_to_join)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NIKKE 冠军竞技场截图助手")
        self.geometry("800x600")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.script_thread = None
        self.stop_event = threading.Event()
        self.nikke_script_module = None
        self.current_mode_value = 1 # Default mode
        self.image_cache = {} # For caching loaded images

        # Main layout frames
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.main_frame.grid_columnconfigure(0, weight=1) # Sidebar
        self.main_frame.grid_columnconfigure(1, weight=3) # Content area
        self.main_frame.grid_rowconfigure(0, weight=1)

        # --- Left Sidebar (Mode Selection) ---
        self.sidebar_frame = ctk.CTkFrame(self.main_frame, width=200)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.sidebar_frame.grid_propagate(False) # Prevent frame from shrinking

        self.sidebar_title = ctk.CTkLabel(self.sidebar_frame, text="模式选择", font=ctk.CTkFont(size=16, weight="bold"))
        self.sidebar_title.pack(pady=10)

        self.modes_structure = {
            "应援用": [
                ("模式 1: 应援预测", 1),
                ("模式 2: 应援复盘", 2),
                ("模式 3: 应援预测", 3),
            ],
            "预测用": [
                ("模式 4: 晋级赛当前小组总览", 4),
                ("模式 5: 冠军赛总览", 5),
            ],
            "分析用": [
                ("模式 6: 晋级赛赛果（共8组）", 6),
                ("模式 7: 晋级赛当前小组赛果", 7),
                ("模式 8: 冠军赛赛果", 8),
            ],
            "图片处理": [
                ("模式 9: 图片标准化和打包", 9),
            ]
        }
        
        self.mode_buttons = []
        for category, modes_in_category in self.modes_structure.items():
            category_label = ctk.CTkLabel(self.sidebar_frame, text=category, font=ctk.CTkFont(size=13, weight="bold"))
            category_label.pack(pady=(10, 2), anchor="w", padx=10)
            for mode_text, mode_val in modes_in_category:
                btn = ctk.CTkButton(
                    self.sidebar_frame,
                    text=mode_text,
                    command=lambda v=mode_val, b=None: self.select_mode(v, b) # b will be set later
                )
                btn.pack(fill="x", padx=10, pady=2)
                self.mode_buttons.append((btn, mode_val)) # Store button and its mode value
        
        # Assign the button instance to the lambda after all buttons are created
        for btn_widget, mode_val in self.mode_buttons:
            btn_widget.configure(command=lambda v=mode_val, b=btn_widget: self.select_mode(v, b))


        # --- Right Content Area ---
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1) # Image/Log area
        self.content_frame.grid_rowconfigure(1, weight=0) # Control area
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Image/Log display area (using a CTkFrame to switch between image and log)
        self.display_area = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.display_area.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.display_area.grid_propagate(False) # Prevent display_area from resizing due to its children
        self.display_area.grid_rowconfigure(0, weight=1)
        self.display_area.grid_columnconfigure(0, weight=1)


        self.image_label = ctk.CTkLabel(self.display_area, text="")
        # self.image_label.grid(row=0, column=0, sticky="nsew") # Use grid for image_label
        
        self.log_textbox = ctk.CTkTextbox(self.display_area, state="disabled", wrap="word")
        # self.log_textbox.grid(row=0, column=0, sticky="nsew") # Use grid for log_textbox
        # Initially, one will be gridded, the other removed from grid.

        # Control area (bottom part of content_frame)
        self.control_area = ctk.CTkFrame(self.content_frame, height=130) # Increased height
        self.control_area.grid(row=1, column=0, sticky="sew", padx=5, pady=(0,5))
        self.control_area.grid_propagate(False)
        self.control_area.grid_columnconfigure((0,1), weight=1)
        self.control_area.grid_rowconfigure((0,1), weight=1)


        self.status_label = ctk.CTkLabel(self.control_area, text="提示: 先进入所选模式的对应界面再点击运行\n 可随时通过 Ctrl + 1 终止脚本运行")
        self.status_label.grid(row=0, column=0, columnspan=2, pady=(5,2), padx=10, sticky="ew")
        
        self.admin_status_label = ctk.CTkLabel(self.control_area, text="管理员权限: 正在检查...")
        self.admin_status_label.grid(row=1, column=0, columnspan=2, pady=(0,5), padx=10, sticky="ew")

        self.start_button = ctk.CTkButton(self.control_area, text="启动脚本", command=self.start_script)
        self.start_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.stop_button = ctk.CTkButton(self.control_area, text="停止脚本", command=self.request_stop_script, state="disabled")
        self.stop_button.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.load_nikke_script_module()
        if self.nikke_script_module:
            self.check_admin_status()
            self.setup_gui_logging()
        
        self.setup_hotkey()
        # Delay initial mode selection and image loading
        self.after_idle(lambda: self.select_mode(self.current_mode_value, self.mode_buttons[0][0]))

    def setup_hotkey(self):
        try:
            keyboard.add_hotkey('ctrl+1', self.request_stop_script_from_hotkey)
            self.log_message("快捷键 Ctrl + 1 已设置为停止脚本。\n", internal=True)
        except Exception as e:
            self.log_message(f"警告: 设置快捷键 Ctrl+1 失败: {e}\n", internal=True)

    def request_stop_script_from_hotkey(self):
        # This method is called from a non-GUI thread (keyboard listener)
        # We need to schedule the GUI update using self.after
        self.after(0, self.request_stop_script)


    def select_mode(self, mode_value, pressed_button):
        self.current_mode_value = mode_value
        self.log_message(f"已选择模式 {mode_value}\n", internal=True) # Log internally, not to main log if script not running
        
        # Update button appearances
        for btn, val in self.mode_buttons:
            if btn == pressed_button:
                btn.configure(fg_color=("#2d6294", "#0e3c71")) # Highlight color
            else:
                btn.configure(fg_color=("#3B8ED0", "#1F6AA5")) # Default CTkButton color

        if not (self.script_thread and self.script_thread.is_alive()):
            self.show_image_for_mode(mode_value)

    def show_image_for_mode(self, mode_value):
        self.log_textbox.grid_remove()  # Hide log by removing from grid
        self.image_label.grid(row=0, column=0, sticky="nsew") # Show image label

        # Use resource_path to get the correct path to assets
        image_path = resource_path(os.path.join("assets", f"{mode_value}.png"))
        logging.debug(f"Attempting to load image from: {image_path}")
        
        # Forcing display_area to update its size before getting width/height
        self.display_area.update_idletasks()
        area_width = self.display_area.winfo_width()
        area_height = self.display_area.winfo_height()

        logging.debug(f"Display area for mode {mode_value}: {area_width}x{area_height}")

        # If area is still too small (e.g., during initial setup), use a minimum sensible size for calculation
        min_render_width = 150
        min_render_height = 150
        if area_width < min_render_width:
            logging.debug(f"Area width {area_width} is less than min_render_width {min_render_width}, adjusting for scaling.")
            area_width = min_render_width
        if area_height < min_render_height:
            logging.debug(f"Area height {area_height} is less than min_render_height {min_render_height}, adjusting for scaling.")
            area_height = min_render_height
            
        try:
            # Try to get from cache first
            # Cache key should consider the target rendering size to avoid using a wrongly scaled cached image
            cache_key = (image_path, area_width, area_height)

            if cache_key in self.image_cache:
                img_display = self.image_cache[cache_key]
                logging.debug(f"Using cached image for {image_path} at size {area_width}x{area_height}")
            else:
                logging.debug(f"Loading image {image_path} for display area {area_width}x{area_height}")
                img_original = Image.open(image_path)
                img_width, img_height = img_original.size

                if img_width == 0 or img_height == 0: # Should not happen with valid images
                    raise ValueError("Image dimensions are zero.")

                # Calculate aspect ratio to fit within area_width and area_height
                ratio = min(area_width / img_width, area_height / img_height)
                
                # Ensure ratio is positive, otherwise, it means area_width/height was 0 or negative.
                if ratio <= 0:
                    # This case should ideally be caught by the min_render_width/height checks
                    # Or if original image itself has 0 dimension (which is checked above)
                    logging.warning(f"Calculated ratio is {ratio}, which is invalid. Using original image size or a default.")
                    # Fallback: use a small default size if ratio is problematic
                    new_width, new_height = min(img_width, 100), min(img_height, 100)
                else:
                    new_width = int(img_width * ratio)
                    new_height = int(img_height * ratio)

                # Ensure new dimensions are at least 1x1
                new_width = max(1, new_width)
                new_height = max(1, new_height)
                
                logging.debug(f"Original: {img_width}x{img_height}, Target Area: {area_width}x{area_height}, Ratio: {ratio:.4f}, New Scaled: {new_width}x{new_height}")

                resized_img = img_original.resize((new_width, new_height), Image.Resampling.LANCZOS)
                img_display = ImageTk.PhotoImage(resized_img)
                self.image_cache[cache_key] = img_display # Cache the PhotoImage object
                img_original.close() # Close the original PIL Image

            self.image_label.configure(image=img_display, text="") # Clear any previous text
            self.image_label.image = img_display # Keep a reference! Crucial for Tkinter PhotoImage.
        
        except FileNotFoundError:
            logging.error(f"Image file not found: {image_path}")
            self.image_label.configure(text=f"图片\n{os.path.basename(image_path)}\n未找到", image=None)
            self.image_label.image = None # Clear previous image
        except Exception as e:
            logging.exception(f"Error loading or processing image {image_path}: {e}")
            self.image_label.configure(text=f"加载图片失败:\n{os.path.basename(image_path)}\n{e}", image=None)
            self.image_label.image = None # Clear previous image


    def show_log_area(self):
        self.image_label.grid_remove() # Hide image by removing from grid
        self.log_textbox.grid(row=0, column=0, sticky="nsew") # Show log

    def load_nikke_script_module(self):
        try:
            import main as nikke_script
            self.nikke_script_module = nikke_script
            self.log_message("成功加载 main.py 模块。\n", internal=True)
        except ImportError as e:
            self.log_message(f"错误: 无法加载 main.py 模块: {e}\n", internal=True)
        except Exception as e:
            self.log_message(f"加载 main.py 时发生未知错误: {e}\n", internal=True)

    def log_message(self, message, internal=False):
        # If script is running, or it's an internal GUI message, log it.
        if (self.script_thread and self.script_thread.is_alive()) or internal:
            if not self.log_textbox.winfo_exists(): return
            current_text = self.log_textbox.get("1.0", "end-1c") # Get current text
            if not current_text.endswith("\n") and len(current_text) > 0: # Add newline if not present
                 message = "\n" + str(message)
            else:
                 message = str(message)

            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", message)
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")

    def setup_gui_logging(self):
        if not self.nikke_script_module:
            return
        logger = self.nikke_script_module.logging.getLogger()
        for handler in logger.handlers[:]:
            if isinstance(handler, self.nikke_script_module.logging.StreamHandler) and handler.stream == sys.stdout:
                 logger.removeHandler(handler)
        gui_log_handler = GUILogHandler(self.log_message)
        formatter = self.nikke_script_module.logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        gui_log_handler.setFormatter(formatter)
        logger.addHandler(gui_log_handler)
        logger.setLevel(self.nikke_script_module.logging.INFO)
        self.log_message("GUI 日志记录器已设置。\n", internal=True)

    def start_script(self):
        if not self.nikke_script_module:
            self.log_message("错误: main.py 模块未加载，无法启动脚本。\n")
            return
        if self.script_thread and self.script_thread.is_alive():
            self.log_message("脚本已在运行中。\n")
            return

        self.show_log_area() # Switch to log view
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

        self.log_message(f"准备启动模式 {self.current_mode_value}\n")
        self.log_message("脚本将在5秒后启动... 请准备好 NIKKE 窗口。\n")
        
        self.start_button.configure(state="disabled")
        for btn, _ in self.mode_buttons:
            btn.configure(state="disabled")
        
        self.after(1000, lambda: self.countdown(4))

    def countdown(self, count):
        if self.stop_event.is_set(): # Check if stop was requested during countdown
            self.log_message("启动被取消。\n")
            self.on_script_finished(stopped_during_countdown=True)
            return

        if count > 0:
            self.log_message(f"...{count}\n")
            self.after(1000, lambda: self.countdown(count - 1))
        else:
            self.log_message("启动脚本...\n")
            self.execute_script_thread()

    def execute_script_thread(self):
        self.stop_event.clear()
        self.stop_button.configure(state="normal")
        self.script_thread = threading.Thread(target=self.run_script_target, args=(self.current_mode_value,))
        self.script_thread.daemon = True
        self.script_thread.start()
        self.after(100, self.check_script_thread_status)

    def run_script_target(self, mode_value):
        try:
            self.nikke_script_module.run_selected_mode(mode_value, self.stop_event, self.log_message)
        except AttributeError:
             self.log_message("错误: 'run_selected_mode' 函数未在 main.py 中定义或加载失败。\n")
        except Exception as e:
            self.log_message(f"脚本执行出错: {e}\n")
            import traceback
            self.log_message(traceback.format_exc() + "\n")
        finally:
            self.after(0, self.on_script_finished) # Schedule GUI update on main thread

    def check_script_thread_status(self):
        if self.script_thread and self.script_thread.is_alive():
            self.after(100, self.check_script_thread_status)
        # else: # Thread finished or not started
            # self.on_script_finished() # This will be called by run_script_target's finally block

    def on_script_finished(self, stopped_during_countdown=False):
        if not stopped_during_countdown:
            if self.stop_event.is_set():
                self.log_message("脚本已停止。\n")
            else:
                # Script should log its own completion, so this might be redundant
                # self.log_message("脚本执行完毕。\n")
                pass
        
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        for btn, _ in self.mode_buttons:
            btn.configure(state="normal")
        
        self.stop_event.clear()
        if not (self.script_thread and self.script_thread.is_alive()): # If not running, show image
            self.show_image_for_mode(self.current_mode_value)


    def request_stop_script(self):
        if self.script_thread and self.script_thread.is_alive():
            self.log_message("正在发送停止信号...\n")
            self.stop_event.set()
            self.stop_button.configure(state="disabled") # Disable stop button once pressed
        else:
            self.log_message("没有正在运行的脚本。\n")
            self.stop_button.configure(state="disabled")

    def check_admin_status(self):
        if not self.nikke_script_module:
            self.admin_status_label.configure(text="管理员权限: main.py 未加载")
            return
        try:
            if self.nikke_script_module.is_admin():
                self.admin_status_label.configure(text="管理员权限: 是", text_color="green")
            else:
                self.admin_status_label.configure(text="管理员权限: 否 (脚本可能无法正常工作!)", text_color="red")
                self.log_message("警告: 脚本未以管理员权限运行，可能导致功能异常。\n", internal=True)
        except AttributeError:
            self.admin_status_label.configure(text="管理员权限: 检查函数未找到")
        except Exception as e:
            self.admin_status_label.configure(text=f"管理员权限: 检查出错")

class GUILogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        msg = self.format(record)
        self.callback(msg) # Callback expects to add its own newline if needed

if __name__ == "__main__":
    # This logic for creating 'assets' is strictly for development mode.
    # It should not run when the application is bundled by PyInstaller.
    if not getattr(sys, 'frozen', False): # True if bundled by PyInstaller
        assets_dev_path = "assets" # Relative to script in dev mode
        if not os.path.exists(assets_dev_path):
            try:
                os.makedirs(assets_dev_path)
                print(f"DEV MODE: Created '{assets_dev_path}' directory. Please place 1.png to 9.png inside it.")
            except OSError as e:
                print(f"DEV MODE: Error creating '{assets_dev_path}' directory: {e}")
    
    # Check for Pillow
    try:
        from PIL import Image, ImageTk
    except ImportError:
        print("错误: Pillow 库未安装。请运行 'pip install Pillow' 来安装。")
        # Attempt to show a Tkinter error dialog if possible, then exit
        try:
            root = tk.Tk()
            root.withdraw() # Hide the main window
            tk.messagebox.showerror("依赖错误", "错误: Pillow 库未安装。\n请运行 'pip install Pillow' 来安装。")
        except:
            pass # If Tkinter itself fails, just print to console
        sys.exit(1)

    # Configure basic logging for direct script execution if no handlers are set up
    # This helps see debug messages from resource_path when running main_gui.py directly
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

    app = App()
    app.mainloop()