def hide_console_window():
    """使用Win32 API隐藏控制台窗口"""
    import ctypes # 导入ctypes模块,用于调用Win32 API
    from ctypes import wintypes # 导入wintypes模块,用于定义Win32 API的结构体和常量
    import platform # 导入platform模块,用于检查当前操作系统

    if platform.system() != 'Windows': # 检查当前操作系统是否为Windows
        return

    # 定义常量
    SW_HIDE = 0

    # 获取控制台窗口句柄
    kernel32 = ctypes.windll.kernel32  # 加载kernel32.dll库,用于调用Win32 API；GetConsoleWindow()函数用于获取当前控制台窗口的句柄
    user32 = ctypes.windll.user32  # 加载user32.dll库,用于调用Win32 API；ShowWindow()函数用于显示或隐藏窗口

    hWnd = kernel32.GetConsoleWindow()  # 获取当前控制台窗口的句柄
    if hWnd:
        # 隐藏窗口
        user32.ShowWindow(hWnd, SW_HIDE)  # 使用ShowWindow()函数隐藏控制台窗口
        console_logger.info("控制台窗口已通过Win32 API隐藏")

def show_program_info():
    """显示程序信息"""
    import json
    from pathlib import Path

    try:
        config_path = Path('config.json')
        if config_path.exists():  # exists()方法检查配置文件是否存在，如果文件不存在，函数会直接返回，使用UI控件的默认状态
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)  # 读取配置文件内容，json.load()将JSON字符串反序列化为Python字典

            show_info = config.get('显示程序信息', False) # 获取配置项'显示程序信息'的值,如果配置文件中没有这个项,则使用默认值False
            if show_info:
                pass
            elif not show_info:
                hide_console_window() # 如果配置项'显示程序信息'为False,则隐藏控制台窗口

    except Exception as e:
        pass

show_program_info()

import sys # 导入sys模块,用于访问与Python解释器相关的变量和函数,如获取命令行参数
from PySide6.QtWidgets import QApplication, QMessageBox # 导入PySide6库中的QApplication类,用于创建Qt应用程序,QMessageBox类,用于显示消息框

from GUI import MainWindow # 导入GUI模块中的MainWindow类,用于创建主窗口
from PyTTSx4 import voice_queue
from ThreadPoolManager import shutdown_thread_pool, safe_submit  # 导入ThreadPoolManager模块,用于管理线程池
from Logger import console_logger, file_logger, both_logger# 导入Logger模块,用于日志记录
from MouseListener import create_basic_mouse_listener, MouseListener_set_ui, stop_mouse_listener # 导入MouseListener模块,用于鼠标监听
import KeyBoardListener # 导入KeyboardListener模块,用于键盘监听


