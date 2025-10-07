# core/utils.py
#
# 此文件现在作为向后兼容层，将所有导入重定向到新的模块化结构
# 为了保持现有代码的兼容性，所有函数调用都会自动映射到新的模块

import warnings
from .automation_utils import (
    check_stop_signal,
    click_coordinates,
    take_screenshot,
    find_and_activate_window,
    get_pixel_color_relative,
    activate_nikke_window_if_needed
)
from .image_utils import (
    stitch_images_vertically,
    stitch_images_horizontally,
    stitch_mode4_overview,
    process_image_to_webp
)
from .file_utils import (
    get_asset_path,
    create_zip_archive,
    get_or_create_mode_output_subdir,
    generate_unique_filepath,
    get_timestamp_for_filename,
    get_base_path
)
from .common_utils import (
    parse_color_string
)

# 发布弃用警告，但不影响功能运行
warnings.warn(
    "core.utils 模块已重构。请直接导入专门的模块: "
    "core.automation_utils, core.image_utils, core.file_utils, core.common_utils",
    DeprecationWarning,
    stacklevel=2
)

# 保持原有的 __all__ 以确保向后兼容
__all__ = [
    # Automation functions
    'check_stop_signal',
    'click_coordinates',
    'take_screenshot',
    'find_and_activate_window',
    'get_pixel_color_relative',
    'activate_nikke_window_if_needed',

    # Image processing functions
    'stitch_images_vertically',
    'stitch_images_horizontally',
    'stitch_mode4_overview',
    'process_image_to_webp',

    # File operations functions
    'get_asset_path',
    'create_zip_archive',
    'get_or_create_mode_output_subdir',
    'generate_unique_filepath',
    'get_timestamp_for_filename',
    'get_base_path',

    # Common utility functions
    'parse_color_string'
]