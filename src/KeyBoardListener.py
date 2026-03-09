from pynput import keyboard  # 键盘监听器
from pynput.keyboard import Key  # 特殊键枚举（如ESC、Ctrl，简化代码）

from Logger import console_logger
from ThreadPoolManager import safe_submit, safe_submit_delayed # 导入ThreadPoolManager模块，用于创建线程池
from PyTTSx4 import add_voice_queue # 导入PyTTSx4模块，用于语音播报

is_status = None # 定义全局变量is_status,用于存储程序运行/暂停状态
current_pressed_keys = set()  # 集合类型，记录当前按下的键，自动去除重复元素，确保每个按键只记录一次
ui = None # 定义全局变量ui,用于存储UI对象

def KBL_set_status(status):
    """接收GUI传递的程序自行状态参数，同步程序运行状态"""
    global is_status
    is_status = status

def set_ui(ui_instance):
    """接收main传递的主窗口实例，设置UI对象"""
    global ui
    ui = ui_instance

def handle_ctrl_l_alt_l_keys(key):
    """处理 左Ctrl + 左Alt 组合键，退出程序"""
    global ui

    ui.exit_requested.emit() # 发送退出信号
    console_logger.info("检测到 左Ctrl + 左Alt 组合键，退出程序")
    # 执行相应的操作，如模拟按键或触发其他事件

def handle_alt_l_g_keys(key):
    """处理 左Alt + 字母键 g 组合键，播报当前的父方案名称和子方案名称"""
    global ui
    console_logger.info("检测到 左Alt + 字母键 g 组合键，播报当前的父方案名称和子方案名称")
    if ui.switch_voice_CheckBox.isChecked() or ui.sub_switch_voice_CheckBox.isChecked(): # 如果方案切换语音播报复选框或子方案切换语音播报复选框被选中
        add_voice_queue(f'{ui.profile_combo.currentText()}，{ui.sub_profile_combo.currentText()}') # 播报当前的父方案名称和子方案名称

def handle_alt_l_h_keys(key):
    """处理 左Alt + 字母键 h 组合键，切换程序暂停/运行状态"""
    global ui
    ui.switch_status_requested.emit() # 发送切换状态信号
    console_logger.info("检测到 左Alt + 字母键 h 组合键，切换程序暂停/运行状态")

def handle_alt_l_j_keys(key):
    """处理 左Alt + 字母键 j 组合键，播报当前程序状态"""
    global ui
    console_logger.info("检测到 左Alt + 字母键 j 组合键，播报当前程序状态")
    if ui.voiceCheckBox.isChecked():  # 如果状态切换语音复选框被选中
        add_voice_queue(f'{ui.current_state_label.text()}')  # 语音播报切换后的状态，ui.current_state_label.text()是获取当前状态标签的文本内容

def handle_alt_l_k_keys(key):
    """处理 左Alt + 字母键 k 组合键，重启程序"""
    global ui
    ui.restart_requested.emit() # 发送重启信号
    console_logger.info("检测到 左Alt + 字母键 k 组合键， 重启程序")
    # 执行相应的操作，如模拟按键或触发其他事件

def handle_tab_keys(key):
    """处理 tab 键，切换程序暂停/运行状态，进行方案识别"""
    global ui

    ui.switch_status_requested.emit() # 发送切换状态信号
    console_logger.info("检测到 tab 键，切换程序暂停/运行状态")
    ui.run_the_recognizer_requested.emit() # 发送运行识别器信号
    console_logger.info("检测到 tab 键，请求运行识别器")

def handle_backspace_keys(key):
    """处理 backspace 键，切换程序暂停/运行状态"""
    global ui
    ui.switch_status_requested.emit() # 发送切换状态信号
    console_logger.info("检测到 backspace 键，切换程序暂停/运行状态")

def handle_m_key(key):
    """处理 字母键 m 键，切换程序暂停/运行状态"""
    global ui
    ui.switch_status_requested.emit() # 发送切换状态信号
    console_logger.info("检测到 字母键 m 键，切换程序暂停/运行状态")

