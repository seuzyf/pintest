import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import cv2
import numpy as np
import json
import os
import sys
import time
import ctypes

# ==========================================
# 动态加载子目录中的 OPT SDK
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
sdk_path = os.path.join(current_dir, "Python")

if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

if os.name == 'nt' and hasattr(os, 'add_dll_directory'):
    if os.path.exists(sdk_path):
        try:
            os.add_dll_directory(sdk_path)
        except Exception:
            pass

os.environ['PATH'] = sdk_path + os.pathsep + os.environ.get('PATH', '')

SCICAM_AVAILABLE = False
try:
    from SciCam_class import *
    SCICAM_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法在 '{sdk_path}' 中加载 OPT SDK。错误详情: {e}")

# ==========================================
# 0. OptCamera (OPT 工业相机驱动封装层)
# ==========================================
class OptCamera:
    """
    OPT（奥普特）工业相机驱动封装层
    基于 SciCam SDK 实现，解决内存违规访问与指针生命周期问题。
    """
    def __init__(self):
        if not SCICAM_AVAILABLE:
            raise ImportError(f"未成功加载 OPT SDK。\n请确保 'SciCam_class.py' 及相关 dll 文件已放置在以下目录：\n{sdk_path}")

        self._is_opened = False
        self.m_cam = None
        
        # 将底层结构体作为实例属性，防止 Python 垃圾回收销毁指针引发 Access Violation
        self._devInfos = None
        self._devInfo = None
        
        step = "初始化相机实例"
        try:
            self.m_cam = SciCamera()
            
            step = "枚举设备(DiscoveryDevices)"
            self._devInfos = SCI_DEVICE_INFO_LIST()
            reVal = SciCamera.SciCam_DiscoveryDevices(self._devInfos, SciCamTLType.SciCam_TLType_Unkown)
            if reVal != SCI_CAMERA_OK:
                raise Exception(f"调用 API 失败，错误码: {reVal}")
            if self._devInfos.count == 0:
                raise Exception("未发现任何 OPT 相机设备，请检查连接线或电源。")
                
            step = "创建设备句柄(CreateDevice)"
            self._devInfo = self._devInfos.pDevInfo[0]
            reVal = self.m_cam.SciCam_CreateDevice(self._devInfo)
            if reVal != SCI_CAMERA_OK:
                raise Exception(f"调用 API 失败，错误码: {reVal}")
                
            time.sleep(0.2)  # 给硬件底层建立通讯留出缓冲时间
                
            step = "打开设备(OpenDevice)"
            reVal = self.m_cam.SciCam_OpenDevice()
            if reVal != SCI_CAMERA_OK:
                raise Exception(f"调用 API 失败，错误码: {reVal}")
                
            time.sleep(0.2)  # 缓冲
                
            step = "开启拉流(StartGrabbing)"
            reVal = self.m_cam.SciCam_StartGrabbing()
            if reVal != SCI_CAMERA_OK:
                raise Exception(f"调用 API 失败，错误码: {reVal}")
                
            self._is_opened = True
            print("OPT 相机初始化并开启拉流成功！")
            
        except Exception as e:
            if self.m_cam:
                try:
                    self.m_cam.SciCam_CloseDevice()
                    self.m_cam.SciCam_DeleteDevice()
                except:
                    pass
            self._is_opened = False
            raise Exception(f"在【{step}】阶段发生异常:\n{str(e)}")

    def isOpened(self):
        return self._is_opened

    def read(self):
        if not self._is_opened:
            return False, None
            
        # 每次读取必须声明全新的 c_void_p 指针对象，避免复用脏指针导致内存违规
        ppayload = ctypes.c_void_p()
            
        try:
            reVal = self.m_cam.SciCam_Grab(ppayload)
            if reVal != SCI_CAMERA_OK:
                return False, None
                
            payloadAttribute = SCI_CAM_PAYLOAD_ATTRIBUTE()
            reVal = SciCam_Payload_GetAttribute(ppayload, payloadAttribute)
            
            if reVal != SCI_CAMERA_OK or not bool(payloadAttribute.isComplete):
                self.m_cam.SciCam_FreePayload(ppayload)
                return False, None
                
            imgAttr = payloadAttribute.imgAttr
            imgPixelType = imgAttr.pixelType
            imgWidth = imgAttr.width
            imgHeight = imgAttr.height
            
            imgData = ctypes.c_void_p()
            reVal = SciCam_Payload_GetImage(ppayload, imgData)
            if reVal != SCI_CAMERA_OK:
                self.m_cam.SciCam_FreePayload(ppayload)
                return False, None

            dstImgSize = ctypes.c_int()
            frame = None
            
            is_mono = imgPixelType in [
                SciCamPixelType.Mono1p, SciCamPixelType.Mono2p, SciCamPixelType.Mono4p,
                SciCamPixelType.Mono8s, SciCamPixelType.Mono8, SciCamPixelType.Mono10,
                SciCamPixelType.Mono10p, SciCamPixelType.Mono12, SciCamPixelType.Mono12p,
                SciCamPixelType.Mono14, SciCamPixelType.Mono16, SciCamPixelType.Mono10Packed,
                SciCamPixelType.Mono12Packed, SciCamPixelType.Mono14p
            ]
            
            target_pixel_type = SciCamPixelType.Mono8 if is_mono else SciCamPixelType.RGB8
            
            reVal = SciCam_Payload_ConvertImage(imgAttr, imgData, target_pixel_type, None, dstImgSize, True)
            if reVal == SCI_CAMERA_OK:
                pDstData = (ctypes.c_ubyte * dstImgSize.value)()
                reVal = SciCam_Payload_ConvertImage(imgAttr, imgData, target_pixel_type, pDstData, dstImgSize, True)
                if reVal == SCI_CAMERA_OK:
                    np_arr = np.ctypeslib.as_array(pDstData)
                    if is_mono:
                        frame = np_arr.reshape((imgHeight, imgWidth))
                        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                    else:
                        frame = np_arr.reshape((imgHeight, imgWidth, 3))
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            self.m_cam.SciCam_FreePayload(ppayload)
            
            if frame is not None:
                return True, frame
            return False, None
            
        except Exception as e:
            print(f"OPT相机取图异常: {e}")
            try:
                self.m_cam.SciCam_FreePayload(ppayload)
            except:
                pass
            return False, None

    def release(self):
        if self._is_opened and self.m_cam is not None:
            try:
                self.m_cam.SciCam_StopGrabbing()
                self.m_cam.SciCam_CloseDevice()
                self.m_cam.SciCam_DeleteDevice()
            except Exception as e:
                print(f"释放相机时发生异常: {e}")
            finally:
                self._is_opened = False
                print("OPT 相机资源已释放")

