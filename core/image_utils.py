# core/image_utils.py
import os
import logging
from PIL import Image


def check_stop_signal(context):
    """检查是否收到了停止信号，如果收到则记录并返回 True，否则返回 False。"""
    if hasattr(context, 'shared') and hasattr(context.shared, 'stop_requested') and context.shared.stop_requested:
        if hasattr(context, 'shared') and hasattr(context.shared, 'logger'):
            context.shared.logger.warning("检测到停止信号。")
        else:
            logging.warning("检测到停止信号 (context.shared.logger 不可用)。")
        return True
    return False


def stitch_images_vertically(context, image_paths: list, output_path: str):
    """
    将一系列图片从上到下垂直拼接成一张图片。
    """
    logger = getattr(context.shared, 'logger', logging)
    logger.info(f"开始垂直拼接图片到 '{output_path}'...")
    if check_stop_signal(context):
        logger.info("操作已取消 (stitch_images_vertically)。")
        return False
    if not image_paths:
        logger.warning("没有提供用于垂直拼接的图片路径。")
        return False

    images = []
    total_height = 0
    max_width = 0

    try:
        for path in image_paths:
            if not os.path.exists(path):
                logger.warning(f"跳过拼接：找不到图片文件 '{path}'")
                continue
            img = Image.open(path)
            images.append(img)
            total_height += img.height
            if img.width > max_width:
                max_width = img.width
            logger.debug(f"读取图片 '{path}' 尺寸: {img.size}")

        if not images:
             logger.error("无法打开任何有效的图片进行垂直拼接。")
             return False

        logger.debug(f"创建垂直拼接画布，尺寸: ({max_width}, {total_height})")
        stitched_image = Image.new('RGB', (max_width, total_height))

        current_y = 0
        for img in images:
            if check_stop_signal(context):
                logger.info("垂直拼接操作在循环中被中断。")
                # 清理已打开的图片
                for open_img in images: # images 列表包含了所有已成功打开的 Image 对象
                    try:
                        open_img.close()
                    except Exception as e_close:
                        logger.debug(f"关闭图片时出错 (中断后清理): {e_close}")
                return False # 或者根据需要返回部分结果的状态
            paste_x = (max_width - img.width) // 2
            stitched_image.paste(img, (paste_x, current_y))
            current_y += img.height
            # img.close() # 在循环结束后统一关闭

        for img in images: # 确保所有图片都被关闭
            try:
                img.close()
            except Exception as e_close:
                logger.debug(f"关闭图片时出错 (正常结束): {e_close}")


        # 确保目录存在
        dir_name = os.path.dirname(output_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        stitched_image.save(output_path)
        logger.info(f"垂直拼接完成，图片已保存为 '{output_path}'")
        return True
    except FileNotFoundError as e:
        logger.error(f"垂直拼接时找不到文件：{e}")
        return False
    except Exception as e:
        logger.error(f"垂直拼接图片时出错: {e}")
        for img in images: # 确保在异常情况下也尝试关闭图片
            try:
                img.close()
            except:
                pass
        return False


def stitch_images_horizontally(context, image_paths: list, output_path: str, alignment: str = 'center', spacing: int = 0, bg_color=(255, 255, 255)):
    """
    将一系列图片从左到右水平拼接成一张图片。

    参数:
        context: 应用上下文对象。
        image_paths: 要拼接的图片文件路径列表。
        output_path: 输出拼接图片的路径。
        alignment: 垂直对齐方式 ('top', 'center', 'bottom')。
        spacing: 图片之间的水平间距 (像素)。
        bg_color: 画布背景颜色 (RGB元组)。
    返回:
        bool: 成功返回 True, 失败返回 False。
    """
    logger = getattr(context.shared, 'logger', logging)
    logger.info(f"开始水平拼接图片到 '{output_path}' (对齐: {alignment}, 间距: {spacing})...")

    if check_stop_signal(context):
        logger.info("操作已取消 (stitch_images_horizontally)。")
        return False

    if not image_paths:
        logger.warning("没有提供用于水平拼接的图片路径。")
        return False

    images = []
    total_width = 0
    max_height = 0

    try:
        for i, path in enumerate(image_paths):
            if check_stop_signal(context):
                logger.info(f"水平拼接在加载图片 {i+1} ('{path}') 前被中断。")
                for img_obj in images: img_obj.close()
                return False
            if not os.path.exists(path):
                logger.warning(f"跳过拼接：找不到图片文件 '{path}'")
                continue
            img = Image.open(path)
            images.append(img)
            total_width += img.width
            if img.height > max_height:
                max_height = img.height
            logger.debug(f"读取图片 '{path}' 尺寸: {img.size}")

        if not images:
            logger.error("无法打开任何有效的图片进行水平拼接。")
            return False

        # 加上图片间的间距
        if len(images) > 1:
            total_width += spacing * (len(images) - 1)

        logger.debug(f"创建水平拼接画布，尺寸: ({total_width}, {max_height}), 背景色: {bg_color}")
        stitched_image = Image.new('RGB', (total_width, max_height), color=bg_color)

        current_x = 0
        for i, img in enumerate(images):
            if check_stop_signal(context):
                logger.info(f"水平拼接在粘贴图片 {i+1} ('{img.filename if hasattr(img, 'filename') else 'N/A'}') 前被中断。")
                for img_obj in images: img_obj.close() # 关闭所有已打开的
                # stitched_image.close() # Pillow Image 对象没有 close 方法
                return False

            paste_y = 0
            if alignment == 'center':
                paste_y = (max_height - img.height) // 2
            elif alignment == 'bottom':
                paste_y = max_height - img.height
            # 'top' alignment is paste_y = 0 (default)

            stitched_image.paste(img, (current_x, paste_y))
            current_x += img.width + spacing
            # img.close() # 在循环结束后统一关闭

        for img in images: # 确保所有图片都被关闭
            try:
                img.close()
            except Exception as e_close:
                logger.debug(f"关闭图片时出错 (正常结束 - 水平拼接): {e_close}")

        # 确保目录存在
        dir_name = os.path.dirname(output_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        stitched_image.save(output_path)
        logger.info(f"水平拼接完成，图片已保存为 '{output_path}'")
        return True
    except FileNotFoundError as e:
        logger.error(f"水平拼接时找不到文件：{e}")
        for img_obj in images: img_obj.close()
        return False
    except Exception as e:
        logger.error(f"水平拼接图片时出错: {e}")
        for img_obj in images: # 确保在异常情况下也尝试关闭图片
            try:
                img_obj.close()
            except:
                pass
        return False


def stitch_mode4_overview(context, image_paths: list, output_path: str, spacing_major: int = 60, spacing_minor: int = 30, background_color=(0, 0, 0)):
    """
    将8张图片分成两行（每行4张）并拼接成一张总览图。
    - 第1行: 图片 1, 2, 3, 4
    - 第2行: 图片 5, 6, 7, 8
    - 间距:
        - (1,2), (3,4), (5,6), (7,8) 之间为 spacing_minor
        - (2,3), (6,7) 之间为 spacing_major
        - 第1行和第2行之间为 spacing_major
    - 背景颜色由 background_color 指定。
    """
    logger = getattr(context.shared, 'logger', logging)
    logger.info(f"开始为模式4/5拼接总览图到 '{output_path}' (主间距: {spacing_major}, 次间距: {spacing_minor}, 背景: {background_color})...")

    if check_stop_signal(context):
        logger.info("操作已取消 (stitch_mode4_overview)。")
        return None # 返回 None 表示失败或未完成

    if not image_paths or len(image_paths) != 8:
        logger.error(f"需要8张图片进行模式4/5总览图拼接，但收到了 {len(image_paths) if image_paths else 0} 张。")
        return None

    images_opened = [] # 用于确保所有打开的图片都被关闭
    try:
        for i, path in enumerate(image_paths):
            if check_stop_signal(context):
                logger.info(f"拼接操作在加载图片 {i+1} ('{path}') 前被中断。")
                for img_obj in images_opened: img_obj.close()
                return None
            if not os.path.exists(path):
                logger.error(f"找不到图片文件 '{path}' (图片 {i+1})，无法进行拼接。")
                for img_obj in images_opened: img_obj.close()
                return None
            img = Image.open(path)
            images_opened.append(img)

        # 假设所有图片尺寸相同，基于第一张图片
        img_width, img_height = images_opened[0].size
        if img_width <= 0 or img_height <= 0:
            logger.error(f"图片尺寸无效: {img_width}x{img_height}。")
            for img_obj in images_opened: img_obj.close()
            return None

        # 计算画布尺寸
        row_width = (img_width * 4) + (spacing_minor * 2) + spacing_major
        canvas_height = (img_height * 2) + spacing_major
        canvas_width = row_width

        logger.debug(f"单张图片尺寸: {img_width}x{img_height}")
        logger.debug(f"画布尺寸: {canvas_width}x{canvas_height}")

        stitched_image = Image.new('RGB', (canvas_width, canvas_height), color=background_color)

        # 粘贴图片 - 第1行
        current_x_r1 = 0
        stitched_image.paste(images_opened[0], (current_x_r1, 0))
        current_x_r1 += img_width + spacing_minor
        stitched_image.paste(images_opened[1], (current_x_r1, 0))
        current_x_r1 += img_width + spacing_major
        stitched_image.paste(images_opened[2], (current_x_r1, 0))
        current_x_r1 += img_width + spacing_minor
        stitched_image.paste(images_opened[3], (current_x_r1, 0))

        # 粘贴图片 - 第2行
        row2_y_offset = img_height + spacing_major
        current_x_r2 = 0
        stitched_image.paste(images_opened[4], (current_x_r2, row2_y_offset))
        current_x_r2 += img_width + spacing_minor
        stitched_image.paste(images_opened[5], (current_x_r2, row2_y_offset))
        current_x_r2 += img_width + spacing_major
        stitched_image.paste(images_opened[6], (current_x_r2, row2_y_offset))
        current_x_r2 += img_width + spacing_minor
        stitched_image.paste(images_opened[7], (current_x_r2, row2_y_offset))

        # 调用者应确保 output_path 是唯一的，并且其目录已创建。
        # 此函数现在直接使用传入的 output_path。
        final_output_path_to_save = output_path # 直接使用传入的路径

        # 确保目录存在 (虽然调用者也可能已创建，但再次检查无害)
        dir_name = os.path.dirname(final_output_path_to_save)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        stitched_image.save(final_output_path_to_save)
        logger.info(f"模式4/5总览图拼接完成，图片已保存为 '{final_output_path_to_save}'")
        return final_output_path_to_save # 返回实际保存的路径

    except FileNotFoundError as e: # Should be caught by os.path.exists earlier
        logger.error(f"拼接模式4/5总览图时找不到文件：{e}")
        return None
    except Exception as e:
        logger.error(f"拼接模式4/5总览图时出错: {e}")
        # import traceback # 用于调试
        # traceback.print_exc()
        return None
    finally:
        for img_obj in images_opened: # 确保关闭所有图片对象
            try:
                img_obj.close()
            except: # nosec
                pass


def process_image_to_webp(context, input_image_path: str, output_webp_dir: str, quality: int = 85, lossless: bool = False):
    """
    将指定的 PNG/JPG 图片转换为 WebP 格式。
    文件名将保持不变，只改变扩展名。

    参数:
        context: 应用上下文。
        input_image_path: 输入图片路径。
        output_webp_dir: WebP 图片的输出目录。
        quality: WebP 压缩质量 (1-100)，仅当 lossless=False 时有效。
        lossless: 是否使用无损压缩。
    """
    logger = getattr(context.shared, 'logger', logging)
    if check_stop_signal(context):
        logger.info("操作已取消 (process_image_to_webp)。")
        return None

    if not os.path.exists(input_image_path):
        logger.error(f"输入图片文件不存在: {input_image_path}")
        return None

    try:
        img = Image.open(input_image_path)
        base_filename = os.path.basename(input_image_path)
        name_without_ext = os.path.splitext(base_filename)[0]
        output_webp_filename = f"{name_without_ext}.webp"
        output_webp_path = os.path.join(output_webp_dir, output_webp_filename)

        os.makedirs(output_webp_dir, exist_ok=True)

        save_params = {'format': 'WEBP'}
        if lossless:
            save_params['lossless'] = True
            # Pillow 文档指出，当 lossless=True 时，quality 参数会被忽略，但一些版本可能仍接受它。
            # 为了清晰，可以只在有损压缩时明确传递 quality。
            # 或者，如果 Pillow 版本支持，可以同时传递 lossless=True 和 method=6 (最慢但压缩最好)
            # save_params['method'] = 6
        else:
            save_params['quality'] = quality

        # 处理透明度：如果图像有alpha通道 (RGBA)，转换为 RGB 以避免某些 WebP 查看器的问题
        # 或者，如果需要保留透明度，确保 Pillow 和 WebP 库支持
        if img.mode == 'RGBA' or img.mode == 'LA' or (img.mode == 'P' and 'transparency' in img.info):
            # 如果目标是无损且需要保留透明度
            if lossless:
                 logger.debug(f"图片 '{input_image_path}' (模式: {img.mode}) 包含透明度，将尝试无损保存以保留。")
            else:
            # 对于有损压缩，通常最好转换为RGB，除非明确需要带alpha的有损WebP
                 logger.debug(f"图片 '{input_image_path}' (模式: {img.mode}) 包含透明度，将转换为 RGB 后进行有损压缩。")
                 img = img.convert('RGB')

        img.save(output_webp_path, **save_params)
        logger.info(f"图片 '{input_image_path}' 已成功转换为 WebP (lossless={lossless}, quality={quality if not lossless else 'N/A'}) 并保存至 '{output_webp_path}'")
        img.close()
        return output_webp_path
    except FileNotFoundError:
        logger.error(f"打开图片失败，文件未找到: {input_image_path}")
        return None
    except Exception as e:
        logger.error(f"处理图片 '{input_image_path}' 到 WebP 时出错: {e}")
        if 'img' in locals() and hasattr(img, 'close'):
            img.close()
        return None