def handle_switch_plan_keys(key):
    """处理小键盘区域字母键 / 或 * 键，切换方案"""
    global ui
    if key == 111: # 如果按下的键是小键盘符号键 /
        ui.switch_plan_requested.emit(-1) # 发送切换方案信号，参数为-1，表示切换到上一个方案
        console_logger.info("检测到 小键盘符号键 / 键，切换上一个父方案")
    elif key == 106: # 如果按下的键是小键盘符号键 *
        ui.switch_plan_requested.emit(1) # 发送切换方案信号，参数为1，表示切换到下一个方案
        console_logger.info("检测到 小键盘符号键 * 键，切换下一个父方案")

def handle_switch_sub_plan_keys(key):
    """处理小键盘区域字母键 + 或 - 键，切换子方案"""
    global ui
    if key == 107: # 如果按下的键是小键盘符号键 +
        ui.switch_sub_plan_requested.emit(1) # 发送切换方案信号，参数为1，表示切换到下一个方案
        console_logger.info("检测到 小键盘符号键 + 键，切换下一个子方案")
    elif key == 109: # 如果按下的键是小键盘符号键 -
        ui.switch_sub_plan_requested.emit(-1) # 发送切换方案信号，参数为-1，表示切换到上一个方案
        console_logger.info("检测到 小键盘符号键 - 键，切换上一个子方案")

def handle_number_switch_sub_plan_keys(key):
    """处理小键盘区域数字键 0-9 键，切换子方案"""
    global ui
    ui.number_switch_sub_plan_requested.emit(key) # 发送切换方案信号，参数为 key.vk 虚拟键码

def handle_key_char_1_2_keys(key):
    """处理字母区域数字键 1-2 键，将程序切换为运行状态，切换方案"""
    global ui, is_status
    if not is_status: # 如果当前状态不是运行状态
        ui.switch_status_requested.emit() # 发送切换状态信号
        console_logger.info("检测到 字母区域数字键 1-2 键，切换程序为运行状态")

    ui.recognizer_switch_plan_requested.emit(1 if key == keyboard.KeyCode.from_char('1') else 2) # 发送切换方案信号，参数为1或2，根据按键判断

def handle_key_char_0_3_9_keys(key):
    """处理字母区域数字键 0，3-9 键，将程序切换为暂停"""
    global ui, is_status
    if is_status: # 如果当前状态是运行状态
        ui.switch_status_requested.emit() # 发送切换状态信号
        console_logger.info(f"检测到 字母区域数字键 {key}，切换程序为暂停状态")

def handle_press_shift_keys(key):
    """处理 shift 键按下事件，将 shift_pressed 状态设置为 True"""
    from MouseListener import set_shift_pressed
    set_shift_pressed(True) # 更新 shift 键是否被按下的状态为 True

def handle_release_shift_keys(key):
    """处理 shift 键释放事件，将 shift_pressed 状态设置为 False"""
    from MouseListener import set_shift_pressed
    set_shift_pressed(False) # 更新 shift 键是否被按下的状态为 False

