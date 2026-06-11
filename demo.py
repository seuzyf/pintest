import sys
import os
import socket
import struct
import platform
from ctypes import CFUNCTYPE, c_void_p
from typing import Reversible

from SciCam_class import *

m_currentCam = SciCamera()

# Show title
def ShowInfoTitle():
	print('*******************************************')
	print('*              SciCamera Demo             *')
	print('*******************************************')

# Clear console output
def ClrScreen():
	print('\033c')

# Wait for user enter choice
def WaitForNumInput(isLimit, minVal, maxVal):
	userInput = int(-1)
	while True:
		userInput = input()
		if userInput.isdigit() == True:
			if isLimit:
				if int(userInput) < minVal or int(userInput) > maxVal:
					sys.stdout.write("Input error, please input again: ")
				else:
					break
			else:
				break
		else:
			sys.stdout.write("Input error, please input again: ")

	return userInput

def WaitForDoubleNumInput():
	while True:
		try:
			d_val = float(input("Please enter a double number: "))
			break
		except ValueError:
			print('Input error, please enter again.')

	return d_val

# Wait for enter any key to continue
def EnterAnyKeyToContinue():
	sys.stdout.write("Press any key to continue...")
	if os.name == 'nt':
		#os.system("pause")
		input()
	else:
		c = sys.stdin.readline()

# Print Menu items
def ShowMenu(strTup):
	print("-------------------------------------------")
	for var in strTup:
		print(var)
	print("-------------------------------------------")
	sys.stdout.write("Please enter your choice based on the menu option number: ")
def uint32_to_ipv4(ip_uint32):
	network_order_ip = socket.htonl(ip_uint32)
	packed_ip = struct.pack("!I", network_order_ip)
	ipv4_address = socket.inet_ntoa(packed_ip)
	return ipv4_address

def GetEnumName(enumCls, value):
	for name, member in enumCls.__members__.items():
		if member == value:
			return name
	return None

