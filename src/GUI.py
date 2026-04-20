from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QTabWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QGridLayout\
    , QCheckBox, QComboBox, QTextEdit, QStatusBar, QDialog, QMessageBox

from PySide6.QtCore import Signal, Qt

import json # 导入json模块,用于操作JSON数据,如读取和写入JSON文件
from pathlib import Path # 导入Path模块,用于操作文件和目录,如获取当前工作目录
import time

from Logger import console_logger, file_logger, both_logger # 导入Logger模块,用于日志记录
from ThreadPoolManager import safe_submit
from MouseListener import ML_set_status, set_profile, set_drag_delay
from KeyBoardListener import KBL_set_status
from PyTTSx4 import add_voice_queue # 导入PyTTSx4模块,用于语音播报
from PaddleOCR import AutomaticRecognition # 导入AutomaticRecognition模块,用于自动识别游戏中的元素

profiles_json = None # 参数方案文件
is_status = False # 全局变量is_status,用于控制程序的运行/暂停状态，初始值为False，表示程序暂停
recognizer = None # 全局变量recognizer,用于存储识别器对象，初始值为None
results = None # 全局变量results,用于存储识别结果字典，初始值为None
skip_next_recognition = False  # 是否跳过下次识别
main_keyboard_area_keys_1_2 = [1] # 全局列表，存储字母区按键1和2的顺序，初始值为空列表，用于在进行识别后，自动切换方案
plan_parameters = None # 全局字典，用于存储方案参数，便于后续解析函数调用

