import cv2
import numpy as np
import json
import base64
import logging

logger = logging.getLogger("VisionEngine")

class VisionEngine:
    def __init__(self):
        self.templates = {'1': None, '2': None}
        self.marks = []
        self.preview_results = [] 
        self.detect_results = []

    def load_template_file(self, filepath):
        try:
            logger.info(f"正在加载模板文件: {filepath}")
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            if "pin_vectors" in data:
                self.templates['1'] = data
                self.templates['2'] = None
            else:
                self.templates = data
                
            self.marks = []
            if 'marks' in self.templates:
                for m in self.templates['marks']:
                    img_cv = self._decode_img(m['img_b64'])
                    self.marks.append({
                        'box': m['box'],
                        'img_cv2': img_cv,
                        'img_b64': m['img_b64']
                    })

            c1 = len(self.templates.get('1', {}).get('pin_vectors', [])) if self.templates.get('1') else 0
            c2 = len(self.templates.get('2', {}).get('pin_vectors', [])) if self.templates.get('2') else 0
            m_cnt = len(self.marks)
            logger.info(f"模板加载成功 | T1: {c1} Pins, T2: {c2} Pins, Marks: {m_cnt}")
            return True, f"模板加载成功 | T1: {c1} Pins, T2: {c2} Pins | Mark点: {m_cnt}个"
        except Exception as e:
            logger.error(f"模板加载失败: {str(e)}")
            return False, f"模板加载失败: {str(e)}"

    def save_template(self, filepath, img, mark_boxes):
        if not self.templates['1'] and not self.templates['2']:
            logger.warning("尝试保存模板时没有任何数据")
            raise ValueError("没有任何模板数据")
            
        self.marks = []
        if img is not None:
            for (x, y, w, h) in mark_boxes:
                x_c = max(0, min(x, img.shape[1]-1))
                y_c = max(0, min(y, img.shape[0]-1))
                w_c = max(1, min(w, img.shape[1]-x_c))
                h_c = max(1, min(h, img.shape[0]-y_c))
                
                roi = img[y_c:y_c+h_c, x_c:x_c+w_c]
                b64 = self._encode_img(roi)
                self.marks.append({
                    'box': (x, y, w, h),
                    'img_b64': b64
                })
        self.templates['marks'] = self.marks
        
        with open(filepath, 'w') as f:
            json.dump(self.templates, f)
        logger.info(f"模板已保存至: {filepath}")

    def _encode_img(self, img):
        _, buf = cv2.imencode('.png', img)
        return base64.b64encode(buf).decode('utf-8')

    def _decode_img(self, b64_str):
        buf = base64.b64decode(b64_str)
        arr = np.frombuffer(buf, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)

    def calculate_iou(self, boxA, boxB):
        boxA = [boxA[0], boxA[1], boxA[0]+boxA[2], boxA[1]+boxA[3]]
        boxB = [boxB[0], boxB[1], boxB[0]+boxB[2], boxB[1]+boxB[3]]
        xA, yA = max(boxA[0], boxB[0]), max(boxA[1], boxB[1])
        xB, yB = min(boxA[2], boxB[2]), min(boxA[3], boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        return interArea / float((boxA[2]-boxA[0])*(boxA[3]-boxA[1]) + (boxB[2]-boxB[0])*(boxB[3]-boxB[1]) - interArea + 1e-6)

    def process_all_templates(self, img, all_boxes, params):
        self.preview_results = []
        self.templates = {'1': None, '2': None}
        info = []
        logger.info("开始生成模板特征...")
        
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
        for fx, fy, fw, fh in frame_boxes:
            roi = img[fy:fy+fh, fx:fx+fw]
            edge_box = self._find_edges_scanline(roi, params['thresh_min'])
            if edge_box:
                found_frames.append((fx + edge_box[0], fy + edge_box[1], edge_box[2], edge_box[3]))
        if not found_frames: 
            raise ValueError("某模板未找到基准边")

        min_x = min(f[0] for f in found_frames); min_y = min(f[1] for f in found_frames)
        max_x = max(f[0] + f[2] for f in found_frames); max_y = max(f[1] + f[3] for f in found_frames)
        ref_center = (int((min_x + max_x)/2), int((min_y + max_y)/2))
        
        found_pins = []
        for px, py, pw, ph in pin_boxes:
            pins_rel = self._find_pins(img[py:py+ph, px:px+pw], params['thresh_min'], params['thresh_max'], params['area_min'])
            for p in pins_rel: found_pins.append((px + p[0], py + p[1], p[2], p[3]))

        vectors = []
        for px, py, pw, ph in found_pins:
            vectors.append({"vec": (px + pw/2 - ref_center[0], py + ph/2 - ref_center[1]), "size": (pw, ph)})
            
        metal_box = (min_x, min_y, max_x-min_x, max_y-min_y)
        
        return {
            'data': {
                "ref_frame_center": ref_center, 
                "pin_vectors": vectors, 
                "params": params, 
                "metal_box": metal_box,
                "user_frame_boxes": frame_boxes 
            },
            'preview': {
                'dashed_lines': [(min_x, 0, min_x, h_img), (max_x, 0, max_x, h_img), (0, min_y, w_img, min_y), (0, max_y, w_img, max_y)],
                'ref_center': ref_center, 'pins': found_pins, 'metal_box': metal_box
            }
        }

    def match_marks(self, frame, exp_pct):
        if not self.marks: return False, (0, 0)
        
        img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        exp_ratio = exp_pct / 100.0
        avg_dx, avg_dy = 0, 0
        
        for mark in self.marks:
            mx, my, mw, mh = mark['box']
            tpl_gray = mark['img_cv2']
            if len(tpl_gray.shape) == 3: tpl_gray = cv2.cvtColor(tpl_gray, cv2.COLOR_BGR2GRAY)
                
            ew, eh = int(mw * exp_ratio), int(mh * exp_ratio)
            sx, sy = max(0, mx - ew), max(0, my - eh)
            ex, ey = min(frame.shape[1], mx + mw + ew), min(frame.shape[0], my + mh + eh)
            
            roi = img_gray[sy:ey, sx:ex]
            if roi.shape[0] < tpl_gray.shape[0] or roi.shape[1] < tpl_gray.shape[1]:
                return False, (0, 0)
                
            res = cv2.matchTemplate(roi, tpl_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            
            if max_val < 0.7:  
                return False, (0, 0)
                
            match_x = sx + max_loc[0]
            match_y = sy + max_loc[1]
            avg_dx += (match_x - mx)
            avg_dy += (match_y - my)
            
        n = len(self.marks)
        return True, (avg_dx // n, avg_dy // n)

    def detect_batch_process(self, img, rois_with_ids, iou_thresh, offset=(0,0)):
        self.detect_results = []
        ox, oy = offset
        logger.info(f"开始批量检测，接收到 {len(rois_with_ids)} 个检测框，偏移量 {offset}")
        
        for (rx_o, ry_o, rw, rh, tmpl_id) in rois_with_ids:
            rx = int(rx_o + ox)
            ry = int(ry_o + oy)
            rx = max(0, min(rx, img.shape[1] - rw))
            ry = max(0, min(ry, img.shape[0] - rh))

            tmpl_data = self.templates.get(tmpl_id)
            if not tmpl_data:
                logger.error(f"无法找到模板: {tmpl_id}")
                self.detect_results.append({'type': 'error', 'box': (rx,ry,rw,rh), 'msg': f"无模板{tmpl_id}"})
                continue
                
            params = tmpl_data['params']
            roi_img = img[ry:ry+rh, rx:rx+rw]
            edge_box_rel = self._find_edges_scanline(roi_img, params['thresh_min'])
            
            if not edge_box_rel:
                logger.warning(f"模板 {tmpl_id} 在检测区未找到基准边")
                self.detect_results.append({'type': 'frame_fail', 'box': (rx,ry,rw,rh)})
                continue
            
            ex, ey, ew, eh = edge_box_rel
            actual_frame_box = (rx + ex, ry + ey, ew, eh)
            actual_center = (actual_frame_box[0] + ew/2, actual_frame_box[1] + eh/2)
            
            prod_res = {'type': 'product', 'tmpl_id': tmpl_id, 'frame_box': actual_frame_box, 'pins': []}
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
                
                final_box, iou = None, 0.0
                if cands:
                    pred_rel = (pred_box[0]-sx, pred_box[1]-sy, pred_box[2], pred_box[3])
                    best_c = max(cands, key=lambda c: self.calculate_iou(pred_rel, c))
                    iou = self.calculate_iou(pred_rel, best_c)
                    final_box = (sx + best_c[0], sy + best_c[1], best_c[2], best_c[3])
                
                prod_res['pins'].append({
                    'pred_box': pred_box, 'actual_box': final_box,
                    'iou': iou, 'status': 'pass' if iou >= iou_thresh else 'fail'
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

        skip = 2; mid_y, mid_x = h // 2, w // 2
        line_l = np.max(binary[max(0, mid_y-1):min(h, mid_y+2), :], axis=0)
        idx = find_falling_edge(line_l[skip:])
        lx = (idx + skip) if idx is not None else 0
        idx = find_falling_edge(line_l[::-1][skip:])
        rx = (w - 1 - (idx + skip)) if idx is not None else w - 1
        
        line_b = np.max(binary[:, max(0, mid_x-1):min(w, mid_x+2)], axis=1)
        idx = find_falling_edge(line_b[::-1][skip:])
        by = (h - 1 - (idx + skip)) if idx is not None else h - 1
        idx = find_falling_edge(np.max(binary[:, max(0, w//3-1):min(w, w//3+2)], axis=1)[skip:])
        ty = (idx + skip) if idx is not None else 0

        if rx - lx < 5 or by - ty < 5: return None
        return (int(lx), int(ty), int(rx - lx), int(by - ty))

    def _find_pins(self, roi, t_min, t_max, a_min):
        if roi.size == 0: return []
        mask = cv2.inRange(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), int(t_min), int(t_max))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return [cv2.boundingRect(c) for c in cnts if cv2.contourArea(c) >= a_min]