# Show device infomation
def ShowDeviceInfo(dev):
	# print device type
	devType = GetEnumName(SciCamDeviceType, dev.devType)
	print('| Device type: ', devType)
	# print device transfer type
	devTlType = GetEnumName(SciCamTLType, dev.tlType)
	print('| Device transfer type: ', devTlType)

	if dev.tlType == SciCamTLType.SciCam_TLType_Gige:

		print('| Camera status: %c' %dev.info.gigeInfo.status)

		camName = ''
		for per in dev.info.gigeInfo.name:
			if per == 0:
				break
			camName = camName + chr(per)
		print('| Camera name: %s' %camName)

		camManufactureName = ''
		for per in dev.info.gigeInfo.manufactureName:
			if per == 0:
				break
			camManufactureName = camManufactureName + chr(per)
		print('| Camera manufactureName: %s' %camManufactureName)

		camModelName = ''
		for per in dev.info.gigeInfo.modelName:
			if per == 0:
				break
			camModelName = camModelName + chr(per)
		print('| Camera modelName: %s' %camModelName)

		camVersion = ''
		for per in dev.info.gigeInfo.version:
			if per == 0:
				break
			camVersion = camVersion + chr(per)
		print('| Camera version: %s' %camVersion)

		camUserDefineName = ''
		for per in dev.info.gigeInfo.userDefineName:
			if per == 0:
				break
			camUserDefineName = camUserDefineName + chr(per)
		print('| Camera userDefineName: %s' %camUserDefineName)

		camSerialNumber = ''
		for per in dev.info.gigeInfo.serialNumber:
			if per == 0:
				break
			camSerialNumber = camSerialNumber + chr(per)
		print('| Camera serialNumber: %s' %camSerialNumber)

		print('| Camera mac: %.2x:%.2x:%.2x:%.2x:%.2x:%.2x' %(dev.info.gigeInfo.mac[0], dev.info.gigeInfo.mac[1], dev.info.gigeInfo.mac[2], dev.info.gigeInfo.mac[3], dev.info.gigeInfo.mac[4], dev.info.gigeInfo.mac[5]))
		camIp = uint32_to_ipv4(dev.info.gigeInfo.ip)
		camMask = uint32_to_ipv4(dev.info.gigeInfo.mask)
		camGateway = uint32_to_ipv4(dev.info.gigeInfo.gateway)
		adapterIp = uint32_to_ipv4(dev.info.gigeInfo.adapterIp)
		adapterMask = uint32_to_ipv4(dev.info.gigeInfo.adapterMask)
		print('| Camera ip: {}'.format(camIp))
		print('| Camera mask: {}'.format(camMask))
		print('| Camera gateway {}'.format(camGateway))
		print('| Camera adapterIp {}'.format(adapterIp))
		print('| Camera adapterMask {}'.format(adapterMask))
		
		camAdapterName = ''
		for per in dev.info.gigeInfo.adapterName:
			if per == 0:
				break
			camAdapterName = camAdapterName + chr(per)
		print('| Camera adapterName: %s' %camAdapterName)

	elif dev.tlType == SciCamTLType.SciCam_TLType_Usb3:

		print('| Camera status: %c' %dev.info.gigeInfo.status)

		camName = ''
		for per in dev.info.usb3Info.name:
			if per == 0:
				break
			camName = camName + chr(per)
		print('| Camera name: {}'.format(camName))

		camManufactureName = ''
		for per in dev.info.usb3Info.manufactureName:
			if per == 0:
				break
			camManufactureName = camManufactureName + chr(per)
		print('| Camera manufactureName: {}'.format(camManufactureName))
		
		camModelName = ''
		for per in dev.info.usb3Info.modelName:
			if per == 0:
				break
			camModelName = camModelName + chr(per)
		print('| Camera modelName: {}'.format(camModelName))
		
		camVersion = ''
		for per in dev.info.usb3Info.version:
			if per == 0:
				break
			camVersion = camVersion + chr(per)
		print('| Camera version: {}'.format(camVersion))
		
		camUserDefineName = ''
		for per in dev.info.usb3Info.userDefineName:
			if per == 0:
				break
			camUserDefineName = camUserDefineName + chr(per)
		print('| Camera userDefineName: {}'.format(camUserDefineName))
		
		camSerialNumber = ''
		for per in dev.info.usb3Info.serialNumber:
			if per == 0:
				break
			camSerialNumber = camSerialNumber + chr(per)
		print('| Camera serialNumber: {}'.format(camSerialNumber))
		
		camGuid = ''
		for per in dev.info.usb3Info.guid:
			if per == 0:
				break
			camGuid = camGuid + chr(per)
		print('| Camera guid: {}'.format(camGuid))

		camU3VVersion = ''
		for per in dev.info.usb3Info.U3VVersion:
			if per == 0:
				break
			camU3VVersion = camU3VVersion + chr(per)
		print('| Camera U3VVersion: {}'.format(camU3VVersion))
		
		camGenCPVersion = ''
		for per in dev.info.usb3Info.GenCPVersion:
			if per == 0:
				break
			camGenCPVersion = camGenCPVersion + chr(per)
		print('| Camera GenCPVersion: {}'.format(camGenCPVersion))
		
	elif dev.tlType == SciCamTLType.SciCam_TLType_CL:
		print('| Card status: %c' %dev.info.clInfo.cardStatus)
		
		cardName = ''
		for per in dev.info.clInfo.cardName:
			if per == 0:
				break
			cardName = cardName + chr(per)
		print('| Card name: {}'.format(cardName))
		
		cardManufacture = ''
		for per in dev.info.clInfo.cardManufacture:
			if per == 0:
				break
			cardManufacture = cardManufacture + chr(per)
		print('| Card manufacture: {}'.format(cardManufacture))
		
		cardModel = ''
		for per in dev.info.clInfo.cardModel:
			if per == 0:
				break
			cardModel = cardModel + chr(per)
		print('| Card model: {}'.format(cardModel))
		
		cardVersion = ''
		for per in dev.info.clInfo.cardVersion:
			if per == 0:
				break
			cardVersion = cardVersion + chr(per)
		print('| Card version: {}'.format(cardVersion))
		
		cardUserDefineName = ''
		for per in dev.info.clInfo.cardUserDefineName:
			if per == 0:
				break
			cardUserDefineName = cardUserDefineName + chr(per)
		print('| Card user define name: {}'.format(cardUserDefineName))
		
		cardSerialNumber = ''
		for per in dev.info.clInfo.cardSerialNumber:
			if per == 0:
				break
			cardSerialNumber = cardSerialNumber + chr(per)
		print('| Card serial number: {}'.format(cardSerialNumber))

		print('| Camera status: %c' %dev.info.clInfo.cameraStatus)
		
		print('| Camera type: {}'.format(dev.info.clInfo.cameraType))
		
		print('| Camera baud: {}'.format(dev.info.clInfo.cameraBaud))
		
		cameraModel = ''
		for per in dev.info.clInfo.cameraModel:
			if per == 0:
				break
			cameraModel = cameraModel + chr(per)
		print('| Camera model: {}'.format(cameraModel))
		
		cameraManufacture = ''
		for per in dev.info.clInfo.cameraManufacture:
			if per == 0:
				break
			cameraManufacture = cameraManufacture + chr(per)
		print('| Camera manufacture: {}'.format(cameraManufacture))
		
		cameraFamily = ''
		for per in dev.info.clInfo.cameraFamily:
			if per == 0:
				break
			cameraFamily = cameraFamily + chr(per)
		print('| Camera family: {}'.format(cameraFamily))
		
		cameraModel = ''
		for per in dev.info.clInfo.cameraModel:
			if per == 0:
				break
			cameraModel = cameraModel + chr(per)
		print('| Camera model: {}'.format(cameraModel))
		
		cameraVersion = ''
		for per in dev.info.clInfo.cameraVersion:
			if per == 0:
				break
			cameraVersion = cameraVersion + chr(per)
		print('| Camera version: {}'.format(cameraVersion))
		
		cameraSerialNumber = ''
		for per in dev.info.clInfo.cameraSerialNumber:
			if per == 0:
				break
			cameraSerialNumber = cameraSerialNumber + chr(per)
		print('| Camera serial number: {}'.format(cameraSerialNumber))
		
		cameraSerialPort = ''
		for per in dev.info.clInfo.cameraSerialPort:
			if per == 0:
				break
			cameraSerialPort = cameraSerialPort + chr(per)
		print('| Camera serial port: {}'.format(cameraSerialPort))
		
		cameraProtocol = ''
		for per in dev.info.clInfo.cameraProtocol:
			if per == 0:
				break
			cameraProtocol = cameraProtocol + chr(per)
		print('| Camera protocol: {}'.format(cameraProtocol))

def GetInputNodeName():
	sys.stdout.write('Please enter node name (string): ')
	node_name = input()[:64].rstrip('\n')
	return node_name

def GetInputDeviceNodeType():
	menu = [
		"[0] SciCam_DeviceXml_Camera",
		"[1] SciCam_DeviceXml_Card",
		"[2] SciCam_DeviceXml_TL",
		"[3] SciCam_DeviceXml_IF",
		"[4] SciCam_DeviceXml_DS",
	]

	ShowMenu(menu)
	op = WaitForNumInput(True, 0, 4)
	return op

