import random # 导入random模块,用于生成随机数
import time
from pynput import mouse # 导入pynput库中的mouse模块,用于监听鼠标事件
import threading # 导入threading模块,用于创建线程

from ThreadPoolManager import safe_submit, safe_submit_delayed # 导入ThreadPoolManager模块，用于创建线程池
from Logger import console_logger, file_logger, both_logger# 导入Logger模块,用于日志记录
from ghub import press_mouse_button, release_mouse_button, mouse_xy # 导入ghub模块,用于模拟鼠标操作

is_status = None # 定义全局变量is_status, 由UI在程序状态改变时传递过来，实现同步
is_dragging = False  # 拖动标志，初始为False，表示未拖动, 用于控制拖动鼠标的操作是否执行，鼠标左键按下时设置为True，松开时设置为False
lock = threading.Lock()  # 创建一个锁对象，用于线程同步

current_pressed_mouse_buttons = set()  # 集合类型,记录当前按下的鼠标按钮
drag_parameters = None # 拖动延时参数，用于存储拖动鼠标延时的最小值和最大值
shift_pressed = False  # 定义全局变量shift_pressed, 用于记录 shift 键是否被按下
is_test_mode_enabled = False # 测试模式标志，初始为False，表示未启用测试模式, 用于控制是否记录鼠标移动事件

ui = None # 定义全局变量ui,用于存储UI对象
mouse_listener = None # 当前鼠标监听器实例
current_profile = None # 定义全局变量profile,用于存储方案参数

def stop_mouse_listener():
    """停止当前鼠标监听器"""
    global mouse_listener

    if mouse_listener is not None:
        mouse_listener.stop()
        mouse_listener = None
        console_logger.warning("鼠标监听器已停止")

def create_basic_mouse_listener():
    """创建基本的鼠标监听器(只有 on_click 点击事件回调函数)"""
    global mouse_listener
    stop_mouse_listener() # 创建基础鼠标监听器前，先停止当前鼠标监听器

    mouse_listener = mouse.Listener(
        on_click = on_click,  # 点击事件回调
        # on_move = on_move,  # 移动事件回调
        # on_scroll = on_scroll  # 滚轮事件回调
    )
    mouse_listener.start() # 启动鼠标监听器
    console_logger.warning("基础鼠标监听器已启动（ on_click 点击事件回调）")

def create_test_mouse_listener():
    """创建测试鼠标监听器( on_click 点击事件和 on_move 移动事件回调函数)"""
    global mouse_listener
    stop_mouse_listener() # 创建测试鼠标监听器前，先停止当前鼠标监听器
    mouse_listener = mouse.Listener(
        on_click = on_click,  # 点击事件回调
        on_move = on_move,  # 移动事件回调
        # on_scroll = on_scroll  # 滚轮事件回调
    )
    mouse_listener.start() # 启动鼠标监听器
    console_logger.warning("测试鼠标监听器已启动（ on_click 点击事件和 on_move 移动事件回调）")

def set_is_test_mode_enabled(enabled):
    """设置测试模式是否启用"""
    global is_test_mode_enabled
    is_test_mode_enabled = enabled # 更新测试模式是否启用的状态

def set_shift_pressed(pressed):
    """设置 shift 键是否被按下"""
    global shift_pressed
    shift_pressed = pressed # 更新 shift 键是否被按下的状态

def set_drag_delay(delay_min, delay_max):
    """设置拖动延迟"""
    global drag_parameters
    if delay_min > delay_max:
        delay_min, delay_max = delay_max, delay_min
    drag_parameters = [delay_min, delay_max]

def set_profile(profile_instance):
    """接收GUI传递的配置文件实例，设置配置文件对象"""
    global current_profile
    current_profile = profile_instance

def MouseListener_set_ui(ui_instance):
    """接收main传递的主窗口实例，设置UI对象"""
    global ui
    ui = ui_instance

def ML_set_status(status):
    """接收GUI传递的程序自行状态参数，同步程序运行状态"""
    global is_status
    is_status = status

def get_param_value(params, key):
    """统一获取参数值，支持字典和对象两种访问方式"""
    if isinstance(params, dict):  # 判断params是否为字典类型；isinstance()是Python的内置函数，用于判断一个对象是否是指定类型的实例，params是要判断的对象，dict是指定的类型
        return params[key]  # 如果是字典类型，直接使用键名访问对应的值
    else:
        return getattr(params, key)  # 如果不是字典类型，使用getattr()函数获取对象的属性值，params是要获取属性的对象，key是要获取的属性名

