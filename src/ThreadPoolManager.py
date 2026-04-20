import time  # 导入 time 模块，用于时间操作
import traceback  # 导入 traceback 模块，用于异常追踪
from concurrent.futures import ThreadPoolExecutor  # 导入 ThreadPoolExecutor 和 Future，用于线程池管理
from functools import wraps  # 导入 wraps 装饰器，用于保留原始函数的元数据

from Logger import console_logger, both_logger  # 导入Logger模块,用于日志记录

# 全局线程池实例，采用单例模式
thread_pool = None

def init_thread_pool():
    """初始化全局线程池"""
    global thread_pool  # 声明全局变量 thread_pool，用于存储线程池实例
    if thread_pool is None:  # 检查线程池是否已经初始化，避免重复初始化
        import os  # 导入 os 模块，用于操作系统相关操作
        max_workers = min(8, (os.cpu_count() or 4) * 2)  # 计算最大线程数，限制在 8 以内
        # os.cpu_count() - 获取CPU核心数; os.cpu_count() or 4 - 安全获取CPU核心数:如果os.cpu_count()返回None（某些系统可能不支持），则使用默认值4; (os.cpu_count() or 4) * 2 - 计算推荐线程数:将CPU核心数乘以2，这是常见的线程池配置策略
        thread_pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='GunPress')  # 创建线程池实例，设置最大线程数，避免资源过度消耗，设置线程名称前缀，便于调试和监控
        console_logger.warning(f"线程池初始化完成，最大线程数: {max_workers}")


def get_thread_pool():
    """获取线程池实例，如果不存在则初始化"""
    '''懒加载模式：首次使用时才初始化线程池; 单例保证：确保全局只有一个线程池实例'''
    global thread_pool
    if thread_pool is None:
        init_thread_pool()
    return thread_pool

'''装饰器模式; 类型: 函数装饰器（高阶函数）; 作用: 包装目标函数，添加异常处理逻辑; 输入: 任意函数 func; 输出: 包装后的安全函数 wrapper'''
def thread_safe(func):
    """线程安全装饰器，自动处理异常"""
    '''异常捕获：自动捕获并记录所有异常; 详细日志：输出函数名和完整异常堆栈; 优雅降级：异常时返回None而非崩溃'''

    '''@wraps(func) 装饰器; 作用: 保留原始函数的元数据（名称、文档字符串等）
重要性: 避免装饰器破坏函数的自省能力
无@wraps: wrapper.__name__ 返回 'wrapper'
有@wraps: wrapper.__name__ 返回原始函数名'''
    @wraps(func)
    def wrapper(*args, **kwargs):
        # args 是一个元组（tuple)，包含所有位置参数（接收任意数量的位置参数，args是约定俗成的名称，可以用其他名称）
        # kwargs 是一个字典(dict)，包含所有关键字参数（接收任意数量的关键字参数，kwargs是约定俗成的名称，可以用其他名称）
        try:
            return func(*args, **kwargs)  # 执行原始函数
        except Exception as e:
            both_logger.error(f"线程池任务执行异常: {func.__name__} - {str(e)}")
            both_logger.error(f"异常详情: {traceback.format_exc()}")
            return None

    return wrapper


def safe_submit(func, *args, **kwargs):
    """安全提交任务到线程池，带异常处理"""
    pool = get_thread_pool()
    if pool:
        # 包装原始函数以处理异常
        safe_func = thread_safe(func)
        return pool.submit(safe_func, *args, **kwargs)
    else:
        console_logger.warning("线程池未初始化，任务提交失败")
        return None


def safe_submit_delayed(delay, func, *args, **kwargs):
    """延迟执行的安全任务提交"""

    def delayed_func():
        time.sleep(delay)
        return func(*args, **kwargs)

    return safe_submit(delayed_func)


def shutdown_thread_pool():
    """关闭线程池"""
    global thread_pool
    if thread_pool:  # 检查线程池是否存在,避免重复关闭
        thread_pool.shutdown(wait=False)  # 关闭线程池，不等待任务完成
        thread_pool = None  # 将线程池实例置为 None，确保不再使用
        console_logger.warning("线程池已关闭")



# 模块导入时自动初始化
init_thread_pool()