def ShowPayloadDataAttribute(ppayload):
	payloadAttribute = SCI_CAM_PAYLOAD_ATTRIBUTE()
	reVal = SciCam_Payload_GetAttribute(ppayload, payloadAttribute)
	if reVal != SCI_CAMERA_OK:
		print('Get payload attribute failed, return error number: %u' %reVal)
	
	print('***********************************')
	print('Payload frameID: {}'.format(payloadAttribute.frameID))
	isComplete = bool(payloadAttribute.isComplete)
	print('Payload isComplete: {}'.format(isComplete))
	hasChunk = bool(payloadAttribute.hasChunk)
	print('Payload hasChunk: {}'.format(hasChunk))
	print('Payload timeStamp: {}'.format(payloadAttribute.timeStamp))
	print('Payload payloadMode: {}'.format(payloadAttribute.payloadMode))
	print('--------------------')
	print('image width: {}'.format(payloadAttribute.imgAttr.width))
	print('image height: {}'.format(payloadAttribute.imgAttr.height))
	print('image offsetX: {}'.format(payloadAttribute.imgAttr.offsetX))
	print('image offsetY: {}'.format(payloadAttribute.imgAttr.offsetY))
	print('image paddingX: {}'.format(payloadAttribute.imgAttr.paddingX))
	print('image paddingY: {}'.format(payloadAttribute.imgAttr.paddingY))
	print('image pixelType: {}'.format(payloadAttribute.imgAttr.pixelType))

def GetNodeValueStr(xmlType, node):
	iVal = SCI_NODE_VAL_INT()
	bVal = c_bool()
	fVal = SCI_NODE_VAL_FLOAT()
	eVal = SCI_NODE_VAL_ENUM()
	sVal = SCI_NODE_VAL_STRING()
	strVal = str('None')

	nodeType = node.type
	if nodeType == SciCamNodeType.SciCam_NodeType_Bool:
		reVal = m_currentCam.SciCam_GetBoolValueEx(xmlType, node.name.decode(), bVal)
		if reVal == SCI_CAMERA_OK:
			strVal = str(bVal.value)
	if nodeType == SciCamNodeType.SciCam_NodeType_Int:
		reVal = m_currentCam.SciCam_GetIntValueEx(xmlType, node.name.decode(), iVal)
		if reVal == SCI_CAMERA_OK:
			strVal = str(iVal.nVal)
	if nodeType == SciCamNodeType.SciCam_NodeType_Float:
		reVal = m_currentCam.SciCam_GetFloatValueEx(xmlType, node.name.decode(), fVal)
		if reVal == SCI_CAMERA_OK:
			strVal = str(fVal.dVal)
	if nodeType == SciCamNodeType.SciCam_NodeType_Enum:
		reVal = m_currentCam.SciCam_GetEnumValueEx(xmlType, node.name.decode(), eVal)
		if reVal == SCI_CAMERA_OK:
			strVal = str(eVal.nVal)
	if nodeType == SciCamNodeType.SciCam_NodeType_String:
		reVal = m_currentCam.SciCam_GetStringValueEx(xmlType, node.name.decode(), sVal)
		if reVal == SCI_CAMERA_OK:
			strVal = str(sVal.val.decode())

	return strVal

from ctypes import CFUNCTYPE
winfun_ctype = CFUNCTYPE
PayloadInfoCallBack = winfun_ctype(None, c_void_p, c_void_p)

def payloadCallbackFunc(ppayload, tag):
	ShowPayloadDataAttribute(ppayload);

CALL_BACK_FUN = PayloadInfoCallBack(payloadCallbackFunc)

def menuItem_GetSdkVersionInformation():
	version = c_uint(SciCamera.SciCam_GetSDKVersion())
	verMain = (version.value >> 24) & 0xff;
	verSub = (version.value >> 16) & 0xff;
	verRev = (version.value >> 8) & 0xff;
	verTest = version.value & 0xff;
	print('SciCamera SDK version is: V%u.%u.%u.%u' %(verMain, verSub, verRev, verTest))

def menuItem_DiscoveryDevices():
	global m_currentDeviceInfo
	print('Please wait ...')

	devInfos = SCI_DEVICE_INFO_LIST()
	reVal = SciCamera.SciCam_DiscoveryDevices(devInfos, SciCamTLType.SciCam_TLType_Unkown)
	if reVal != SCI_CAMERA_OK:
		print('Discovery devices failed, return error number: %d' %reVal)
		return

	print('The number of discovered devices is: ', devInfos.count)
	for index in range(0, devInfos.count):
		print('-------------------------------------------')
		print('| ---- Index: ', index)
		ShowDeviceInfo(devInfos.pDevInfo[index])

	if devInfos.count != 0:
		print('-------------------------------------------')
		sys.stdout.write('Please enter your selection based on the index: ')
		userInput = WaitForNumInput(True, 0, devInfos.count - 1)
		m_currentDeviceInfo = devInfos.pDevInfo[int(userInput)]

def menuItem_OpenDevice():
	reVal = m_currentCam.SciCam_CreateDevice(m_currentDeviceInfo)
	if reVal != SCI_CAMERA_OK:
		print('Create device failed, return error number: %u' %reVal)
		return

	reVal = m_currentCam.SciCam_OpenDevice()
	if reVal != SCI_CAMERA_OK:
		print('Open device failed, return error number: %u' %reVal)
		return
	print('Open device success!')

def menuItem_CloseDevice():
	reVal = m_currentCam.SciCam_CloseDevice();
	if reVal != SCI_CAMERA_OK:
		print('Close device failed, return error number: %u' %reVal)
	else:
		m_currentCam.SciCam_DeleteDevice()
		print('Close device success!')

def menuItem_CL_OpenCam():
	reVal = m_currentCam.SciCam_CreateDevice(m_currentDeviceInfo)
	if reVal != SCI_CAMERA_OK:
		print('Create device failed, return error code: %u' %reVal)
		return
	reVal = m_currentCam.SciCam_CL_OpenCam()
	if reVal != SCI_CAMERA_OK:
		print('Open CL camera failed, return error code: %u' %reVal)
	else:
		print('Open CL camera success!')

def menuItem_CL_CloseCam():
	reVal = m_currentCam.SciCam_CL_CloseCam()
	if(reVal != SCI_CAMERA_OK):
		print('Close CL camera failed, return error code: %u' %reVal)
	else:
		print('Close CL camera success.')

def menuItem_IsDeviceOpen():
	reVal = m_currentCam.SciCam_IsDeviceOpen()
	if reVal:
		print('Device/Camera is opened')
	else:
		print('Device/Camera is not opened')