# 定义按键到处理函数的映射
KEY_ACTION_MAP = { # frozenset 不可变集合，用于存储按键组合,与按键顺序无关，内容相同即为相同集合
    frozenset([keyboard.Key.ctrl_l, keyboard.Key.alt_l]): handle_ctrl_l_alt_l_keys, # 左Ctrl + 左Alt 组合键，退出程序
    frozenset([keyboard.Key.alt_l, keyboard.KeyCode.from_char('g')]): handle_alt_l_g_keys, # 左Alt + 字母键 g 组合键，播报当前的父方案名称和子方案名称
    frozenset([keyboard.Key.alt_l, keyboard.KeyCode.from_char('h')]): handle_alt_l_h_keys, # 左Alt + 字母键 h 组合键，切换程序暂停/运行状态
    frozenset([keyboard.Key.alt_l, keyboard.KeyCode.from_char('j')]): handle_alt_l_j_keys, # 左Alt + 字母键 j 组合键，播报当前程序状态
    frozenset([keyboard.Key.alt_l, keyboard.KeyCode.from_char('k')]): handle_alt_l_k_keys, # 左Alt + 字母键 k 组合键，重启程序
    frozenset([keyboard.KeyCode.from_char('m')]) : handle_m_key, # 字母键 m 键，切换程序暂停/运行状态
    frozenset([keyboard.Key.tab]) : handle_tab_keys, # tab 键，切换程序暂停/运行状态，进行方案识别
    frozenset([keyboard.Key.backspace]) : handle_backspace_keys, # backspace 键，切换程序暂停/运行状态
    frozenset([keyboard.Key.shift]) : handle_press_shift_keys, # shift 键，将 shift_pressed 状态设置为 True
    frozenset([111]) : handle_switch_plan_keys, # 小键盘符号键 / 键，切换上一个父方案
    frozenset([106]) : handle_switch_plan_keys, # 小键盘符号键 * 键，切换下一个父方案
    frozenset([107]) : handle_switch_sub_plan_keys, # 小键盘符号键 + 键，切换下一个子方案
    frozenset([109]) : handle_switch_sub_plan_keys, # 小键盘符号键 - 键，切换上一个子方案
    frozenset([keyboard.KeyCode.from_char('0')]): handle_key_char_0_3_9_keys, # 字母区域数字键 0，3-9 键，将程序切换为暂停
    frozenset([keyboard.KeyCode.from_char('3')]): handle_key_char_0_3_9_keys, # 字母区域数字键 0，3-9 键，将程序切换为暂停
    frozenset([keyboard.KeyCode.from_char('4')]): handle_key_char_0_3_9_keys, # 字母区域数字键 0，3-9 键，将程序切换为暂停
    frozenset([keyboard.KeyCode.from_char('5')]): handle_key_char_0_3_9_keys, # 字母区域数字键 0，3-9 键，将程序切换为暂停
    frozenset([keyboard.KeyCode.from_char('6')]): handle_key_char_0_3_9_keys, # 字母区域数字键 0，3-9 键，将程序切换为暂停
    frozenset([keyboard.KeyCode.from_char('7')]): handle_key_char_0_3_9_keys, # 字母区域数字键 0，3-9 键，将程序切换为暂停
    frozenset([keyboard.KeyCode.from_char('8')]): handle_key_char_0_3_9_keys, # 字母区域数字键 0，3-9 键，将程序切换为暂停
    frozenset([keyboard.KeyCode.from_char('9')]): handle_key_char_0_3_9_keys, # 字母区域数字键 0，3-9 键，将程序切换为暂停
    frozenset([keyboard.KeyCode.from_char('1')]): handle_key_char_1_2_keys, # 字母区域数字键 1-2 键，将程序切换为运行状态，切换方案
    frozenset([keyboard.KeyCode.from_char('2')]): handle_key_char_1_2_keys, # 字母区域数字键 1-2 键，将程序切换为运行状态，切换方案
}

# 定义需要处理的按键集合
relevant_keys = {
    # 小键盘符号键 虚拟键码 +, -, *, /
    107, 109, 106, 111,
    # 小键盘区域数字键 虚拟键码 0-9
    96, 97, 98, 99, 100, 101, 102, 103, 104, 105,
    # 字母区域数字键 0-9
    keyboard.KeyCode.from_char('0'), keyboard.KeyCode.from_char('1'), keyboard.KeyCode.from_char('2'), keyboard.KeyCode.from_char('3'),
    keyboard.KeyCode.from_char('4'), keyboard.KeyCode.from_char('5'), keyboard.KeyCode.from_char('6'), keyboard.KeyCode.from_char('7'),
    keyboard.KeyCode.from_char('8'), keyboard.KeyCode.from_char('9'),
    # 左Ctrl键和左Alt键，tab键，backspace键，shift键
    keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.Key.tab, keyboard.Key.backspace, keyboard.Key.shift,
    # 字母键 g, h, j, k, m
    keyboard.KeyCode.from_char('g'), keyboard.KeyCode.from_char('h'), keyboard.KeyCode.from_char('j'), keyboard.KeyCode.from_char('k'), keyboard.KeyCode.from_char('m'),
}

