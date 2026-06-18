import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
import os
import glob
import sys
import io
import tempfile

# resources.py 会在打包前由 build.py 自动生成，包含内嵌的图片二进制数据（base64）
# 在运行时优先从 resources 中读取，如不存在则回退到磁盘文件
try:
    import resources
except Exception:
    resources = None


class ImageToFontConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("图像转字模工具")
        self.root.geometry("960x800")
        
        # 设置窗口图标
        self.set_window_icon()
        
        # 存储参数
        self.brightness = tk.DoubleVar(value=0)
        self.contrast = tk.DoubleVar(value=1.0)
        self.scan_direction = tk.StringVar(value="vertical")  # 扫描方向: vertical(垂直) 或 horizontal(水平)
        self.scan_order = tk.StringVar(value="left_to_right_top_to_bottom")  # 扫描顺序
        self.invert_color = tk.BooleanVar(value=False)  # 反色
        self.rotation = tk.StringVar(value="0")  # 旋转角度
        self.horizontal_flip = tk.BooleanVar(value=False)  # 水平镜像
        self.vertical_flip = tk.BooleanVar(value=False)  # 垂直镜像
        self.slideshow_interval = tk.IntVar(value=500)  # 幻灯片切换间隔（毫秒）
        self.video_frame_interval = tk.IntVar(value=30)  # 视频帧间隔
        self.image_folder = tk.StringVar()
        self.output_file = tk.StringVar()
        self.video_file = tk.StringVar()  # 视频文件路径
        
        # 幻灯片播放相关
        self.slideshow_images = []
        self.slideshow_index = 0
        self.slideshow_running = False
        self.slideshow_job = None
        
        # 当前显示的图像
        self.current_image = None
        self.processed_image = None
        
        # 创建UI
        self.create_widgets()
        
    def set_window_icon(self):
        """设置窗口图标"""
        try:
            # 首先尝试从磁盘读取（开发模式）或 PyInstaller 的临时目录读取（打包后）
            icon_path = "cym_icon.ico"
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, "cym_icon.ico")

            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                return

            # 如果磁盘上没有 icon 文件，尝试从内嵌 resources 加载
            if resources is not None and hasattr(resources, 'get'):
                data = resources.get('cym_icon.ico')
                if data:
                    # 将二进制写入临时文件，然后使用 iconbitmap 加载
                    tf = tempfile.NamedTemporaryFile(delete=False, suffix='.ico')
                    try:
                        tf.write(data)
                        tf.flush()
                        tf.close()
                        self.root.iconbitmap(tf.name)
                    finally:
                        # 不立即删除，Windows 下 iconbitmap 需要文件存在；文件会在程序退出后由系统清理或手动删除
                        pass
        except Exception as e:
            # 如果设置图标失败，不中断程序运行
            print(f"设置图标失败: {e}")
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)  # 调整列权重，让预览区域更宽
        main_frame.columnconfigure(1, weight=0)  # 幻灯片区域不扩展
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件设置", padding="10")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="图像文件夹:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.image_folder, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        ttk.Button(file_frame, text="浏览...", command=self.browse_folder).grid(row=0, column=2, sticky=tk.E, pady=2)
        
        ttk.Label(file_frame, text="输出文件:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.output_file, width=50).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        ttk.Button(file_frame, text="浏览...", command=self.browse_output).grid(row=1, column=2, sticky=tk.E, pady=2)
        
        # 视频文件选择
        ttk.Label(file_frame, text="视频文件:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.video_file, width=50).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        ttk.Button(file_frame, text="浏览...", command=self.browse_video).grid(row=2, column=2, sticky=tk.E, pady=2)
        
        # 视频帧间隔设置
        ttk.Label(file_frame, text="帧间隔:").grid(row=3, column=0, sticky=tk.W, pady=2)
        frame_interval_frame = ttk.Frame(file_frame)
        frame_interval_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        ttk.Entry(frame_interval_frame, textvariable=self.video_frame_interval, width=10).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(frame_interval_frame, text="帧").grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        ttk.Button(frame_interval_frame, text="从视频生成图片", command=self.extract_frames_from_video).grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        
        # 参数调节区域
        param_frame = ttk.LabelFrame(main_frame, text="图像参数调节", padding="10")
        param_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        param_frame.columnconfigure(1, weight=1)
        
        # 亮度调节
        ttk.Label(param_frame, text="亮度:").grid(row=0, column=0, sticky=tk.W, pady=2)
        brightness_scale = ttk.Scale(param_frame, from_=-100, to=100, variable=self.brightness, orient=tk.HORIZONTAL, command=self.update_preview)
        brightness_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        self.brightness_label = ttk.Label(param_frame, text="0")
        self.brightness_label.grid(row=0, column=2, sticky=tk.W, pady=2)
        
        # 对比度调节
        ttk.Label(param_frame, text="对比度:").grid(row=1, column=0, sticky=tk.W, pady=2)
        contrast_scale = ttk.Scale(param_frame, from_=0, to=3, variable=self.contrast, orient=tk.HORIZONTAL, command=self.update_preview)
        contrast_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        self.contrast_label = ttk.Label(param_frame, text="1.0")
        self.contrast_label.grid(row=1, column=2, sticky=tk.W, pady=2)
        
        # 反色选项
        ttk.Checkbutton(param_frame, text="反色", variable=self.invert_color, command=self.update_preview).grid(row=2, column=0, sticky=tk.W, pady=2)
        
        # 旋转角度选项
        ttk.Label(param_frame, text="旋转角度:").grid(row=3, column=0, sticky=tk.W, pady=2)
        rotation_frame = ttk.Frame(param_frame)
        rotation_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        ttk.Radiobutton(rotation_frame, text="0°", variable=self.rotation, value="0", command=self.update_preview).pack(side=tk.LEFT)
        ttk.Radiobutton(rotation_frame, text="90°", variable=self.rotation, value="90", command=self.update_preview).pack(side=tk.LEFT)
        ttk.Radiobutton(rotation_frame, text="180°", variable=self.rotation, value="180", command=self.update_preview).pack(side=tk.LEFT)
        ttk.Radiobutton(rotation_frame, text="270°", variable=self.rotation, value="270", command=self.update_preview).pack(side=tk.LEFT)
        
        # 镜像选项
        mirror_frame = ttk.Frame(param_frame)
        mirror_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=2)
        ttk.Checkbutton(mirror_frame, text="水平镜像", variable=self.horizontal_flip, command=self.update_preview).pack(side=tk.LEFT)
        ttk.Checkbutton(mirror_frame, text="垂直镜像", variable=self.vertical_flip, command=self.update_preview).pack(side=tk.LEFT)
        
        # 幻灯片间隔时间调节
        ttk.Label(param_frame, text="幻灯片间隔(ms):").grid(row=5, column=0, sticky=tk.W, pady=2)
        interval_frame = ttk.Frame(param_frame)
        interval_frame.grid(row=5, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        ttk.Entry(interval_frame, textvariable=self.slideshow_interval, width=10).pack(side=tk.LEFT)
        ttk.Scale(interval_frame, from_=100, to=5000, variable=self.slideshow_interval, orient=tk.HORIZONTAL, command=lambda x: self.slideshow_interval.set(int(float(x)))).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 扫描方向调节
        ttk.Label(param_frame, text="扫描方向:").grid(row=6, column=0, sticky=tk.W, pady=2)
        direction_frame = ttk.Frame(param_frame)
        direction_frame.grid(row=6, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        
        ttk.Radiobutton(direction_frame, text="垂直", variable=self.scan_direction, value="vertical", command=self.update_preview).pack(side=tk.LEFT)
        ttk.Radiobutton(direction_frame, text="水平", variable=self.scan_direction, value="horizontal", command=self.update_preview).pack(side=tk.LEFT)
        
        # 扫描顺序调节
        ttk.Label(param_frame, text="扫描顺序:").grid(row=7, column=0, sticky=tk.W, pady=2)
        order_frame1 = ttk.Frame(param_frame)
        order_frame1.grid(row=7, column=1, sticky=(tk.W, tk.E), padx=(5, 5), columnspan=2)
        
        ttk.Radiobutton(order_frame1, text="从左到右，从上到下", variable=self.scan_order, value="left_to_right_top_to_bottom", command=self.update_preview).pack(side=tk.LEFT)
        ttk.Radiobutton(order_frame1, text="从上到下，从左到右", variable=self.scan_order, value="top_to_bottom_left_to_right", command=self.update_preview).pack(side=tk.LEFT)
        
        order_frame2 = ttk.Frame(param_frame)
        order_frame2.grid(row=8, column=1, sticky=(tk.W, tk.E), padx=(5, 5), columnspan=2)
        
        ttk.Radiobutton(order_frame2, text="从右到左，从上到下", variable=self.scan_order, value="right_to_left_top_to_bottom", command=self.update_preview).pack(side=tk.LEFT)
        ttk.Radiobutton(order_frame2, text="从下到上，从左到右", variable=self.scan_order, value="bottom_to_top_left_to_right", command=self.update_preview).pack(side=tk.LEFT)
        
        order_frame3 = ttk.Frame(param_frame)
        order_frame3.grid(row=9, column=1, sticky=(tk.W, tk.E), padx=(5, 5), columnspan=2)
        
        ttk.Radiobutton(order_frame3, text="从左到右，从下到上", variable=self.scan_order, value="left_to_right_bottom_to_top", command=self.update_preview).pack(side=tk.LEFT)
        ttk.Radiobutton(order_frame3, text="从右到左，从下到上", variable=self.scan_order, value="right_to_left_bottom_to_top", command=self.update_preview).pack(side=tk.LEFT)
        
        order_frame4 = ttk.Frame(param_frame)
        order_frame4.grid(row=10, column=1, sticky=(tk.W, tk.E), padx=(5, 5), columnspan=2)
        
        ttk.Radiobutton(order_frame4, text="从上到下，从右到左", variable=self.scan_order, value="top_to_bottom_right_to_left", command=self.update_preview).pack(side=tk.LEFT)
        ttk.Radiobutton(order_frame4, text="从下到上，从右到左", variable=self.scan_order, value="bottom_to_top_right_to_left", command=self.update_preview).pack(side=tk.LEFT)
        
        # 图像预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="图像预览", padding="10")
        preview_frame.grid(row=11, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(11, weight=1)
        
        # Canvas用于显示图像
        self.canvas = tk.Canvas(preview_frame, bg="white")
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 滚动条
        v_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 幻灯片播放区域
        slideshow_frame = ttk.LabelFrame(main_frame, text="幻灯片播放", padding="10")
        slideshow_frame.grid(row=11, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0), pady=(0, 10))
        slideshow_frame.columnconfigure(0, weight=1)
        slideshow_frame.rowconfigure(0, weight=1)
        slideshow_frame.config(width=300)  # 设置幻灯片区域的固定宽度
        
        # 幻灯片Canvas，保持256x128像素大小
        self.slideshow_canvas = tk.Canvas(slideshow_frame, bg="black", width=256, height=128)
        self.slideshow_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 幻灯片控制按钮
        slideshow_control_frame = ttk.Frame(slideshow_frame)
        slideshow_control_frame.grid(row=1, column=0, pady=(5, 0))
        
        self.play_button = ttk.Button(slideshow_control_frame, text="播放", command=self.start_slideshow)
        self.play_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(slideshow_control_frame, text="停止", command=self.stop_slideshow, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 控制按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=12, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="刷新预览", command=self.refresh_preview).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="开始转换", command=self.convert_images).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="退出", command=self.root.quit).pack(side=tk.LEFT)
        
        # 添加激励按钮
        self.inspire_button = ttk.Button(main_frame, text="激励", command=self.show_inspire_image)
        self.inspire_button.grid(row=13, column=0, sticky=tk.SW, padx=(10, 0), pady=(10, 10))
        
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.image_folder.set(folder)
            
    def browse_output(self):
        file = filedialog.asksaveasfilename(
            defaultextension=".c",
            filetypes=[("C Files", "*.c"), ("All Files", "*.*")]
        )
        if file:
            self.output_file.set(file)
            
    def browse_video(self):
        file = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv"), ("All Files", "*.*")]
        )
        if file:
            self.video_file.set(file)
            
    def extract_frames_from_video(self):
        video_path = self.video_file.get()
        if not video_path:
            messagebox.showwarning("警告", "请选择视频文件")
            return
            
        output_folder = self.image_folder.get()
        if not output_folder:
            messagebox.showwarning("警告", "请选择图像输出文件夹")
            return
            
        frame_interval = self.video_frame_interval.get()
        if frame_interval <= 0:
            messagebox.showwarning("警告", "帧间隔必须大于0")
            return
            
        try:
            # 创建输出文件夹
            os.makedirs(output_folder, exist_ok=True)
            
            # 打开视频文件
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                messagebox.showerror("错误", "无法打开视频文件")
                return
                
            frame_count = 0
            saved_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # 每隔指定帧数保存一帧
                if frame_count % frame_interval == 0:
                    # 调整图像大小为128x64
                    resized_frame = cv2.resize(frame, (128, 64))
                    
                    # 保存图像
                    filename = f"frame_{saved_count:04d}.png"
                    filepath = os.path.join(output_folder, filename)
                    cv2.imwrite(filepath, resized_frame)
                    saved_count += 1
                    
                frame_count += 1
                
            cap.release()
            
            messagebox.showinfo("完成", f"成功从视频中提取 {saved_count} 帧图像到:\n{output_folder}")
            
            # 更新预览
            self.refresh_preview()
            
        except Exception as e:
            messagebox.showerror("错误", f"提取视频帧时发生错误:\n{str(e)}")
            
    def apply_brightness_contrast(self, image):
        # 应用亮度和对比度调整
        brightness = self.brightness.get()
        contrast = self.contrast.get()
        
        # 转换为浮点型进行计算
        img = image.astype(np.float32)
        
        # 应用对比度和亮度
        img = img * contrast + brightness
        
        # 截断到有效范围
        img = np.clip(img, 0, 255)
        
        # 转换回uint8
        return img.astype(np.uint8)
        
    def convert_to_bitmap(self, image):
        # 将图像转换为128x64的二值图像
        # 图像已经是128*64大小，不需要调整尺寸
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # 应用亮度和对比度调整
        adjusted = self.apply_brightness_contrast(gray)
        
        # 应用图像变换
        # 旋转
        if self.rotation.get() == "90":
            adjusted = cv2.rotate(adjusted, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation.get() == "180":
            adjusted = cv2.rotate(adjusted, cv2.ROTATE_180)
        elif self.rotation.get() == "270":
            adjusted = cv2.rotate(adjusted, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
        # 水平镜像
        if self.horizontal_flip.get():
            adjusted = cv2.flip(adjusted, 1)
            
        # 垂直镜像
        if self.vertical_flip.get():
            adjusted = cv2.flip(adjusted, 0)
            
        # 调整回128x64大小
        adjusted = cv2.resize(adjusted, (128, 64), interpolation=cv2.INTER_NEAREST)
        
        # 反色处理
        if self.invert_color.get():
            adjusted = 255 - adjusted
        
        # 转换为二值图像
        _, binary = cv2.threshold(adjusted, 127, 255, cv2.THRESH_BINARY)
        
        return binary
        
    def image_to_font_data(self, image):
        # 将图像转换为字模数据
        binary_img = self.convert_to_bitmap(image)
        
        font_data = []
        
        # 根据扫描方向和扫描顺序生成数据
        if self.scan_direction.get() == "vertical":
            # 垂直扫描方式
            if self.scan_order.get() == "left_to_right_top_to_bottom":
                # 先从左到右，再从上到下
                for j in range(8):  # 8页 (64行 / 8行每页)
                    for i in range(128):  # 128列
                        byte_val = 0
                        for bit in range(8):  # 每页8行
                            row = j * 8 + bit
                            col = i
                            if row < 64 and col < 128:
                                # 如果是黑色像素（值为0），则设置对应位为1
                                if binary_img[row, col] == 0:
                                    byte_val |= (1 << (7 - bit))  # 高位在前
                        font_data.append(byte_val)
            elif self.scan_order.get() == "top_to_bottom_left_to_right":
                # 先从上到下，再从左到右
                for j in range(8):  # 8页 (64行 / 8行每页)
                    for i in range(128):  # 128列
                        byte_val = 0
                        for bit in range(8):  # 每页8行
                            row = j * 8 + bit
                            col = i
                            if row < 64 and col < 128:
                                # 如果是黑色像素（值为0），则设置对应位为1
                                if binary_img[row, col] == 0:
                                    byte_val |= (1 << (7 - bit))  # 高位在前
                        font_data.append(byte_val)
            elif self.scan_order.get() == "right_to_left_top_to_bottom":
                # 先从右到左，再从上到下
                for j in range(8):  # 8页 (64行 / 8行每页)
                    for i in range(127, -1, -1):  # 128列，从右到左
                        byte_val = 0
                        for bit in range(8):  # 每页8行
                            row = j * 8 + bit
                            col = i
                            if row < 64 and col < 128:
                                # 如果是黑色像素（值为0），则设置对应位为1
                                if binary_img[row, col] == 0:
                                    byte_val |= (1 << (7 - bit))  # 高位在前
                        font_data.append(byte_val)
            elif self.scan_order.get() == "bottom_to_top_left_to_right":
                # 先从下到上，再从左到右
                for j in range(7, -1, -1):  # 8页，从下到上
                    for i in range(128):  # 128列
                        byte_val = 0
                        for bit in range(8):  # 每页8行
                            row = j * 8 + (7 - bit)  # 行号从下到上
                            col = i
                            if row < 64 and col < 128:
                                # 如果是黑色像素（值为0），则设置对应位为1
                                if binary_img[row, col] == 0:
                                    byte_val |= (1 << bit)  # 高位在前，但位顺序需要调整
                        font_data.append(byte_val)
            elif self.scan_order.get() == "left_to_right_bottom_to_top":
                # 先从左到右，再从下到上
                for j in range(7, -1, -1):  # 8页，从下到上
                    for i in range(128):  # 128列
                        byte_val = 0
                        for bit in range(8):  # 每页8行
                            row = j * 8 + bit  # 行号从下到上
                            col = i
                            if row < 64 and col < 128:
                                # 如果是黑色像素（值为0），则设置对应位为1
                                if binary_img[row, col] == 0:
                                    byte_val |= (1 << (7 - bit))  # 高位在前
                        font_data.append(byte_val)
            elif self.scan_order.get() == "right_to_left_bottom_to_top":
                # 先从右到左，再从下到上
                for j in range(7, -1, -1):  # 8页，从下到上
                    for i in range(127, -1, -1):  # 128列，从右到左
                        byte_val = 0
                        for bit in range(8):  # 每页8行
                            row = j * 8 + bit  # 行号从下到上
                            col = i
                            if row < 64 and col < 128:
                                # 如果是黑色像素（值为0），则设置对应位为1
                                if binary_img[row, col] == 0:
                                    byte_val |= (1 << (7 - bit))  # 高位在前
                        font_data.append(byte_val)
            elif self.scan_order.get() == "top_to_bottom_right_to_left":
                # 先从上到下，再从右到左
                for j in range(8):  # 8页 (64行 / 8行每页)
                    for i in range(127, -1, -1):  # 128列，从右到左
                        byte_val = 0
                        for bit in range(8):  # 每页8行
                            row = j * 8 + bit
                            col = i
                            if row < 64 and col < 128:
                                # 如果是黑色像素（值为0），则设置对应位为1
                                if binary_img[row, col] == 0:
                                    byte_val |= (1 << (7 - bit))  # 高位在前
                        font_data.append(byte_val)
            else:  # bottom_to_top_right_to_left
                # 先从下到上，再从右到左
                for j in range(7, -1, -1):  # 8页，从下到上
                    for i in range(127, -1, -1):  # 128列，从右到左
                        byte_val = 0
                        for bit in range(8):  # 每页8行
                            row = j * 8 + (7 - bit)  # 行号从下到上
                            col = i
                            if row < 64 and col < 128:
                                # 如果是黑色像素（值为0），则设置对应位为1
                                if binary_img[row, col] == 0:
                                    byte_val |= (1 << bit)  # 高位在前，但位顺序需要调整
                        font_data.append(byte_val)
        else:  # horizontal
            # 水平扫描方式
            if self.scan_order.get() == "left_to_right_top_to_bottom":
                # 先从左到右，再从上到下
                for row in range(64):
                    for col in range(128):
                        # 每8个水平像素组成一个字节
                        if col % 8 == 0:
                            byte_val = 0
                            for bit in range(8):
                                pixel_col = col + bit
                                if row < 64 and pixel_col < 128:
                                    # 如果是黑色像素（值为0），则设置对应位为1
                                    if binary_img[row, pixel_col] == 0:
                                        byte_val |= (1 << (7 - bit))  # 高位在前
                            font_data.append(byte_val)
            elif self.scan_order.get() == "top_to_bottom_left_to_right":
                # 先从上到下，再从左到右
                for col in range(128):
                    for row in range(64):
                        # 每8个垂直像素组成一个字节
                        if row % 8 == 0:
                            byte_val = 0
                            for bit in range(8):
                                pixel_row = row + bit
                                if pixel_row < 64 and col < 128:
                                    # 如果是黑色像素（值为0），则设置对应位为1
                                    if binary_img[pixel_row, col] == 0:
                                        byte_val |= (1 << (7 - bit))  # 高位在前
                            font_data.append(byte_val)
            elif self.scan_order.get() == "right_to_left_top_to_bottom":
                # 先从右到左，再从上到下
                for row in range(64):
                    for col in range(127, -1, -1):  # 从右到左
                        # 每8个水平像素组成一个字节
                        if (127 - col) % 8 == 0:
                            byte_val = 0
                            for bit in range(8):
                                pixel_col = col - bit
                                if row < 64 and pixel_col >= 0:
                                    # 如果是黑色像素（值为0），则设置对应位为1
                                    if binary_img[row, pixel_col] == 0:
                                        byte_val |= (1 << bit)  # 高位在前，但位顺序需要调整
                            font_data.append(byte_val)
            elif self.scan_order.get() == "bottom_to_top_left_to_right":
                # 先从下到上，再从左到右
                for col in range(128):
                    for row in range(63, -1, -1):  # 从下到上
                        # 每8个垂直像素组成一个字节
                        if (63 - row) % 8 == 0:
                            byte_val = 0
                            for bit in range(8):
                                pixel_row = row + bit
                                if pixel_row < 64 and col < 128:
                                    # 如果是黑色像素（值为0），则设置对应位为1
                                    if binary_img[pixel_row, col] == 0:
                                        byte_val |= (1 << (7 - bit))  # 高位在前
                            font_data.append(byte_val)
            elif self.scan_order.get() == "left_to_right_bottom_to_top":
                # 先从左到右，再从下到上
                for row in range(63, -1, -1):  # 从下到上
                    for col in range(128):
                        # 每8个水平像素组成一个字节
                        if col % 8 == 0:
                            byte_val = 0
                            for bit in range(8):
                                pixel_col = col + bit
                                if row >= 0 and pixel_col < 128:
                                    # 如果是黑色像素（值为0），则设置对应位为1
                                    if binary_img[row, pixel_col] == 0:
                                        byte_val |= (1 << (7 - bit))  # 高位在前
                            font_data.append(byte_val)
            elif self.scan_order.get() == "right_to_left_bottom_to_top":
                # 先从右到左，再从下到上
                for row in range(63, -1, -1):  # 从下到上
                    for col in range(127, -1, -1):  # 从右到左
                        # 每8个水平像素组成一个字节
                        if (127 - col) % 8 == 0:
                            byte_val = 0
                            for bit in range(8):
                                pixel_col = col - bit
                                if row >= 0 and pixel_col >= 0:
                                    # 如果是黑色像素（값为0），则设置对应位为1
                                    if binary_img[row, pixel_col] == 0:
                                        byte_val |= (1 << bit)  # 高位在前，但位顺序需要调整
                            font_data.append(byte_val)
            elif self.scan_order.get() == "top_to_bottom_right_to_left":
                # 先从上到下，再从右到左
                for col in range(127, -1, -1):  # 从右到左
                    for row in range(64):
                        # 每8个垂直像素组成一个字节
                        if row % 8 == 0:
                            byte_val = 0
                            for bit in range(8):
                                pixel_row = row + bit
                                if pixel_row < 64 and col >= 0:
                                    # 如果是黑色像素（값为0），则设置对应位为1
                                    if binary_img[pixel_row, col] == 0:
                                        byte_val |= (1 << (7 - bit))  # 高位在前
                            font_data.append(byte_val)
            else:  # bottom_to_top_right_to_left
                # 先从下到上，再从右到左
                for col in range(127, -1, -1):  # 从右到左
                    for row in range(63, -1, -1):  # 从下到上
                        # 每8个垂直像素组成一个字节
                        if (63 - row) % 8 == 0:
                            byte_val = 0
                            for bit in range(8):
                                pixel_row = row + bit
                                if pixel_row < 64 and col >= 0:
                                    # 만약 검은색 픽셀(값이 0)이면 해당 비트를 1로 설정
                                    if binary_img[pixel_row, col] == 0:
                                        byte_val |= (1 << (7 - bit))  # 고위가 앞쪽
                            font_data.append(byte_val)
                
        return font_data
        
    def update_preview(self, event=None):
        # 更新参数标签
        self.brightness_label.config(text=f"{self.brightness.get():.0f}")
        self.contrast_label.config(text=f"{self.contrast.get():.2f}")
        
        # 更新预览图像
        self.refresh_preview()
            
    def refresh_preview(self):
        folder = self.image_folder.get()
        if not folder:
            messagebox.showwarning("警告", "请先选择图像文件夹")
            return
            
        # 获取文件夹中的图片
        image_files = glob.glob(os.path.join(folder, "*.png")) + \
                     glob.glob(os.path.join(folder, "*.jpg")) + \
                     glob.glob(os.path.join(folder, "*.jpeg")) + \
                     glob.glob(os.path.join(folder, "*.bmp"))
                     
        if not image_files:
            messagebox.showwarning("警告", "所选文件夹中没有找到图像文件")
            return
            
        # 显示所有图片的预览
        self.show_all_images_preview(image_files)
        
        # 更新幻灯片
        self.update_slideshow(image_files)
            
    def show_all_images_preview(self, image_files):
        # 清除之前的预览
        self.canvas.delete("all")
        
        # 创建一个Frame来容纳所有预览图像
        frame = tk.Frame(self.canvas, bg="white")
        self.canvas.create_window((0, 0), window=frame, anchor="nw")
        
        # 显示所有图片
        images_per_row = 4
        preview_size = (128, 64)
        
        self.preview_images = []
        for i, img_path in enumerate(image_files[:16]):  # 限制最多显示16张图片
            try:
                # 读取图像
                image = cv2.imread(img_path)
                if image is None:
                    continue
                    
                # 检查图像尺寸
                h, w = image.shape[:2]
                if h != 64 or w != 128:
                    continue
                    
                # 处理图像
                processed = self.convert_to_bitmap(image)
                
                # 转换为RGB格式以便在tkinter中显示
                rgb_image = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
                
                # 转换为tkinter可用格式
                from PIL import Image, ImageTk
                pil_image = Image.fromarray(rgb_image)
                tk_image = ImageTk.PhotoImage(pil_image)
                self.preview_images.append(tk_image)  # 保持引用防止被垃圾回收
                
                # 计算位置
                row = i // images_per_row
                col = i % images_per_row
                
                # 创建图像标签
                label_frame = tk.Frame(frame, relief=tk.RAISED, bd=2)
                label_frame.grid(row=row*2, column=col, padx=5, pady=5)
                
                # 显示图像
                img_label = tk.Label(label_frame, image=tk_image, bg="white")
                img_label.pack()
                
                # 显示文件名
                filename = os.path.basename(img_path)
                name_label = tk.Label(label_frame, text=filename, bg="white")
                name_label.pack()
                
            except Exception as e:
                print(f"无法加载图像 {img_path}: {e}")
        
        # 更新滚动区域
        frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
    def update_slideshow(self, image_files):
        # 更新幻灯片图像列表
        self.slideshow_images = []
        for img_path in image_files:
            try:
                # 读取图像
                image = cv2.imread(img_path)
                if image is None:
                    continue
                    
                # 检查图像尺寸
                h, w = image.shape[:2]
                if h != 64 or w != 128:
                    continue
                    
                # 处理图像
                processed = self.convert_to_bitmap(image)
                
                # 转换为RGB格式以便在tkinter中显示
                rgb_image = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
                
                # 转换为tkinter可用格式，放大到256x128
                from PIL import Image, ImageTk
                pil_image = Image.fromarray(rgb_image)
                pil_image = pil_image.resize((256, 128), Image.LANCZOS)
                tk_image = ImageTk.PhotoImage(pil_image)
                self.slideshow_images.append(tk_image)  # 保持引用防止被垃圾回收
            except Exception as e:
                print(f"无法加载幻灯片图像 {img_path}: {e}")
        
        # 显示第一张图像
        self.slideshow_index = 0
        if self.slideshow_images:
            self.slideshow_canvas.delete("all")
            self.slideshow_canvas.create_image(
                self.slideshow_canvas.winfo_width() // 2,
                self.slideshow_canvas.winfo_height() // 2,
                anchor=tk.CENTER,
                image=self.slideshow_images[0]
            )
        
    def show_processed_image(self):
        if not hasattr(self, 'preview_image') or self.preview_image is None:
            return
            
        # 处理图像
        processed = self.convert_to_bitmap(self.preview_image)
        
        # 转换为RGB格式以便在tkinter中显示
        rgb_image = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
        
        # 转换为tkinter可用格式
        from PIL import Image, ImageTk
        pil_image = Image.fromarray(rgb_image)
        self.tk_image = ImageTk.PhotoImage(pil_image)
        
        # 在canvas中显示
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        
    def start_slideshow(self):
        if not self.slideshow_images:
            messagebox.showwarning("警告", "没有可播放的图像")
            return
            
        self.slideshow_running = True
        self.play_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.slideshow()
        
    def stop_slideshow(self):
        self.slideshow_running = False
        if self.slideshow_job:
            self.slideshow_canvas.after_cancel(self.slideshow_job)
        self.play_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
    def slideshow(self):
        if not self.slideshow_running:
            return
            
        if self.slideshow_images:
            # 显示当前图像
            self.slideshow_canvas.delete("all")
            self.slideshow_canvas.create_image(
                self.slideshow_canvas.winfo_width() // 2,
                self.slideshow_canvas.winfo_height() // 2,
                anchor=tk.CENTER,
                image=self.slideshow_images[self.slideshow_index]
            )
            
            # 更新索引
            self.slideshow_index = (self.slideshow_index + 1) % len(self.slideshow_images)
            
        # 设置下次更新
        self.slideshow_job = self.slideshow_canvas.after(self.slideshow_interval.get(), self.slideshow)
        
    def convert_images(self):
        folder = self.image_folder.get()
        output = self.output_file.get()
        
        if not folder:
            messagebox.showwarning("警告", "请选择图像文件夹")
            return
            
        if not output:
            messagebox.showwarning("警告", "请选择输出文件")
            return
            
        # 查找所有图像文件
        image_files = glob.glob(os.path.join(folder, "*.png")) + \
                     glob.glob(os.path.join(folder, "*.jpg")) + \
                     glob.glob(os.path.join(folder, "*.jpeg")) + \
                     glob.glob(os.path.join(folder, "*.bmp"))
                     
        if not image_files:
            messagebox.showwarning("警告", "所选文件夹中没有找到图像文件")
            return
            
        # 检查所有图像尺寸
        for img_path in image_files:
            image = cv2.imread(img_path)
            if image is not None:
                h, w = image.shape[:2]
                if h != 64 or w != 128:
                    messagebox.showwarning("警告", f"图像 {os.path.basename(img_path)} 尺寸应为128*64，当前尺寸为{w}*{h}")
            
        # 写入输出文件
        try:
            # 生成.c文件
            with open(output, 'w', encoding='utf-8') as f:
                f.write("// 字模数据文件\n")
                f.write("#include <stdint.h>\n\n")
                
                for i, img_path in enumerate(image_files):
                    # 读取图像
                    image = cv2.imread(img_path)
                    if image is None:
                        continue
                        
                    # 检查图像尺寸
                    h, w = image.shape[:2]
                    if h != 64 or w != 128:
                        continue
                        
                    # 转换为字模数据
                    font_data = self.image_to_font_data(image)
                    
                    # 生成数组名: IMG_DATA1, IMG_DATA2, ...
                    array_name = f"IMG_DATA{i+1}"
                    
                    # 写入数组
                    f.write(f"const uint8_t {array_name}[] = {{ ")
                    for j, byte_val in enumerate(font_data):
                        if j % 16 == 0 and j > 0:
                            f.write("\n  ")
                        f.write(f"0x{byte_val:02X}")
                        if j < len(font_data) - 1:
                            f.write(",")
                    f.write("\n};\n\n")
                    
                # 添加gif函数
                slideshow_interval = self.slideshow_interval.get()
                f.write("void gif(void) {\n")
                for i in range(len(image_files)):
                    array_name = f"IMG_DATA{i+1}"
                    f.write(f"    OLED_ShowImage(0,0,128,64,{array_name});OLED_Update();delay_1ms({slideshow_interval});OLED_Clear();\n")
                f.write("}\n")
                    
            # 生成.h文件
            header_file = output.replace('.c', '.h') if output.endswith('.c') else output + '.h'
            with open(header_file, 'w', encoding='utf-8') as f:
                # 获取文件名作为保护宏的一部分
                header_filename = os.path.basename(header_file)
                header_name_upper = ''.join(c.upper() if c.isalnum() else '_' for c in header_filename)
                protect_macro = f"__{header_name_upper}"
                
                f.write(f"#ifndef {protect_macro}\n")
                f.write(f"#define {protect_macro}\n\n")
                f.write("#include <stdint.h>\n\n")
                
                # 写入外部声明
                for i in range(len(image_files)):
                    array_name = f"IMG_DATA{i+1}"
                    f.write(f"extern const uint8_t {array_name}[];\n")
                    
                # 补充额外的声明到25个
                for i in range(len(image_files), 25):
                    array_name = f"IMG_DATA{i+1}"
                    f.write(f"extern const uint8_t {array_name}[];\n")
                    
                # 添加gif函数声明
                f.write("\nextern void gif(void);\n")
                    
                f.write(f"\n#endif // {protect_macro}\n")
                    
            messagebox.showinfo("完成", f"成功转换 {len(image_files)} 个图像文件\n生成文件:\n{output}\n{header_file}")
        except Exception as e:
            messagebox.showerror("错误", f"转换过程中发生错误:\n{str(e)}")

    def show_inspire_image(self):
        # 加载并显示激励图片，优先从内嵌 resources 加载，回退到磁盘文件
        img_path = "jili.jpg"  # 默认磁盘文件名
        from PIL import Image, ImageTk

        try:
            pil_image = None

            # 先尝试磁盘路径
            if os.path.exists(img_path):
                pil_image = Image.open(img_path)

            # 如果磁盘没有，尝试从 resources 中读取
            if pil_image is None and resources is not None and hasattr(resources, 'get'):
                data = resources.get('jili.jpg') or resources.get('jili.png')
                if data:
                    pil_image = Image.open(io.BytesIO(data))

            if pil_image is None:
                raise FileNotFoundError('激励图片未找到（磁盘或内嵌资源中均无）')

            # 转换为tkinter可用格式
            tk_image = ImageTk.PhotoImage(pil_image)

            # 创建新的窗口
            inspire_window = tk.Toplevel(self.root)
            inspire_window.title("谢谢您的激励！")
            inspire_window.geometry(f"{pil_image.width}x{pil_image.height}")  # 设置窗口大小为图片尺寸

            # 在新窗口中显示图像
            canvas = tk.Canvas(inspire_window, bg="white", width=pil_image.width, height=pil_image.height)
            canvas.pack(fill=tk.BOTH, expand=True)

            # 显示图像
            canvas.create_image(
                pil_image.width // 2,
                pil_image.height // 2,
                anchor=tk.CENTER,
                image=tk_image
            )

            # 保持引用防止被垃圾回收
            canvas.image = tk_image

            # 禁止调整窗口大小
            inspire_window.resizable(False, False)

        except Exception as e:
            messagebox.showwarning("警告", f"无法加载激励图片: {e}")

def main():
    root = tk.Tk()
    app = ImageToFontConverter(root)
    root.mainloop()


if __name__ == "__main__":
    main()