def menuItem_IsCLCameraOpen():
	reVal = m_currentCam.SciCam_CL_IsCamOpen()
	if reVal:
		print('CL Camera is opened')
	else:
		print('CL Camera is not opened')

def menuItem_SetGrabTimeout():
	sys.stdout.write('Please enter the grab timeout: ')
	op = int(WaitForNumInput(False, 0, 0))
	reVal = m_currentCam.SciCam_SetGrabTimeout(op)
	if reVal != SCI_CAMERA_OK:
		print('Set grab timeout failed, return error number: %u' %reVal)
	else:
		print('Set grab timeout success, current itmeout is: %u' %op)

def menuItem_GetGrabTimeout():
	timeout = c_uint(0)
	reVal = m_currentCam.SciCam_GetGrabTimeout(timeout)
	if reVal != SCI_CAMERA_OK:
		print('Get grab timeout failed, return error code: %u' %reVal)
	else:
		print('Get grab timeout success. Current grab timeout is: {} ms'.format(timeout.value))

def menuItem_SetGrabStrategy():
	menu = [
		"Please select the grab stategy:",
		"[0] OneByOne",
		"[1] Latest",
		"[2] Upcoming"
	]
	ShowMenu(menu)
	userInput = WaitForNumInput(True, 0, 2)
	reVal = m_currentCam.SciCam_SetGrabStrategy(int(userInput))
	if reVal == SCI_CAMERA_OK:
		print('Set grab strategy success.')
	else:
		print('Set grab strategy failed, return error code: %u' %reVal)

def menuItem_GetGrabStrategy():
	grabStrategy = c_int(0)
	reVal = m_currentCam.SciCam_GetGrabStrategy(grabStrategy)
	if reVal == SCI_CAMERA_OK:
		grabStrategyStr = GetEnumName(SciCamGrabStrategy, grabStrategy.value)
		print('Get grab strategy success. Current grab strategy is: ', grabStrategyStr)
	else:
		print('Get grab strategy failed, return error code: %u' %reVal);

def menuItem_SetGrabBufferCount():
	sys.stdout.write('Please input grab buffer count: ')
	bufferCount = int(WaitForNumInput(True, 0, 99999))
	reVal = m_currentCam.SciCam_SetGrabBufferCount(bufferCount)
	if reVal == SCI_CAMERA_OK:
		print('Set grab buffer count success!')
	else:
		print('Set grab buffer count failed, return error code: %u' %reVal)

def menuItem_GetGrabBufferCount():
	bufferCount = c_uint(0)
	reVal = m_currentCam.SciCam_GetGrabBufferCount(bufferCount)
	if reVal == SCI_CAMERA_OK:
		print('Get grab buffer count success. Current grab buffer count is: {}'.format(bufferCount.value))
	else:
		print('Get grab buffer count failed, return error code: %u' %reVal)

def menuItem_StartGrabbing():
	reVal = m_currentCam.SciCam_StartGrabbing()
	if reVal != SCI_CAMERA_OK:
		print('Start grabbing failed, return error number: %u' %reVal)
	else:
		print('Start grabbing success!')


def menuItem_StopGrabbing():
	reVal = m_currentCam.SciCam_StopGrabbing()
	if reVal != SCI_CAMERA_OK:
		print('Stop grabbing failed, return error number: %u' %reVal)
	else:
		print('Stop grabbing success!')

def menuItem_RegisterPayloadCallBack():
	reVal = m_currentCam.SciCam_RegisterPayloadCallBack(CALL_BACK_FUN, None, True)
	if reVal != SCI_CAMERA_OK:
		print('Register payload callback function failed, return error number: %u' %reVal)
	else:
		print('Register payload callback function success.')

def menuItem_UnRegisterPayloadCallBack():
	reVal = m_currentCam.SciCam_RegisterPayloadCallBack(None, None, True)
	if reVal != SCI_CAMERA_OK:
		print('Unregister payload callback function failed, return error number: %u' %reVal)
	else:
		print('Unregister payload callback function success.')

def menuItem_GrabOneImage():
	ppayload = ctypes.c_void_p()
	reVal = m_currentCam.SciCam_Grab(ppayload)
	if reVal != SCI_CAMERA_OK:
		print('Grab failed, return error number: %u' %reVal)
		return
	else:
		print('Grab success!')

	ShowPayloadDataAttribute(ppayload);
	reVal = m_currentCam.SciCam_FreePayload(ppayload)
	if reVal != SCI_CAMERA_OK:
		print('Free payload failed, return error number: %u' %reVal)
		
