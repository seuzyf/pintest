import os
import sys
import time
import ctypes
import cv2
import numpy as np
import logging

# 获取独立的 logger
logger = logging.getLogger("CameraManager")

# ==========================================
# 动态加载子目录中的 OPT SDK
# ==========================================
# 判断是否被 PyInstaller 打包
if getattr(sys, 'frozen', False):
    # 打包模式：SDK 位于临时目录 sys._MEIPASS 中
    base_dir = sys._MEIPASS
else:
    # 开发模式：SDK 位于当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))

sdk_path = os.path.join(base_dir, "Python")

if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

if os.name == 'nt' and hasattr(os, 'add_dll_directory'):
    if os.path.exists(sdk_path):
        try:
            os.add_dll_directory(sdk_path)
        except Exception as e:
            logger.warning(f"添加 DLL 目录失败: {e}")

os.environ['PATH'] = sdk_path + os.pathsep + os.environ.get('PATH', '')

SCICAM_AVAILABLE = False
try:
    from SciCam_class import *
    SCICAM_AVAILABLE = True
    logger.info("OPT SciCam SDK 导入成功")
except ImportError as e:
    logger.error(f"无法加载 OPT SDK。错误详情: {e}")


class OptCamera:
    """
    OPT（奥普特）工业相机驱动封装层
    基于 SciCam SDK 实现，解决内存违规访问与指针生命周期问题。
    """
    def __init__(self):
        if not SCICAM_AVAILABLE:
            raise ImportError(f"未成功加载 OPT SDK，请检查目录：{sdk_path}")

        self._is_opened = False
        self.m_cam = None
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
                
            time.sleep(0.2)
                
            step = "打开设备(OpenDevice)"
            reVal = self.m_cam.SciCam_OpenDevice()
            if reVal != SCI_CAMERA_OK:
                raise Exception(f"调用 API 失败，错误码: {reVal}")
                
            time.sleep(0.2)
                
            step = "开启拉流(StartGrabbing)"
            reVal = self.m_cam.SciCam_StartGrabbing()
            if reVal != SCI_CAMERA_OK:
                raise Exception(f"调用 API 失败，错误码: {reVal}")
                
            self._is_opened = True
            logger.info("OPT 相机初始化并开启拉流成功！")
            
        except Exception as e:
            logger.error(f"OPT 相机在【{step}】阶段发生异常: {str(e)}")
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
            logger.error(f"OPT相机取图异常: {e}")
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
                logger.info("OPT 相机资源已释放")
            except Exception as e:
                logger.error(f"释放相机时发生异常: {e}")
            finally:
                self._is_opened = False
