import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import cv2
import os
import time
import logging
from datetime import datetime

# ==========================================
# 初始化全局日志系统
# ==========================================
log_filename = f"pintest_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MainUI")

# 引入已解耦的核心模块
from camera_manager import OptCamera
from vision_engine import VisionEngine

# ==========================================
# 自定义 UI 组件
# ==========================================

class ScrollableFrame(ttk.Frame):
    """支持鼠标滚轮和滚动条的容器面板"""
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg="#2E2E2E", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # 保证内部 frame 宽度跟随 canvas 变化
        self.canvas.bind(
            '<Configure>', 
            lambda e: self.canvas.itemconfig(self.window_id, width=e.width)
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def update_scroll_bindings(self):
        """递归绑定鼠标滚轮事件到所有子组件，以确保在控件上滚动不失效"""
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def bind_tree(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                bind_tree(child)
                
        bind_tree(self.canvas)

class SlideSwitch(tk.Canvas):
    def __init__(self, master, command=None, width=40, height=22, bg="#2E2E2E", **kwargs):
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0, **kwargs)
        self.state = False
        self.command = command
        self.width = width
        self.height = height
        self.rect = self.create_round_rect(2, 2, width-2, height-2, radius=10, fill="#777", outline="#777", tags="bg")
        self.knob = self.create_oval(4, 4, height-4, height-4, fill="white", outline="white", tags="knob")
        self.bind("<Button-1>", self.toggle)
        self.tag_bind("bg", "<Button-1>", self.toggle)
        self.tag_bind("knob", "<Button-1>", self.toggle)

    def create_round_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius,
                  x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2,
                  x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius,
                  x1, y1+radius, x1, y1]
        return self.create_polygon(points, smooth=True, **kwargs)

    def toggle(self, event=None, force_state=None):
        if force_state is not None: self.state = force_state
        else: self.state = not self.state
        fill_color = "#4CAF50" if self.state else "#777"
        self.itemconfig(self.rect, fill=fill_color, outline=fill_color)
        move_x = self.width - self.height if self.state else 4
        self.coords(self.knob, move_x, 4, move_x + self.height - 8, self.height - 4)
        if self.command and force_state is None: self.command(self.state)

    def set_state(self, state): self.toggle(force_state=state)

class ZoomableCanvas(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs, highlightthickness=0)
        self.bind("<MouseWheel>", self.on_zoom)
        self.bind("<ButtonPress-3>", self.on_pan_start)
        self.bind("<B3-Motion>", self.on_pan_drag)
        self.bind("<Configure>", self.on_resize)
        
        self.org_image_pil = None 
        self.tk_image = None      
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self._pan_start = None

    def load_image(self, cv_img):
        if cv_img is None: return
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2RGB) if len(cv_img.shape) == 2 else cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        self.org_image_pil = Image.fromarray(cv_img)
        self._reset_view()
        self.redraw()

    def swap_image(self, cv_img):
        if cv_img is None: return
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2RGB) if len(cv_img.shape) == 2 else cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        self.org_image_pil = Image.fromarray(cv_img)
        self.redraw()

    def _reset_view(self):
        cw, ch = self.winfo_width(), self.winfo_height()
        if not self.org_image_pil: return
        iw, ih = self.org_image_pil.size
        if cw > 0 and ch > 0:
            self.scale = min(cw/iw, ch/ih) * 0.9
            self.offset_x = (cw - iw * self.scale) / 2
            self.offset_y = (ch - ih * self.scale) / 2

    def redraw(self):
        if self.org_image_pil is None: return
        cw, ch = self.winfo_width(), self.winfo_height()
        x1 = max(0, int(-self.offset_x / self.scale))
        y1 = max(0, int(-self.offset_y / self.scale))
        iw, ih = self.org_image_pil.size
        x2 = min(iw, int((cw - self.offset_x) / self.scale) + 1)
        y2 = min(ih, int((ch - self.offset_y) / self.scale) + 1)
        
        if x2 <= x1 or y2 <= y1:
            self.delete("img_bg")
            return

        region = self.org_image_pil.crop((x1, y1, x2, y2))
        disp_w, disp_h = int((x2 - x1) * self.scale), int((y2 - y1) * self.scale)
        if disp_w <= 0 or disp_h <= 0: return
        
        self.tk_image = ImageTk.PhotoImage(region.resize((disp_w, disp_h), Image.NEAREST))
        self.delete("img_bg")
        self.create_image(x1 * self.scale + self.offset_x, y1 * self.scale + self.offset_y, image=self.tk_image, anchor="nw", tags="img_bg")
        self.tag_lower("img_bg")

    def on_zoom(self, event):
        if self.org_image_pil is None: return
        factor = 1.1 if event.delta > 0 else 0.9
        mouse_img_x = (event.x - self.offset_x) / self.scale
        mouse_img_y = (event.y - self.offset_y) / self.scale
        self.scale *= factor
        self.offset_x = event.x - mouse_img_x * self.scale
        self.offset_y = event.y - mouse_img_y * self.scale
        self.redraw()
        self.event_generate("<<ViewChanged>>")

    def on_pan_start(self, event): self._pan_start = (event.x, event.y)
    def on_pan_drag(self, event):
        if not self._pan_start: return
        self.offset_x += event.x - self._pan_start[0]
        self.offset_y += event.y - self._pan_start[1]
        self._pan_start = (event.x, event.y)
        self.redraw()
        self.event_generate("<<ViewChanged>>")
        
    def on_resize(self, event): self.redraw(); self.event_generate("<<ViewChanged>>")
    def img2canvas(self, ix, iy): return ix * self.scale + self.offset_x, iy * self.scale + self.offset_y
    def canvas2img(self, cx, cy): return int((cx - self.offset_x) / self.scale), int((cy - self.offset_y) / self.scale)