def menuItem_GrabOneImageAndSave():
	menu = [
		"[ 0] Return to the previous menu",
		"[ 1] Save BMP",
		"[ 2] Save JPG",
		"[ 3] Save TIFF",
		"[ 4] Save PNG",
	]
	ShowMenu(menu)
	op = int(WaitForNumInput(True, 0, 4))
	if op == 0:
		return
	
	ppayload = ctypes.c_void_p()
	reVal = m_currentCam.SciCam_Grab(ppayload)
	if reVal != SCI_CAMERA_OK:
		print('Grab failed, return error number: %u' %reVal)
		return

	payloadAttribute = SCI_CAM_PAYLOAD_ATTRIBUTE()
	reVal = SciCam_Payload_GetAttribute(ppayload, payloadAttribute)
	
	if reVal != SCI_CAMERA_OK:
		print('Get payload attribute failed, return error number: %u' %reVal)
		m_currentCam.SciCam_FreePayload(ppayload)
		return
	
	imgIsComplete = bool(payloadAttribute.isComplete)
	payloadMode = payloadAttribute.payloadMode
	imgPixelType = payloadAttribute.imgAttr.pixelType
	imgWidth = payloadAttribute.imgAttr.width
	imgHeight = payloadAttribute.imgAttr.height
	framID = payloadAttribute.frameID

	if op == 1:
		save_file_param = "Image_W{}_H{}_fID_{}.bmp".format(imgWidth, imgHeight, framID)
	if op == 2:
		save_file_param = "Image_W{}_H{}_fID_{}.jpeg".format(imgWidth, imgHeight, framID)
	if op == 3:
		save_file_param = "Image_W{}_H{}_fID_{}.tiff".format(imgWidth, imgHeight, framID)
	if op == 4:
		save_file_param = "Image_W{}_H{}_fID_{}.png".format(imgWidth, imgHeight, framID)
	
	
	if not imgIsComplete or payloadMode != SciCamPayloadMode.SciCam_PayloadMode_2D:
		print('Image data is not complete or payload type error.')
		m_currentCam.SciCam_FreePayload(ppayload)
		return
	
	imgData = ctypes.c_void_p()
	reVal = SciCam_Payload_GetImage(ppayload, imgData)
	if reVal != SCI_CAMERA_OK:
		print('Get image data failed, return error number: %u' %reVal)
		
	dstImgSize = ctypes.c_int()
	if imgPixelType == SciCamPixelType.Mono1p or \
		imgPixelType == SciCamPixelType.Mono2p or \
		imgPixelType == SciCamPixelType.Mono4p or \
		imgPixelType == SciCamPixelType.Mono8s or \
		imgPixelType == SciCamPixelType.Mono8 or \
		imgPixelType == SciCamPixelType.Mono10 or \
		imgPixelType == SciCamPixelType.Mono10p or \
		imgPixelType == SciCamPixelType.Mono12 or \
		imgPixelType == SciCamPixelType.Mono12p or \
		imgPixelType == SciCamPixelType.Mono14 or \
		imgPixelType == SciCamPixelType.Mono16 or \
		imgPixelType == SciCamPixelType.Mono10Packed or \
		imgPixelType == SciCamPixelType.Mono12Packed or \
		imgPixelType == SciCamPixelType.Mono14p:
		reVal = SciCam_Payload_ConvertImage(payloadAttribute.imgAttr, imgData, SciCamPixelType.Mono8, None, dstImgSize, True)
		if reVal == SCI_CAMERA_OK:
			pDstData = (ctypes.c_ubyte * dstImgSize.value)()
			reVal = SciCam_Payload_ConvertImageEx(payloadAttribute.imgAttr, imgData, SciCamPixelType.Mono8, pDstData, dstImgSize, True,0)
			if reVal == SCI_CAMERA_OK:
				reVal = SciCam_Payload_SaveImage(save_file_param, SciCamPixelType.Mono8, pDstData, imgWidth, imgHeight)
				if reVal == SCI_CAMERA_OK:
					print('Save Image success.')
				else:
					print('Save Image failed, return error number: %u' %reVal)
			else:
				print ('ConVert image failed, return error number: %u' %reVal)
		else:
			print ('ConVert image failed, return error number: %u' %reVal)
	else:
		reVal = SciCam_Payload_ConvertImage(payloadAttribute.imgAttr, imgData, SciCamPixelType.RGB8, None, dstImgSize, True)
		if reVal == SCI_CAMERA_OK:
			pDstData = (ctypes.c_ubyte * dstImgSize.value)()
			reVal = SciCam_Payload_ConvertImage(payloadAttribute.imgAttr, imgData, SciCamPixelType.RGB8, pDstData, dstImgSize, True)
			if reVal == SCI_CAMERA_OK:
				reVal = SciCam_Payload_SaveImage(save_file_param, SciCamPixelType.RGB8, pDstData, imgWidth, imgHeight)
				if reVal == SCI_CAMERA_OK:
					print('Save Image success.')
				else:
					print('Save Image failed, return error number: %u' %reVal)
			else:
				print ('ConVert image failed, return error number: %u' %reVal)
		else:
			print ('ConVert image failed, return error number: %u' %reVal)
	
	m_currentCam.SciCam_FreePayload(ppayload)

