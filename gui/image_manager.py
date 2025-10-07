import os
import logging
from PIL import Image, ImageTk
from core.utils import get_asset_path


class ImageManager:
    """图像管理器，负责图像的加载、缩放和显示"""

    def __init__(self, display_area, image_label, app_context=None):
        self.display_area = display_area
        self.image_label = image_label
        self.app_context = app_context

        self.current_asset_image_name = None
        self.target_aspect_ratio = 5 / 4

    def set_current_image_name(self, image_name):
        """设置当前图像名称"""
        self.current_asset_image_name = image_name

    def has_current_image(self):
        """检查是否有当前图像"""
        return self.current_asset_image_name is not None

    def display_image(self, event=None):
        """显示图像"""
        if not self.current_asset_image_name:
            # 没有选择图像
            self.set_placeholder_text("请选择一个模式")
            self.hide_log()
            self.show_image()
            return

        self.hide_log()
        self.show_image()

        try:
            logger = self._get_logger()
            log_prefix = "_resize_and_display_image"
            if event:
                log_prefix += f" (event {event.type})"

            image_path = get_asset_path(self.current_asset_image_name)
            if os.path.exists(image_path):
                # 确保显示区域尺寸是最新的
                self.display_area.update_idletasks()
                width = self.display_area.winfo_width()
                height = self.display_area.winfo_height()

                if logger:
                    logger.debug(f"{log_prefix}: display_area current dimensions: width={width}, height={height}")

                # 计算可用空间和图像尺寸
                padding = 20
                available_width = width - padding if width > padding else 1
                available_height = height - padding if height > padding else 1

                # 根据宽高比计算最终图像尺寸
                if available_width / available_height > self.target_aspect_ratio:
                    img_height = available_height
                    img_width = int(img_height * self.target_aspect_ratio)
                else:
                    img_width = available_width
                    img_height = int(img_width / self.target_aspect_ratio)

                # 如果计算出的尺寸太小，使用默认尺寸
                if img_width < 50 or img_height < 40:
                    default_width_for_ratio = 400
                    img_width = default_width_for_ratio
                    img_height = int(default_width_for_ratio / self.target_aspect_ratio)
                    if logger:
                        logger.debug(f"{log_prefix}: Calculated dimensions too small, falling back to default {img_width}x{img_height}")

                if logger:
                    logger.debug(f"{log_prefix}: Calculated image size for 5:4: img_width={img_width}, img_height={img_height}")

                # 加载和缩放图像
                pil_image = Image.open(image_path)

                # 根据Pillow版本选择重采样过滤器
                try:
                    # Pillow 9.0.0+ 使用 Resampling 枚举
                    resample_filter = Image.Resampling.LANCZOS
                except AttributeError:
                    # 旧版本使用常量
                    resample_filter = Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS

                resized_pil_image = pil_image.resize((img_width, img_height), resample_filter)
                if logger:
                    logger.debug(f"{log_prefix}: PIL image resized to: {resized_pil_image.size} using filter {resample_filter}")

                # 转换为PhotoImage
                photo_image = ImageTk.PhotoImage(resized_pil_image)
                if logger:
                    logger.debug(f"{log_prefix}: Resized PIL image converted to ImageTk.PhotoImage")

                # 显示图像
                self.image_label.configure(image=photo_image, text="")
                self.image_label.image = photo_image  # 保持引用

                # 更新标签尺寸信息
                self.image_label.update_idletasks()
                label_w = self.image_label.winfo_width()
                label_h = self.image_label.winfo_height()
                if logger:
                    logger.debug(f"{log_prefix}: image_label actual dimensions: width={label_w}, height={label_h}")
            else:
                self.set_placeholder_text(f"图片 {self.current_asset_image_name} 未找到\n路径: {image_path}")
                if logger:
                    logger.warning(f"{log_prefix}: Image file not found: {image_path}")

        except Exception as e:
            self.set_placeholder_text(f"加载图片 {self.current_asset_image_name} 失败: {e}")
            logger = self._get_logger()
            if logger:
                logger.exception(f"Error loading image {self.current_asset_image_name}:")

    def hide_image(self):
        """隐藏图像"""
        self.image_label.grid_forget()

    def show_image(self):
        """显示图像"""
        self.image_label.grid(row=0, column=0, sticky="nsew")

    def hide_log(self):
        """隐藏日志文本框"""
        # 这个方法需要主应用传入log_textbox引用
        pass

    def show_log(self):
        """显示日志文本框"""
        # 这个方法需要主应用传入log_textbox引用
        pass

    def set_placeholder_text(self, text):
        """设置占位符文本"""
        self.image_label.configure(image=None, text=text)

    def set_display_area(self, display_area):
        """设置显示区域"""
        self.display_area = display_area

    def set_image_label(self, image_label):
        """设置图像标签"""
        self.image_label = image_label

    def set_log_textbox(self, log_textbox):
        """设置日志文本框"""
        self.log_textbox = log_textbox

    def _get_logger(self):
        """获取日志记录器"""
        if self.app_context and hasattr(self.app_context, 'shared') and self.app_context.shared.logger:
            return self.app_context.shared.logger
        return logging.getLogger("ImageManagerLogger")


class LogComponent:
    """日志组件"""

    def __init__(self, display_area, log_textbox):
        self.display_area = display_area
        self.log_textbox = log_textbox

    def show_log(self):
        """显示日志文本框"""
        self.log_textbox.grid(row=0, column=0, sticky="nsew")

    def hide_log(self):
        """隐藏日志文本框"""
        self.log_textbox.grid_forget()

    def clear_log(self):
        """清空日志文本框"""
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def set_log_textbox(self, log_textbox):
        """设置日志文本框"""
        self.log_textbox = log_textbox