class MainWindow(QMainWindow): #主窗口

    exit_requested = Signal() # 定义 请求退出 信号
    restart_requested = Signal() # 定义 请求重启 信号
    switch_status_requested = Signal() # 定义 请求切换状态 信号
    switch_plan_requested = Signal(int) # 定义 请求切换父方案 信号，参数为切换方向，1为下一个，-1为上一个
    switch_sub_plan_requested = Signal(int) # 定义 请求切换子方案 信号，参数为切换方向，1为下一个，-1为上一个
    number_switch_sub_plan_requested = Signal(int) # 定义 数字键切换子方案 信号，参数为虚拟键码
    run_the_recognizer_requested = Signal() # 定义 请求运行识别器 信号
    ocr_results_update_requested = Signal(object, object, object)  # 识别结果文本框更新信号，参数：results_verify, results, startup
    recognizer_switch_plan_requested = Signal(int) # 定义 使用识别结果切换父方案和子方案 信号，参数为参按键，1为字母区按键1，2为字母区按键2
    test_info_te_update_requested = Signal(str) # 测试信息文本框更新信号，参数为测试信息文本

    def __init__(self): #初始化
        super().__init__() #调用父类的初始化方法
        self.init_ui() #调用init_ui方法，初始化UI界面
        self.init_data() #调用init_data方法，初始化数据
        self.load_config() #调用load_config方法，加载配置文件
        self.connect_signal_slot_function() #调用connect_signal_slot_function方法，连接信号与槽函数

    def init_ui(self):
        self.setWindowTitle("游戏助手1.7.1")  # 设置窗口标题

        mainWidget = QWidget() #创建一个主窗口控件
        self.setCentralWidget(mainWidget) #将主窗口控件设置为窗口的中央控件
        mainWidget_layout = QHBoxLayout(mainWidget) #创建一个水平布局,并将其设置为主窗口控件的布局

        centralWidget = QTabWidget() #创建一个标签页控件
        # centralWidget_layout = QHBoxLayout(centralWidget) #创建一个水平布局,并将其设置为标签页控件的布局
        mainWidget_layout.addWidget(centralWidget) #将标签页控件添加到主窗口控件的布局中

        baseTab = QWidget() #创建基础设置标签页
        baseTab_layout = QGridLayout(baseTab) #创建一个网格布局,并将其设置为标签页控件的布局

        self.pauseButton = QPushButton("暂停/运行", baseTab) #创建暂停/运行按钮
        self.pauseButton.clicked.connect(self.switch_status) #绑定按钮的点击事件
        baseTab_layout.addWidget(self.pauseButton, 0, 0, 1, 2) #将按钮添加到网格布局中

        self.exitButton = QPushButton("退出", baseTab) #创建退出按钮
        self.exitButton.clicked.connect(self.exit_app) #绑定按钮的点击事件
        baseTab_layout.addWidget(self.exitButton, 1, 0, 1, 2) #将按钮添加到网格布局中

        baseTab_layout.addWidget(QLabel('鼠标移动次数：'), 2, 0) #将标签添加到网格布局中
        self.move_count_label = QLabel('0') #创建对应次数显示标签,并设置初始值为0
        baseTab_layout.addWidget(self.move_count_label, 2, 1) #将标签添加到网格布局中

        baseTab_layout.addWidget(QLabel('鼠标移动距离：'), 3, 0) #将标签添加到网格布局中
        self.move_distance_label = QLabel('0') #创建对应距离显示标签
        baseTab_layout.addWidget(self.move_distance_label, 3, 1) #将标签添加到网格布局中

        baseTab_layout.addWidget(QLabel('鼠标移动时间：'), 4, 0) #将标签添加到网格布局中
        self.move_time_label = QLabel('0') #创建对应时间显示标签
        baseTab_layout.addWidget(self.move_time_label, 4, 1) #将标签添加到网格布局中

        baseTab_layout.addWidget(QLabel('语音播报内容：'), 5, 0) #将标签添加到网格布局中
        self.voice_broadcast_label = QLabel(' ') #创建对应内容显示标签
        baseTab_layout.addWidget(self.voice_broadcast_label, 5, 1) #将标签添加到网格布局中

        baseTab_layout.addWidget(QLabel('当前状态：'), 6, 0) #将标签页添加到网格布局中
        self.current_state_label = QLabel('暂停') #创建对应状态显示标签
        baseTab_layout.addWidget(self.current_state_label, 6, 1) #将标签添加到网格布局中

        self.resetButton = QPushButton("重启程序", baseTab) #创建重启程序按钮
        self.resetButton.clicked.connect(self.restart_app) #绑定按钮的点击事件
        baseTab_layout.addWidget(self.resetButton, 7, 0, 1, 2) #将按钮添加到网格布局中

        centralWidget.addTab(baseTab, "基础设置") #将标签页添加到标签页控件中

        paramsTab = QWidget() #创建参数设置标签页
        paramsTab_layout = QGridLayout() #创建一个网格布局
        paramsTab_QVBoxLayout = QVBoxLayout(paramsTab) #创建一个垂直布局,并将其设置为标签页控件的布局

        paramsTab_layout.addWidget(QLabel('参数方案：'), 0, 0, 1, 1) #将标签添加到网格布局中
        self.profile_combo = QComboBox() #创建参数方案下拉框
        self.profile_combo.currentTextChanged.connect(self.refresh_sub_plan_list) # 父方案下拉框的内容改变时，刷新子方案列表
        #self.profile_combo.textActivated.connect(self.refresh_parent_plan_list) # 手动改变父方案下拉框的内容时，刷新子方案列表
        '''currentIndexChanged,选中索引变化,由用户或程序触发； currentTextChanged，显示文本变化，由用户或程序触发
        activated，用户改变选择项目，传递索引(int)，仅用户触发； textActivated，用户改变选择项目，传递文本(str)，仅用户触发'''
        paramsTab_layout.addWidget(self.profile_combo, 1, 0, 1, 2) #将下拉框添加到网格布局中

        paramsTab_layout.addWidget(QLabel('子方案：'), 0, 2, 1, 1) #将标签添加到网格布局中
        self.sub_profile_combo = QComboBox() #创建子方案下拉框
        self.sub_profile_combo.currentTextChanged.connect(self.load_profile) # 子方案下拉框的内容改变时，加载对应的子方案参数
        #self.sub_profile_combo.textActivated.connect(self.load_profile) # 手动改变子方案下拉框的内容时，加载对应的子方案参数
        paramsTab_layout.addWidget(self.sub_profile_combo, 1, 2, 1, 1) #将下拉框添加到网格布局中

        self.load_btn = QPushButton("加载方案", paramsTab) #创建加载方案按钮
        self.load_btn.clicked.connect(self.load_profile) # 点击 加载方案 按钮时，加载对应的子方案参数
        paramsTab_layout.addWidget(self.load_btn, 2, 0, 1, 1) #将按钮添加到网格布局中

        self.save_btn = QPushButton("保存方案", paramsTab) #创建保存方案按钮
        self.save_btn.clicked.connect(self.save_sub_profile) #绑定按钮的点击事件
        paramsTab_layout.addWidget(self.save_btn, 2, 1, 1, 1) #将按钮添加到网格布局中

        self.delete_btn = QPushButton("删除方案", paramsTab) #创建删除方案按钮
        self.delete_btn.clicked.connect(self.delete_sub_profile) #绑定按钮的点击事件
        paramsTab_layout.addWidget(self.delete_btn, 2, 2, 1, 1) #将按钮添加到网格布局中

        self.reload_btn = QPushButton("重新载入方案", paramsTab) #创建重载方案按钮
        # self.reload_btn.clicked.connect(lambda: print("重新载入方案")) #绑定按钮的点击事件（现采用文本框焦点状态，调用解析方案参数函数，点击此按钮可使文本框失焦，效果相同，故无需绑定）
        paramsTab_layout.addWidget(self.reload_btn, 3, 0, 1, 2) #将按钮添加到网格布局中

        self.update_btn = QPushButton("更新方案参数", paramsTab) #创建更新方案按钮
        self.update_btn.clicked.connect(self.update_sub_profile) #绑定按钮的点击事件
        paramsTab_layout.addWidget(self.update_btn, 3, 2, 1, 1) #将按钮添加到网格布局中

        paramsTab_QVBoxLayout.addLayout(paramsTab_layout) #将网格布局添加到垂直布局中

        paramsTab_QVBoxLayout.addWidget(QLabel('方案信息：')) #将标签添加到垂直布局中
        self.plan_information = QTextEdit() #创建方案信息文本框
        self.plan_information.focusOutEvent = self.plan_information_focus_out #绑定文本框的焦点离开事件,当文本框失去焦点时，调用plan_information_focus_out函数
        paramsTab_QVBoxLayout.addWidget(self.plan_information) #将文本框添加到垂直布局中

        centralWidget.addTab(paramsTab, "参数设置") #将标签页添加到标签页控件中

        otherTab = QWidget() #创建其他设置标签页
        otherTab_layout = QGridLayout(otherTab) #创建一个网格布局,并将其设置为标签页控件的布局

        self.voiceCheckBox = QCheckBox("状态切换语音", otherTab) #创建状态切换语音复选框
        otherTab_layout.addWidget(self.voiceCheckBox, 0, 0) #将复选框添加到网格布局中

        self.switch_voice_CheckBox = QCheckBox("方案切换语音", otherTab) #创建方案切换语音复选框
        otherTab_layout.addWidget(self.switch_voice_CheckBox, 1, 0) #将复选框添加到网格布局中

        self.adjust_voice_CheckBox = QCheckBox("方案调整语音", otherTab) #创建方案调整语音复选框
        otherTab_layout.addWidget(self.adjust_voice_CheckBox, 2, 0) #将复选框添加到网格布局中

        self.sub_switch_voice_CheckBox = QCheckBox("子方案切换语音", otherTab) #创建子方案切换语音复选框
        otherTab_layout.addWidget(self.sub_switch_voice_CheckBox, 3, 0) #将复选框添加到网格布局中

        self.auto_start_ocr_CheckBox = QCheckBox("自动启动OCR", otherTab) #创建自动启动OCR复选框
        self.auto_start_ocr_CheckBox.stateChanged.connect(lambda: safe_submit(self.management_recognizer)) #绑定复选框的状态改变事件，使用线程池安全提交; 确保在独立线程中管理识别器，避免阻塞主线程;使用lambda表达式避免立即调用函数
        otherTab_layout.addWidget(self.auto_start_ocr_CheckBox, 4, 0) #将复选框添加到网格布局中

        self.fire_flash_Scope_CheckBox = QCheckBox("开火闪镜", otherTab) #创建开火闪镜复选框
        otherTab_layout.addWidget(self.fire_flash_Scope_CheckBox, 5, 0) #将复选框添加到网格布局中

        self.show_program_info_CheckBox = QCheckBox("显示程序信息", otherTab) #创建显示程序信息复选框
        otherTab_layout.addWidget(self.show_program_info_CheckBox, 0, 3) #将复选框添加到网格布局中

        self.Show_basic_information_CheckBox = QCheckBox("显示基础信息", otherTab) #创建显示基础信息复选框
        otherTab_layout.addWidget(self.Show_basic_information_CheckBox, 1, 3) #将复选框添加到网格布局中

        self.Show_advanced_information_CheckBox = QCheckBox("显示详细信息", otherTab) #创建显示高级信息复选框
        otherTab_layout.addWidget(self.Show_advanced_information_CheckBox, 2, 3) #将复选框添加到网格布局中

        self.always_on_top_CheckBox = QCheckBox("始终置顶", otherTab) #创建始终置顶复选框
        otherTab_layout.addWidget(self.always_on_top_CheckBox, 3, 3) #将复选框添加到网格布局中

        self.auto_switch_profile_CheckBox = QCheckBox("自动切换方案", otherTab) #创建自动切换方案复选框
        otherTab_layout.addWidget(self.auto_switch_profile_CheckBox, 4, 3) #将复选框添加到网格布局中

        self.file_squat_CheckBox = QCheckBox("开火蹲起", otherTab) #创建开火蹲起复选框
        otherTab_layout.addWidget(self.file_squat_CheckBox, 5, 3) #将复选框添加到网格布局中

        otherTab_layout.addWidget(QLabel('延时拖动(毫秒)：'), 6, 0) #将标签添加到网格布局中
        self.drag_delay_min_input = QLineEdit('30') #创建对应延时显示框
        self.drag_delay_min_input.focusOutEvent = self.DragDelay_LineEdit_focusout #绑定文本框的焦点离开事件,当文本框失去焦点时，调用DragDelay_LineEdit_focusout函数
        otherTab_layout.addWidget(self.drag_delay_min_input, 6, 1) #将标签添加到网格布局中
        self.drag_delay_max_input = QLineEdit('80') #创建对应延时显示框
        self.drag_delay_max_input.focusOutEvent = self.DragDelay_LineEdit_focusout #绑定文本框的焦点离开事件,当文本框失去焦点时，调用DragDelay_LineEdit_focusout函数
        otherTab_layout.addWidget(self.drag_delay_max_input, 6, 3) #将标签添加到网格布局中

        centralWidget.addTab(otherTab, "其他设置") #将标签页添加到标签页控件中


        ocrTab = QWidget() #创建图像识别标签页
        ocrTab_layout = QGridLayout() #创建一个网格布局
        ocrTab_QVBoxLayout = QVBoxLayout(ocrTab) #创建一个垂直布局,并将其设置为标签页控件的布局

        self.manual_positioning_btn = QPushButton("手动定位") #创建手动定位按钮
        self.manual_positioning_btn.clicked.connect(lambda: print("手动定位")) #绑定按钮的点击事件
        ocrTab_layout.addWidget(self.manual_positioning_btn, 0, 0) #将按钮添加到网格布局中

        self.exit_positioning_btn = QPushButton("退出定位") #创建退出定位按钮
        self.exit_positioning_btn.clicked.connect(lambda: print("退出定位")) #绑定按钮的点击事件
        ocrTab_layout.addWidget(self.exit_positioning_btn, 0, 1) #将按钮添加到网格布局中

        self.restart_ocr_btn = QPushButton("重启OCR") #创建重启OCR按钮
        self.restart_ocr_btn.clicked.connect(lambda: safe_submit(self.start_recognizer)) #绑定按钮的点击事件,使用线程池安全提交;
        ocrTab_layout.addWidget(self.restart_ocr_btn, 1, 0) #将按钮添加到网格布局中

        self.exit_ocr_btn = QPushButton("退出OCR") #创建退出OCR按钮
        self.exit_ocr_btn.clicked.connect(lambda: safe_submit(self.stop_recognizer)) #绑定按钮的点击事件,使用线程池安全提交;
        ocrTab_layout.addWidget(self.exit_ocr_btn, 1, 1) #将按钮添加到网格布局中

        self.ocr_regions_parameter_plan_combo = QComboBox() # 创建 OCR识别区域参数方案 下拉框
        self.ocr_regions_parameter_plan_combo.currentTextChanged.connect(self.load_ocr_profile) # 绑定下拉框的文本改变事件,当文本改变时，调用load_ocr_profile函数加载OCR识别区域参数方案
        ocrTab_layout.addWidget(self.ocr_regions_parameter_plan_combo, 2, 0,) #将下拉框添加到网格布局中

        self.update_ocr_plan_btn = QPushButton("更新ocr方案参数") #创建更新OCR识别区域参数方案按钮
        self.update_ocr_plan_btn.clicked.connect(self.update_ocr_profile) #绑定按钮的点击事件
        ocrTab_layout.addWidget(self.update_ocr_plan_btn, 2, 1) #将按钮添加到网格布局中

        self.save_ocr_regions_parameter_btn = QPushButton("保存方案") #创建保存OCR识别区域参数按钮
        self.save_ocr_regions_parameter_btn.clicked.connect(self.save_ocr_profile) #绑定按钮的点击事件
        ocrTab_layout.addWidget(self.save_ocr_regions_parameter_btn, 3, 0) #将按钮添加到网格布局中

        self.delete_ocr_regions_parameter_btn = QPushButton("删除方案") #创建删除OCR识别区域参数按钮
        self.delete_ocr_regions_parameter_btn.clicked.connect(self.delete_ocr_profile) #绑定按钮的点击事件
        ocrTab_layout.addWidget(self.delete_ocr_regions_parameter_btn, 3, 1) #将按钮添加到网格布局中

        ocrTab_QVBoxLayout.addLayout(ocrTab_layout) #将网格布局添加到垂直布局中

        ocr_tabWidget = QTabWidget() # 创建一个标签页控件

        ocr_coordinates_tab = QWidget() # 创建识别坐标标签页
        ocr_coordinates_tab_layout = QHBoxLayout(ocr_coordinates_tab) # 创建一个水平布局,并将其设置为标签页控件的布局

        self.ocr_coordinates_te = QTextEdit() # 创建识别坐标显示文本框
        self.ocr_coordinates_te.focusOutEvent = self.ocr_coordinates_te_focus_out  # 绑定文本框的焦点离开事件,当文本框失去焦点时，调用ocr_coordinates_te_focus_out函数
        ocr_coordinates_tab_layout.addWidget(self.ocr_coordinates_te) # 将文本框添加到水平布局中

        ocr_tabWidget.addTab(ocr_coordinates_tab, "识别坐标") # 将标签页添加到标签页控件中

        ocr_result = QWidget() # 创建识别结果标签页
        ocr_result_layout = QHBoxLayout(ocr_result) # 创建一个水平布局,并将其设置为标签页控件的布局

        self.ocr_result_te = QTextEdit() # 创建识别结果显示文本框
        self.ocr_result_te.setReadOnly(True) # 设置为只读模式,用户不能编辑其中的内容
        ocr_result_layout.addWidget(self.ocr_result_te) # 将文本框添加到水平布局中

        ocr_tabWidget.addTab(ocr_result, "识别结果") # 创建识别结果标签页

        ocrTab_QVBoxLayout.addWidget(ocr_tabWidget) # 将标签页控件添加到垂直布局中

        centralWidget.addTab(ocrTab, "图像识别") #将标签页添加到标签页控件中

        testTab = QWidget() #创建测试标签页
        testTab_layout = QVBoxLayout(testTab) #创建一个垂直布局,并将其设置为标签页控件的布局

        testTab_grid_layout = QGridLayout() # 创建一个网格布局

        self.test_mode_checkbox = QCheckBox('测试模式') # 创建测试模式复选框
        self.test_mode_checkbox.stateChanged.connect(self.toggle_test_mode) # 绑定复选框的状态改变事件,当复选框状态改变时，调用toggle_test_mode函数
        testTab_grid_layout.addWidget(self.test_mode_checkbox, 0, 0) # 将复选框添加到网格布局中

        self.auto_adjust_parameter_checkbox = QCheckBox('自动调整参数') # 创建自动调整参数复选框
        self.auto_adjust_parameter_checkbox.stateChanged.connect(lambda: print('自动调整参数')) # 绑定复选框的状态改变事件,当复选框状态改变时，调用toggle_auto_adjust_parameter函数
        testTab_grid_layout.addWidget(self.auto_adjust_parameter_checkbox, 0, 1) # 将复选框添加到网格布局中

        self.adjust_parameter_btn = QPushButton("调整参数") # 创建调整参数按钮
        self.adjust_parameter_btn.clicked.connect(self.adjust_parameter_information) # 绑定按钮的点击事件,当按钮点击时，调用adjust_parameter_information函数
        testTab_grid_layout.addWidget(self.adjust_parameter_btn, 1, 0, 1, 2) # 将按钮添加到网格布局中

        # 将网格布局添加到垂直布局中
        testTab_layout.addLayout(testTab_grid_layout)

        testTab_layout.addWidget(QLabel('测试信息'))# 添加一个测试信息文字标签
        self.test_info_te = QTextEdit() # 创建测试信息显示文本框
        self.test_info_te.setReadOnly(True) # 设置为只读模式,用户不能编辑其中的内容
        testTab_layout.addWidget(self.test_info_te) # 将文本框添加到垂直布局中

        centralWidget.addTab(testTab, "测试窗口") #将标签页添加到标签页控件中

        self.statusber = QStatusBar() #创建状态栏
        self.statusber.showMessage("就绪") #设置状态栏显示的信息
        self.setStatusBar(self.statusber) #将状态栏添加到窗口中

    def connect_signal_slot_function(self):
        '''连接信号与槽函数'''
        self.exit_requested.connect(self.exit_app) # 连接退出请求信号到退出程序函数
        self.restart_requested.connect(self.restart_app) # 连接重启请求信号到重启程序函数
        self.switch_status_requested.connect(self.switch_status) # 连接切换状态请求信号到切换程序状态函数
        self.switch_plan_requested.connect(self.key_switch_parent_plan) # 连接切换父方案请求信号到切换父方案函数
        self.switch_sub_plan_requested.connect(self.key_switch_sub_plan) # 连接切换子方案请求信号到切换子方案函数
        self.number_switch_sub_plan_requested.connect(self.key_number_switch_sub_plan) # 连接数字键切换子方案请求信号到指定切换子方案函数
        self.run_the_recognizer_requested.connect(lambda: safe_submit(self.run_the_recognizer)) # 连接运行识别器请求信号到运行识别器函数，使用线程池安全提交; 确保在独立线程中运行识别器，避免阻塞主线程;使用lambda表达式避免立即调用函数
        self.recognizer_switch_plan_requested.connect(self.recognizer_switch_plan) # 连接使用识别结果切换父方案和子方案请求信号到切换父方案函数
        self.ocr_results_update_requested.connect(self.display_recognition_results) # 连接识别结果文本框更新信号到更新识别结果函数
        self.test_info_te_update_requested.connect(self.set_test_info_te) # 连接测试信息文本框更新信号到更新测试信息函数

    def plan_information_focus_out(self, event):
        """自定义方案信息文本框焦点离开事件处理"""
        # 调用解析函数
        self.parse_plan_parameters() # 方案信息文本框焦点离开时，调用parse_plan_parameters函数，解析方案参数
        # 调用父类方法确保正常行为
        super(QTextEdit, self.plan_information).focusOutEvent(event)

    def DragDelay_LineEdit_focusout(self, event):
        """自定义延时拖动文本框焦点离开事件处理"""
        # 调用解析函数
        set_drag_delay(int(self.drag_delay_min_input.text()), int(self.drag_delay_max_input.text())) # 在文本框失去焦点后，调用set_drag_delay函数，传递参数
        # 调用父类方法确保正常行为
        super(QLineEdit, self.drag_delay_min_input).focusOutEvent(event)
        super(QLineEdit, self.drag_delay_max_input).focusOutEvent(event)

    def has_input_focus(self):
        """检查是否有输入控件处于焦点"""
        focused_widget = QApplication.focusWidget()  # 获取当前获得焦点的控件
        if focused_widget is not None: # 如果有控件处于焦点
            # 检查是否是输入相关的控件，包括QLineEdit, QTextEdit, QComboBox
            return isinstance(focused_widget, (QLineEdit, QTextEdit, QComboBox))
        return False

    def switch_status(self):
        '''切换运行状态'''
        if self.has_input_focus(): # 在切换运行状态时，如果有输入控件处于焦点
            return # 不切换状态

        global is_status # 声明使用全局变量is_status
        is_status = not is_status # 切换程序运行/暂停状态
        ML_set_status(is_status) # 调用ML_set_status函数，向MouseListener传递程序运行/暂停状态参数
        KBL_set_status(is_status) # 调用KBL_set_status函数，向KeyBoardListener传递程序运行/暂停状态参数

        if is_status: # 如果程序处于运行状态
            self.pauseButton.setText("暂停") # 将按钮文本设置为“暂停”
            self.current_state_label.setText("运行") # 将当前状态标签文本设置为“运行”

        else: # 如果程序处于暂停状态
            self.pauseButton.setText("运行") # 将按钮文本设置为“运行”
            self.current_state_label.setText("暂停") # 将当前状态标签文本设置为“暂停”

        parent_profile = self.profile_combo.currentText()  # 获取当前选中的父方案名称
        sub_profile = self.sub_profile_combo.currentText()  # 获取当前选中的子方案名称
        # 如果程序处于运行状态，状态栏显示“正在运行 - 父方案/子方案”，如果处于暂停状态，状态栏显示“已暂停 - 父方案/子方案”
        self.statusber.showMessage(
            f'正在运行 - {parent_profile}/{sub_profile}' if is_status else f'已暂停 - {parent_profile}/{sub_profile}')  # 设置状态栏显示的信息
        if self.voiceCheckBox.isChecked():  # 如果状态切换语音复选框被选中
            add_voice_queue(f'{self.current_state_label.text()}')  # 语音播报切换后的状态，ui.current_state_label.text()是获取当前状态标签的文本内容

    def exit_app(self):
        '''退出程序'''
        self.stop_recognizer() # 退出程序前，停止识别器
        self.save_config() # 保存配置文件
        self.close() # 关闭窗口
        QApplication.instance().quit() # 退出应用程序

    def restart_app(self):
        '''重启程序'''
        import os
        import sys
        import subprocess

        self.stop_recognizer() # 重启程序前，停止识别器
        self.save_config() # 保存配置文件
        self.close() # 关闭窗口
        QApplication.instance().quit() # 退出应用程序

        subprocess.Popen(
            [sys.executable, os.path.join(os.path.dirname(__file__), 'main.py')], # 启动新的Python进程，执行当前脚本
            shell = False, # 不使用shell执行命令，即不调用cmd.exe
            #creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS, # CREATE_NO_WINDOW:不显示窗口; DETACHED_PROCESS:分离进程，使其成为后台进程
        )

    def save_config(self):
        '''保存配置'''
        config = {
            '状态切换语音': self.voiceCheckBox.isChecked(),
            '方案切换语音': self.switch_voice_CheckBox.isChecked(),
            '方案调整语音': self.adjust_voice_CheckBox.isChecked(),
            '子方案切换语音': self.sub_switch_voice_CheckBox.isChecked(),
            '自动启动OCR': self.auto_start_ocr_CheckBox.isChecked(),
            '开火闪镜': self.fire_flash_Scope_CheckBox.isChecked(),
            '显示程序信息': self.show_program_info_CheckBox.isChecked(),
            '显示基础信息': self.Show_basic_information_CheckBox.isChecked(),
            '显示详细信息': self.Show_advanced_information_CheckBox.isChecked(),
            '始终置顶': self.always_on_top_CheckBox.isChecked(),
            '自动切换方案': self.auto_switch_profile_CheckBox.isChecked(),
            '开火蹲起': self.file_squat_CheckBox.isChecked(),
            '延时拖动(毫秒)': {
                '最小值': self.drag_delay_min_input.text(),
                '最大值': self.drag_delay_max_input.text(),
            },
            '父方案': self.profile_combo.currentText(),
            '子方案': self.sub_profile_combo.currentText(),
            'OCR方案': self.ocr_regions_parameter_plan_combo.currentText(),
        }

        try:
            config_path = Path('config.json')  # 配置文件路径，pathlib.Path类创建文件路径对象，配置文件保存为当前目录下的config.json文件
            with open(config_path, 'w', encoding='utf-8') as f:  # with管理文件资源，自动关闭文件，以写入模式打开，覆盖原有内容，指定编码为UTF-8，确保中文字符正确保存
                json.dump(config, f, indent=4, ensure_ascii=False)
                # json.dump()将Python字典序列化为JSON字符串并写入文件，indent=4参数指定缩进为4个空格，确保JSON文件的可读性，ensure_ascii=False参数指定不使用ASCII编码，保留中文字符
            console_logger.info("配置文件保存成功")
            return True
        except Exception as e:
            both_logger.debug(f'保存配置文件失败: {str(e)}')
            return False

    def load_config(self):
        '''加载配置文件'''
        try:
            config_path = Path('config.json')
            if config_path.exists(): # exists()方法检查配置文件是否存在，如果文件不存在，函数会直接返回，使用UI控件的默认状态
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)  # 读取配置文件内容，json.load()将JSON字符串反序列化为Python字典

                # 恢复复选框状态
                self.voiceCheckBox.setChecked(config.get('状态切换语音', True))
                # 使用config.get()方法获取配置值，第二个参数是默认值
                # 使用setChecked()方法恢复复选框状态，如果配置中缺少某个选项，使用默认值
                self.switch_voice_CheckBox.setChecked(config.get('方案切换语音', True))
                self.adjust_voice_CheckBox.setChecked(config.get('方案调整语音', True))
                self.sub_switch_voice_CheckBox.setChecked(config.get('子方案切换语音', True))
                self.auto_start_ocr_CheckBox.setChecked(config.get('自动启动OCR', False))
                self.fire_flash_Scope_CheckBox.setChecked(config.get('开火闪镜', False))
                self.show_program_info_CheckBox.setChecked(config.get('显示程序信息', True))
                self.Show_basic_information_CheckBox.setChecked(config.get('显示基础信息', False))
                self.Show_advanced_information_CheckBox.setChecked(config.get('显示详细信息', False))
                self.always_on_top_CheckBox.setChecked(config.get('始终置顶', True))
                self.auto_switch_profile_CheckBox.setChecked(config.get('自动切换方案', True))
                self.file_squat_CheckBox.setChecked(config.get('开火蹲起', False))

                # 恢复延时拖动参数
                delay_config = config.get('延时拖动(毫秒)', {}) # 先获取嵌套的延时配置字典
                self.drag_delay_min_input.setText(str(delay_config.get('最小值', '30'))) # 使用setText()方法恢复输入框文本
                self.drag_delay_max_input.setText(str(delay_config.get('最大值', '80'))) # str()将数值转换为字符串，确保文本框显示正确的数值

                # 恢复方案选择
                self.profile_combo.setCurrentText(config.get('父方案', '')) # 使用setCurrentText()方法恢复下拉框选中项，setCurrentText()在文本不存在时会静默失败，不会显示设置的文本
                self.sub_profile_combo.setCurrentText(config.get('子方案', '')) # 如果配置中没有对应的方案，使用空字符串
                self.ocr_regions_parameter_plan_combo.setCurrentText(config.get('OCR方案', '')) # 如果配置中没有对应的OCR方案，使用空字符串

                console_logger.info("配置文件加载成功")

                if is_status:  # 如果程序处于运行状态
                    self.pauseButton.setText("暂停")  # 将按钮文本设置为“暂停”
                    self.current_state_label.setText("运行")  # 将当前状态标签文本设置为“运行”
                else:  # 如果程序处于暂停状态
                    self.pauseButton.setText("运行")  # 将按钮文本设置为“运行”
                    self.current_state_label.setText("暂停")  # 将当前状态标签文本设置为“暂停”

                parent_profile = self.profile_combo.currentText()  # 获取当前选中的父方案名称
                sub_profile = self.sub_profile_combo.currentText()  # 获取当前选中的子方案名称
                # 如果程序处于运行状态，状态栏显示“正在运行 - 父方案/子方案”，如果处于暂停状态，状态栏显示“已暂停 - 父方案/子方案”
                self.statusber.showMessage(
                    f'正在运行 - {parent_profile}/{sub_profile}' if is_status else f'已暂停 - {parent_profile}/{sub_profile}')  # 设置状态栏显示的信息

                # self.parse_plan_parameters() # 在程序初始化-加载配置文件后，调用此函数解析方案参数
                set_drag_delay(int(self.drag_delay_min_input.text()), int(self.drag_delay_max_input.text())) # 在程序初始化-加载配置文件后，调用此函数传递拖动延迟参数

        except Exception as e:
            both_logger.debug(f'加载配置文件失败: {str(e)}')

    class ProfileSaveDialog(QDialog):
        '''继承自QDialog：用于创建模态对话框;
        内嵌类：定义在ControlUI类内部，可以访问父类的属性和方法;
        模态对话框：用户必须完成对话框操作才能继续使用主窗口'''

        def __init__(self, parent=None):
            '''parent参数：接收父窗口引用，确保对话框显示在父窗口中央'''
            super().__init__(parent)
            self.setWindowTitle('保存方案')  # 设置对话框标题为'保存方案'
            layout = QVBoxLayout()  # 创建垂直布局管理器

            self.parent_label = QLabel('父方案名称:')
            self.parent_input = QLineEdit()
            layout.addWidget(self.parent_label)
            layout.addWidget(self.parent_input)

            self.child_label = QLabel('子方案名称:')
            self.child_input = QLineEdit()
            layout.addWidget(self.child_label)
            layout.addWidget(self.child_input)

            self.ok_btn = QPushButton('确定')
            self.ok_btn.clicked.connect(self.accept)  # 信号连接：点击按钮触发accept()方法，关闭对话框并返回QDialog.Accepted
            layout.addWidget(self.ok_btn)

            self.setLayout(layout)

        def get_names(self):  # 返回元组形式的(父方案名, 子方案名)
            return self.parent_input.text(), self.child_input.text()

    def save_sub_profile(self):
        """保存方案参数"""
        global profiles_json # 保存方案时，使用全局变量

        dialog = self.ProfileSaveDialog(self)  # 创建对话框实例
        if dialog.exec_() == QDialog.Accepted:  # 调用exec_()显示对话框并等待用户操作
            parent_name, child_name = dialog.get_names()  # 获取用户输入的方案名称
            if not parent_name or not child_name:  # 检查输入是否为空
                QMessageBox.about(self, '错误', '父方案和子方案名称均不能为空！', QMessageBox.Ok)
                return

            profile_data= self.plan_information.toPlainText() # toPlainText()方法获取文本框的纯文本内容作为方案参数
            if not profile_data:
                QMessageBox.about(self, '错误', '方案参数不能为空！', QMessageBox.Ok)
                return
            try:
                profile_data = json.loads(profile_data)  # 解析JSON字符串为字典；json.loads()将JSON字符串反序列化为Python字典
                # 检查方案是否存在，不存在则创建
                if parent_name not in profiles_json:
                    profiles_json[parent_name] = {}
                if child_name not in profiles_json[parent_name]:
                    profiles_json[parent_name][child_name] = {}
                # 将方案参数添加到方案文件里
                profiles_json[parent_name][child_name] = profile_data  # 将方案参数添加到方案文件里

            except json.JSONDecodeError as e:
                QMessageBox.about(self, '错误', f'方案参数格式错误:{str(e)}', QMessageBox.Ok)
                both_logger.error(f'方案参数格式错误:{str(e)}')
                return

            # profile_dir = Path('profiles') / parent_name  # 父方案目录路径
            # profile_dir.mkdir(parents=True, exist_ok=True)  # 创建父方案目录，parents=True确保父目录也被创建，exist_ok=True如果目录已存在则不抛出异常
            profile_path = Path('profiles.json')  # 子方案文件路径

            try:
                with open(profile_path, 'w', encoding='utf-8') as f:
                    json.dump(profiles_json, f, ensure_ascii=False, indent=4)  # 写入方案参数到文件
                QMessageBox.about(self, '成功', f'方案{parent_name}-{child_name}已保存到 {profile_path}')
                self.refresh_parent_plan_list()  # 保存方案后，刷新父方案列表

            except Exception as e:
                QMessageBox.about(self, '错误', f'保存方案参数失败: {str(e)}')
                both_logger.error(f'保存方案参数失败: {str(e)}')

    def read_profiles_json(self):
        """读取参数方案文件"""
        global profiles_json # 声明使用全局变量

        profile_path = Path('profiles.json')
        if not profile_path.exists(): # 如果文件不存在，弹出提示框并返回，不执行任何操作
            console_logger.info(f'未找到{profile_path}')
            return
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profiles_json = json.load(f)  # 读取JSON文件内容，将其转换为Python对象（通常是字典或列表）并赋值给profiles_json
        except Exception as e:
            both_logger.error(f'读取参数方案文件失败: {str(e)}')

    def save_profiles_json(self):
        """保存方案参数文件"""
        global profiles_json

        profile_path = Path('profiles.json')
        try:
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profiles_json, f, ensure_ascii=False, indent=4)  # 写入方案参数到文件
            self.refresh_parent_plan_list()  # 保存方案参数文件后，刷新父方案列表

        except Exception as e:
            QMessageBox.about(self, '错误', f'保存方案参数文件失败: {str(e)}')
            both_logger.error(f'保存方案参数文件失败: {str(e)}')

    def refresh_parent_plan_list(self):
        """刷新父方案列表"""
        global profiles_json # 声明使用全局变量

        parent_name = self.profile_combo.currentText()  # 获取当前选中的父方案名称
        '''combo.count() - 返回下拉列表中项目的总数(整数（int)),用于判断和遍历
         combo.itemText(index) - 根据索引获取下拉列表中对应项目的文本内容; index：整数，项目的索引（从0开始）;返回字符串（str），对应索引的文本内容，用于获取具体内容
         combo.findText(text) - 在下拉列表中查找指定文本，返回对应的索引; text：字符串，要查找的文本;返回整数（int），找到的索引；如果没找到返回-1，用于查找和验证存在性'''
        if profiles_json == None: # 如果profiles_json为空
            self.read_profiles_json()  # 读取参数方案文件

        if profiles_json: # 如果profiles_json不为空
            # profile_dir = Path('profiles')  # 父方案目录路径
            # profile_dir.mkdir(parents=True, exist_ok=True) # .mkdir(parents=True, exist_ok=True)创建父目录，parents=True确保父目录也被创建，exist_ok=True如果目录已存在则不抛出异常
            # parent_plans = [d.name for d in profile_dir.iterdir() if d.is_dir()]  # 列出所有子目录，即父方案名称
            parent_plans = profiles_json.keys()  # 从JSON文件中获取所有父方案名称
            self.profile_combo.clear()  # 清空下拉框
            self.profile_combo.addItems(parent_plans)  # 添加父方案名称到下拉框，如果列表不为空：自动显示第一个项目，如果列表为空：显示空白
            if parent_name and parent_name in parent_plans:  # 如果parent_name不是空字符串且存在于parent_plans列表中，则设置下拉框的当前文本为parent_name
                self.profile_combo.setCurrentText(parent_name)
            console_logger.info(f'父方案列表已刷新')

    def refresh_sub_plan_list(self):
        """刷新子方案列表"""
        global profiles_json # 声明使用全局变量

        parent_name = self.profile_combo.currentText()  # 获取当前选中的父方案名称
        if not parent_name: # 如果parent_name为空字符串，则直接返回，不执行任何操作
            return

        if profiles_json: # 如果profiles_json不为空
            # profile_dir = Path('profiles') / parent_name  # 父方案目录路径
            # if not profile_dir.exists():  # 如果目录不存在，直接返回
            #     return
            # sub_plans = [f.stem for f in profile_dir.iterdir() if f.is_file() and f.suffix == '.json']  # 列出所有子方案文件，即子方案名称
            sub_plans = profiles_json[parent_name].keys()  # 从JSON文件指定键中获取所有子方案名称
            self.sub_profile_combo.clear()  # 清空下拉框
            self.sub_profile_combo.addItems(sub_plans)  # 添加子方案名称到下拉框
            console_logger.info(f'子方案列表已刷新')

    def load_profile(self):
        """加载方案参数"""
        global profiles_json, plan_parameters # 声明使用全局变量

        parent_name = self.profile_combo.currentText()  # 获取当前选中的父方案名称
        sub_name = self.sub_profile_combo.currentText()  # 获取当前选中的子方案名称

        if not parent_name or not sub_name: # 如果parent_name或sub_name为空字符串，则直接返回，不执行任何操作
            return

        # profile_path = Path('profiles') / parent_name / f'{sub_name}.json'  # 子方案文件路径
        # if not profile_path.exists(): # 如果文件不存在，弹出提示框并返回，不执行任何操作
        #     QMessageBox.about(self, '错误', f'方案{parent_name}-{sub_name}不存在')
        #     return

        try:
            profile_data = profiles_json[parent_name][sub_name]  # 从JSON文件指定键中获取子方案参数
            plan_parameters = profile_data  # 将方案参数赋值给plan_parameters变量，便于后续解析函数调用

            formatted_json = json.dumps(profile_data, ensure_ascii=False, indent=4) # 使用json.dumps将字典格式化为JSON字符串
            self.plan_information.setPlainText(formatted_json)  # 设置方案信息文本框的文本为格式化的JSON字符串
            console_logger.info(f'方案：{parent_name}-{sub_name} 已加载')

            self.parse_plan_parameters()  # 加载方案参数后，调用此函数解析方案参数
            # with open(profile_path, 'r', encoding='utf-8') as f:
            #     profile_data = json.load(f)  # 读取方案参数,json.load(f)用于从文件对象f中读取JSON数据并将其转换为Python对象（通常是字典或列表）
            #     # plan_parameters[parent_name + '-' + sub_name] = profile_data  # 设置键为父方案+子方案名称，值为方案参数字典
            #
            #     formatted_json = json.dumps(profile_data, ensure_ascii=False, indent=4) # 修复：使用json.dumps将字典格式化为JSON字符串
            #     self.plan_information.setPlainText(formatted_json)  # 设置方案信息文本框的文本为格式化的JSON字符串
            #     console_logger.info(f'方案：{parent_name}-{sub_name} 已加载')
            #     self.parse_plan_parameters()  # 加载方案参数后，调用此函数解析方案参数
        except Exception as e:
            QMessageBox.about(self, '错误', f'加载方案参数失败: {str(e)}')
            both_logger.error(f'加载方案参数失败: {str(e)}')

    def delete_sub_profile(self):
        """删除子方案"""
        global profiles_json

        parent_name = self.profile_combo.currentText()  # 获取当前选中的父方案名称
        sub_name = self.sub_profile_combo.currentText()  # 获取当前选中的子方案名称
        if not parent_name or not sub_name: # 如果parent_name或sub_name为空字符串，则直接返回，不执行任何操作
            return

        profile_path = Path('profiles.json')  # 子方案文件路径
        if not profile_path.exists(): # 如果文件不存在，弹出提示框并返回，不执行任何操作
            QMessageBox.about(self, '错误', f'方案{parent_name}-{sub_name}不存在')
            return
        reply = QMessageBox.question(self, '确认删除', f'确定删除 {parent_name}-{sub_name} 吗？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                # 删除子方案
                if parent_name in profiles_json and sub_name in profiles_json[parent_name]:
                    del profiles_json[parent_name][sub_name]
                    # 如果父方案下没有子方案了，可以选择删除父方案
                    if not profiles_json[parent_name]:
                        del profiles_json[parent_name]
                self.save_profiles_json() # 删除子方案后，保存参数方案文件
                QMessageBox.about(self, '成功', f'方案{parent_name}-{sub_name}已删除')

                self.refresh_sub_plan_list()  # 删除子方案后，刷新子方案列表
                console_logger.info(f'方案：{parent_name}-{sub_name} 已删除')
            except Exception as e:
                QMessageBox.about(self, '错误', f'删除方案参数失败: {str(e)}')
                both_logger.error(f'删除方案参数失败: {str(e)}')
        else:
            console_logger.info(f'取消删除操作')

    def update_sub_profile(self):
        """更新子方案"""
        global profiles_json

        parent_name = self.profile_combo.currentText()  # 获取当前选中的父方案名称
        sub_name = self.sub_profile_combo.currentText()  # 获取当前选中的子方案名称

        if not parent_name or not sub_name:
            return

        profile_path = Path('profiles.json')  # 子方案文件路径
        if not profile_path.exists():
            return

        profile_data = self.plan_information.toPlainText()  # 获取方案参数

        try:
            profile_data = json.loads(profile_data)  # 解析JSON字符串为字典；json.loads()将JSON字符串反序列化为Python字典
            profiles_json[parent_name][sub_name] = profile_data

            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profiles_json, f, ensure_ascii=False, indent=4)  # 写入方案参数到文件；json.dump()将Python字典序列化为JSON字符串并写入文件

            QMessageBox.about(self, '成功', f'方案 {parent_name}-{sub_name} 已更新')
            console_logger.info(f'方案：{parent_name}-{sub_name} 已更新')
            self.load_profile()  # 更新子方案，加载更新后的方案参数
        except json.JSONDecodeError as e:
            QMessageBox.about(self, '错误', f'方案参数格式错误: {str(e)}')
            both_logger.error(f'方案参数格式错误: {str(e)}')

    class ProfileParameters:
        """参数方案类"""

        def __init__(self):
            self.base_params = None  # 基础参数
            self.time_segments = []  # 时间段参数列表
            self.time_segments.sort(key=lambda
                x: x.start_time)  # 按开始时间排序；sort()是列表对象的一个方法，用于对列表中的元素进行排序，key参数用于指定排序的规则，lambda x: x.start_time表示按时间段的开始时间进行排序

    class TimeSegmentParameters:
        """时间段参数类"""

        def __init__(self, start_time, end_time, x_min, x_max, y_min, y_max, sleep_min, sleep_max):
            self.start_time = start_time
            self.end_time = end_time
            self.x_min = x_min
            self.x_max = x_max
            self.y_min = y_min
            self.y_max = y_max
            self.sleep_min = sleep_min
            self.sleep_max = sleep_max

    def parse_plan_parameters(self):
        '''解析方案参数'''
        global plan_parameters # 声明使用全局变量

        try:
            data = json.loads(self.plan_information.toPlainText())  # 从UI界面文本框中获取方案参数，并解析为字典
            # data = plan_parameters  # 从全局变量plan_parameters中获取方案参数
        except json.JSONDecodeError as e:
            QMessageBox.about(self, '错误', f'方案参数格式错误: {str(e)}')
            return

        base_params = data["参数信息"]["基础参数"] # 从字典中获取基础参数，查找键为"参数信息"的字典中的"基础参数"键对应的值
        profile = self.ProfileParameters()  # 创建一个ProfileParameters对象
        profile.base_params = self.parse_basic_parameter_range(base_params)  # 解析基础参数，并将结果赋值给profile对象的base_params属性

        for time_range, params in data["参数信息"].items(): # 遍历“参数信息”字典中的键值对
            if time_range == "基础参数":  # 如果键为"基础参数"，则跳过
                continue  # 跳过基础参数

            start_time, end_time = self.parse_time_range(time_range) # 解析时间段字符串，返回开始时间和结束时间
            parmas_obj = self.parse_parameter_range(params) # 创建时间段参数对象，将解析后的时间范围和参数范围作为参数传递给TimeSegmentParameters类的构造函数，**param_obj用于将字典中的键值对作为关键字参数传递给构造函数
            time_segment = self.TimeSegmentParameters(start_time, end_time, **parmas_obj) # 创建一个TimeSegment对象
            profile.time_segments.append(time_segment) # 将TimeSegment对象添加到profile对象的time_segments列表中，用于存储时间段参数对象

        console_logger.info(f'方案参数解析完成')
        set_profile(profile)  # 将解析后的方案参数对象传递给set_profile函数，用于设置全局变量profile

    def parse_basic_parameter_range(self, params):
        """解析基础参数范围字符串"""
        x_range = params["x轴偏移"].split('--')  # 以'--'为分隔符，将字符串分割成两个部分，以列表形式赋值给x_range变量
        y_range = params["y轴移动量"].split('--')
        sleep_range = params["间隔时间"].split('--')
        move_y_min = params["y轴最小移动量"]

        return {
            'x_min': int(x_range[0]),  # 将列表中的第一个元素转换为整数，并赋值给x_min变量
            'x_max': int(x_range[-1]),  # 将列表中的最后一个元素转换为整数，并赋值给x_max变量
            'y_min': int(y_range[0]),
            'y_max': int(y_range[-1]),
            'sleep_min': int(sleep_range[0]),
            'sleep_max': int(sleep_range[-1]),
            'move_y_min': int(move_y_min)
        }

    def parse_time_range(self, time_str):
        """解析时间范围字符串"""
        try:
            start, end = time_str.split('-')  # 以'-'为分隔符，将字符串分割成两个部分，以列表形式赋值给start和end变量
            return float(start), float(end)  # 将字符串转换为浮点数，并返回
        except:
            print(f'解析时间范围字符串错误: {time_str}')
            return 0.0, float('inf')  # 默认无限大

    def parse_parameter_range(self, params):
        """解析参数范围字符串"""
        x_range = params["x轴偏移"].split('--')  # 以'--'为分隔符，将字符串分割成两个部分，以列表形式赋值给x_range变量
        y_range = params["y轴移动量"].split('--')
        sleep_range = params["间隔时间"].split('--')

        return {
            'x_min': int(x_range[0]),  # 将列表中的第一个元素转换为整数，并赋值给x_min变量
            'x_max': int(x_range[-1]),  # 将列表中的最后一个元素转换为整数，并赋值给x_max变量
            'y_min': int(y_range[0]),
            'y_max': int(y_range[-1]),
            'sleep_min': int(sleep_range[0]),
            'sleep_max': int(sleep_range[-1])
        }

    def key_switch_parent_plan(self, direction):
        '''切换父方案'''
        if self.has_input_focus(): # 在切换父方案时，如果有输入控件处于焦点
            return # 如果有输入控件处于焦点，则不切换父方案

        current_index = self.profile_combo.currentIndex()  # 获取当前选中的父方案索引
        count = self.profile_combo.count()  # 获取父方案数量
        if count == 0:  # 如果父方案数量为0，则直接返回
            return
        new_index = (current_index + direction) % count  # 计算新的索引
        self.profile_combo.setCurrentIndex(new_index)  # 设置新的索引

        if self.switch_voice_CheckBox.isChecked():  # 如果方案切换语音播报复选框被选中
            add_voice_queue(f"{self.profile_combo.currentText()}")  # 播报当前的父方案名称

    def key_switch_sub_plan(self, direction):
        '''切换子方案'''
        if self.has_input_focus(): # 在切换子方案时，如果有输入控件处于焦点
            return # 如果有输入控件处于焦点，则不切换子方案

        current_index = self.sub_profile_combo.currentIndex()  # 获取当前选中的子方案索引
        count = self.sub_profile_combo.count()  # 获取子方案数量
        if count == 0:  # 如果子方案数量为0，则直接返回
            return
        new_index = (current_index + direction) % count  # 计算新的索引
        self.sub_profile_combo.setCurrentIndex(new_index)  # 设置新的索引
        if self.sub_switch_voice_CheckBox.isChecked():  # 如果方案切换语音播报复选框被选中
            add_voice_queue(f"{self.sub_profile_combo.currentText()}")  # 播报当前的子方案名称

    Key_vk_switch_sub_plan_map = {
        96: '瞄准镜', # 小键盘数字键0
        97: '1倍镜', # 小键盘数字键1
        98: '2倍镜', # 小键盘数字键2
        99: '3倍镜', # 小键盘数字键3
        100: '4倍镜', # 小键盘数字键4
        101: '5倍镜', # 小键盘数字键5
        102: '6倍镜', # 小键盘数字键6
        103: '7倍镜', # 小键盘数字键7
        104: '8倍镜', # 小键盘数字键8
        105: '红点', # 小键盘数字键9
    }
    def key_number_switch_sub_plan(self, key_vk):
        '''小键盘数字键指定切换子方案'''
        if self.has_input_focus(): # 在小键盘指定切换子方案时，如果有输入控件处于焦点
            return # 如果有输入控件处于焦点，则不切换子方案

        sub_plan_name = self.Key_vk_switch_sub_plan_map[key_vk]
        self.sub_profile_combo.setCurrentText(sub_plan_name)
        if self.sub_switch_voice_CheckBox.isChecked():  # 如果方案切换语音播报复选框被选中2
            add_voice_queue(f"{self.sub_profile_combo.currentText()}")  # 播报当前的子方案名称

    def recognizer_switch_plan(self, key):
        '''使用识别结果切换父方案和子方案'''
        if self.has_input_focus(): # 在使用识别结果切换方案时，如果有输入控件处于焦点
            return # 如果有输入控件处于焦点，则不切换方案

        global results, recognizer, main_keyboard_area_keys_1_2

        if results is None or recognizer is None or not self.auto_switch_profile_CheckBox.isChecked(): # 如果识别结果为空，或识别器对象为空，或自动切换方案复选框未被选中，则直接返回
            return # 直接返回，不执行后续操作

        main_keyboard_area_keys_1_2.append(key) # 将按键添加到列表中，1或2
        del main_keyboard_area_keys_1_2[0: -1]  # 删除列表中第一个到最后一个元素之间的所有元素

        if key == 1: # 如果按键为字母区按键1

            index = self.profile_combo.findText(results['1号枪']['识别文本']) # 查找下拉框里是否有指定文本
            if index != -1: # 如果在父方案组合框中找到匹配项
                # 设置父方案为识别结果中results['gun_1']['对比识别结果']
                self.profile_combo.setCurrentText(results['1号枪']['识别文本'])
                sub_index = self.sub_profile_combo.findText(results['1号枪-倍镜']['识别文本'])
                if sub_index != -1: # 如果在子方案组合框中找到匹配项
                    self.sub_profile_combo.setCurrentText(results['1号枪-倍镜']['识别文本'])
                elif sub_index == -1: # 如果在子方案组合框中未找到匹配项
                    if results['1号枪-倍镜']['识别文本'] in ['瞄准镜','红点', '全息']:
                        self.sub_profile_combo.setCurrentText('1倍镜')
                    else:
                        self.sub_profile_combo.setCurrentIndex(0) # 设置子方案为第一个选项
            elif index == -1: # 如果在父方案组合框中未找到匹配项
                self.profile_combo.setCurrentText('M416突击步枪') # 设置父方案为M416突击步枪
                # 设置子方案为识别结果中results['1号枪']['识别文本']
                self.sub_profile_combo.setCurrentText(results['1号枪-倍镜']['识别文本'])

        elif key == 2: # 如果按键为字母区按键2

            index = self.profile_combo.findText(results['2号枪']['识别文本'])
            if index != -1: # 如果在父方案组合框中找到匹配项
                # 设置父方案为识别结果中results['gun_2']['对比识别结果']
                self.profile_combo.setCurrentText(results['2号枪']['识别文本'])
                sub_index = self.sub_profile_combo.findText(results['2号枪-倍镜']['识别文本'])
                if sub_index != -1: # 如果在子方案组合框中找到匹配项
                    self.sub_profile_combo.setCurrentText(results['2号枪-倍镜']['识别文本'])
                elif sub_index == -1: # 如果在子方案组合框中未找到匹配项
                    if results['2号枪-倍镜']['识别文本'] in ['瞄准镜','红点', '全息']:
                        self.sub_profile_combo.setCurrentText('1倍镜')
                    else:
                        self.sub_profile_combo.setCurrentIndex(0) # 设置子方案为第一个选项
            elif index == -1: # 如果在父方案组合框中未找到匹配项
                self.profile_combo.setCurrentText('M416突击步枪') # 设置父方案为M416突击步枪
                # 设置子方案为识别结果中results['2号枪']['识别文本']
                self.sub_profile_combo.setCurrentText(results['2号枪-倍镜']['识别文本'])

    def management_recognizer(self):
        '''管理识别器，提交线程池运行'''
        if self.auto_start_ocr_CheckBox.checkState() == Qt.Checked:  # 如果自动启动OCR复选框被选中
            console_logger.info('复选框选中，启动识别器')
            self.start_recognizer()  # 启动识别器
        else:
            console_logger.info('复选框未选中，停止识别器')
            self.stop_recognizer()  # 停止识别器

    def start_recognizer(self):
        '''启动识别器，线程池运行'''
        global recognizer # 声明 recognizer 为全局变量

        if recognizer is None: # 如果识别器对象为 None，则说明识别器未创建
            console_logger.info('正在创建识别器')
            self.ocr_results_update_requested.emit( None, None, '正在创建识别器') # 启动时，发送识别结果文本框更新信号，startup
            recognizer = AutomaticRecognition("screenshots") # 创建识别器，初始化OCRv5模型
            console_logger.info('识别器创建完成') # 打印识别器已创建日志
            self.ocr_results_update_requested.emit( None, None, '识别器创建完成') # 启动时，发送识别结果文本框更新信号，startup
        else:
            console_logger.info('识别器已存在') # 打印识别器已存在日志
            self.ocr_results_update_requested.emit( None, None, '识别器已存在') # 启动时，发送识别结果文本框更新信号，startup

    def stop_recognizer(self):
        '''停止识别器，线程池运行'''
        global recognizer # 声明 recognizer 为全局变量

        if recognizer is not None: # 如果识别器对象不为 None，则说明识别器已创建
            recognizer.clean_up() # 清理识别器资源
            recognizer = None # 将识别器对象设置为 None，停止识别器
            console_logger.info('识别器已停止') # 打印识别器已停止日志

    def display_recognition_results(self, results_verify, results=None, startup=None):
        '''显示识别结果到文本框， 通过信号机制在主线程中更新UI
        :param results_verify: 验证区域识别结果
        :param results: 完整识别结果（可选）
        :param startup: 启动信息（可选）
        '''
        display_text = ''

        if startup:  # 如果startup参数不为None
            display_text += f"{startup}\n"

        if results_verify:  # 如果验证区域识别结果不为空
            display_text = "=== 识别结果 ===\n\n"
            # 显示验证区域结果
            display_text += "【验证区域】\n"
            for region_name, result_data in results_verify.items():  # 遍历验证区域识别结果；.items()方法返回一个键值对元组的视图对象
                if '识别文本' in result_data and result_data['识别文本']:  # 如果验证区域识别结果中包含识别文本，且识别文本不为空
                    text = result_data.get('识别文本', '未识别')  # 获取识别文本，若不存在则设为未识别
                    score = result_data.get('置信度', 'N/A')  # 获取置信度，若不存在则设为N/A
                    ocr_time = result_data.get('识别耗时', 'N/A')  # 获取识别耗时，若不存在则设为N/A
                    display_text += f"{region_name}: {text:} (置信度: {score}, 识别耗时: {ocr_time})\n"
                else:
                    display_text += f"{region_name}: 未识别到文本\n"

        # 如果有完整识别结果，也显示出来
        if results:  # 如果完整识别结果不为空
            display_text += "\n【完整识别】\n"
            for region_name, result_data in results.items():  # 遍历完整识别结果；.items()方法返回一个键值对元组的视图对象
                if 'error' in result_data:  # 如果完整识别结果中包含错误信息
                    display_text += f"{region_name}: 错误 - {result_data['error']}\n"
                else:
                    text = result_data.get('识别文本', '未识别')
                    score = result_data.get('置信度', '未知')  # 获取置信度，若不存在则设为未知
                    ocr_time = result_data.get('识别耗时', 'N/A')  # 获取识别耗时，若不存在则设为N/A
                    display_text += f"{region_name}: {text:} (置信度: {score}, 识别耗时: {ocr_time})\n"

        # 显示到文本框
        self.ocr_result_te.setPlainText(display_text)  # 将识别结果文本设置到文本框中

        # 自动滚动到顶部
        self.ocr_result_te.verticalScrollBar().setValue(0)  # .verticalScrollBar() 方法返回文本框的垂直滚动条对象;.setValue(0) 方法将滚动条值设置为0，即滚动到顶部

    def run_the_recognizer(self):
        '''运行识别器，支持智能跳过机制，在线程池中运行'''
        global results, recognizer, skip_next_recognition

        if recognizer is None: # 如果识别器对象为 None，则说明识别器未创建
            return # 如果识别器对象为 None，则说明识别器未创建，直接返回

        # 如果上次验证有结果，这次跳过
        if skip_next_recognition: # 如果上次验证有结果，这次跳过
            skip_next_recognition = False # 重置跳过标识
            console_logger.info('上次验证有结果，本次跳过') # 打印上次验证有结果，这次跳过日志
            return

        # 执行验证区域识别
        time.sleep(0.25) # 等待0.3秒，确保背包界面已经打开
        results_verify = recognizer.recognize_verify_regions()
        current_verify_result = results_verify['背包']['识别文本']

        # 设置下次是否跳过
        if current_verify_result == '背包': # 如果验证区域有匹配项，且匹配项为背包
            # 验证成功，下次跳过
            skip_next_recognition = True # 标识下次跳过

            # 同时执行完整识别
            results = recognizer.recognize_all_regions()
            console_logger.info('验证区域有匹配项，执行完整识别')
            # 显示识别结果到文本框， 通过信号机制在主线程中更新UI
            self.ocr_results_update_requested.emit(results_verify, results, None) # 进行完整识别后，更新识别结果到文本框

            if main_keyboard_area_keys_1_2: # 如果main_keyboard_area_keys_1_2列表不为空
                key = main_keyboard_area_keys_1_2.pop(-1) # 从列表中取出最后一个按键
                self.recognizer_switch_plan_requested.emit(key) # 在完整识别后，根据列表中最后一个按键，自动切换方案，发射信号

        else:
            # 验证失败，下次不跳过
            skip_next_recognition = False # 标识下次不跳过
            console_logger.info('验证区域无匹配项，下次不跳过') # 打印验证区域无匹配项，下次不跳过日志
            # 显示识别结果到文本框， 通过信号机制在主线程中更新UI
            self.ocr_results_update_requested.emit(results_verify, results, None) # 进行验证区域识别后，更新识别结果到文本框

    class OcrProfileSaveDialog(QDialog):
        '''继承自QDialog：用于创建模态对话框;
        内嵌类：定义在ControlUI类内部，可以访问父类的属性和方法;
        模态对话框：用户必须完成对话框操作才能继续使用主窗口'''

        def __init__(self, parent=None):
            '''parent参数：接收父窗口引用，确保对话框显示在父窗口中央'''
            super().__init__(parent)
            self.setWindowTitle('保存OCR方案')  # 设置对话框标题为'保存OCR方案'
            layout = QVBoxLayout()  # 创建垂直布局管理器

            self.ocr_profile_label = QLabel('OCR方案名称:') # 创建标签，显示'OCR方案名称:'
            self.ocr_profile_input = QLineEdit() # 创建文本框，用户输入OCR方案名称
            layout.addWidget(self.ocr_profile_label) # 添加OCR方案名称标签到布局
            layout.addWidget(self.ocr_profile_input) # 添加OCR方案名称文本框到布局

            self.ok_btn = QPushButton('确定')
            self.ok_btn.clicked.connect(self.accept)  # 信号连接：点击按钮触发accept()方法，关闭对话框并返回QDialog.Accepted
            layout.addWidget(self.ok_btn)

            self.setLayout(layout)

        def get_names(self):
            return self.ocr_profile_input.text() # 返回OCR方案名称文本框的文本内容

    def save_ocr_profile(self):
        """保存OCR方案参数"""
        dialog = self.OcrProfileSaveDialog(self)  # 创建对话框实例
        if dialog.exec_() == QDialog.Accepted:  # 调用exec_()显示对话框并等待用户操作
            ocr_profile_name = dialog.get_names()  # 获取用户输入的OCR方案名称
            if not ocr_profile_name:  # 检查输入是否为空
                QMessageBox.about(self, '错误', 'OCR方案名称不能为空！', QMessageBox.Ok)
                return

            ocr_profile_data= self.ocr_coordinates_te.toPlainText() # toPlainText()方法获取文本框的纯文本内容作为方案参数
            if not ocr_profile_data:
                QMessageBox.about(self, '错误', 'OCR方案参数不能为空！', QMessageBox.Ok)
                return
            try:
                ocr_profile_data = json.loads(ocr_profile_data)  # 尝试将文本内容解析为JSON格式
            except json.JSONDecodeError as e:
                QMessageBox.about(self, '错误', f'OCR方案参数格式错误:{str(e)}', QMessageBox.Ok)
                both_logger.error(f'OCR方案参数格式错误:{str(e)}')
                return

            profile_dir = Path('ocr_profiles')  # 目录路径
            profile_dir.mkdir(parents=True, exist_ok=True)  # 创建父方案目录，parents=True确保父目录也被创建，exist_ok=True如果目录已存在则不抛出异常
            profile_path = profile_dir / f'{ocr_profile_name}.json'  # 子方案文件路径

            try:
                with open(profile_path, 'w', encoding='utf-8') as f:
                    json.dump(ocr_profile_data, f, ensure_ascii=False, indent=4)  # 写入方案参数到文件
                QMessageBox.about(self, '成功', f'OCR方案{ocr_profile_name}已保存到 {profile_path}')
                self.refresh_ocr_profile_list()  # 保存ocr方案后，刷新OCR方案列表

            except Exception as e:
                QMessageBox.about(self, '错误', f'保存方案参数失败: {str(e)}')
                both_logger.error(f'保存方案参数失败: {str(e)}')

    def refresh_ocr_profile_list(self):
        """刷新OCR方案列表"""
        ocr_profile_name = self.ocr_regions_parameter_plan_combo.currentText()  # 获取当前选中的OCR方案名称
        '''combo.count() - 返回下拉列表中项目的总数(整数（int)),用于判断和遍历
         combo.itemText(index) - 根据索引获取下拉列表中对应项目的文本内容; index：整数，项目的索引（从0开始）;返回字符串（str），对应索引的文本内容，用于获取具体内容
         combo.findText(text) - 在下拉列表中查找指定文本，返回对应的索引; text：字符串，要查找的文本;返回整数（int），找到的索引；如果没找到返回-1，用于查找和验证存在性'''
        ocr_profile_dir = Path('ocr_profiles')  # OCR方案目录路径
        ocr_profile_dir.mkdir(parents=True, exist_ok=True) # .mkdir(parents=True, exist_ok=True)创建目录，parents=True确保目录也被创建，exist_ok=True如果目录已存在则不抛出异常

        ocr_plans = [f.stem for f in ocr_profile_dir.iterdir() if f.is_file() and f.suffix == '.json']  # 列出所有方案文件，即方案名称

        self.ocr_regions_parameter_plan_combo.clear()  # 清空下拉框
        self.ocr_regions_parameter_plan_combo.addItems(ocr_plans)  # 添加OCR方案名称到下拉框，如果列表不为空：自动显示第一个项目，如果列表为空：显示空白
        console_logger.info(f'OCR方案列表已刷新')

        if ocr_profile_name and ocr_profile_name in ocr_plans: # 如果ocr_profile_name不是空字符串且存在于ocr_plans列表中，则设置下拉框的当前文本为ocr_profile_name
            self.ocr_regions_parameter_plan_combo.setCurrentText(ocr_profile_name)

    def load_ocr_profile(self):
        """加载OCR方案参数"""
        ocr_profile_name = self.ocr_regions_parameter_plan_combo.currentText()  # 获取当前选中的OCR方案名称
        if not ocr_profile_name: # 如果ocr_profile_name为空字符串，则直接返回，不执行任何操作
            return
        ocr_profile_path = Path('ocr_profiles') / f'{ocr_profile_name}.json'  # OCR方案文件路径
        if not ocr_profile_path.exists(): # 如果文件不存在，弹出提示框并返回，不执行任何操作
            QMessageBox.about(self, '错误', f'OCR方案{ocr_profile_name}不存在')
            return
        try:
            with open(ocr_profile_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)  # 读取方案参数
                formatted_json = json.dumps(profile_data, ensure_ascii=False, indent=4) # 修复：使用json.dumps将字典格式化为JSON字符串
                self.ocr_coordinates_te.setPlainText(formatted_json)  # 显示格式化的JSON
                console_logger.info(f'OCR方案：{ocr_profile_name} 已加载')
                self.parse_ocr_plan_parameters()  # 在每次加载方案参数后，调用此函数解析方案参数
        except Exception as e:
            QMessageBox.about(self, '错误', f'加载方案参数失败: {str(e)}')
            both_logger.error(f'加载方案参数失败: {str(e)}')

    def parse_ocr_plan_parameters(self):
        '''解析OCR方案参数'''
        try:
            ocr_data = json.loads(self.ocr_coordinates_te.toPlainText())  # 从UI界面文本框中获取方案参数，并解析为字典
            from PaddleOCR import set_ocr_regions
            set_ocr_regions(ocr_data) # 设置OCR区域
        except json.JSONDecodeError as e:
            QMessageBox.about(self, '错误', f'OCR方案参数格式错误: {str(e)}')
            return

    def delete_ocr_profile(self):
        """删除OCR方案"""
        ocr_profile_name = self.ocr_regions_parameter_plan_combo.currentText()  # 获取当前选中的OCR方案名称
        if not ocr_profile_name: # 如果ocr_profile_name为空字符串，则直接返回，不执行任何操作
            return

        ocr_profile_path = Path('ocr_profiles') / f'{ocr_profile_name}.json'  # OCR方案文件路径
        if not ocr_profile_path.exists(): # 如果文件不存在，弹出提示框并返回，不执行任何操作
            QMessageBox.about(self, '错误', f'OCR方案{ocr_profile_name}不存在')
            return

        reply = QMessageBox.question(self, '确认删除', f'确定删除OCR方案 {ocr_profile_name} 吗？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes: # 如果用户点击了确认删除按钮
            try:
                ocr_profile_path.unlink()  # 删除OCR方案文件，.unlink()方法用于删除文件或目录
                QMessageBox.about(self, '成功', f'OCR方案{ocr_profile_name}已删除')
                self.refresh_ocr_profile_list()  # 删除ocr方案后，刷新OCR方案列表
                console_logger.info(f'OCR方案：{ocr_profile_name} 已删除')
            except Exception as e:
                QMessageBox.about(self, '错误', f'删除OCR方案参数失败: {str(e)}')
                both_logger.error(f'删除OCR方案参数失败: {str(e)}')
        else:
            console_logger.info(f'取消删除操作')

    def ocr_coordinates_te_focus_out(self, event):
        '''识别坐标文本框失去焦点时，解析方案参数'''
        self.parse_ocr_plan_parameters()  # 解析OCR方案参数
        # 调用父类方法确保正常行为
        super(QTextEdit, self.ocr_coordinates_te).focusOutEvent(event)

    def update_ocr_profile(self):
        """更新OCR方案"""
        ocr_profile_name = self.ocr_regions_parameter_plan_combo.currentText()  # 获取当前选中的OCR方案名称
        if not ocr_profile_name: # 如果ocr_profile_name为空字符串，则直接返回，不执行任何操作
            return
        ocr_profile_path = Path('ocr_profiles') / f'{ocr_profile_name}.json'  # OCR方案文件路径
        if not ocr_profile_path.exists(): # 如果文件不存在，直接返回，不执行任何操作
            return
        ocr_profile_data = self.ocr_coordinates_te.toPlainText()  # 获取OCR方案参数
        try:
            ocr_profile_data = json.loads(ocr_profile_data)  # 解析JSON字符串为字典；json.loads()将JSON字符串反序列化为Python字典
            with open(ocr_profile_path, 'w', encoding='utf-8') as f:
                json.dump(ocr_profile_data, f, ensure_ascii=False, indent=4)  # 写入OCR方案参数到文件；json.dump()将Python字典序列化为JSON字符串并写入文件
            QMessageBox.about(self, '成功', f'OCR方案 {ocr_profile_name} 已更新')
            console_logger.info(f'OCR方案：{ocr_profile_name} 已更新')
            self.parse_ocr_plan_parameters()  # 在文本框更新后，解析OCR方案参数
        except json.JSONDecodeError as e:
            QMessageBox.about(self, '错误', f'OCR方案参数格式错误: {str(e)}')
            both_logger.error(f'OCR方案参数格式错误: {str(e)}')

    def toggle_test_mode(self, state):
        '''切换测试模式'''
        if state == 2: # 如果测试模式按钮被选中
            from MouseListener import create_test_mouse_listener, set_is_test_mode_enabled
            set_is_test_mode_enabled(True) # 设置测试模式为启用状态
            create_test_mouse_listener() # 创建测试鼠标监听器

        elif state == 0: # 如果测试模式按钮未被选中
            from MouseListener import create_basic_mouse_listener, set_is_test_mode_enabled
            set_is_test_mode_enabled(False) # 设置测试模式为禁用状态
            create_basic_mouse_listener() # 创建基本鼠标监听器

    def set_test_info_te(self, test_text):
        '''设置测试信息文本框的文本'''
        self.test_info_te.setPlainText(test_text) # 设置测试信息文本框的文本为test_text
        # 自动滚动到顶部
        self.test_info_te.verticalScrollBar().setValue(0) # .verticalScrollBar() 方法返回文本框的垂直滚动条对象;.setValue(0) 方法将滚动条值设置为0，即滚动到顶部

    # 创建一个函数，使用self.test_info_te里的测试信息，修改self.plan_information里的方案参数
    def adjust_parameter_information(self):
        """根据测试信息调整方案参数"""
        # 1. 解析测试信息
        test_data = {} # 用于存储解析后的测试数据，键为时间范围，值为像素数
        for line in self.test_info_te.toPlainText().split('\n'): # 遍历测试信息文本框的每一行；.toPlainText() 方法返回文本框的纯文本内容；.split('\n') 方法将文本按换行符分割为行列表
            if ':' in line: # 如果当前行包含冒号，说明是一个时间范围-像素数对
                time_range, pixel_str = line.split(':') # 将当前行按冒号分割为时间范围和像素数对
                time_range = time_range.replace(' ', '').replace('s', '') # 移除时间范围字符串的所有空格和s
                pixels = int(float(pixel_str.strip())) # 先转换为浮点数，再转换为整数；.strip() 方法移除字符串首尾空格
                test_data[time_range] = pixels # 将解析后的时间范围和像素数添加到test_data字典中

        # 2. 更新方案参数
        # 获取self.plan_information里的文本，并序列化为Python字典
        plan_text = self.plan_information.toPlainText() # 获取计划信息文本框的文本
        try:
            plan_dict = json.loads(plan_text) # 解析计划信息文本框的文本为Python字典；json.loads()将JSON字符串反序列化为Python字典
        except json.JSONDecodeError as e:
            QMessageBox.about(self, '错误', f'方案参数格式错误: {str(e)}')
            both_logger.error(f'方案参数格式错误: {str(e)}')
            return

        new_plan = {} # 创建一个空字典，用于存储更新后的方案参数
        new_plan['基础参数'] = plan_dict['参数信息']['基础参数'] # 从plan_dict中获取基础参数，并将其赋值给new_plan['基础参数']

        for time_range, pixels in test_data.items(): # 遍历test_data字典中的每个时间范围-像素数对
            # 计算y轴移动量范围 (像素/4的±1范围)
            base_value = pixels / 4 # 计算像素数除以4的结果，作为y轴移动量的基础值
            y_min = max(0, int(base_value - 1))  # 确保不小于0；int() 方法将浮点数转换为整数；max(0, ...) 方法确保y_min不小于0
            y_max = max(1, int(base_value + 1)) # 计算y轴移动量的上限值；int() 方法将浮点数转换为整数；max(1, ...) 方法确保y_max不小于1

            new_plan[time_range] = {
                "x轴偏移": "-1--1",
                "y轴移动量": f"{y_min}--{y_max}",
                "间隔时间": "20--30",
            }

        # 3. 更新UI显示
        plan_dict['参数信息'] = new_plan
        # 将self.plan_information显示文本设置为plan_dict的JSON字符串表示
        self.plan_information.setPlainText(json.dumps(plan_dict, ensure_ascii=False, indent=4)) # json.dumps() 将Python字典序列化为JSON字符串；ensure_ascii=False 确保非ASCII字符不被转义；indent=4 缩进4个空格

    def init_data(self):
        '''初始化数据'''
        self.refresh_parent_plan_list()  # 初始化时，刷新父方案列表
        self.refresh_ocr_profile_list()  # 初始化时，刷新OCR方案列表


if __name__ == "__main__":
    app = QApplication()
    window = MainWindow()
    window.show()
    app.exec()