# ==========================================
# 0.5. 自定义 UI 组件 (滑动开关)
# ==========================================
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
        if force_state is not None:
            self.state = force_state
        else:
            self.state = not self.state
            
        fill_color = "#4CAF50" if self.state else "#777"
        self.itemconfig(self.rect, fill=fill_color, outline=fill_color)
        
        move_x = self.width - self.height if self.state else 4
        self.coords(self.knob, move_x, 4, move_x + self.height - 8, self.height - 4)
        
        if self.command and force_state is None: 
            self.command(self.state)

    def set_state(self, state):
        self.toggle(force_state=state)

# ==========================================
# 1. ZoomableCanvas (画布组件)
# ==========================================
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
        if len(cv_img.shape) == 2: 
            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2RGB)
        else:
            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        self.org_image_pil = Image.fromarray(cv_img)
        self._reset_view()
        self.redraw()

    def swap_image(self, cv_img):
        if cv_img is None: return
        if len(cv_img.shape) == 2: 
            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2RGB)
        else:
            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
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
        
        x1 = int(-self.offset_x / self.scale)
        y1 = int(-self.offset_y / self.scale)
        x2 = int((cw - self.offset_x) / self.scale) + 1
        y2 = int((ch - self.offset_y) / self.scale) + 1
        
        iw, ih = self.org_image_pil.size
        x1 = max(0, x1); y1 = max(0, y1)
        x2 = min(iw, x2); y2 = min(ih, y2)
        
        if x2 <= x1 or y2 <= y1:
            self.delete("img_bg")
            return

        region = self.org_image_pil.crop((x1, y1, x2, y2))
        disp_w = int((x2 - x1) * self.scale)
        disp_h = int((y2 - y1) * self.scale)
        
        if disp_w <= 0 or disp_h <= 0: return
        
        region_resized = region.resize((disp_w, disp_h), Image.NEAREST)
        self.tk_image = ImageTk.PhotoImage(region_resized)
        
        self.delete("img_bg")
        pos_x = x1 * self.scale + self.offset_x
        pos_y = y1 * self.scale + self.offset_y
        self.create_image(pos_x, pos_y, image=self.tk_image, anchor="nw", tags="img_bg")
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

    def on_pan_start(self, event):
        self._pan_start = (event.x, event.y)

    def on_pan_drag(self, event):
        if not self._pan_start: return
        dx = event.x - self._pan_start[0]
        dy = event.y - self._pan_start[1]
        self.offset_x += dx
        self.offset_y += dy
        self._pan_start = (event.x, event.y)
        self.redraw()
        self.event_generate("<<ViewChanged>>")
        
    def on_resize(self, event):
        self.redraw()
        self.event_generate("<<ViewChanged>>")

    def img2canvas(self, ix, iy):
        cx = ix * self.scale + self.offset_x
        cy = iy * self.scale + self.offset_y
        return cx, cy

    def canvas2img(self, cx, cy):
        ix = (cx - self.offset_x) / self.scale
        iy = (cy - self.offset_y) / self.scale
        return int(ix), int(iy)

