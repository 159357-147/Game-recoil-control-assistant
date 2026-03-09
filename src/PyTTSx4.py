import time  # 导入time模块,用于时间相关操作
import pyttsx4  # 导入pyttsx4模块,用于语音合成
import queue  # 导入queue模块,用于语音队列
import threading  # 导入threading模块,用于线程操作

# from ThreadPoolManager import safe_submit  # 导入线程池管理器,用于提交任务到线程池
from Logger import console_logger, file_logger, both_logger# 导入Logger模块,用于日志记录

engine = pyttsx4.init()  # 初始化引擎
is_running = False  # 用于跟踪是否有任务正在执行
voice_queue = queue.Queue()  # 初始化语音队列

def start_voice_thread():
    """启动语音线程（守护线程）"""
    voice_thread = threading.Thread(target=speak, daemon=True)
    voice_thread.start()
    return voice_thread

def add_voice_queue(text):
    voice_queue.put(text)  # 将文本添加到队列中

    if voice_queue.qsize() == 1:  # 如果队列中只有一个文本
        if is_running:  # 如果正在进行语音播报
            pass  # 不提交新任务
        elif not is_running:  # 如果任务未执行,则提交新任务
            # safe_submit(speak)  # 提交任务到线程池进行播报
            voice_thread = threading.Thread(target=speak, daemon=True) # 创建语音线程（守护线程）；target指定线程要执行的函数，daemon=True表示线程为守护线程，主线程结束时会自动结束
            voice_thread.start()  # 启动语音线程

    elif voice_queue.qsize() > 1:  # 如果队列中有多个文本,则删除第一个文本
        voice_queue.get()  # 获取第一个文本，同时会删除这个文本
        voice_queue.task_done()  # 标记任务已完成

def speak():
    global is_running  # 声明 is_running 为全局变量
    # engine = pyttsx4.init()  # 初始化引擎

    while not voice_queue.empty():  # 当队列不为空时继续循环
        is_running = True  # 标记任务正在执行

        console_logger.info(f'语音队列正在循环')  # 输出详细信息到控制台

        if voice_queue.qsize() == 1:  # 队列大小为1时执行播报任务
            text = voice_queue.get()  # 获取队列中的文本，timeout参数指定等待时间，如果超过0.5秒没有文本，则抛出异常，并标记任务已完成

            if text:  # 如果文本不为空
                engine.say(text)  # 播放文本
                engine.runAndWait()  # 阻塞线程，等待播放完成
                # engine.stop() # 停止引擎,释放资源，重置状态

            voice_queue.task_done()  # 标记任务已完成
        # time.sleep(0.2)

    console_logger.info(f'语音队列循环结束')  # 输出详细信息到控制台
    is_running = False  # 标记任务已完成

if __name__ == "__main__":
    for i in range(10):
        text = f"这是第{i+1}条文本"
        add_voice_queue(text)
        time.sleep(0.5)

    time.sleep(5)
    add_voice_queue('最后一条文本')

    while True:
        add_voice_queue(input('请输入文本：'))