def menuItem_ReadWriteNode():
	menu = [
		"[ 0] Return to the previous menu",
		"[ 1] GetIntValue",
		"[ 2] SetIntValue",
		"[ 3] GetFloatValue",
		"[ 4] SetFloatValue",
		"[ 5] GetBoolValue",
		"[ 6] SetBoolValue",
		"[ 7] GetStringValue",
		"[ 8] SetStringValue",
		"[ 9] GetEnumValue",
		"[10] SetEnumValue",
		"[11] SetEnumValueByString",
		"[12] SetCommandValue",
		"[13] GetNodes",
		"[14] GetIntValueEx",
		"[15] SetIntValueEx",
		"[16] GetFloatValueEx",
		"[17] SetFloatValueEx",
		"[18] GetBoolValueEx",
		"[19] SetBoolValueEx",
		"[20] GetStringValueEx",
		"[21] SetStringValueEx",
		"[22] GetEnumValueEx",
		"[23] SetEnumValueEx",
		"[24] SetEnumValueByStringEx",
		"[25] SetCommandValueEx",
		"[26] GetNodesEx",
	]
	ShowMenu(menu)
	op = int(WaitForNumInput(True, 0, 26))
	if op == 0:
		return
	elif op == 1:
		nodeName = GetInputNodeName()
		nodeVal = SCI_NODE_VAL_INT()
		reVal = m_currentCam.SciCam_GetIntValue(nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('---- Node Name: ', nodeName)
			print('---- Node Value: ', nodeVal.nVal)
			print('---- Node Max: ', nodeVal.nMax)
			print('---- Node Min: ', nodeVal.nMin)
			print('---- Node Inc: ', nodeVal.nInc)
		else:
			print('Get node: %s value(int) failed, return error code: %u' %(nodeName, reVal))
	elif op == 2:
		nodeName = GetInputNodeName()
		sys.stdout.write('Please input node value(int): ')
		nodeVal = int(WaitForNumInput(False, 0, 0))
		reVal = m_currentCam.SciCam_SetIntValue(nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('Set node: %s, val: %d success!' %(nodeName, nodeVal))
		else:
			print('Set node: %s value(int) failed, return error code: %u' %(nodeName, reVal))
	elif op == 3:
		nodeName = GetInputNodeName()
		nodeVal = SCI_NODE_VAL_FLOAT()
		reVal = m_currentCam.SciCam_GetFloatValue(nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('---- Node Name:', nodeName)
			print('---- Node Value:', nodeVal.dVal)
			print('---- Node Max:', nodeVal.dMax)
			print('---- Node Min:', nodeVal.dMin)
			print('---- Node Inc:', nodeVal.dInc)
		else:
			print('Get node: %s value(float) failed, return error code: %u' %(nodeName, reVal))
	elif op == 4:
		nodeName = GetInputNodeName()
		sys.stdout.write('Please input node value(float): ')
		nodeVal = float(WaitForDoubleNumInput())
		reVal = m_currentCam.SciCam_SetFloatValue(nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('set node: %s, val: %f success!' %(nodeName, nodeVal))
		else:
			print('Set node: %s value(float) failed, return error code: %u' %(nodeName, reVal))
	elif op == 5:
		nodeName = GetInputNodeName()
		nodeVal = c_bool()
		reVal = m_currentCam.SciCam_GetBoolValue(nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('---- Node Name: ', nodeName)
			print('---- Node Value: ', nodeVal.value)
		else:
			print('Get node: %s value(bool) failed, return error code: %u' %(nodeName, reVal))
	elif op == 6:
		nodeName = GetInputNodeName()
		sys.stdout.write('Please input node value(0 is False, ~0 is True): ')
		nNodeVal = WaitForNumInput(False, 0, 0)
		if int(nNodeVal) == 0:
			nodeVal = False
		else:
			nodeVal = True
		reVal = m_currentCam.SciCam_SetBoolValue(nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('Set node: {nodeName}, val: {} success!'.format(nodeVal))
		else:
			print('Set node: %s value(bool) failed, return error code: %u' %(nodeName, reVal))
	elif op == 7:
		nodeName = GetInputNodeName()
		nodeVal = SCI_NODE_VAL_STRING()
		reVal = m_currentCam.SciCam_GetStringValue(nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('---- Node Name: ', nodeName)
			print('---- Node Value: ', nodeVal.val.decode())
		else:
			print('Get node: %s value(string) failed, return error code: %u' %(nodeName, reVal))
	elif op == 8:
		nodeName = GetInputNodeName()
		sys.stdout.write('Please input node value(string): ')
		nodeVal = input().rstrip('\n')[:1024]
		reVal = m_currentCam.SciCam_SetStringValue(nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('Set node: {}, val: {} success!'.format(nodeName, nodeVal.decode()))
		else:
			print('Set node: %s value(string) failed, return error code: %u' %(nodeName, reVal))
	elif op == 9:
		nodeName = GetInputNodeName()
		nodeVal = SCI_NODE_VAL_ENUM()
		reVal = m_currentCam.SciCam_GetEnumValue(nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('---- Node Name: ', nodeName)
			print('---- Node current value: %d' %nodeVal.nVal)
			print('-------- Node enum item count: %d' %nodeVal.itemCount)
			print('-------- Node enum items:')
			for i in range(nodeVal.itemCount):
				print("-------- {}\t{}".format(nodeVal.items[i].val, nodeVal.items[i].desc))
		else:
			print('Get node: %s value(enum) failed, return error code: %u' %(nodeName, reVal))
	elif op == 10:
		nodeName = GetInputNodeName()
		sys.stdout.write('Please input node value(int): ')
		nodeVal = int(WaitForNumInput(False, 0, 0))
		reVal = m_currentCam.SciCam_SetEnumValue(nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('Set node: {}, val: {} success!'.format(nodeName, nodeVal))
		else:
			print('Set node: %s value(enum) failed, return error code: %u' %(nodeName, reVal))
	elif op == 11:
		nodeName = GetInputNodeName()
		sys.stdout.write('Please input node value(string): ')
		nodeVal = input().rstrip('\n')[:1024]
		reVal = m_currentCam.SciCam_SetEnumValueByString(nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('Set node: {}, val: {} success!'.format(nodeName, nodeVal.decode()))
		else:
			print('Set node: %s value(enum) failed, return error code: %u' %(nodeName, reVal))
	elif op == 12:
		nodeName = GetInputNodeName()
		menu = [
			"[0] Cancel",
			"[1] Execute"
		]
		ShowMenu(menu)
		op = WaitForNumInput(True, 0, 1)
		if int(op) == 1:
			reVal = m_currentCam.SciCam_SetCommandValue(nodeName)
		if reVal == SCI_CAMERA_OK:
			print('Set node: %s command value success!' %nodeName)
		else:
			print('Set node: %s command value failed, return error code: %u' %(nodeName, reVal))
	elif op == 13:
		nodesCount = c_uint(0)
		reVal = m_currentCam.SciCam_GetNodes(None, nodesCount)
		if reVal == SCI_CAMERA_OK:
			if nodesCount.value == 0:
				print('Get nodes success, but the nodes Count is 0.')
				return
			ClrScreen()
			print('Successfully retrieved all nodes of the device, the number of nodes is: %d' %nodesCount.value)
			nodes = (SCI_CAM_NODE * nodesCount.value)()
			reVal = m_currentCam.SciCam_GetNodes(ctypes.cast(nodes, PSCI_CAM_NODE).contents, nodesCount)
			if reVal == SCI_CAMERA_OK:
				print("-" * 135)
				print("{:<70s}{:<15s}{:<15s}{:<15s}{:<15s}{:<15s}".format("NodeName", "NodeType", "Namespace", "Visibility", "AccessMode", "Value"))
				print("-" * 135)

				for i in range(nodesCount.value):
					node = nodes[i]
					sys.stdout.write('  ' * node.level)
					sys.stdout.write('{:<{}s}'.format(node.name.decode(), 70 - int(node.level) * 2))
					sys.stdout.write('{:<{}s}'.format(GetEnumName(SciCamNodeType, node.type).split('_')[-1], 15))
					sys.stdout.write('{:<{}s}'.format(GetEnumName(SciCamNodeNameSpace, node.nameSpace).split('_')[-1], 15))
					sys.stdout.write('{:<{}s}'.format(GetEnumName(SciCamNodeVisibility, node.visibility).split('_')[-1], 15))
					sys.stdout.write('{:<{}s}'.format(GetEnumName(SciCamNodeAccessMode, node.accessMode).split('_')[-1], 15))
					strVal = GetNodeValueStr(SciCamDeviceXmlType.SciCam_DeviceXml_Camera, node)
					print(strVal)
					#print('{:<{}{}}'.format(15, strVal))
			else:
				print('Get nodes failed, return error code: %u' %reVal)
		else:
			print('Get nodes failed, return error code: %u' %reVal)
	elif op == 14:
		nodeName = GetInputNodeName()
		xmlType = int(GetInputDeviceNodeType())
		nodeVal = SCI_NODE_VAL_INT()
		reVal = m_currentCam.SciCam_GetIntValueEx(xmlType, nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('---- Node Name: ', nodeName)
			print('---- Node Value: ', nodeVal.nVal)
			print('---- Node Max: ', nodeVal.nMax)
			print('---- Node Min: ', nodeVal.nMin)
			print('---- Node Inc: ', nodeVal.nInc)
		else:
			print('Get node: %s value(int) failed, return error code: %u' %(nodeName, reVal))
	elif op == 15:
		nodeName = GetInputNodeName()
		xmlType = int(GetInputDeviceNodeType())
		sys.stdout.write('Please input node value(int): ')
		nodeVal = int(WaitForNumInput(False, 0, 0))
		reVal = m_currentCam.SciCam_SetIntValueEx(xmlType, nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('Set node: %s, val: %d success!' %(nodeName, nodeVal))
		else:
			print('Set node: %s value(int) failed, return error code: %u' %(nodeName, reVal))
	elif op == 16:
		nodeName = GetInputNodeName()
		xmlType = int(GetInputDeviceNodeType())
		nodeVal = SCI_NODE_VAL_FLOAT()
		reVal = m_currentCam.SciCam_GetFloatValueEx(xmlType, nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('---- Node Name:', nodeName)
			print('---- Node Value:', nodeVal.dVal)
			print('---- Node Max:', nodeVal.dMax)
			print('---- Node Min:', nodeVal.dMin)
			print('---- Node Inc:', nodeVal.dInc)
		else:
			print('Get node: %s value(float) failed, return error code: %u' %(nodeName, reVal))
	elif op == 17:
		nodeName = GetInputNodeName()
		xmlType = int(GetInputDeviceNodeType())
		sys.stdout.write('Please input node value(float): ')
		nodeVal = float(WaitForDoubleNumInput())
		reVal = m_currentCam.SciCam_SetFloatValueEx(xmlType, nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('set node: %s, val: %f success!' %(nodeName, nodeVal))
		else:
			print('Set node: %s value(float) failed, return error code: %u' %(nodeName, reVal))
	elif op == 18:
		nodeName = GetInputNodeName()
		xmlType = int(GetInputDeviceNodeType())
		nodeVal = c_bool()
		reVal = m_currentCam.SciCam_GetBoolValueEx(xmlType, nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('---- Node Name: ', nodeName)
			print('---- Node Value: ', nodeVal.value)
		else:
			print('Get node: %s value(bool) failed, return error code: %u' %(nodeName, reVal))
	elif op == 19:
		nodeName = GetInputNodeName()
		xmlType = int(GetInputDeviceNodeType())
		sys.stdout.write('Please input node value(0 is False, ~0 is True): ')
		nNodeVal = WaitForNumInput(False, 0, 0)
		if int(nNodeVal) == 0:
			nodeVal = False
		else:
			nodeVal = True
		reVal = m_currentCam.SciCam_SetBoolValueEx(xmlType, nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('Set node: {}, val: {} success!'.format(nodeName, nodeVal))
		else:
			print('Set node: %s value(bool) failed, return error code: %u' %(nodeName, reVal))
	elif op == 20:
		nodeName = GetInputNodeName()
		xmlType = int(GetInputDeviceNodeType())
		nodeVal = SCI_NODE_VAL_STRING()
		reVal = m_currentCam.SciCam_GetStringValueEx(xmlType, nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('---- Node Name: ', nodeName)
			print('---- Node Value: ', nodeVal.val.decode())
		else:
			print('Get node: %s value(string) failed, return error code: %u' %(nodeName, reVal))
	elif op == 21:
		nodeName = GetInputNodeName()
		xmlType = int(GetInputDeviceNodeType())
		sys.stdout.write('Please input node value(string): ')
		nodeVal = input().rstrip('\n')[:1024]
		reVal = m_currentCam.SciCam_SetStringValueEx(xmlType, nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('Set node: {}, val: {} success!'.format(nodeName, nodeVal.decode()))
		else:
			print('Set node: %s value(string) failed, return error code: %u' %(nodeName, reVal))
	elif op == 22:
		nodeName = GetInputNodeName()
		xmlType = int(GetInputDeviceNodeType())
		nodeVal = SCI_NODE_VAL_ENUM()
		reVal = m_currentCam.SciCam_GetEnumValueEx(xmlType, nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('---- Node Name: ', nodeName)
			print('---- Node current value: %d' %nodeVal.nVal)
			print('-------- Node enum item count: %d' %nodeVal.itemCount)
			print('-------- Node enum items:')
			for i in range(nodeVal.itemCount):
				print("-------- {}\t{}".format(nodeVal.items[i].val, nodeVal.items[i].desc))
		else:
			print('Get node: %s value(enum) failed, return error code: %u' %(nodeName, reVal))
	elif op == 23:
		nodeName = GetInputNodeName()
		xmlType = int(GetInputDeviceNodeType())
		sys.stdout.write('Please input node value(int): ')
		nodeVal = int(WaitForNumInput(False, 0, 0))
		reVal = m_currentCam.SciCam_SetEnumValueEx(xmlType, nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('Set node: {}, val: {} success!'.format(nodeName, nodeVal))
		else:
			print('Set node: %s value(enum) failed, return error code: %u' %(nodeName, reVal))
	elif op == 24:
		nodeName = GetInputNodeName()
		xmlType = int(GetInputDeviceNodeType())
		sys.stdout.write('Please input node value(string): ')
		nodeVal = input().rstrip('\n')[:1024]
		reVal = m_currentCam.SciCam_SetEnumValueByStringEx(xmlType, nodeName, nodeVal)
		if reVal == SCI_CAMERA_OK:
			print('Set node: {}, val: {} success!'.format(nodeName, nodeVal.decode()))
		else:
			print('Set node: %s value(enum) failed, return error code: %u' %(nodeName, reVal))
	elif op == 25:
		nodeName = GetInputNodeName()
		xmlType = int(GetInputDeviceNodeType())
		menu = [
			"[0] Cancel",
			"[1] Execute"
		]
		ShowMenu(menu)
		op = WaitForNumInput(True, 0, 1)
		if int(op) == 1:
			reVal = m_currentCam.SciCam_SetCommandValueEx(xmlType, nodeName)
		if reVal == SCI_CAMERA_OK:
			print('Set node: %s command value success!' %nodeName)
		else:
			print('Set node: %s command value failed, return error code: %u' %(nodeName, reVal))
	elif op == 26:
		xmlType = int(GetInputDeviceNodeType())
		nodesCount = c_uint(0)
		reVal = m_currentCam.SciCam_GetNodesEx(xmlType, None, nodesCount)
		if reVal == SCI_CAMERA_OK:
			if nodesCount.value == 0:
				print('Get nodes success, but the nodes Count is 0.')
				return
			ClrScreen()
			print('Successfully retrieved all nodes of the device, the number of nodes is: %d' %nodesCount.value)
			nodes = (SCI_CAM_NODE * nodesCount.value)()
			reVal = m_currentCam.SciCam_GetNodesEx(xmlType, ctypes.cast(nodes, PSCI_CAM_NODE).contents, nodesCount)
			if reVal == SCI_CAMERA_OK:
				print("-" * 135)
				print("{:<70s}{:<15s}{:<15s}{:<15s}{:<15s}{:<15s}".format("NodeName", "NodeType", "Namespace", "Visibility", "AccessMode", "Value"))
				print("-" * 135)

				for i in range(nodesCount.value):
					node = nodes[i]
					sys.stdout.write('  ' * node.level)
					sys.stdout.write('{:<{}s}'.format(node.name.decode(), 70 - int(node.level) * 2))
					sys.stdout.write('{:<{}s}'.format(GetEnumName(SciCamNodeType, node.type).split('_')[-1], 15))
					sys.stdout.write('{:<{}s}'.format(GetEnumName(SciCamNodeNameSpace, node.nameSpace).split('_')[-1], 15))
					sys.stdout.write('{:<{}s}'.format(GetEnumName(SciCamNodeVisibility, node.visibility).split('_')[-1], 15))
					sys.stdout.write('{:<{}s}'.format(GetEnumName(SciCamNodeAccessMode, node.accessMode).split('_')[-1], 15))
					strVal = GetNodeValueStr(xmlType, node)
					print(strVal)
					#print('{:<{}{}}'.format(15, strVal))
			else:
				print('Get nodes failed, return error code: %u' %reVal)


				
		else:
			print('Get nodes failed, return error code: %u' %reVal)



def ShowMainMenu():
	mainMenu = [
		"[ 0] Exit program",
		"[ 1] Get SDK version information",
		"[ 2] Discovery devices",
		"[ 3] Open device",
		"[ 4] Close device",
		"[ 5] Open CL Camera",
		"[ 6] Close CL Camera",
		"[ 7] Check device/camera open status",
		"[ 8] Check CL camera open status",
		"[ 9] Set grab timeout",
		"[10] Get grab timeout",
		"[11] Set grab strategy",
		"[12] Get grab strategy",
		"[13] Set grab buffer count",
		"[14] Get grab buffer count",
		"[15] Start grabbing",
		"[16] Stop grabbing",
		"[17] Register payload callback",
		"[18] Unregister payload callback",
		"[19] Grab one image",
		"[20] Grab one image and save",
		"[21] Device node"
	]

	while(True):
		ClrScreen()
		ShowInfoTitle()
		ShowMenu(mainMenu)
		op = WaitForNumInput(True, 0, 21)

		if int(op) == 0:
			break
		ClrScreen()
		if int(op) == 1:
			menuItem_GetSdkVersionInformation()
		elif int(op) == 2:
			menuItem_DiscoveryDevices()
		elif int(op) == 3:
			menuItem_OpenDevice()
		elif int(op) == 4:
			menuItem_CloseDevice()
		elif int(op) == 5:
			menuItem_CL_OpenCam()
		elif int(op) == 6:
			menuItem_CL_CloseCam()
		elif int(op) == 7:
			menuItem_IsDeviceOpen()
		elif int(op) == 8:
			menuItem_IsCLCameraOpen()
		elif int(op) == 9:
			menuItem_SetGrabTimeout()
		elif int(op) == 10:
			menuItem_GetGrabTimeout()
		elif int(op) == 11:
			menuItem_SetGrabStrategy()
		elif int(op) == 12:
			menuItem_GetGrabStrategy()
		elif int(op) == 13:
			menuItem_SetGrabBufferCount()
		elif int(op) == 14:
			menuItem_GetGrabBufferCount()
		elif int(op) == 15:
			menuItem_StartGrabbing()
		elif int(op) == 16:
			menuItem_StopGrabbing()
		elif int(op) == 17:
			menuItem_RegisterPayloadCallBack()
		elif int(op) == 18:
			menuItem_UnRegisterPayloadCallBack()
		elif int(op) == 19:
			menuItem_GrabOneImage()
		elif int(op) == 20:
			menuItem_GrabOneImageAndSave()
		elif int(op) == 21:
			menuItem_ReadWriteNode()

		EnterAnyKeyToContinue()

	print('Exit program...')


ShowMainMenu()