def cleanup_resources():
    """执行完整的资源清理，确保程序优雅退出"""
    try:
        # 设置程序退出标志
        '''作用：通知所有运行中的线程和循环应该停止;重要性：防止清理过程中产生新的任务或事件'''
        global is_exiting
        is_exiting = True

        # 停止鼠标和键盘监听器
        try:
            stop_mouse_listener() # 退出程序前，先停止鼠标监听器
        except Exception as e:
            both_logger.error(f"停止鼠标监听器失败: {e}") # 输出错误信息到控制台和文件

        try:
            if 'keyboard_listener' in globals() and keyboard_listener:
                keyboard_listener.stop()
                console_logger.warning("键盘监听器已停止") # 输出基本信息到控制台
        except Exception as e:
            both_logger.error(f"停止键盘监听器失败: {e}") # 输出错误信息到控制台和文件

        # 清理语音队列
        try:
            if 'voice_queue' in globals() and voice_queue:
                voice_queue.put(None)  # 发送终止信号
                console_logger.warning("语音队列已清理") # 输出基本信息到控制台
        except Exception as e:
            both_logger.error(f"清理语音队列失败: {e}") # 输出错误信息到控制台和文件

        # 清理UI资源
        try:
            if 'ui' in globals() and ui:
                ui.close()
                console_logger.warning("UI资源已清理") # 输出基本信息到控制台
        except Exception as e:
            both_logger.error(f"清理UI资源失败: {e}") # 输出错误信息到控制台和文件

        # 清理临时文件和缓存
        # try:
        #     cleanup_temp_files()
        #     console_logger.warning("临时文件已清理") # 输出基本信息到控制台
        # except Exception as e:
        #     both_logger.error(f"清理临时文件失败: {e}") # 输出错误信息到控制台和文件

        # 关闭线程池
        try:
            shutdown_thread_pool()
            console_logger.warning("线程池已关闭") # 输出基本信息到控制台
        except Exception as e:
            both_logger.error(f"关闭线程池失败: {e}") # 输出错误信息到控制台和文件

        console_logger.warning("资源清理完成")  # 输出基本信息到控制台

    except Exception as e:
        both_logger.error(f"资源清理过程中发生异常: {e}") # 输出错误信息到控制台和文件
        # 即使发生异常，也要尝试基本清理
        import traceback
        traceback.print_exc()

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """全局异常处理函数"""  # 用于捕获和处理程序中所有未被捕获的异常

    if issubclass(exc_type, KeyboardInterrupt):
        '''允许键盘中断特殊处理KeyboardInterrupt异常（通常是用户按Ctrl+C）；使用sys.__excepthook__调用系统的默认异常处理；允许程序正常响应键盘中断信号；避免阻止用户通过Ctrl+C终止程序'''
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    both_logger.debug(f"捕获到未处理的异常:\n异常类型：{exc_type.__name__}\n异常信息: {exc_value}\n异常追踪：{exc_traceback}") # 记录异常信息到日志文件

    try:
        '''使用QMessageBox.critical显示错误消息框，使用None作为父窗口，表示消息框没有父窗口'''
        QMessageBox.critical(None, "程序错误",
                             f"捕获到未处理的异常:\n 异常类型：{exc_type.__name__}\n异常信息: {exc_value}\n异常追踪：{exc_traceback}")
    except:
        pass # 如果消息框显示失败，忽略异常

if __name__ == "__main__":

    # global ui # 定义全局变量ui,用于存储UI对象
    app = QApplication() # 创建一个应用程序对象,用于管理整个应用程序的生命周期

    sys.excepthook = global_exception_handler # 设置全局异常处理函数,用于捕获和处理程序中所有未被捕获的异常
    import atexit # 导入atexit模块,用于注册程序退出时的清理函数
    atexit.register(cleanup_resources) # 注册清理函数,用于在程序退出时执行资源清理操作

    # 创建基础鼠标监听器，只有 on_click 点击事件回调函数
    create_basic_mouse_listener()
    # mouse_listener = MouseListener.mouse.Listener(
    #     on_click = MouseListener.on_click,  # 点击事件回调
    #     # on_move = MouseListener.on_move,  # 移动事件回调
    #     # on_scroll = MouseListener.on_scroll  # 滚轮事件回调
    # )

    # 创建键盘监听器实例，指定回调函数
    keyboard_listener = KeyBoardListener.keyboard.Listener(
        on_press=KeyBoardListener.on_press,  # 按键按下时调用的函数
        on_release=KeyBoardListener.on_release  # 按键释放时调用的函数
    )

    window = MainWindow() # 创建一个主窗口对象,用于显示应用程序的主界面
    window.show() # 显示主窗口,使窗口可见

    KeyBoardListener.set_ui(window) # 设置MainWindow实例到KeyBoardListener模块的ui变量中
    MouseListener_set_ui(window) # 设置MainWindow实例到MouseListener模块的ui变量中
    # 启动监听（异步方式）
    # 监听器在后台运行，捕获鼠标事件
    # 事件会触发对应的回调函数进行处理
    # mouse_listener.start()
    # 启动监听（后台线程，非阻塞）
    keyboard_listener.start()

    sys.exit(app.exec()) # 启动应用程序的事件循环,等待用户的操作,直到应用程序被关闭;返回应用程序的退出状态码
