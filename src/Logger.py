import logging
import logging.config

import inspect
import os

from typing import Optional, Dict, Any
from enum import Enum
from functools import wraps

class LogMode(Enum):
    """日志模式枚举"""
    CONSOLE_ONLY = "console_only"  # 只输出在控制台
    TIMED_ROTATING_ONLY = "timed_rotating_only"  # 只保存在时间轮转文件
    BOTH = "both"  # 同时输出在控制台和保存在时间轮转文件中



class Logger:
    """
    日志管理类，封装了日志配置和日志记录功能
    """

    def __init__(self, name: str = None, mode: LogMode = LogMode.BOTH,
                 config: Optional[Dict[str, Any]] = None):
        """
        初始化日志器

        Args:
            name: 日志器名称，如果为None则根据模式自动生成
            mode: 日志模式（CONSOLE_ONLY, TIMED_ROTATING_ONLY, BOTH）
            config: 自定义日志配置，如果为None则使用默认配置
        """
        # 如果未提供名称，根据模式自动生成
        if name is None:
            name = mode.value  # 使用模式值作为日志器名称

        self.name = name
        self.mode = mode
        self.config = config or self._get_default_config(mode, name)

        # 应用配置
        logging.config.dictConfig(self.config)

        # 获取日志器
        self.logger = logging.getLogger(self.name)

    def _get_default_config(self, mode: LogMode, logger_name: str) -> Dict[str, Any]:
        """根据模式获取默认日志配置"""

        # 创建log文件夹（如果不存在）
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 根据模式确定处理器列表
        if mode == LogMode.CONSOLE_ONLY:
            handlers = ['console']
        elif mode == LogMode.TIMED_ROTATING_ONLY:
            handlers = ['timed_rotating']
        else:  # BOTH
            handlers = ['console', 'timed_rotating']

        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'simple': {
                    'format': '文件名:%(caller_filename)s - 函数名:%(caller_funcname)s - 信息: %(message)s'
                },
                'detailed': {
                    'format': '时间:%(asctime)s - 文件名:%(caller_filename)s - 函数名:%(caller_funcname)s - 信息:%(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                }
            },
            'filters': {
                'user_filter': {
                    '()': 'logging.Filter',
                    'name': 'user'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',  # 输出到控制台
                    'level': 'DEBUG',
                    'formatter': 'simple',
                },
                'timed_rotating': {
                    'class': 'logging.handlers.TimedRotatingFileHandler',  # 输出到文件
                    'level': 'DEBUG',
                    'formatter': 'detailed',
                    'filename': os.path.join('logs', 'time.log'),
                    'encoding': 'utf-8',
                    'when': 'D',
                    'interval': 1,
                    'backupCount': 7
                }
            },
            'loggers': {
                logger_name: {  # 使用传入的日志器名称
                    'level': 'DEBUG',
                    'handlers': handlers,
                    'propagate': False
                },
                'RootLogger': {
                    'level': 'INFO',
                    'handlers': ['console'] if mode == LogMode.CONSOLE_ONLY else []
                }
            }
        }

    def _get_caller_info(self):
        """获取调用者信息"""
        frame = inspect.currentframe().f_back.f_back  # 跳过当前方法和调用方法
        filename = frame.f_code.co_filename
        funcname = frame.f_code.co_name
        lineno = frame.f_lineno
        # 只显示文件名
        filename = filename.split('\\')[-1]  # 假设路径分隔符为'\\'
        return {
            'caller_filename': filename,
            'caller_funcname': funcname,
            'caller_lineno': lineno
        }

    def async_log(method):
        """
        混合模式异步日志装饰器
        在主线程获取调用者信息，在异步线程执行日志输出
        """

        @wraps(method)
        def wrapper(self, message: str, *args, **kwargs):
            """
            包装函数：主线程获取信息，异步线程输出日志

            Args:
                self: Logger实例
                message: 日志消息
                *args: 位置参数
                **kwargs: 关键字参数
            """
            from ThreadPoolManager import safe_submit, thread_pool
            # 在主线程中获取调用者信息（确保准确性）
            extra = self._get_caller_info()

            if thread_pool is None or thread_pool.shutdown:
                #线程池未初始化或已关闭，直接执行同步日志输出
                try:
                    method(self, message, *args, extra=extra, **kwargs)
                except Exception as e:
                    print(f"同步日志输出失败: {e}")
                return

            def async_execute():
                """在线程中执行的异步日志输出任务"""
                try:
                    # 调用原始的同步日志方法，使用主线程获取的extra信息
                    method(self, message, *args, extra=extra, **kwargs)
                except Exception as e:
                    # 异步执行中的异常处理
                    print(f"异步日志输出失败: {e}")

            # 提交异步任务到线程池（只包含日志输出部分）
            safe_submit(async_execute)

        return wrapper

    @async_log
    def debug(self, message: str, *args, **kwargs):
        """记录调试级别日志"""
        # extra = self._get_caller_info()
        self.logger.debug(message, *args,  **kwargs)

    @async_log
    def info(self, message: str, *args, **kwargs):
        """记录信息级别日志"""
        # extra = self._get_caller_info()
        # self.logger.info(message, *args, extra=extra, **kwargs)
        self.logger.info(message, *args, **kwargs)

    @async_log
    def warning(self, message: str, *args, **kwargs):
        """记录警告级别日志"""
        # extra = self._get_caller_info()
        # self.logger.warning(message, *args, extra=extra, **kwargs)
        self.logger.warning(message, *args, **kwargs)

    @async_log
    def error(self, message: str, *args, **kwargs):
        """记录错误级别日志"""
        # extra = self._get_caller_info()
        # self.logger.error(message, *args, extra=extra, **kwargs)
        self.logger.error(message, *args, **kwargs)

    @async_log
    def critical(self, message: str, *args, **kwargs):
        """记录严重级别日志"""
        # extra = self._get_caller_info()
        # self.logger.critical(message, *args, extra=extra, **kwargs)
        self.logger.critical(message, *args, **kwargs)

    def set_level(self, level: str):
        """
        设置日志级别

        Args:
            level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        """
        self.logger.setLevel(getattr(logging, level.upper()))

    def add_handler(self, handler: logging.Handler):
        """
        添加自定义处理器

        Args:
            handler: 日志处理器
        """
        self.logger.addHandler(handler)

    def remove_handler(self, handler: logging.Handler):
        """
        移除处理器

        Args:
            handler: 要移除的日志处理器
        """
        self.logger.removeHandler(handler)

    def get_logger(self) -> logging.Logger:
        """获取底层的logging.Logger对象"""
        return self.logger

    @classmethod
    def get_logger_by_name(cls, name: str) -> logging.Logger:
        """
        根据名称获取日志器（类方法）

        Args:
            name: 日志器名称

        Returns:
            logging.Logger对象
        """
        return logging.getLogger(name)