def on_press(key):
    """按键按下时触发"""
    global current_pressed_keys  # 声明全局变量current_pressed_keys

    if key not in current_pressed_keys and key in relevant_keys:  # 如果当前按下的键不在已按下键集合中，且在需要处理的集合中
        current_pressed_keys.add(key)  # 将字符表示添加到集合中
        safe_submit(process_press, key) # 提交耗时任务到线程池，立即返回，不阻塞监听线程
        # console_logger.warning(f"添加按键 {key} 后的集合：{current_pressed_keys}")

    elif hasattr(key, 'vk') and key.vk not in current_pressed_keys and key.vk in relevant_keys:  # 如果key存在虚拟键码，且虚拟键码不在已按下键集合中，且在需要处理的集合中
        current_pressed_keys.add(key.vk)  # 将虚拟键码添加到集合中
        safe_submit(process_press, key.vk) # 提交耗时任务到线程池，立即返回，不阻塞监听线程
        # console_logger.warning(f"添加按键 {key.vk} 虚拟键码后的集合：{current_pressed_keys}")

    else:
        return  # 直接返回

def on_release(key):
    """按键释放时触发"""
    global current_pressed_keys  # 声明全局变量current_pressed_keys

    if key in current_pressed_keys:  # 如果当前释放的键在集合中
        current_pressed_keys.remove(key) # 如果在集合中，移除该键
        # 提交耗时任务到线程池，立即返回，不阻塞监听线程
        safe_submit(process_release, key)
    elif hasattr(key, 'vk') and key.vk in current_pressed_keys:  # 如果当前释放的键的虚拟键码在集合中
        current_pressed_keys.remove(key.vk) # 如果在集合中，移除该键的虚拟键码
        # console_logger.warning(f"移除按键 {key.vk} 虚拟键码后的集合：{current_pressed_keys}")
    else:
        return # 直接返回

def process_press(key):
    """线程池中处理按键按下事件"""
    if isinstance(key, int): # 如果是虚拟键码；isinstance()是Python的内置函数，用于判断一个对象是否是指定类型的实例，key是传递的按键对象，int是
        if 96 <= key <= 105: # 如果是小键盘区域数字键
            console_logger.warning(f"按下小键盘数字键：{key}")
            handle_number_switch_sub_plan_keys(key)
        elif key in (107, 109, 106, 111): # 如果是小键盘符号键+ - * /
            pressed_keys = frozenset(current_pressed_keys & relevant_keys) # 获取当前按下的键与需要处理的键的冻结交集

            if pressed_keys in KEY_ACTION_MAP: # 检查集合中的元素是否在映射表中
                KEY_ACTION_MAP[pressed_keys](key) # 执行对应键的处理函数
            else:
                console_logger.warning(f"未检测到按键映射：{pressed_keys}") # 输出基本信息到控制台
    else:
        pressed_keys = frozenset(current_pressed_keys & relevant_keys) # 获取当前按下的键与需要处理的键的冻结交集

        if pressed_keys in KEY_ACTION_MAP: # 检查集合中的元素是否在映射表中
            KEY_ACTION_MAP[pressed_keys](key) # 执行对应键的处理函数
        else:
            console_logger.warning(f"未检测到按键映射：{pressed_keys}") # 输出基本信息到控制台

def process_release(key):
    """线程池中处理按键释放事件"""

    # console_logger.warning(f"删除按键 {key} 后的集合：{current_pressed_keys}")
    if key == keyboard.Key.shift: # 如果是 shift 键
        handle_release_shift_keys(key) # 处理 shift 键，切换程序暂停/运行状态


if __name__ == "__main__":

    from concurrent.futures import ThreadPoolExecutor  # 导入ThreadPoolExecutor模块，用于创建线程池
    # 创建线程池（指定最大线程数，避免资源耗尽）
    executor = ThreadPoolExecutor(max_workers=2)
    # 创建监听器实例
    listener = keyboard.Listener(
        on_press=on_press,  # 按键按下时调用的函数
        on_release=on_release  # 按键释放时调用的函数
    )
    # 启动监听（后台线程，非阻塞）
    listener.start()

    # 手动停止监听（可选，如在其他逻辑中调用）
    # listener.stop()
    # 阻塞主线程（可选，避免程序直接退出）
    listener.join()  # 也可使用input("按回车停止...")