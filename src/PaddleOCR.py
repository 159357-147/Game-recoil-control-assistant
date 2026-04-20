import time # 导入time模块，用于时间操作
import os # 导入os模块，用于文件操作
from pathlib import Path # 导入Path模块，用于路径操作
import mss # 导入mss模块，用于截图
import numpy as np  # 导入numpy模块，用于数组操作


# 定义截图区域，左上角坐标-右下角坐标
REGIONS = {
    '1号枪': '1281,0-1408,22',  # 区域1，1号枪械
    '1号枪-倍镜': '1479,91-1538,116',  # 区域2，1号枪械倍镜
    '2号枪': '1281,452-1408,474',  # 区域3，2号枪械
    '2号枪-倍镜': '1479,542-1538,567',  # 区域4，2号枪械倍镜
}
# 定义验证区域
Verify = {
    '背包': '1640,0-1687,30'  # 区域5，背包位置
}

def set_ocr_regions(ocr_data):
    """设置OCR区域
    :param ocr_data: OCR区域字典，键为区域名称，值为区域字符串
    """
    global REGIONS, Verify
    try:
        REGIONS = ocr_data['REGIONS'] # 从OCR区域字典中获取REGIONS区域，键为区域名称，值为区域字符串，覆盖默认REGIONS区域
        Verify = ocr_data['Verify'] # 从OCR区域字典中获取Verify区域，键为区域名称，值为区域字符串
        print(f"设置OCR区域参数成功")
    except Exception as e:
        print(f"设置OCR区域参数时出错: {e}")

def parse_region(region_str):
    """解析区域字符串，返回坐标元组
    :param region_str: 区域字符串，格式为 "x1,y1-x2,y2"
    """
    start, end = region_str.split('-')  # 区域字符串格式为 "x1,y1-x2,y2"，使用 "-" 分割为两个坐标字符串,start 为 "x1,y1"，end 为 "x2,y2"
    x1, y1 = map(int, start.split(','))  # 坐标字符串格式为 "x,y"，使用 "," 分割为两个坐标整数,x1 为 "x1"，y1 为 "y1"，map(int, ...) 表示将字符串转换为整数
    x2, y2 = map(int, end.split(','))  # 坐标字符串格式为 "x,y"，使用 "," 分割为两个坐标整数,x2 为 "x2"，y2 为 "y2"
    return (x1, y1, x2, y2)  # 返回坐标元组

def capture_region(dict_name, screenshots_dir):
    """使用mss截取指定区域并保存为png
    :param dict_name: 字典名称，用于查找参数字典中的坐标
    :param screenshots_dir: 截图保存目录，用于存储截取的图像
    :return: 截图对象列表
    """
    image_input = []  # 初始化一个列表，储存所有的截图对象

    with mss.mss() as sct: # 打开mss截图工具；with 语句用于自动管理资源，确保在使用后及时关闭，as sct 表示将 mss.mss() 实例赋值给 sct
        for region_name in dict_name.keys():  # 遍历 dict_name 的所有键；.keys()获取dict_name的所有键，例如 '1号枪'
            # 解析区域坐标
            region = parse_region(dict_name[region_name])  # 解析区域字符串，返回坐标元组;REGIONS[region_name] 表示从 REGIONS 字典中获取 region_name 对应的区域字符串
            monitor = {"left": region[0], # 截图区域左上角 x 坐标 x1
                       "top": region[1], # 截图区域左上角 y 坐标 y1
                       "width": region[2] - region[0], # 截图区域宽度 x2 - x1
                       "height": region[3] - region[1] # 截图区域高度 y2 - y1
                       }

            # 截图
            time.sleep(0.01)  # 暂停10毫秒
            screenshot = sct.grab(monitor) # 截取指定区域的图像，返回图像对象;sct.grab() 方法用于截取指定区域的图像
            screenshot_obj = np.asarray(screenshot)[:,:,:3]  # 直接取前 3 通道，符合PaddleOCR输入要求
            image_input.append(screenshot_obj)  # 将截图对象添加到列表中

            filename = f"{region_name}.png"  # 定义截图文件名，格式为 "区域名称.png"
            filepath = os.path.join(screenshots_dir, filename)  # 拼接截图文件路径，将 screenshots_dir 和 filename 拼接起来，得到完整的文件路径

            # mss保存为png
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=filepath) # 将截图对象转换为png格式，保存到 filepath 路径；screenshot.rgb 表示截图对象的rgb数据，screenshot.size 表示截图对象的大小

    return image_input  # 返回截图对象列表