# ==========================================
# 主界面类
# ==========================================
class ModernUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.engine = VisionEngine()
        logger.info("启动应用，引擎模块已加载")
        self.title("Pin针偏位度检测(OPT)")
        self.geometry("1400x950")
        self.configure(bg="#2E2E2E")
        self._init_styles()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.cap = None
        self.is_live = False
        self.latest_frame = None
        
        self.auto_trigger_on = False
        self.last_check_time = 0
        self.preview_live = True 
        self.trigger_waiting = False
        self.trigger_cooldown = False

        self.cv_img = None
        self.draw_mode = None
        self.rect_start = None
        self.temp_rect_id = None
        
        self.tmpl_boxes = {'frame_1': [], 'pin_1': [], 'frame_2': [], 'pin_2': []}
        self.mark_boxes = []
        
        self.test_img_list = []
        self.curr_idx = -1
        self.test_rois = []
        
        self.var_preview_mode = tk.BooleanVar(value=False)
        self.var_dist_thresh = tk.DoubleVar(value=50.0)
        self.var_pixel_size = tk.DoubleVar(value=5.0)
        
        self.var_save_path = tk.StringVar(value="")
        self.var_task_order = tk.StringVar(value="")
        self.var_emp_id = tk.StringVar(value="")
        self.current_sn = ""
        self.sn_window = None

        # --- 新增统计变量 ---
        self.stats_task_order = ""
        self.stats_ok_count = 0
        self.stats_ng_count = 0
        self.stats_total_count = 0

        self._init_layout()
        self.canvas.bind("<<ViewChanged>>", self.redraw_overlays)
        self.bind('<Return>', self.capture_image)

    def _init_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#2E2E2E")
        self.style.configure("TLabel", background="#2E2E2E", foreground="white")
        self.style.configure("TButton", background="#4A4A4A", foreground="white")
        self.style.configure("TNotebook", background="#2E2E2E", borderwidth=0)
        self.style.configure("TLabelframe", background="#2E2E2E", foreground="white")
        self.style.configure("TLabelframe.Label", background="#2E2E2E", foreground="#AAA")

    def _init_layout(self):
        sidebar_container = ttk.Frame(self, width=320)
        sidebar_container.pack(side="left", fill="y", padx=5, pady=5)
        
        cam_frame = ttk.LabelFrame(sidebar_container, text="📷 相机控制")
        cam_frame.pack(side="top", fill="x", pady=(0, 10))
        self.btn_cam = ttk.Button(cam_frame, text="打开相机", command=self.toggle_camera)
        self.btn_cam.pack(fill="x", padx=5, pady=2)
        ttk.Button(cam_frame, text="手动取图 (Enter)", command=self.capture_image).pack(fill="x", padx=5, pady=2)
        
        self.sidebar = ttk.Notebook(sidebar_container)
        self.sidebar.pack(fill="both", expand=True)
        
        # 将原有直接绑定的 frame 替换为 ScrollableFrame 容器
        self.tab_template = ScrollableFrame(self.sidebar)
        self.sidebar.add(self.tab_template, text="1. 双模板制作")
        self._init_tab_template(self.tab_template.scrollable_frame)
        
        self.tab_detect = ScrollableFrame(self.sidebar)
        self.sidebar.add(self.tab_detect, text="2. 批量检测")
        self._init_tab_detect(self.tab_detect.scrollable_frame)
        
        self.sidebar.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # 初始化滚动事件绑定
        self.after(100, lambda: self.tab_template.update_scroll_bindings())
        self.after(100, lambda: self.tab_detect.update_scroll_bindings())

        # --- 修改底部状态栏布局 ---
        self.status_bar_frame = ttk.Frame(self)
        self.status_bar_frame.pack(side="bottom", fill="x", padx=10, pady=5)
        
        # 左侧保留原有的提示信息
        self.lbl_status = ttk.Label(self.status_bar_frame, text="就绪", wraplength=800, font=("Segoe UI", 11, "bold"))
        self.lbl_status.pack(side="left", fill="x", expand=True)

        # 右侧新增专属的统计信息显示栏
        self.lbl_stats = ttk.Label(self.status_bar_frame, text="统计: 暂无数据", font=("Segoe UI", 11, "bold"), foreground="#4CAF50")
        self.lbl_stats.pack(side="right", padx=(10, 0))

        self.canvas = ZoomableCanvas(self, bg="#1E1E1E")
        self.canvas.pack(side="right", fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_down)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_up)

    def _init_tab_template(self, p):
        f = ttk.Frame(p); f.pack(fill="x", padx=10, pady=10)
        ttk.Button(f, text="📂 加载标准图", command=self.load_img_template).pack(fill="x")
        ttk.Separator(f).pack(fill="x", pady=10)
        
        lf1 = ttk.LabelFrame(f, text=" 模板 1 (蓝色/绿色) "); lf1.pack(fill="x", pady=5)
        ttk.Button(lf1, text="🖊️ 画基准框 [1]", command=lambda: self.set_mode('frame_1')).pack(fill="x", pady=2)
        ttk.Button(lf1, text="🖊️ 画Pin区域 [1]", command=lambda: self.set_mode('pin_1')).pack(fill="x", pady=2)
        
        lf2 = ttk.LabelFrame(f, text=" 模板 2 (橙色/黄色) "); lf2.pack(fill="x", pady=5)
        ttk.Button(lf2, text="🖊️ 画基准框 [2]", command=lambda: self.set_mode('frame_2')).pack(fill="x", pady=2)
        ttk.Button(lf2, text="🖊️ 画Pin区域 [2]", command=lambda: self.set_mode('pin_2')).pack(fill="x", pady=2)
        
        lf3 = ttk.LabelFrame(f, text=" 定位与矫正 (Mark点) "); lf3.pack(fill="x", pady=5)
        ttk.Button(lf3, text="🖊️ 绘制Mark点", command=lambda: self.set_mode('mark')).pack(fill="x", pady=2)
        ttk.Button(lf3, text="🗑️ 删除上一个Mark", command=self.delete_last_mark).pack(fill="x", pady=2)
        
        ttk.Button(f, text="🗑️ 清除所有画框", command=self.clear_tmpl_boxes).pack(fill="x", pady=10)
        
        ttk.Label(f, text="参数设置:").pack(anchor="w")
        self.s_min = tk.Scale(f, from_=0, to=255, orient="h", label="Min Thresh", bg="#2E2E2E", fg="white", command=self.upd_view); self.s_min.set(80); self.s_min.pack(fill="x")
        self.s_max = tk.Scale(f, from_=0, to=255, orient="h", label="Max Thresh", bg="#2E2E2E", fg="white", command=self.upd_view); self.s_max.set(255); self.s_max.pack(fill="x")
        self.s_area = tk.Scale(f, from_=1, to=100, orient="h", label="Min Area", bg="#2E2E2E", fg="white"); self.s_area.set(10); self.s_area.pack(fill="x")
        
        ttk.Checkbutton(f, text="二值化预览", variable=self.var_preview_mode, command=self.upd_view).pack(fill="x", pady=5)
        ttk.Button(f, text="⚡ 生成双模板预览", command=self.analyze_template).pack(fill="x", pady=5)
        ttk.Button(f, text="💾 保存模板文件", command=self.save_template).pack(fill="x", pady=5)

    def _init_tab_detect(self, p):
        f = ttk.Frame(p); f.pack(fill="x", padx=10, pady=10)
        ttk.Button(f, text="📂 加载模板文件", command=self.load_template_file).pack(fill="x")
        ttk.Button(f, text="📂 加载测试文件夹", command=self.load_test_folder).pack(fill="x", pady=5)
        
        nav = ttk.Frame(f); nav.pack(fill="x")
        ttk.Button(nav, text="< 上张", width=8, command=self.prev_img).pack(side="left")
        self.lbl_idx = ttk.Label(nav, text="0/0"); self.lbl_idx.pack(side="left", expand=True)
        ttk.Button(nav, text="下张 >", width=8, command=self.next_img).pack(side="right")
        
        ttk.Separator(f).pack(fill="x", pady=10)
        
        # --- 数据存储与任务令设置 ---
        path_lf = ttk.LabelFrame(f, text=" 检测数据存储设置 ")
        path_lf.pack(fill="x", pady=5)
        
        task_emp_frame = ttk.Frame(path_lf)
        task_emp_frame.pack(fill="x", padx=5, pady=(5, 2))
        
        ttk.Label(task_emp_frame, text="任务令:").pack(side="left")
        ttk.Entry(task_emp_frame, textvariable=self.var_task_order, width=12).pack(side="left", padx=(2, 10))
        
        ttk.Label(task_emp_frame, text="测试员工号:").pack(side="left")
        ttk.Entry(task_emp_frame, textvariable=self.var_emp_id, width=10).pack(side="left", padx=(2, 0))

        ttk.Button(path_lf, text="📁 设置根保存路径", command=self.select_save_path).pack(fill="x", padx=5, pady=2)
        ttk.Label(path_lf, textvariable=self.var_save_path, foreground="#AAA").pack(fill="x", padx=5, pady=(0,5))
        
        # --- 扫码触发检测 ---
        sn_lf = ttk.LabelFrame(f, text=" 扫码触发检测 (SN输入) ")
        sn_lf.pack(fill="x", pady=5)
        ttk.Button(sn_lf, text="🔍 扫码枪输入 SN (弹窗)", command=self.open_sn_dialog).pack(fill="x", padx=5, pady=5)

        ttk.Separator(f).pack(fill="x", pady=10)
        
        auto_lf = ttk.LabelFrame(f, text=" 自动触发检测 (需Mark点) ")
        auto_lf.pack(fill="x", pady=5)
        
        auto_row = ttk.Frame(auto_lf)
        auto_row.pack(fill="x", padx=5, pady=5)
        ttk.Label(auto_row, text="开启自动检测:").pack(side="left")
        self.switch_auto = SlideSwitch(auto_row, command=self.on_auto_switch)
        self.switch_auto.pack(side="right", padx=5)
        
        self.var_delay = tk.DoubleVar(value=0.5)
        tk.Scale(auto_lf, from_=0, to=10, resolution=0.1, orient="h", label="匹配后延迟触发 (0-10s)", variable=self.var_delay, bg="#2E2E2E", fg="white").pack(fill="x", padx=5, pady=2)
        
        self.var_mark_exp = tk.IntVar(value=20)
        tk.Scale(auto_lf, from_=0, to=100, orient="h", label="Mark点搜索范围外扩 (0-100%)", variable=self.var_mark_exp, bg="#2E2E2E", fg="white").pack(fill="x", padx=5, pady=2)
        
        ttk.Separator(f).pack(fill="x", pady=10)
        
        ttk.Label(f, text="检测画框:", font=("",10,"bold")).pack(anchor="w")
        ttk.Button(f, text="📥 加载模板1检测框", command=lambda: self.load_tmpl_roi('1')).pack(fill="x", pady=2)
        ttk.Button(f, text="📥 加载模板2检测框", command=lambda: self.load_tmpl_roi('2')).pack(fill="x", pady=2)
        ttk.Button(f, text="🖊️ 画待测区 (用模板1检测)", command=lambda: self.set_mode('test_roi_1')).pack(fill="x", pady=2)
        ttk.Button(f, text="🖊️ 画待测区 (用模板2检测)", command=lambda: self.set_mode('test_roi_2')).pack(fill="x", pady=2)
        ttk.Button(f, text="🗑️ 清除当前框", command=self.clear_test_boxes).pack(fill="x", pady=5)
        
        ttk.Separator(f).pack(fill="x", pady=10)
        
        param_f = ttk.Frame(f)
        param_f.pack(fill="x", pady=10)
        
        # 偏移合格阈值输入框
        dist_f = ttk.Frame(param_f)
        dist_f.pack(side="left", padx=(0, 10))
        ttk.Label(dist_f, text="偏移合格阈值(um):").pack(side="left")
        ttk.Entry(dist_f, textvariable=self.var_dist_thresh, width=6).pack(side="left", padx=(2,0))
        
        # 单像素物理距离输入框
        px_f = ttk.Frame(param_f)
        px_f.pack(side="left")
        ttk.Label(px_f, text="单像素距离(um):").pack(side="left")
        ttk.Entry(px_f, textvariable=self.var_pixel_size, width=6).pack(side="left", padx=(2,0))

        ttk.Button(f, text="🔍 开始手动检测", command=self.run_detection).pack(fill="x", pady=15)

    def toggle_camera(self):
        if not self.is_live:
            try:
                logger.info("尝试打开相机...")
                self.cap = OptCamera()
            except Exception as e:
                logger.error(f"相机连接异常: {e}")
                messagebox.showerror("相机连接失败", str(e))
                return
                
            if not self.cap.isOpened():
                logger.error("相机连接失败")
                messagebox.showerror("相机错误", "无法连接到 OPT 相机！\n请检查设备连接或 SDK 驱动是否正常。")
                return
                
            self.is_live = True
            self.preview_live = True
            self.btn_cam.config(text="关闭相机/恢复实时")
            self.update_camera()
        else:
            if not self.preview_live:
                logger.info("恢复相机实时预览")
                self.preview_live = True
                self.lbl_status.config(text="已恢复实时预览")
                self.engine.detect_results = []
                self.redraw_overlays()
            else:
                logger.info("关闭相机")
                self.is_live = False
                if self.cap: self.cap.release()
                self.btn_cam.config(text="打开相机")
                self.lbl_status.config(text="相机已关闭")

    def update_camera(self):
        if self.is_live and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.latest_frame = frame
                
                if self.auto_trigger_on and self.engine.marks:
                    now = time.time()
                    if now - self.last_check_time >= 1.0:
                        self.last_check_time = now
                        
                        if not self.trigger_waiting and not self.trigger_cooldown:
                            matched, offset = self.engine.match_marks(frame, self.var_mark_exp.get())
                            if matched:
                                logger.info(f"Mark点匹配成功，偏移量：{offset}")
                                self.trigger_waiting = True
                                delay_ms = int(self.var_delay.get() * 1000)
                                self.lbl_status.config(text=f"匹配到Mark，偏移 {offset}，延迟 {delay_ms/1000.0}秒后检测...")
                                self.after(delay_ms, lambda offset=offset: self.do_auto_trigger(offset))
                                
                        elif self.trigger_cooldown:
                            matched, _ = self.engine.match_marks(frame, self.var_mark_exp.get())
                            if not matched: 
                                logger.info("工件已移出视野，重置自动触发状态")
                                self.trigger_cooldown = False
                                self.preview_live = True
                                self.engine.detect_results = []
                                self.lbl_status.config(text="自动触发已重置，等待新工件进入...")
                
                if self.preview_live:
                    self.cv_img = frame.copy()
                    self.canvas.swap_image(self.cv_img)
                    
        self.after(30, self.update_camera)

    def do_auto_trigger(self, initial_offset):
        if not self.auto_trigger_on:
            self.trigger_waiting = False
            return
            
        self.capture_image()
        if self.cv_img is not None:
            matched, final_offset = self.engine.match_marks(self.cv_img, self.var_mark_exp.get())
            offset_to_use = final_offset if matched else initial_offset
            logger.info(f"执行自动触发检测，最终偏移量: {offset_to_use}")
            self.run_detection(offset=offset_to_use)
            self.lbl_status.config(text="检测完成，画面已锁定，请等待工件移出视野以重置...")
            
        self.trigger_waiting = False
        self.trigger_cooldown = True

    def capture_image(self, event=None, skip_detect=False):
        if self.latest_frame is None:
            messagebox.showwarning("提示", "当前没有图像，请先加载图片或打开相机")
            return
            
        self.cv_img = self.latest_frame.copy()
        if self.is_live: self.preview_live = False
            
        self.canvas.load_image(self.cv_img)
        self.redraw_overlays()
        if not self.auto_trigger_on:
            logger.info("用户手动截取图像")
            self.lbl_status.config(text="已手动取图，预览画面已锁定（点击相机按钮恢复）。")

        if self.sidebar.index("current") == 1 and not self.auto_trigger_on and not skip_detect:
            self.run_detection()

    # ==========================================
    # SN扫描与自动图片保存控制逻辑 (基于任务令)
    # ==========================================
    def select_save_path(self):
        path = filedialog.askdirectory(title="选择检测图片保存根路径")
        if path:
            self.var_save_path.set(path)
            logger.info(f"图片自动保存根路径已设置为: {path}")

    def open_sn_dialog(self):
        if not self.test_rois:
            messagebox.showwarning("警告", "请先绘制或加载待测区，再开启扫码检测！")
            return

        if self.sn_window and self.sn_window.winfo_exists():
            self.sn_window.focus_set()
            return

        self.sn_window = tk.Toplevel(self)
        self.sn_window.title("SN扫码输入")
        self.sn_window.geometry("400x130")
        self.sn_window.attributes("-topmost", True)
        self.sn_window.transient(self) 

        ttk.Label(self.sn_window, text="请使用扫码枪扫描SN (自动回车触发):", font=("Segoe UI", 11)).pack(pady=10)
        self.sn_entry = ttk.Entry(self.sn_window, font=("Segoe UI", 14))
        self.sn_entry.pack(fill="x", padx=20, pady=5)
        self.sn_entry.focus_set()
        
        self.sn_entry.bind('<Return>', self.on_sn_entered)

    def on_sn_entered(self, event):
        self.current_sn = self.sn_entry.get().strip()
        self.sn_window.destroy()
        self.after(100, self.trigger_sn_detection)

    def trigger_sn_detection(self):
        self.capture_image(skip_detect=True)
        if self.cv_img is None:
            messagebox.showerror("错误", "未能获取图像，请检查相机状态")
            self.current_sn = ""
            return

        is_ok = self.run_detection()

        if is_ok:
            self.lbl_status.config(text=f"[{self.current_sn}] 检测OK。请扫描下一个。")
            self.current_sn = ""
            self.after(500, self.open_sn_dialog)
        else:
            self.lbl_status.config(text=f"[{self.current_sn}] 检测NG！需要人工确认！")
            messagebox.showwarning("检测 NG", f"SN: {self.current_sn}\n\n该产品检测出不良 (NG) 或出现错误，请手动确认！")
            self.current_sn = ""
            self.after(500, self.open_sn_dialog)

    def save_detection_images(self, is_ok):
        save_path = self.var_save_path.get()
        if not save_path or not os.path.exists(save_path):
            return

        task_order = self.var_task_order.get().strip()
        if not task_order:
            task_order = "未命名任务"

        # 根据任务令在根目录下创建子文件夹
        task_dir = os.path.join(save_path, task_order)
        raw_dir = os.path.join(task_dir, "raw")
        ok_dir = os.path.join(task_dir, "ok")
        ng_dir = os.path.join(task_dir, "ng")

        for d in [raw_dir, ok_dir, ng_dir]:
            os.makedirs(d, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        sn_str = getattr(self, 'current_sn', '')
        file_name = f"{sn_str}_{ts}.jpg" if sn_str else f"{ts}.jpg"

        # 1. 保存原始整版图
        raw_path = os.path.join(raw_dir, file_name)
        cv2.imwrite(raw_path, self.cv_img)

        # 2. 绘制包含结果的图片
        res_img = self.cv_img.copy()

        for (x, y, w, h, tid) in self.test_rois:
            color = (255, 255, 0) if tid == '1' else (255, 0, 255)
            cv2.rectangle(res_img, (x, y), (x+w, y+h), color, 1)
            cv2.putText(res_img, f"T{tid}", (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

        for res in self.engine.detect_results:
            if res['type'] in ['error', 'frame_fail']:
                bx, by, bw, bh = res['box']
                cv2.rectangle(res_img, (bx, by), (bx+bw, by+bh), (0, 0, 255), 2)
                cv2.putText(res_img, "Fail", (bx, by-5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            elif res['type'] == 'product':
                fx, fy, fw, fh = res['frame_box']
                cv2.rectangle(res_img, (fx, fy), (fx+fw, fy+fh), (255, 0, 0), 1)
                for p in res['pins']:
                    c = (0, 255, 0) if p['status'] == 'pass' else (0, 0, 255)
                    px, py, pw, ph = p['pred_box']
                    cv2.rectangle(res_img, (px, py), (px+pw, py+ph), (0, 255, 255), 1)
                    if p['actual_box']:
                        ax, ay, aw, ah = p['actual_box']
                        cv2.rectangle(res_img, (ax, ay), (ax+aw, ay+ah), c, 2)
                        cv2.putText(res_img, f"{p['dist']:.1f}um", (ax, ay-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 1)
                    else:
                        cv2.putText(res_img, "Lost", (px, py-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # 3. 按最终判定存入 OK 或 NG 目录
        target_dir = ok_dir if is_ok else ng_dir
        res_path = os.path.join(target_dir, file_name)
        cv2.imwrite(res_path, res_img)
        
        emp_id = self.var_emp_id.get().strip()
        logger.info(f"图片自动归档完成 (任务令: {task_order}, 员工号: {emp_id if emp_id else '无'}): {file_name} -> {target_dir}")
        
    # ==========================================

    def update_task_stats(self, is_ok):
        """更新当前任务令的统计情况"""
        current_task = self.var_task_order.get().strip()
        if not current_task:
            current_task = "未命名任务"
            
        # 如果任务令发生变更，重置统计数据
        if current_task != self.stats_task_order:
            self.stats_task_order = current_task
            self.stats_ok_count = 0
            self.stats_ng_count = 0
            self.stats_total_count = 0
            
        self.stats_total_count += 1
        if is_ok:
            self.stats_ok_count += 1
        else:
            self.stats_ng_count += 1
            
        emp_id = self.var_emp_id.get().strip()
        emp_info = f", 测试员工号: {emp_id}" if emp_id else ""
        
        stats_text = f"任务: {self.stats_task_order} | OK: {self.stats_ok_count} | NG: {self.stats_ng_count} | 总计: {self.stats_total_count}"
        
        # 更新状态栏右侧统计显示
        self.lbl_stats.config(text=stats_text)
        
        # 记录到日志系统
        logger.info(f"【测试统计】{stats_text}{emp_info}")

    def on_auto_switch(self, state):
        if state and not self.engine.marks:
            messagebox.showwarning("警告", "当前模板未包含Mark点！请先在模板制作页面绘制并保存包含Mark点的模板。")
            self.switch_auto.set_state(False)
            self.auto_trigger_on = False
            return
        self.auto_trigger_on = state
        logger.info(f"自动触发状态切换为: {state}")
        self.lbl_status.config(text=f"自动触发已{'开启' if state else '关闭'}")

    def on_tab_changed(self, e):
        self.draw_mode = None
        self.lbl_status.config(text="模式切换")
        self.redraw_overlays()

    def set_mode(self, mode):
        self.draw_mode = mode
        self.lbl_status.config(text=f"当前绘制: {mode}")

    def delete_last_mark(self):
        if self.mark_boxes:
            self.mark_boxes.pop()
            self.redraw_overlays()

    def upd_view(self, v=None):
        if self.sidebar.index("current") == 0 and self.var_preview_mode.get():
            if self.cv_img is None: return
            gray = cv2.cvtColor(self.cv_img, cv2.COLOR_BGR2GRAY)
            _, b = cv2.threshold(gray, int(self.s_min.get()), 255, cv2.THRESH_BINARY)
            self.canvas.swap_image(b)
        elif self.cv_img is not None:
            self.canvas.swap_image(self.cv_img)

    def load_img_template(self):
        p = filedialog.askopenfilename()
        if p:
            logger.info(f"加载标准图: {p}")
            self.cv_img = cv2.imread(p)
            self.latest_frame = self.cv_img.copy() 
            self.canvas.load_image(self.cv_img)
            self.clear_tmpl_boxes()

    def clear_tmpl_boxes(self):
        self.tmpl_boxes = {'frame_1': [], 'pin_1': [], 'frame_2': [], 'pin_2': []}
        self.mark_boxes = []
        self.engine.preview_results = []
        self.redraw_overlays()

    def analyze_template(self):
        if self.cv_img is None: return
        self.var_preview_mode.set(False); self.upd_view()
        params = {"thresh_min": self.s_min.get(), "thresh_max": self.s_max.get(), "area_min": self.s_area.get()}
        try:
            msg = self.engine.process_all_templates(self.cv_img, self.tmpl_boxes, params)
            self.redraw_overlays()
            self.lbl_status.config(text=f"生成成功: {msg}")
        except Exception as e:
            logger.error(f"生成双模板预览报错: {e}")
            messagebox.showerror("Error", str(e))

    def save_template(self):
        f = filedialog.asksaveasfilename(defaultextension=".json")
        if f: 
            try:
                self.engine.save_template(f, self.cv_img, self.mark_boxes)
                messagebox.showinfo("OK", "保存成功")
            except Exception as e: 
                messagebox.showerror("Err", str(e))

    def load_template_file(self):
        f = filedialog.askopenfilename()
        if f:
            ok, msg = self.engine.load_template_file(f)
            self.mark_boxes = [m['box'] for m in self.engine.marks]
            self.lbl_status.config(text=msg)
            self.redraw_overlays()

    def load_tmpl_roi(self, tid):
        data = self.engine.templates.get(tid)
        if data:
            if 'user_frame_boxes' in data and data['user_frame_boxes']:
                for box in data['user_frame_boxes']:
                    x, y, w, h = box
                    self.test_rois.append((x, y, w, h, tid))
                self.redraw_overlays()
                self.lbl_status.config(text=f"已成功加载模板 {tid} 的用户原始手绘检测框。")
            elif 'metal_box' in data: 
                x, y, w, h = data['metal_box']
                self.test_rois.append((x, y, w, h, tid))
                self.redraw_overlays()
                self.lbl_status.config(text=f"已成功加载模板 {tid} 的基准检测框 (旧版数据兼容)。")
            else:
                messagebox.showwarning("警告", f"模板{tid}无检测框数据，请先生成并保存。")
        else:
            messagebox.showwarning("警告", f"未找到模板{tid}。")

    def load_test_folder(self):
        d = filedialog.askdirectory()
        if d:
            logger.info(f"加载测试文件夹: {d}")
            self.test_img_list = [os.path.join(d,x) for x in os.listdir(d) if x.endswith(('.jpg','.png','.bmp'))]
            if self.test_img_list:
                self.curr_idx = 0; self._load_test_img()

    def prev_img(self):
        if self.curr_idx > 0: self.curr_idx -= 1; self._load_test_img()
        
    def next_img(self):
        if self.curr_idx < len(self.test_img_list)-1: self.curr_idx += 1; self._load_test_img()

    def _load_test_img(self):
        p = self.test_img_list[self.curr_idx]
        logger.info(f"加载测试图像: {p}")
        self.cv_img = cv2.imread(p)
        self.latest_frame = self.cv_img.copy()
        self.canvas.load_image(self.cv_img)
        self.test_rois = []
        self.engine.detect_results = []
        self.redraw_overlays()
        self.lbl_idx.config(text=f"{self.curr_idx+1}/{len(self.test_img_list)}")

    def clear_test_boxes(self):
        self.test_rois = []
        self.engine.detect_results = []
        self.redraw_overlays()

    def run_detection(self, offset=(0,0)):
        if self.cv_img is None or not self.test_rois: return False
        try:
            res = self.engine.detect_batch_process(
                self.cv_img, 
                self.test_rois, 
                dist_thresh=self.var_dist_thresh.get(), 
                pixel_size=self.var_pixel_size.get(), 
                offset=offset
            )
            self.redraw_overlays()
            ok_cnt = sum(1 for r in res if r['type']=='product' and all(p['status']=='pass' for p in r['pins']))
            
            is_all_ok = (len(res) > 0 and ok_cnt == len(res))
            
            result_txt = f"检测完成 | 全部OK的产品数: {ok_cnt} / {len(res)}"
            logger.info(result_txt)
            
            # 保存图片归档
            self.save_detection_images(is_all_ok)
            
            # 同步更新统计情况
            self.update_task_stats(is_all_ok)
            
            # 不影响原有的手动测试/非扫码状态显示
            if not getattr(self, 'current_sn', '') and not self.auto_trigger_on:
                self.lbl_status.config(text=result_txt)
                
            return is_all_ok
        except Exception as e:
            logger.error(f"检测报错: {e}")
            messagebox.showerror("Err", str(e))
            return False

    def on_down(self, e):
        if not self.draw_mode: return
        self.rect_start = self.canvas.canvas2img(e.x, e.y)
        color = "cyan" if "1" in self.draw_mode else "orange"
        if self.draw_mode == 'mark': color = "purple"
        self.temp_rect_id = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline=color, width=2, dash=(2,2), tags="overlay")

    def on_drag(self, e):
        if self.temp_rect_id:
            x0, y0 = self.canvas.img2canvas(*self.rect_start)
            self.canvas.coords(self.temp_rect_id, x0, y0, e.x, e.y)

    def on_up(self, e):
        if not self.temp_rect_id: return
        self.canvas.delete(self.temp_rect_id); self.temp_rect_id = None
        
        end = self.canvas.canvas2img(e.x, e.y)
        x, y = min(self.rect_start[0], end[0]), min(self.rect_start[1], end[1])
        w, h = abs(end[0]-self.rect_start[0]), abs(end[1]-self.rect_start[1])
        if w<5 or h<5: return
        
        tab = self.sidebar.index("current")
        if tab == 0:
            if self.draw_mode in self.tmpl_boxes:
                self.tmpl_boxes[self.draw_mode].append((x, y, w, h))
            elif self.draw_mode == 'mark':
                if len(self.mark_boxes) >= 3: messagebox.showwarning("提示", "最多只能绘制3个Mark点！")
                else: self.mark_boxes.append((x, y, w, h))
        elif tab == 1:
            if self.draw_mode == 'test_roi_1': self.test_rois.append((x, y, w, h, '1'))
            elif self.draw_mode == 'test_roi_2': self.test_rois.append((x, y, w, h, '2'))
        
        self.redraw_overlays()

    def redraw_overlays(self, e=None):
        self.canvas.delete("overlay")
        tab = self.sidebar.index("current")
        
        if tab == 0:
            for b in self.tmpl_boxes['frame_1']: self._rect(b, "blue", 1)
            for b in self.tmpl_boxes['pin_1']: self._rect(b, "green", 1)
            for b in self.tmpl_boxes['frame_2']: self._rect(b, "orange", 1)
            for b in self.tmpl_boxes['pin_2']: self._rect(b, "yellow", 1)
            for b in self.mark_boxes:
                self._rect(b, "purple", 2)
                self._text(b[0], b[1]-15, "Mark", "purple")
            
            for item in self.engine.preview_results:
                is_t1 = (item['id'] == '1')
                col_frame = "magenta" if is_t1 else "cyan"
                col_pin = "lime" if is_t1 else "gold"
                res = item['res']
                for p in res['pins']: self._rect(p, col_pin, 2)
                for l in res['dashed_lines']: 
                    p1 = self.canvas.img2canvas(l[0], l[1]); p2 = self.canvas.img2canvas(l[2], l[3])
                    self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=col_frame, dash=(4,4), tags="overlay")

        elif tab == 1:
            for (x,y,w,h,tid) in self.test_rois:
                color = "cyan" if tid=='1' else "magenta"
                self._rect((x,y,w,h), color, 1, dash=(4,4))
                self._text(x, y, f"T{tid}", color)
            
            for res in self.engine.detect_results:
                if res['type'] == 'error' or res['type'] == 'frame_fail':
                    self._rect(res['box'], "red", 2)
                    self._text(res['box'][0], res['box'][1], "Fail", "red")
                elif res['type'] == 'product':
                    self._rect(res['frame_box'], "blue", 1)
                    for p in res['pins']:
                        c = "lime" if p['status']=='pass' else "red"
                        self._rect(p['pred_box'], "yellow", 1, dash=(2,2))
                        if p['actual_box']:
                            self._rect(p['actual_box'], c, 2)
                            self._text(p['actual_box'][0], p['actual_box'][1]-10, f"{p['dist']:.1f}um", c)
                        else:
                            self._text(p['pred_box'][0], p['pred_box'][1], "Lost", "red")

    def _rect(self, b, c, w, dash=None):
        x,y,w_b,h_b = b
        c1 = self.canvas.img2canvas(x, y); c2 = self.canvas.img2canvas(x+w_b, y+h_b)
        self.canvas.create_rectangle(c1[0], c1[1], c2[0], c2[1], outline=c, width=w, dash=dash, tags="overlay")

    def _text(self, x, y, txt, c):
        cx, cy = self.canvas.img2canvas(x, y)
        self.canvas.create_text(cx, cy, text=txt, fill=c, anchor="sw", font=("Arial", 10, "bold"), tags="overlay")

    def on_closing(self):
        logger.info("程序准备退出")
        if hasattr(self, 'cap') and self.cap: self.cap.release()
        self.destroy()

if __name__ == "__main__":
    app = ModernUI()
    app.mainloop()