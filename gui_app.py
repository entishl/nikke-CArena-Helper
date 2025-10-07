import ctypes
import sys
from gui.app import NikkeGuiApp


def check_admin_and_exit_if_not():
    """检查管理员权限，如果没有则退出"""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except AttributeError:
        # 回退处理，假设不是管理员
        is_admin = False
        print("Warning: Could not determine admin status via ctypes.windll.shell32.IsUserAnAdmin().")

    if not is_admin:
        ctypes.windll.user32.MessageBoxW(
            0,
            "请以管理员权限运行此程序！\n\n程序即将退出。",
            "权限不足",
            0x00000010 | 0x00000000  # MB_ICONERROR | MB_OK
        )
        sys.exit(1)


if __name__ == '__main__':
    # 检查管理员权限
    check_admin_and_exit_if_not()

    # 创建并运行应用
    app = NikkeGuiApp()

    # 更新日志处理器的文本框引用
    if hasattr(app, 'logging_manager') and app.logging_manager:
        app.logging_manager.update_log_handler_textbox(app.log_textbox)

    # 运行主循环
    app.mainloop()