def get_parameters_for_elapsed(profile, elapsed):
    """根据已流逝时间获取对应的参数"""
    # 首先检查是否有匹配的时间段
    for segment in profile.time_segments:  # 遍历时间段参数列表；profile.time_segments是一个列表，用于存储所有时间段参数对象
        if segment.start_time <= elapsed < segment.end_time:  # 如果当前时间在时间段范围内
            return segment  # 返回对应的参数对象

    # 如果没有匹配的时间段，使用基础参数
    return profile.base_params

# 定义鼠标事件回调函数
def on_click(x, y, button, pressed):
    '''x, y: 鼠标点击的屏幕坐标
    button: 鼠标按钮 (mouse.Button.left/right/middle/x1/x2)
    pressed: 布尔值，True表示按下，False表示释放'''
    # action = "按下" if pressed else "释放"
    # print(f"在({x}, {y}){action}鼠标{button}键") # 输出鼠标点击事件到控制台

    safe_submit(process_click, x, y, button, pressed) # 提交耗时任务到线程池，立即返回，不阻塞监听线程

def on_move(x, y):
    '''x, y: 鼠标移动后的新坐标'''
    safe_submit(process_move,x, y) # 将鼠标移动事件提交到线程池，立即返回，不阻塞监听线程

def on_scroll(x, y, dx, dy):
    '''x, y: 滚轮操作时的鼠标位置
    dx, dy: 滚轮滚动的水平和垂直距离'''
    return

# 定义需要处理的鼠标按钮集合
relevant_mouse_buttons = {
    # 鼠标左键，侧边按钮
    mouse.Button.left, mouse.Button.x1, mouse.Button.x2,
}

def drag_mouse():
    '''拖动鼠标'''
    global is_dragging, is_status, ui, current_profile, drag_parameters  # 声明全局变量

    try:
        delay_min, delay_max = drag_parameters[0], drag_parameters[-1]
        delay_ms = random.randint(delay_min, delay_max) / 1000
        time.sleep(delay_ms)
    except Exception as e:
        console_logger.error(f"参数加载失败: {e}")
        return

    total_x_movement = 0 # 记录总水平移动距离
    start_drag_time = time.time() # 记录开始拖动的时间

    while is_dragging and is_status: # 当拖动标志为True且程序运行状态为True时

        if mouse.Button.x1 in current_pressed_mouse_buttons or mouse.Button.x2 in current_pressed_mouse_buttons: # 如果侧边按钮x1或x2被按下
            break # 如果侧边按钮x1或x2被按下，跳出循环，结束拖动
        if shift_pressed: # 如果 shift 键被按下
            continue # 如果 shift 键被按下，跳过当前循环，继续下一次循环

        current_time = time.time() # 获取当前时间
        elapsed = current_time - start_drag_time # 计算已过去的时间
        # 根据已流逝时间获取对应的参数
        params = get_parameters_for_elapsed(current_profile, elapsed) # 调用get_parameters_for_elapsed函数获取对应的参数，elapsed是已流逝的时间，current_profile是储存当前方案参数的profile类

        if total_x_movement >= 5 or total_x_movement <= -5: # 如果水平移动距离超过5或小于-5
            x_offset = (-total_x_movement + 2) if total_x_movement > 0 else (-total_x_movement - 2) # 如果水平移动距离超过5或小于-5，反向移动鼠标，移动距离为当前水平移动距离的相反数再加2
        else:
            x_offset = random.randint(get_param_value(params, 'x_min'), get_param_value(params, 'x_max'))

        y_move = random.randint(get_param_value(params, 'y_min'), get_param_value(params, 'y_max'))

        total_x_movement += x_offset # 累加水平移动距离

        mouse_xy(x_offset, y_move) # 调用mouse_xy函数移动鼠标

        sleep_time = random.uniform(get_param_value(params, 'sleep_min') / 1000, get_param_value(params, 'sleep_max') / 1000) # 生成随机的休眠时间，random.uniform生成一个浮点数随机数，包含两端点
        time.sleep(sleep_time) # 休眠一段时间

        # 记录当前使用的参数信息（用于调试）
        # console_logger.debug(f"已流逝时间: {elapsed:.2f}s, 使用参数: x[{get_param_value(params, 'x_min')}-{get_param_value(params, 'x_max')}], y[{get_param_value(params, 'y_min')}-{get_param_value(params, 'y_max')}], sleep[{get_param_value(params, 'sleep_min')}-{get_param_value(params, 'sleep_max')}ms]")
        # print(f"已流逝时间: {elapsed:.2f}s, 使用参数: x[{get_param_value(params, 'x_min')}-{get_param_value(params, 'x_max')}], y[{get_param_value(params, 'y_min')}-{get_param_value(params, 'y_max')}], sleep[{get_param_value(params,'sleep_min')}-{get_param_value(params,'sleep_max')}ms]")