class AutomaticRecognition:
    def __init__(self, base_dir="screenshots"):
        self.model = None  # 初始化OCRv5模型为None
        self.base_dir = Path(base_dir) # Path() 函数用于将字符串路径转换为 Path 对象；base_dir 是主目录路径，默认值为 "screenshots"
        # 创建截图目录
        self.base_dir.mkdir(exist_ok=True) # 创建主目录；mkdir()方法用于创建目录，exist_ok=True表示如果目录已存在，不会抛出异常
        self.initialise_PP_OCRv5() # 初始化OCRv5模型

    def initialise_PP_OCRv5(self):
        """初始化OCRv5模型"""
        os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
        # 禁用模型源检查，避免下载模型时的警告

        from paddleocr import TextRecognition  # 导入PaddleOCR模块，用于OCR识别
        # global model # 声明 model 为全局变量，以便在函数中修改它

        start_time = time.time()  # 记录开始时间

        self.model = TextRecognition(
            model_name="PP-OCRv5_server_rec",  # 模型名称，v5文字识别模型
            model_dir="./PaddleOCRv5Model/PP-OCRv5_server_rec",  # 文本识别模型路径
            cpu_threads = 1 # 在CPU上推理时使用的线程数量
        )

        end_time = time.time()  # 记录结束时间
        print(f"初始化耗时: {(end_time - start_time) * 1000:.2f} 毫秒")

    def clean_up(self):
        """清理资源"""
        if self.model is not None:
            # 尝试释放模型资源
            del self.model
            self.model = None

    def recognize_all_regions(self):
        """识别所有区域的装备"""
        results = {}  # 初始化一个空字典，用于存储所有验证区域的识别结果
        region_dir = self.base_dir  # 将截图保存路径赋值给 region_dir；
        start_time = time.time()  # 记录开始时间

        screenshot_objects = capture_region(REGIONS, region_dir)  # 调用 capture_region() 函数，截取 识别区域的图像，并保存到 region_dir 目录中

        output = self.model.predict(input = screenshot_objects, batch_size = len(screenshot_objects))

        for i in range(len(REGIONS)):
            name = list(REGIONS.keys())[i]  # 获取 REGIONS 字典的第 i 个键，赋值给 name 变量
            text = output[i]['rec_text']  # 识别文本；从 res 中提取 rec_text 字段，赋值给 text 变量
            score = output[i]['rec_score']  # 识别置信度；从 res 中提取 rec_score 字段，赋值给 score 变量

            if text:  # 如果识别到了文字
                results[name] = {  # 存储对比识别结果的字典，键为区域名称 region_name，值为另一个字典
                    '识别文本': text,  # 识别文本
                    '置信度': f"{score * 100:.2f} %",  # 识别置信度
                    '识别耗时': f"{(time.time() - start_time) * 1000:.0f} 毫秒",  # 识别耗时
                }
                # print(
                #     f"{name}: 识别结果 - {text} (置信度: {score * 100:.4f} % )")
            else:
                results[name] = {
                    '识别文本': None,  # 识别文本
                    '置信度': None,  # 识别置信度
                    '识别耗时': f"{(time.time() - start_time) * 1000:.0f} 毫秒",  # 识别耗时
                }
                # print(f"{name}: 未识别到文本")

        return results  # 返回所有装备区域的识别结果字典，键为区域名称，值为另一个字典，包含截图路径和对比识别结果（或错误信息）

    def recognize_verify_regions(self):
        """识别验证区域"""
        results_verify = {}  # 初始化一个空字典，用于存储所有验证区域的识别结果
        region_dir = self.base_dir  # 将截图保存路径赋值给 region_dir；
        start_time = time.time()  # 记录开始时间

        screenshot_objects = capture_region(Verify, region_dir)  # 调用 capture_region() 函数，截取 验证 Verify 区域的图像，并保存到 region_dir 目录中

        output = self.model.predict(input = screenshot_objects, batch_size = len(screenshot_objects))

        for i in range(len(Verify)):
            name = list(Verify.keys())[i]  # 获取 Verify 字典的第 i 个键，赋值给 name 变量
            text = output[i]['rec_text']  # 识别文本；从 res 中提取 rec_text 字段，赋值给 text 变量
            score = output[i]['rec_score']  # 识别置信度；从 res 中提取 rec_score 字段，赋值给 score 变量

            if text:  # 如果识别到了文字
                results_verify[name] = {  # 存储对比识别结果的字典，键为区域名称 region_name，值为另一个字典
                    '识别文本': text,  # 识别文本
                    '置信度': f"{score * 100:.2f} %",  # 识别置信度
                    '识别耗时': f"{(time.time() - start_time) * 1000:.0f} 毫秒",  # 识别耗时
                }
                # print(
                #     f"{name}: 识别结果 - {text} (置信度: {score * 100:.4f} % )")
            else:
                results_verify[name] = {
                    '识别文本': None,  # 识别文本
                    '置信度': None,  # 识别置信度
                    '识别耗时': f"{(time.time() - start_time) * 1000:.0f} 毫秒",  # 识别耗时
                }
                # print(f"{name}: 未识别到文本")

        return results_verify  # 返回所有验证区域的识别结果字典，键为区域名称，值为另一个字典，包含截图路径和对比识别结果（或错误信息）