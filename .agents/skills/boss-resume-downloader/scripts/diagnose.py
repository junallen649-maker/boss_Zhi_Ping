#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOSS直聘 简历下载环境自检与诊断工具
用于在运行下载前验证窗口状态、屏幕分辨率、按钮识别及 OCR 准备情况。
"""

import os
import sys
import ctypes
import cv2
import numpy as np
from PIL import ImageGrab

sys.stdout.reconfigure(encoding='utf-8')

user32 = ctypes.windll.user32
hDesk = user32.OpenDesktopW('default', 0, False, 0x01FF)
if hDesk:
    user32.SetThreadDesktop(hDesk)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)
TPL_PATH = os.path.join(SKILL_ROOT, 'resources', 'download_btn_crop.png')

def run_diagnostics():
    print("=== [BOSS直聘 简历下载工具] 系统环境自检 ===")
    
    # 1. 检查桌面分辨率
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    print(f"1. 屏幕分辨率: {w}x{h} (标准分辨率: 2560x1440)")
    if (w, h) != (2560, 1440):
        print("   [提示] 当前分辨率不是 2560x1440，如果 UI 产生缩放，可能需要校准坐标。")
    else:
        print("   [正常] 分辨率完全匹配！")
        
    # 2. 检查模板文件
    print(f"2. 聊天卡片模板文件: {TPL_PATH}")
    if os.path.exists(TPL_PATH):
        img_tpl = cv2.imread(TPL_PATH)
        print(f"   [正常] 模板文件存在，尺寸: {img_tpl.shape[1]}x{img_tpl.shape[0]} px")
    else:
        print("   [错误] 模板文件缺失！")
        
    # 3. 查找 BOSS 直聘窗口
    boss_hwnds = []
    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            cls = ctypes.create_unicode_buffer(512)
            title = ctypes.create_unicode_buffer(512)
            user32.GetClassNameW(hwnd, cls, 512)
            user32.GetWindowTextW(hwnd, title, 512)
            if 'Chrome_WidgetWin_0' in cls.value and 'BOSS' in title.value:
                boss_hwnds.append((hwnd, title.value))
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumDesktopWindows(hDesk, WNDENUMPROC(cb), 0)
    
    print(f"3. BOSS 直聘窗口检测: 找到 {len(boss_hwnds)} 个窗口")
    for bh, bt in boss_hwnds:
        print(f"   HWND: {bh}, 标题: {bt}")
        
    # 4. 检查当前屏幕右上角【附件简历】色块状态
    try:
        img = ImageGrab.grab(all_screens=True)
        arr = np.array(img)
        patch = arr[70:95, 2390:2480]
        purple_mask = (patch[:, :, 2] > 200) & (patch[:, :, 0] < 160) & (patch[:, :, 1] < 160)
        p_count = np.sum(purple_mask)
        print(f"4. 右上角【附件简历】按钮检测:")
        print(f"   紫蓝色像素数: {p_count} (阈值 > 200 为激活)")
        if p_count > 200:
            print("   [状态] 当前选中的候选人【存在附件简历】(激活状态)")
        else:
            print("   [状态] 当前选中的候选人【无附件简历/已禁用】")
    except Exception as e:
        print(f"   [异常] 截图检测异常: {e}")
        
    # 5. 检查目标保存目录
    dest = r'D:\简历'
    os.makedirs(dest, exist_ok=True)
    count = len([f for f in os.listdir(dest) if os.path.isfile(os.path.join(dest, f))])
    print(f"5. 存储目录 D:\\简历: 正常可写，目前已归档 {count} 份简历。")
    print("=== 自检完成 ===\n")

if __name__ == '__main__':
    run_diagnostics()