def handle_mouse_button_left(x, y, button, pressed):
    '''处理鼠标左键事件'''
    global is_dragging  # 声明全局变量is_dragging

    if mouse.Button.x1 in current_pressed_mouse_buttons or mouse.Button.x2 in current_pressed_mouse_buttons: # 如果侧边按钮x1或x2被按下
        return  # 如果侧边按钮x1或x2被按下，直接返回,不处理鼠标左键事件

    if button == mouse.Button.left : # 再次验证，如果是鼠标左键事件

        if pressed: # 如果是按下事件
            # console_logger.info("检测到鼠标左键按下事件")
            with lock: # 获取锁
                is_dragging = True # 设置为正在拖动
            safe_submit(drag_mouse) # 提交拖动任务到线程池

            if is_test_mode_enabled: # 如果是测试模式处于启用状态
                global move_records
                start_time = time.time() # 记录开始拖动的时间
                start_y = y # 记录开始拖动的Y坐标
                move_records = [(start_time, start_y)]  # 初始化移动记录（时间戳，Y坐标）

        elif not pressed: # 如果是释放事件
            with lock: # 获取锁
                is_dragging = False # 设置为停止拖动

            if is_test_mode_enabled:  # 如果是测试模式处于启用状态
                end_time = time.time() # 记录结束拖动的时间
                end_y = y # 记录结束拖动的Y坐标
                move_records.append((end_time, end_y)) # 添加结束拖动的记录（时间戳，Y坐标）
                # 计算每0.1秒的Y轴像素变化量
                if len(move_records) >= 2: # 如果移动记录中至少有2个点
                    calculate_y_changes_per_01s()
    else:
        return # 直接返回

def calculate_y_changes_per_01s():
    """计算每0.1秒的Y轴像素变化量"""
    global move_records

    if len(move_records) < 2: # 如果列表长度小于2，无法计算变化量，直接返回
        return

    # 按时间排序（确保数据有序）
    move_records.sort(key=lambda record: record[0]) # .sort()方法对列表进行排序，key参数指定排序依据，lambda record: record[0]表示按记录中的第一个元素（时间戳）进行排序

    start_time = move_records[0][0] # 获取移动记录中的第一个时间戳（开始拖动的时间）
    end_time = move_records[-1][0] # 获取移动记录中的最后一个时间戳（结束拖动的时间）
    total_duration = end_time - start_time # 计算总持续时间（结束时间减去开始时间）

    # 计算0.1秒间隔的数量
    interval_count = int(total_duration / 0.1) + 1 # 计算0.1秒间隔的数量，int(total_duration / 0.1)表示总持续时间除以0.1，得到0.1秒间隔的数量，+1表示包括最后一个间隔

    y_changes = []  # 存储每0.1秒的Y轴变化量

    for i in range(interval_count):
        target_time = start_time + i * 0.1 # 计算当前0.1秒间隔的目标时间点（开始时间加上当前间隔数乘以0.1）
        next_time = target_time + 0.1 # 计算下一个0.1秒间隔的时间点（目标时间加上0.1）

        # 找到目标时间点的Y坐标
        target_y = get_closest_y(target_time) # 获取目标时间点最接近的Y坐标
        next_y = get_closest_y(next_time) # 获取下一个0.1秒间隔的时间点最接近的Y坐标

        # 计算变化量（像素变化）
        change = next_y - target_y
        y_changes.append(f'{i * 0.1:.1f} - {(i + 1) * 0.1:.1f}s: {change:+.1f}  \n')

    ui.test_info_te_update_requested.emit("\n".join(y_changes)) # 发射测试信息文本框更新信号，参数为y_changes列表的字符串表示
    return y_changes