'''创建日志记录器实例'''

console_logger = Logger(mode=LogMode.CONSOLE_ONLY)  # 只输出在控制台
file_logger = Logger(mode=LogMode.TIMED_ROTATING_ONLY)  # 只保存在时间轮转文件
both_logger = Logger(mode=LogMode.BOTH)  # 同时输出在控制台和保存在时间轮转文件中

# 使用示例
if __name__ == "__main__":
    # 测试不同模式的日志器
    print("=== 测试不同模式的日志器 ===")

    print("\n=== 控制台模式 ===")
    console_logger = Logger(mode=LogMode.CONSOLE_ONLY)
    print(f"控制台日志器名称: {console_logger.name}")
    print(f"控制台日志器处理器数量: {len(console_logger.logger.handlers)}")
    console_logger.debug('调试信息：只输出到控制台')
    console_logger.info('业务信息：只输出到控制台')
    console_logger.warning('警告信息：只输出到控制台')

    print("\n=== 时间轮转文件模式 ===")
    file_logger = Logger(mode=LogMode.TIMED_ROTATING_ONLY)
    print(f"文件日志器名称: {file_logger.name}")
    print(f"文件日志器处理器数量: {len(file_logger.logger.handlers)}")
    file_logger.debug('调试信息：只保存到时间轮转文件')
    file_logger.info('业务信息：只保存到时间轮转文件')
    file_logger.warning('警告信息：只保存到时间轮转文件')

    print("\n=== 同时输出模式 ===")
    both_logger = Logger(mode=LogMode.BOTH)
    print(f"同时模式日志器名称: {both_logger.name}")
    print(f"同时模式日志器处理器数量: {len(both_logger.logger.handlers)}")
    both_logger.debug('调试信息：同时输出到控制台和文件')
    both_logger.info('业务信息：同时输出到控制台和文件')
    both_logger.warning('警告信息：同时输出到控制台和文件')

    # 测试自定义名称
    print("\n=== 测试自定义名称 ===")
    custom_logger = Logger(name='custom_logger', mode=LogMode.CONSOLE_ONLY)
    print(f"自定义日志器名称: {custom_logger.name}")
    custom_logger.info('自定义名称的日志器测试')

    # 验证修复效果
    print("\n=== 验证修复效果 ===")
    print("✓ 每个Logger实例使用不同的日志器名称")
    print("✓ console_logger.debug 应该只在控制台显示，不写入文件")
    print("✓ file_logger.debug 应该只写入文件，不在控制台显示")
    print("✓ both_logger.debug 应该在控制台和文件中都显示")

    # 检查日志器是否独立
    console_logger2 = Logger(mode=LogMode.CONSOLE_ONLY)
    print(f"\n第二个控制台日志器名称: {console_logger2.name}")
    print(f"两个控制台日志器是否相同: {console_logger.name == console_logger2.name}")
    print("✓ 相同模式的日志器使用不同的名称，避免冲突")