# ==========================================
# 2. VisionEngine (核心逻辑 - 双模板支持)
# ==========================================
class VisionEngine:
    def __init__(self):
        self.templates = {
            '1': None,
            '2': None
        }
        self.preview_results = [] 
        self.detect_results = []

    def load_template_file(self, filepath):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            if "pin_vectors" in data:
                self.templates['1'] = data
                self.templates['2'] = None
                return True, "旧版模板 -> 载入为模板1"
            else:
                self.templates = data
                c1 = len(data.get('1', {}).get('pin_vectors', [])) if data.get('1') else 0
                c2 = len(data.get('2', {}).get('pin_vectors', [])) if data.get('2') else 0
                return True, f"双模板加载成功 | T1: {c1} Pins, T2: {c2} Pins"
        except Exception as e:
            return False, f"模板加载失败: {str(e)}"

    def save_template(self, filepath):
        if not self.templates['1'] and not self.templates['2']:
            raise ValueError("没有任何模板数据")
        with open(filepath, 'w') as f:
            json.dump(self.templates, f)

    def calculate_iou(self, boxA, boxB):
        boxA = [boxA[0], boxA[1], boxA[0]+boxA[2], boxA[1]+boxA[3]]
        boxB = [boxB[0], boxB[1], boxB[0]+boxB[2], boxB[1]+boxB[3]]
        xA = max(boxA[0], boxB[0]); yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2]); yB = min(boxA[3], boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        return interArea / float(boxAArea + boxBArea - interArea + 1e-6)

    def process_all_templates(self, img, all_boxes, params):
        self.preview_results = []
        self.templates = {'1': None, '2': None}
        info = []
        
        if all_boxes['frame_1'] and all_boxes['pin_1']:
            res1 = self._generate_single_template(img, all_boxes['frame_1'], all_boxes['pin_1'], params)
            self.templates['1'] = res1['data']
            self.preview_results.append({'id': '1', 'res': res1['preview']})
            info.append(f"T1: {len(res1['data']['pin_vectors'])} Pins")
            
        if all_boxes['frame_2'] and all_boxes['pin_2']:
            res2 = self._generate_single_template(img, all_boxes['frame_2'], all_boxes['pin_2'], params)
            self.templates['2'] = res2['data']
            self.preview_results.append({'id': '2', 'res': res2['preview']})
            info.append(f"T2: {len(res2['data']['pin_vectors'])} Pins")
            
        return " | ".join(info) if info else "未画完整的框"

    def _generate_single_template(self, img, frame_boxes, pin_boxes, params):
        h_img, w_img = img.shape[:2]
        found_frames = []
        
        for f_box in frame_boxes:
            fx, fy, fw, fh = f_box
            roi = img[fy:fy+fh, fx:fx+fw]
            edge_box = self._find_edges_scanline(roi, params['thresh_min'])
            if edge_box:
                ex, ey, ew, eh = edge_box
                found_frames.append((fx + ex, fy + ey, ew, eh))

        if not found_frames: raise ValueError("某模板未找到基准边")

        min_x = min(f[0] for f in found_frames); min_y = min(f[1] for f in found_frames)
        max_x = max(f[0] + f[2] for f in found_frames); max_y = max(f[1] + f[3] for f in found_frames)
        ref_center = (int((min_x + max_x)/2), int((min_y + max_y)/2))
        
        found_pins = []
        for p_box in pin_boxes:
            px, py, pw, ph = p_box
            roi = img[py:py+ph, px:px+pw]
            pins_rel = self._find_pins(roi, params['thresh_min'], params['thresh_max'], params['area_min'])
            for p in pins_rel:
                found_pins.append((px + p[0], py + p[1], p[2], p[3]))

        vectors = []
        for (px, py, pw, ph) in found_pins:
            pcx, pcy = px + pw/2, py + ph/2
            vectors.append({
                "vec": (pcx - ref_center[0], pcy - ref_center[1]),
                "size": (pw, ph)
            })
            
        return {
            'data': {"ref_frame_center": ref_center, "pin_vectors": vectors, "params": params},
            'preview': {
                'dashed_lines': [(min_x, 0, min_x, h_img), (max_x, 0, max_x, h_img), (0, min_y, w_img, min_y), (0, max_y, w_img, max_y)],
                'ref_center': ref_center,
                'pins': found_pins,
                'metal_box': (min_x, min_y, max_x-min_x, max_y-min_y)
            }
        }

    def detect_batch_process(self, img, rois_with_ids, iou_thresh):
        self.detect_results = []
        for (rx, ry, rw, rh, tmpl_id) in rois_with_ids:
            tmpl_data = self.templates.get(tmpl_id)
            if not tmpl_data:
                self.detect_results.append({'type': 'error', 'box': (rx,ry,rw,rh), 'msg': f"无模板{tmpl_id}"})
                continue
                
            params = tmpl_data['params']
            roi_img = img[ry:ry+rh, rx:rx+rw]
            edge_box_rel = self._find_edges_scanline(roi_img, params['thresh_min'])
            
            if not edge_box_rel:
                self.detect_results.append({'type': 'frame_fail', 'box': (rx,ry,rw,rh)})
                continue
            
            ex, ey, ew, eh = edge_box_rel
            actual_frame_box = (rx + ex, ry + ey, ew, eh)
            actual_center = (actual_frame_box[0] + actual_frame_box[2]/2, actual_frame_box[1] + actual_frame_box[3]/2)
            
            prod_res = {
                'type': 'product',
                'tmpl_id': tmpl_id,
                'frame_box': actual_frame_box,
                'pins': []
            }
            
            for vec_data in tmpl_data['pin_vectors']:
                vx, vy = vec_data['vec']
                w_tmpl, h_tmpl = vec_data['size']
                pred_cx, pred_cy = actual_center[0] + vx, actual_center[1] + vy
                pred_box = (int(pred_cx - w_tmpl/2), int(pred_cy - h_tmpl/2), int(w_tmpl), int(h_tmpl))
                
                margin = 20
                sx = max(0, int(pred_box[0] - margin)); sy = max(0, int(pred_box[1] - margin))
                sw = int(pred_box[2] + margin*2); sh = int(pred_box[3] + margin*2)
                sx = min(sx, img.shape[1]-1); sy = min(sy, img.shape[0]-1)
                
                roi_search = img[sy:sy+sh, sx:sx+sw]
                cands = self._find_pins(roi_search, params['thresh_min'], params['thresh_max'], params['area_min'])
                
                final_box = None
                iou = 0.0
                if cands:
                    pred_rel = (pred_box[0]-sx, pred_box[1]-sy, pred_box[2], pred_box[3])
                    best_c = max(cands, key=lambda c: self.calculate_iou(pred_rel, c))
                    iou = self.calculate_iou(pred_rel, best_c)
                    final_box = (sx + best_c[0], sy + best_c[1], best_c[2], best_c[3])
                
                prod_res['pins'].append({
                    'pred_box': pred_box,
                    'actual_box': final_box,
                    'iou': iou,
                    'status': 'pass' if iou >= iou_thresh else 'fail'
                })
            
            self.detect_results.append(prod_res)
        return self.detect_results

    def _find_edges_scanline(self, roi, thresh_val):
        h, w = roi.shape[:2]
        if h < 10 or w < 10: return None
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        _, binary = cv2.threshold(blurred, int(thresh_val), 255, cv2.THRESH_BINARY)
        
        def find_falling_edge(arr):
            diff = np.diff(arr.astype(np.int16))
            idx = np.where(diff < -100)[0]
            return idx[0] if len(idx) > 0 else None

        skip = 2
        mid_y = h // 2
        line_l = np.max(binary[max(0, mid_y-1):min(h, mid_y+2), :], axis=0)
        idx = find_falling_edge(line_l[skip:])
        lx = (idx + skip) if idx is not None else 0
        
        idx = find_falling_edge(line_l[::-1][skip:])
        rx = (w - 1 - (idx + skip)) if idx is not None else w - 1
        
        mid_x = w // 2
        line_b = np.max(binary[:, max(0, mid_x-1):min(w, mid_x+2)], axis=1)
        idx = find_falling_edge(line_b[::-1][skip:])
        by = (h - 1 - (idx + skip)) if idx is not None else h - 1
        
        mid_x3 = w // 3
        line_t = np.max(binary[:, max(0, mid_x3-1):min(w, mid_x3+2)], axis=1)
        idx = find_falling_edge(line_t[skip:])
        ty = (idx + skip) if idx is not None else 0

        fw, fh = rx - lx, by - ty
        if fw < 5 or fh < 5: return None
        return (int(lx), int(ty), int(fw), int(fh))

    def _find_pins(self, roi, t_min, t_max, a_min):
        if roi.size == 0: return []
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mask = cv2.inRange(gray, int(t_min), int(t_max))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return [cv2.boundingRect(c) for c in cnts if cv2.contourArea(c) >= a_min]

# ==========================================
# 3. 自动触发配置对话框
# ==========================================
class AutoTriggerDialog(tk.Toplevel):
    def __init__(self, parent, frame, current_config, callback):
        super().__init__(parent)
        self.title("自动触发配置")
        self.geometry("900x650")
        self.configure(bg="#2E2E2E")
        self.callback = callback
        
        self.cv_img = frame.copy() if frame is not None else np.zeros((480, 640, 3), dtype=np.uint8)
        
        self.det_roi = current_config.get("det_roi", None)
        self.feat_roi = current_config.get("feat_roi", None)
        self.freq_val = tk.DoubleVar(value=current_config.get("freq", 1.0))
        self.thresh_val = tk.DoubleVar(value=current_config.get("thresh", 0.7))
        
        self.draw_mode = None
        self.rect_start = None
        self.temp_rect_id = None
        
        self._init_ui()
        self.canvas.load_image(self.cv_img)
        self.redraw_regions()

    def _init_ui(self):
        style = ttk.Style()
        style.configure("TButton", background="#4A4A4A", foreground="white")
        
        top_frame = tk.Frame(self, bg="#2E2E2E")
        top_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(top_frame, text="1. 添加检测区域 (蓝框)", command=lambda: self.set_mode("det")).pack(side="left", padx=5)
        ttk.Button(top_frame, text="2. 添加特征点 (红框)", command=lambda: self.set_mode("feat")).pack(side="left", padx=5)
        ttk.Button(top_frame, text="清空绘制", command=self.clear_all).pack(side="left", padx=5)
        
        tk.Label(top_frame, text="频率(次/秒):", bg="#2E2E2E", fg="white").pack(side="left", padx=(20, 2))
        tk.Entry(top_frame, textvariable=self.freq_val, width=5).pack(side="left")
        
        tk.Label(top_frame, text="阈值(0-1):", bg="#2E2E2E", fg="white").pack(side="left", padx=(10, 2))
        tk.Entry(top_frame, textvariable=self.thresh_val, width=5).pack(side="left")
        
        ttk.Button(top_frame, text="保存并关闭", command=self.on_save).pack(side="right", padx=5)
        
        self.lbl_status = tk.Label(self, text="请先绘制检测区域，然后在区域内部绘制特征点", bg="#2E2E2E", fg="yellow")
        self.lbl_status.pack(fill="x", padx=10)
        
        self.canvas = ZoomableCanvas(self, bg="#1E1E1E")
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.canvas.bind("<ButtonPress-1>", self.on_down)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_up)

    def set_mode(self, mode):
        self.draw_mode = mode
        if mode == "det":
            self.lbl_status.config(text="正在绘制检测区域...")
        elif mode == "feat":
            if not self.det_roi:
                messagebox.showwarning("提示", "请先绘制检测区域！")
                self.draw_mode = None
            else:
                self.lbl_status.config(text="正在绘制特征点（必须在检测区域内）...")

    def clear_all(self):
        self.det_roi = None
        self.feat_roi = None
        self.redraw_regions()

    def on_down(self, e):
        if not self.draw_mode: return
        self.rect_start = self.canvas.canvas2img(e.x, e.y)
        color = "cyan" if self.draw_mode == "det" else "red"
        self.temp_rect_id = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline=color, width=2, tags="config_overlay")

    def on_drag(self, e):
        if self.temp_rect_id:
            x0, y0 = self.canvas.img2canvas(*self.rect_start)
            self.canvas.coords(self.temp_rect_id, x0, y0, e.x, e.y)

    def on_up(self, e):
        if not self.temp_rect_id: return
        self.canvas.delete(self.temp_rect_id)
        self.temp_rect_id = None
        
        end = self.canvas.canvas2img(e.x, e.y)
        x = min(self.rect_start[0], end[0])
        y = min(self.rect_start[1], end[1])
        w = abs(end[0] - self.rect_start[0])
        h = abs(end[1] - self.rect_start[1])
        
        if w < 5 or h < 5: return
        
        if self.draw_mode == "det":
            self.det_roi = (x, y, w, h)
            self.feat_roi = None 
            
        elif self.draw_mode == "feat":
            dx, dy, dw, dh = self.det_roi
            if x >= dx and y >= dy and x + w <= dx + dw and y + h <= dy + dh:
                self.feat_roi = (x, y, w, h)
            else:
                messagebox.showerror("错误", "特征点只能在检测区域中绘制！")
                
        self.draw_mode = None
        self.lbl_status.config(text="绘制完成。")
        self.redraw_regions()

    def redraw_regions(self):
        self.canvas.delete("config_overlay")
        if self.det_roi:
            dx, dy, dw, dh = self.det_roi
            c1 = self.canvas.img2canvas(dx, dy)
            c2 = self.canvas.img2canvas(dx+dw, dy+dh)
            self.canvas.create_rectangle(c1[0], c1[1], c2[0], c2[1], outline="cyan", width=2, tags="config_overlay")
            self.canvas.create_text(c1[0], c1[1], text=" 检测区域", fill="cyan", anchor="sw", tags="config_overlay")
        
        if self.feat_roi:
            fx, fy, fw, fh = self.feat_roi
            c1 = self.canvas.img2canvas(fx, fy)
            c2 = self.canvas.img2canvas(fx+fw, fy+fh)
            self.canvas.create_rectangle(c1[0], c1[1], c2[0], c2[1], outline="red", width=2, tags="config_overlay")
            self.canvas.create_text(c1[0], c1[1], text=" 特征点", fill="red", anchor="sw", tags="config_overlay")

    def on_save(self):
        if not self.det_roi or not self.feat_roi:
            messagebox.showwarning("警告", "必须绘制检测区域和特征点！")
            return
        
        try:
            freq = float(self.freq_val.get())
            thresh = float(self.thresh_val.get())
        except ValueError:
            messagebox.showerror("错误", "频率和阈值必须为数字")
            return
            
        config = {
            "det_roi": self.det_roi,
            "feat_roi": self.feat_roi,
            "freq": freq,
            "thresh": thresh
        }
        self.callback(config)
        self.destroy()