def get_closest_y(target_time):
    """获取指定时间最接近的Y坐标"""
    global move_records
    if not move_records:
        return 0
    return min(move_records, key=lambda record: abs(record[0] - target_time))[1]

def handle_mouse_button_x1_x2(x, y, button, pressed):
    '''处理鼠标侧边按钮1和2事件'''

    if button in (mouse.Button.x1, mouse.Button.x2): # 再次验证，如果是鼠标侧边按钮1或2事件
        # console_logger.info("检测到鼠标侧边按钮1或2事件")
        if pressed: # 如果是按下事件
            delay_ms = random.randint(5, 20) / 1000 # 随机生成一个5到30毫秒的延迟
            console_logger.info(f"侧边按钮{button}按下， 延迟{delay_ms * 1000}毫秒后按下左键")

            def press_left_button():
                '''延迟按下左键'''
                press_mouse_button(1) # 调用函数按下左键

            safe_submit_delayed(delay_ms, press_left_button) # 提交延迟任务到线程池
        elif not pressed: # 如果是释放事件
            delay_ms = random.randint(5, 20) / 1000 # 随机生成一个5到30毫秒的延迟
            console_logger.info(f"侧边按钮{button}释放， 延迟{delay_ms * 1000}毫秒后释放左键")

            def release_left_button():
                '''延迟释放左键'''
                release_mouse_button(1) # 调用函数释放左键

            safe_submit_delayed(delay_ms, release_left_button) # 提交延迟任务到线程池
    else:
        return # 直接返回

# 定义鼠标按钮对应的操作映射
MOUSE_BUTTONS_ACTION_MAP = {
    mouse.Button.left: handle_mouse_button_left,
    mouse.Button.x1: handle_mouse_button_x1_x2,
    mouse.Button.x2: handle_mouse_button_x1_x2,
}

def process_click(x, y, button, pressed):
    '''处理鼠标点击事件,线程池运行'''
    global current_pressed_mouse_buttons  # 声明全局变量current_pressed_mouse_buttons

    if pressed and (button in relevant_mouse_buttons): # 如果当前按下的按钮在需要处理的集合中
        current_pressed_mouse_buttons.add(button)  # 将当前按下的按钮添加到集合中
        #console_logger.info(f'将鼠标按钮 {button} 添加到集合中')
    elif not pressed and (button in current_pressed_mouse_buttons):  # 如果当前释放的按钮在集合中
        current_pressed_mouse_buttons.discard(button)  # 从集合中移除当前释放的按钮
        #console_logger.info(f'将鼠标按钮 {button} 从集合中移除')
    else:
        return  # 直接返回
    MOUSE_BUTTONS_ACTION_MAP[button](x, y, button, pressed) # 执行对应按钮的处理函数
    # console_logger.info(f"异步处理点击：({x}, {y})，按钮：{button}，状态：{f'按下' if pressed else '释放'}")

def process_move(x, y):
    '''处理鼠标移动事件，线程池运行'''
    # console_logger.info(f"异步处理移动事件：({x}, {y})")
    if is_test_mode_enabled and is_dragging: # 如果是测试模式处于启用状态且正在拖动
        move_records.append((time.time(), y)) # 添加当前移动的记录（时间戳，Y坐标）

if __name__ == "__main__":

    from concurrent.futures import ThreadPoolExecutor  # 导入ThreadPoolExecutor模块，用于创建线程池
    # 创建线程池（指定最大线程数，避免资源耗尽）
    executor = ThreadPoolExecutor(max_workers=2)

    # 创建鼠标监听器，指定回调函数
    mouse_listener = mouse.Listener(
        on_click=on_click,  # 点击事件回调
        on_move=on_move,  # 移动事件回调
        on_scroll=on_scroll  # 滚轮事件回调
    )
    # 启动监听（异步方式）
    # 监听器在后台运行，捕获鼠标事件
    # 事件会触发对应的回调函数进行处理
    mouse_listener.start()

    # 4. 阻塞主线程（可选，比如等待用户输入后停止）
    mouse_listener.join()  # 也可使用其他方式阻塞，如input("按回车停止监听...")
