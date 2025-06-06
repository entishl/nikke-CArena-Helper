# modes/mode9.py
import os
import glob
import shutil # 导入 shutil 模块
from core import utils as core_utils

def run(context):
    logger = context.shared.logger
    cc = context.shared.constants

    logger.info("===== 运行模式 9: 图片处理与打包 =====")

    if core_utils.check_stop_signal(context):
        logger.info("模式9：检测到停止信号，提前退出。")
        return

    try:
        # 从 context.mode_config 获取由 app.py 准备好的实际路径
        # app.py 会处理 m9_input_dir_relative, m9_input_subdir 等逻辑
        input_dir = getattr(context.mode_config, 'm9_actual_input_dir', None)
        output_webp_dir = getattr(context.mode_config, 'm9_actual_output_webp_dir', None)
        zip_filepath = getattr(context.mode_config, 'm9_actual_zip_filepath', None) # 本地变量名为 zip_filepath, 获取的属性为 m9_actual_zip_filepath

        # 获取其他模式9特定配置
        webp_quality = getattr(context.mode_config, 'm9_webp_quality', 85)
        webp_lossless = getattr(context.mode_config, 'm9_webp_lossless', False) # 新增获取 lossless 配置
        delete_originals = getattr(context.mode_config, 'm9_del_orig_after_webp', False)
        delete_webp_after_zip = getattr(context.mode_config, 'm9_del_webp_after_zip', True)

        if not input_dir:
            logger.error("模式9: 关键配置 'm9_actual_input_dir' 未在 mode_config 中找到。无法继续。")
            return
        
        # 检查 input_dir 是否为有效目录
        if not os.path.isdir(input_dir):
            logger.error(f"模式9: 输入路径 '{input_dir}' 不是一个有效的目录。无法继续。")
            return

        if not output_webp_dir:
            logger.error("模式9: 关键配置 'm9_actual_output_webp_dir' 未在 mode_config 中找到。无法继续。")
            # app.py 应该已经创建了 output_webp_dir
            return
        if not zip_filepath:
            logger.error("模式9: 关键配置 'm9_actual_zip_filepath' 未在 mode_config 中找到。无法继续。")
            return
        
        # app.py 应该已经创建了 output_webp_dir，移除这里的makedirs
        logger.info(f"模式9: 输入目录: {input_dir}")
        logger.info(f"模式9: WebP输出目录: {output_webp_dir}")
        logger.info(f"模式9: ZIP文件路径: {zip_filepath}")
        logger.info(f"模式9: WebP质量: {webp_quality}, WebP无损: {webp_lossless}, 删除原图: {delete_originals}, 打包后删除WebP: {delete_webp_after_zip}")

        # 1. 处理图片到 WebP
        logger.info(f"模式9: 开始处理 '{input_dir}' 中的图片到 WebP 格式，输出到 '{output_webp_dir}' (质量: {webp_quality}, 无损: {webp_lossless})")
        
        # 支持的图片格式
        supported_formats = ('*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif')
        image_files_to_process = []
        for fmt in supported_formats:
            image_files_to_process.extend(glob.glob(os.path.join(input_dir, fmt)))
        # 移除了处理 input_dir 为单个文件的逻辑


        if not image_files_to_process:
            logger.warning(f"模式9: 在输入目录 '{input_dir}' 中没有找到支持的图片文件进行处理。")
        else:
            processed_count = 0
            for img_path in image_files_to_process:
                if core_utils.check_stop_signal(context):
                    logger.info("模式9: 图片处理过程中检测到停止信号。")
                    break
                
                # 检查 img_path 是否是目录，如果是，则跳过
                if os.path.isdir(img_path):
                    logger.debug(f"模式9: 跳过目录 '{img_path}'。")
                    continue

                logger.info(f"模式9: 正在处理图片 '{img_path}'")
                # process_image_to_webp 需要接收 quality 参数
                # 我们需要修改 core_utils.process_image_to_webp 来接受这个参数
                # 暂时假设它已修改，或传递 context.mode_config.m9_webp_quality
                # 为了简单起见，这里直接传递 quality 值
                webp_path = core_utils.process_image_to_webp(context, img_path, output_webp_dir, quality=webp_quality, lossless=webp_lossless)
                if webp_path:
                    logger.info(f"模式9: 图片 '{img_path}' 已成功转换为 '{webp_path}'")
                    processed_count += 1
                    if delete_originals:
                        try:
                            os.remove(img_path)
                            logger.info(f"模式9: 已删除原图 '{img_path}'")
                        except Exception as e_del_orig:
                            logger.warning(f"模式9: 删除原图 '{img_path}' 失败: {e_del_orig}")
                else:
                    logger.error(f"模式9: 图片 '{img_path}' 转换失败。")
            logger.info(f"模式9: WebP 图片处理完成，共处理 {processed_count} 张图片。")

        if core_utils.check_stop_signal(context):
            logger.info("模式9：检测到停止信号，打包操作将被跳过。")
            return

        # 2. 打包 WebP 图片 (如果 output_webp_dir 中有内容)
        if os.path.exists(output_webp_dir) and os.listdir(output_webp_dir):
            logger.info(f"模式9: 开始将 '{output_webp_dir}' 的内容打包到 '{zip_filepath}'")
            success = core_utils.create_zip_archive(context, output_webp_dir, zip_filepath)
            if success:
                logger.info(f"模式9: 目录 '{output_webp_dir}' 已成功打包到 '{zip_filepath}'")
                if delete_webp_after_zip:
                    logger.info(f"模式9: 打包成功，开始删除WebP目录 '{output_webp_dir}'")
                    try:
                        shutil.rmtree(output_webp_dir)
                        logger.info(f"模式9: WebP目录 '{output_webp_dir}' 已删除。")
                    except Exception as e_del_webp:
                        logger.warning(f"模式9: 删除WebP目录 '{output_webp_dir}' 失败: {e_del_webp}")
            else:
                logger.error(f"模式9: 打包目录 '{output_webp_dir}' 失败。")
        else:
            logger.warning(f"模式9: WebP输出目录 '{output_webp_dir}' 为空或不存在，跳过打包操作。")

    except Exception as e:
        logger.exception(f"模式9执行期间发生错误: {e}")
    finally:
        logger.info("模式9执行完毕。")
# 移除了 if __name__ == '__main__': 测试代码块