# ==========================================
# 4. ModernUI (主界面集成)
# ==========================================
class ModernUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.engine = VisionEngine()
        self.title("Pin针偏位度检测(OPT)")
        self.geometry("1400x950")
        self.configure(bg="#2E2E2E")
        self._init_styles()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.cap = None
        self.is_live = False
        self.latest_frame = None
        
        self.auto_config = {
            "det_roi": None, "feat_roi": None, 
            "freq": 1.0, "thresh": 0.7, "feat_tpl_gray": None
        }
        self.auto_trigger_on = False
        self.last_check_time = 0
        self.last_trigger_time = 0
        self.preview_live = True 

        self.cv_img = None
        self.draw_mode = None
        self.rect_start = None
        self.temp_rect_id = None
        
        self.tmpl_boxes = {
            'frame_1': [], 'pin_1': [], 
            'frame_2': [], 'pin_2': []
        }
        self.var_preview_mode = tk.BooleanVar(value=False)
        
        self.test_img_list = []
        self.curr_idx = -1
        self.test_rois = []
        self.var_iou_thresh = tk.DoubleVar(value=0.5)

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
        
        cam_frame = ttk.LabelFrame(sidebar_container, text="📷 相机与自动取图")
        cam_frame.pack(side="top", fill="x", pady=(0, 10))
        
        self.btn_cam = ttk.Button(cam_frame, text="打开相机", command=self.toggle_camera)
        self.btn_cam.pack(fill="x", padx=5, pady=2)
        
        self.btn_cap = ttk.Button(cam_frame, text="手动取图 (Enter)", command=self.capture_image)
        self.btn_cap.pack(fill="x", padx=5, pady=2)
        
        auto_row = ttk.Frame(cam_frame)
        auto_row.pack(fill="x", padx=5, pady=5)
        ttk.Label(auto_row, text="自动触发:").pack(side="left")
        
        self.switch_auto = SlideSwitch(auto_row, command=self.on_auto_switch)
        self.switch_auto.pack(side="left", padx=10)
        
        ttk.Button(auto_row, text="⚙️ 设置", width=6, command=self.open_auto_config).pack(side="right")
        
        self.sidebar = ttk.Notebook(sidebar_container)
        self.sidebar.pack(fill="both", expand=True)
        
        self.tab_template = ttk.Frame(self.sidebar)
        self.sidebar.add(self.tab_template, text="1. 双模板制作")
        self._init_tab_template(self.tab_template)
        
        self.tab_detect = ttk.Frame(self.sidebar)
        self.sidebar.add(self.tab_detect, text="2. 批量检测")
        self._init_tab_detect(self.tab_detect)
        
        self.sidebar.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        self.lbl_status = ttk.Label(self, text="就绪", wraplength=1000, font=("Segoe UI", 11, "bold"))
        self.lbl_status.pack(side="bottom", fill="x", padx=10, pady=5)

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
        
        ttk.Separator(f).pack(fill="x", pady=15)
        ttk.Label(f, text="检测画框:", font=("",10,"bold")).pack(anchor="w")
        
        ttk.Button(f, text="🖊️ 画待测区 (用模板1检测)", command=lambda: self.set_mode('test_roi_1')).pack(fill="x", pady=2)
        ttk.Button(f, text="🖊️ 画待测区 (用模板2检测)", command=lambda: self.set_mode('test_roi_2')).pack(fill="x", pady=2)
        ttk.Button(f, text="🗑️ 清除当前框", command=self.clear_test_boxes).pack(fill="x", pady=5)
        
        ttk.Separator(f).pack(fill="x", pady=10)
        tk.Scale(f, from_=0.1, to=1.0, res=0.05, orient="h", label="IOU 合格阈值", bg="#2E2E2E", fg="white", variable=self.var_iou_thresh).pack(fill="x")
        ttk.Button(f, text="🔍 开始检测", command=self.run_detection).pack(fill="x", pady=15)

    def toggle_camera(self):
        if not self.is_live:
            try:
                self.cap = OptCamera()
            except Exception as e:
                messagebox.showerror("相机连接失败", str(e))
                return
                
            if not self.cap.isOpened():
                messagebox.showerror("相机错误", "无法连接到 OPT 相机！\n请检查设备连接或 SDK 驱动是否正常。")
                return
                
            self.is_live = True
            self.preview_live = True
            self.btn_cam.config(text="关闭相机/恢复实时")
            self.update_camera()
        else:
            if not self.preview_live:
                self.preview_live = True
                self.lbl_status.config(text="已恢复实时预览")
                self.engine.detect_results = []
                self.redraw_overlays()
            else:
                self.is_live = False
                if self.cap: self.cap.release()
                self.btn_cam.config(text="打开相机")
                self.lbl_status.config(text="相机已关闭")

    def update_camera(self):
        if self.is_live and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.latest_frame = frame
                
                if self.auto_trigger_on and self.auto_config["feat_tpl_gray"] is not None and self.auto_config["det_roi"] is not None:
                    now = time.time()
                    if now - self.last_check_time >= (1.0 / self.auto_config["freq"]):
                        self.last_check_time = now
                        if now - self.last_trigger_time > 2.0:
                            dx, dy, dw, dh = self.auto_config["det_roi"]
                            det_img = frame[dy:dy+dh, dx:dx+dw]
                            
                            if det_img.size > 0:
                                gray_det = cv2.cvtColor(det_img, cv2.COLOR_BGR2GRAY)
                                tpl = self.auto_config["feat_tpl_gray"]
                                
                                if gray_det.shape[0] >= tpl.shape[0] and gray_det.shape[1] >= tpl.shape[1]:
                                    res = cv2.matchTemplate(gray_det, tpl, cv2.TM_CCOEFF_NORMED)
                                    _, max_val, _, _ = cv2.minMaxLoc(res)
                                    
                                    if max_val >= self.auto_config["thresh"]:
                                        self.last_trigger_time = now
                                        self.capture_image()
                
                if self.preview_live:
                    self.cv_img = frame.copy()
                    self.canvas.swap_image(self.cv_img)
                    
            self.after(30, self.update_camera)

    def capture_image(self, event=None):
        if self.latest_frame is None:
            messagebox.showwarning("提示", "当前没有图像，请先加载图片或打开相机")
            return
            
        self.cv_img = self.latest_frame.copy()
        
        if self.is_live:
            self.preview_live = False
            
        self.canvas.load_image(self.cv_img)
        self.redraw_overlays()
        self.lbl_status.config(text="已成功取图，预览画面已锁定（点击相机按钮恢复）。")

        if self.sidebar.index("current") == 1:
            self.run_detection()

    def on_auto_switch(self, state):
        if state and (not self.auto_config["det_roi"] or not self.auto_config["feat_roi"]):
            messagebox.showwarning("警告", "请先点击⚙️设置按钮配置检测区域和特征点！")
            self.switch_auto.set_state(False)
            self.auto_trigger_on = False
            return
        self.auto_trigger_on = state
        self.lbl_status.config(text=f"自动触发已{'开启' if state else '关闭'}")

    def open_auto_config(self):
        if self.latest_frame is None:
            messagebox.showwarning("提示", "请先打开相机获取实时画面")
            return
        AutoTriggerDialog(self, self.latest_frame, self.auto_config, self.save_auto_config)

    def save_auto_config(self, config):
        self.auto_config.update(config)
        fx, fy, fw, fh = config["feat_roi"]
        feat_img_bgr = self.latest_frame[fy:fy+fh, fx:fx+fw]
        self.auto_config["feat_tpl_gray"] = cv2.cvtColor(feat_img_bgr, cv2.COLOR_BGR2GRAY)
        self.lbl_status.config(text="自动触发配置保存成功！")

    def on_tab_changed(self, e):
        self.draw_mode = None
        self.lbl_status.config(text="模式切换")

    def set_mode(self, mode):
        self.draw_mode = mode
        self.lbl_status.config(text=f"当前绘制: {mode}")

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
            self.cv_img = cv2.imread(p)
            self.latest_frame = self.cv_img.copy() 
            self.canvas.load_image(self.cv_img)
            self.clear_tmpl_boxes()

    def clear_tmpl_boxes(self):
        self.tmpl_boxes = {'frame_1': [], 'pin_1': [], 'frame_2': [], 'pin_2': []}
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
            messagebox.showerror("Error", str(e))

    def save_template(self):
        f = filedialog.asksaveasfilename(defaultextension=".json")
        if f: 
            try:
                self.engine.save_template(f)
                messagebox.showinfo("OK", "保存成功")
            except Exception as e: messagebox.showerror("Err", str(e))

    def load_template_file(self):
        f = filedialog.askopenfilename()
        if f:
            ok, msg = self.engine.load_template_file(f)
            self.lbl_status.config(text=msg)

    def load_test_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.test_img_list = [os.path.join(d,x) for x in os.listdir(d) if x.endswith(('.jpg','.png','.bmp'))]
            if self.test_img_list:
                self.curr_idx = 0
                self._load_test_img()

    def prev_img(self):
        if self.curr_idx > 0:
            self.curr_idx -= 1; self._load_test_img()
            
    def next_img(self):
        if self.curr_idx < len(self.test_img_list)-1:
            self.curr_idx += 1; self._load_test_img()

    def _load_test_img(self):
        p = self.test_img_list[self.curr_idx]
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

    def run_detection(self):
        if self.cv_img is None or not self.test_rois: return
        try:
            res = self.engine.detect_batch_process(self.cv_img, self.test_rois, self.var_iou_thresh.get())
            self.redraw_overlays()
            ok_cnt = sum(1 for r in res if r['type']=='product' and all(p['status']=='pass' for p in r['pins']))
            self.lbl_status.config(text=f"检测完成 | 全部OK的产品数: {ok_cnt} / {len(res)}")
        except Exception as e:
            messagebox.showerror("Err", str(e))

    def on_down(self, e):
        if not self.draw_mode: return
        self.rect_start = self.canvas.canvas2img(e.x, e.y)
        color = "cyan" if "1" in self.draw_mode else "orange"
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
        elif tab == 1:
            if self.draw_mode == 'test_roi_1':
                self.test_rois.append((x, y, w, h, '1'))
            elif self.draw_mode == 'test_roi_2':
                self.test_rois.append((x, y, w, h, '2'))
        
        self.redraw_overlays()

    def redraw_overlays(self, e=None):
        self.canvas.delete("overlay")
        tab = self.sidebar.index("current")
        
        if tab == 0:
            for b in self.tmpl_boxes['frame_1']: self._rect(b, "blue", 1)
            for b in self.tmpl_boxes['pin_1']: self._rect(b, "green", 1)
            for b in self.tmpl_boxes['frame_2']: self._rect(b, "orange", 1)
            for b in self.tmpl_boxes['pin_2']: self._rect(b, "yellow", 1)
            
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
                            self._text(p['actual_box'][0], p['actual_box'][1]-10, f"{p['iou']:.2f}", c)
                        else:
                            self._text(p['pred_box'][0], p['pred_box'][1], "Lost", "red")

    def _rect(self, b, c, w, dash=None):
        x,y,w_b,h_b = b
        c1 = self.canvas.img2canvas(x, y)
        c2 = self.canvas.img2canvas(x+w_b, y+h_b)
        self.canvas.create_rectangle(c1[0], c1[1], c2[0], c2[1], outline=c, width=w, dash=dash, tags="overlay")

    def _text(self, x, y, txt, c):
        cx, cy = self.canvas.img2canvas(x, y)
        self.canvas.create_text(cx, cy, text=txt, fill=c, anchor="sw", font=("Arial", 10, "bold"), tags="overlay")

    def on_closing(self):
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
        self.destroy()

if __name__ == "__main__":
    app = ModernUI()
    app.mainloop()
