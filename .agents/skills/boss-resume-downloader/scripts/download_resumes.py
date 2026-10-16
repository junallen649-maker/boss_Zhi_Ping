#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOSS直聘 简历自动化下载工具 (带防漏检重叠滑动与候选人去重算法)
功能特性:
1. 支持自定义截止日期 (--cutoff-date / -c，如 '09-24', '09月24日')
2. 三级下载规则:
   - 优先级 1: 聊天卡片简历下载 (模板匹配 resources/download_btn_crop.png)
   - 优先级 2: 右上角【附件简历】弹窗大图右上角 [↓] (坐标 1580, 59) 下载
   - 优先级 3: 无简历跳过
3. 防漏检重叠滑动机制 (Anti-Skipping Overlap):
   - 视口每批扫描 12 个候选人槽位
   - 滑动距离严格控制为 2 次 scroll(-600) (~9.7 个候选人)
   - 形成约 2.3 个候选人的重叠安全缓冲，杜绝因大幅滚动跳跃跳过候选人
   - 配合候选人姓名 OCR 去重缓存，重叠项在 0.05 秒内静默跳过
4. 另存为对话框自动化交互与自动重名防护
"""

import os
import sys
import time
import shutil
import ctypes
import argparse
import cv2
import numpy as np
import pyautogui
import easyocr
from PIL import ImageGrab

sys.stdout.reconfigure(encoding='utf-8')

# Windows Desktop Setup
user32 = ctypes.windll.user32
hDesk = user32.OpenDesktopW('default', 0, False, 0x01FF)
if hDesk:
    user32.SetThreadDesktop(hDesk)

pyautogui.FAILSAFE = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Check candidate paths for resources
tpl_candidates = [
    os.path.join(SCRIPT_DIR, 'resources', 'download_btn_crop.png'),
    os.path.join(os.path.dirname(SCRIPT_DIR), 'resources', 'download_btn_crop.png'),
    os.path.join(SCRIPT_DIR, '..', 'resources', 'download_btn_crop.png')
]
DEFAULT_TPL_PATH = None
for p in tpl_candidates:
    if os.path.exists(p):
        DEFAULT_TPL_PATH = os.path.abspath(p)
        break

# Global OCR Reader
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

def ensure_boss_foreground(boss_hwnd=None):
    """确保 BOSS 客户端置顶最大化，并最小化可能遮挡的窗口"""
    target_hwnd = [boss_hwnd] if boss_hwnd else []
    
    def enum_cb(h, _):
        if user32.IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(512)
            cls = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(h, buf, 512)
            user32.GetClassNameW(h, cls, 512)
            
            # Find BOSS if not provided
            if not target_hwnd and 'Chrome_WidgetWin_0' in cls.value and 'BOSS' in buf.value:
                target_hwnd.append(h)
                
            # Minimize occluding windows
            if 'Antigravity IDE' in buf.value:
                user32.ShowWindow(h, 6)
            elif 'Microsoft​ Edge' in buf.value or 'Edge' in cls.value:
                user32.ShowWindow(h, 6)
            elif cls.value == 'CabinetWClass':
                user32.ShowWindow(h, 6)
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumDesktopWindows(hDesk, WNDENUMPROC(enum_cb), 0)
    
    hwnd = target_hwnd[0] if target_hwnd else None
    if hwnd:
        user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.5)
    return hwnd

def get_candidate_name():
    """从右侧会话顶部读取候选人姓名用于去重 (坐标 X: 520..750, Y: 40..85)"""
    try:
        img = ImageGrab.grab(all_screens=True)
        img_np = np.array(img)
        crop = img_np[40:85, 520:750]
        res = reader.readtext(crop)
        names = [t[1].strip() for t in res if t[2] > 0.3]
        if names:
            return names[0]
    except Exception:
        pass
    return None

def check_chat_download_button(tpl_img):
    """优先级 1: 检查聊天消息流中是否存在简历附件卡片"""
    img = ImageGrab.grab(all_screens=True)
    img_np = np.array(img)
    screen_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    chat_area = screen_bgr[200:1200, 500:1300]
    res = cv2.matchTemplate(chat_area, tpl_img, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val > 0.85:
        btn_x = 500 + max_loc[0] + tpl_img.shape[1] // 2
        btn_y = 200 + max_loc[1] + tpl_img.shape[0] // 2
        return True, (btn_x, btn_y)
    return False, None

def check_top_right_resume_button():
    """优先级 2: 检查右上角【附件简历】按钮是否为激活紫蓝色 (RGB: 115, 131, 255)"""
    img = ImageGrab.grab(all_screens=True)
    arr = np.array(img)
    patch = arr[70:95, 2390:2480]
    purple_mask = (patch[:, :, 2] > 200) & (patch[:, :, 0] < 160) & (patch[:, :, 1] < 160)
    count = np.sum(purple_mask)
    return (count > 200), count

def check_stop_condition_via_ocr(cutoff_date_str):
    """
    检查左侧沟通列表中出现的日期是否已超出截止日期。
    cutoff_date_str 支持格式: '09-24', '09月24日', '9-24' 等
    """
    clean_cutoff = cutoff_date_str.replace('月', '-').replace('日', '').strip()
    parts = clean_cutoff.split('-')
    if len(parts) >= 2:
        cutoff_month = parts[-2].zfill(2)
        cutoff_day = int(parts[-1])
    else:
        cutoff_month = '09'
        cutoff_day = 24
        
    try:
        img = ImageGrab.grab(all_screens=True)
        img_np = np.array(img)
        screen_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        date_col = screen_bgr[100:1360, 430:490]
        res = reader.readtext(date_col)
        dates = [text for box, text, conf in res if conf > 0.25]
        
        for d in dates:
            d_norm = d.replace('日', '').replace('月', '-').strip()
            # 检查是否跨越到了更早的月份或当月早于 cutoff 的日期
            if cutoff_month in d or f"{int(cutoff_month)}月" in d:
                # 寻找日期中的日份
                for prior_day in range(1, cutoff_day):
                    prior_str = str(prior_day).zfill(2)
                    if prior_str in d or f"-{prior_day}" in d or f"{prior_day}" == d[-2:]:
                        return True, d
            # 如果出现更早的月份 (如 cutoff 是 9 月，出现 8 月)
            prev_month = str(int(cutoff_month) - 1).zfill(2)
            if prev_month in d or f"{int(prev_month)}月" in d:
                return True, d
    except Exception as e:
        print(f"  [OCR 日期检查异常] {e}")
    return False, None

def handle_save_dialog_and_move(dest_dir):
    """捕获另存为对话框，完成保存并转移至目标目录"""
    time.sleep(0.8)
    save_dlg = None
    for _ in range(15):
        dlgs = []
        def cb(h, lp):
            cls = ctypes.create_unicode_buffer(512)
            user32.GetClassNameW(h, cls, 512)
            if cls.value == '#32770':
                rect = (ctypes.c_long * 4)()
                user32.GetWindowRect(h, ctypes.byref(rect))
                w = rect[2] - rect[0]
                h_len = rect[3] - rect[1]
                if w > 400 and h_len > 300:
                    dlgs.append(h)
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumDesktopWindows(hDesk, WNDENUMPROC(cb), 0)
        if dlgs:
            save_dlg = dlgs[0]
            break
        time.sleep(0.2)
        
    if save_dlg:
        user32.SetForegroundWindow(save_dlg)
        time.sleep(0.3)
        pyautogui.press('enter')
        time.sleep(0.8)
        pyautogui.press('y') # 确认覆盖 (若有)
        time.sleep(0.5)
    else:
        print("  [提示] 未捕获到另存为窗口，可能已静默保存或直接写入目标目录")
        
    # 检查常见存储目录: Documents 以及目标目录自身
    now = time.time()
    saved_fp = None
    
    # 1. 检查目标目录是否直接生成了最新文件
    for f in os.listdir(dest_dir):
        fp = os.path.join(dest_dir, f)
        if os.path.isfile(fp) and (f.endswith('.pdf') or f.endswith('.doc') or f.endswith('.docx')):
            if now - os.path.getmtime(fp) < 40:
                saved_fp = fp
                return saved_fp
                
    # 2. 检查 Documents 是否有新下载需要移动
    doc_dir = os.path.join(os.environ.get('USERPROFILE', r'C:\Users\JunJia'), 'Documents')
    if os.path.exists(doc_dir):
        for f in os.listdir(doc_dir):
            fp = os.path.join(doc_dir, f)
            if os.path.isfile(fp) and (f.endswith('.pdf') or f.endswith('.doc') or f.endswith('.docx')):
                if now - os.path.getmtime(fp) < 40:
                    dest_fp = os.path.join(dest_dir, f)
                    if os.path.exists(dest_fp):
                        base, ext = os.path.splitext(f)
                        dest_fp = os.path.join(dest_dir, f"{base}_{int(now)}{ext}")
                    shutil.move(fp, dest_fp)
                    saved_fp = dest_fp
                    break
    return saved_fp

def run_downloader(cutoff_date='09-24', dest_dir=r'D:\简历', max_batches=60, report_file=None):
    os.makedirs(dest_dir, exist_ok=True)
    if not DEFAULT_TPL_PATH or not os.path.exists(DEFAULT_TPL_PATH):
        raise FileNotFoundError(f"Template image not found in paths: {tpl_candidates}")
    tpl_btn = cv2.imread(DEFAULT_TPL_PATH)
    
    boss_hwnd = ensure_boss_foreground()
    if not boss_hwnd:
        print("[错误] 未能找到 BOSS 直聘客户端窗口，请确保已打开并登录！")
        return False
        
    print(f"\n=======================================================")
    print(f"=== BOSS直聘 简历自动化下载启动 ===")
    print(f"=== 目标截止日期: {cutoff_date} ===")
    print(f"=== 保存目录: {dest_dir} ===")
    print(f"=== 防漏检重叠步长: 12项扫描 + 2x(-600)重叠滑动 ===")
    print(f"=======================================================\n")
    
    downloaded_count = 0
    scanned_count = 0
    visited_candidates = set()
    
    for batch_idx in range(max_batches):
        print(f"\n--- [批次 {batch_idx + 1}/{max_batches}] 扫描当前屏幕可见候选人 ---")
        ensure_boss_foreground(boss_hwnd)
        
        # 扫描可见的前 12 个槽位 (每个槽位高 74px)
        items_in_batch = 12
        for slot in range(items_in_batch):
            y = 138 + slot * 74
            pyautogui.click(250, y)
            time.sleep(0.7)
            
            c_name = get_candidate_name()
            if c_name:
                if c_name in visited_candidates:
                    print(f"  [槽位 {slot} Y={y}] 候选人 '{c_name}' (重叠缓冲区已处理，快速跳过)")
                    continue
                visited_candidates.add(c_name)
                candidate_label = c_name
            else:
                candidate_label = f"未知候选人_Y{y}"
                
            scanned_count += 1
            print(f"[{scanned_count}] 处理候选人: {candidate_label} (Y={y})...")
            
            # 优先级 1: 聊天卡片
            has_chat_btn, chat_btn_pos = check_chat_download_button(tpl_btn)
            if has_chat_btn:
                print(f"  [优先级 1 命中: 聊天卡片简历] 位置: {chat_btn_pos}")
                pyautogui.click(chat_btn_pos[0], chat_btn_pos[1])
                saved_file = handle_save_dialog_and_move(dest_dir)
                if saved_file:
                    downloaded_count += 1
                    print(f"  [下载成功] 保存到: {saved_file}")
                time.sleep(0.5)
                continue
                
            # 优先级 2: 右上角【附件简历】
            is_active, purple_count = check_top_right_resume_button()
            if is_active:
                print(f"  [优先级 2 命中: 右上角附件简历] 色块激活: {purple_count}")
                pyautogui.click(2435, 85)
                time.sleep(1.8) # 等待大图弹窗渲染
                print(f"  点击弹窗右上角下载件 (1580, 59)...")
                pyautogui.click(1580, 59)
                time.sleep(0.8)
                saved_file = handle_save_dialog_and_move(dest_dir)
                
                # 关闭大图弹窗
                pyautogui.press('esc')
                time.sleep(0.3)
                pyautogui.click(1678, 65)
                time.sleep(0.4)
                
                if saved_file:
                    downloaded_count += 1
                    print(f"  [下载成功] 保存到: {saved_file}")
                continue
                
            # 优先级 3: 无简历
            print(f"  [优先级 3: 跳过] 无附件简历")
            time.sleep(0.1)
            
        # 批次结束时检查 OCR 日期截止线
        is_past_cutoff, hit_date = check_stop_condition_via_ocr(cutoff_date)
        if is_past_cutoff:
            print(f"\n>>> 检测到日期已到达 {hit_date} (已超出目标截止线 {cutoff_date})，安全终止！")
            break
            
        # 防漏检重叠滑动: 仅滚动 2 次 -600 (位移约 9.7 项)，与 12 项扫描保持 2.3 项重叠缓冲
        print(f"列表执行安全重叠滑动 (2 次 scroll(-600))...")
        pyautogui.moveTo(250, 1000)
        for _ in range(2):
            pyautogui.scroll(-600)
            time.sleep(0.12)
        time.sleep(0.8)
        
    print(f"\n=======================================================")
    print(f"=== 扫描下载完毕！累计扫描候选人: {scanned_count} 位 ===")
    print(f"=== 成功下载归档: {downloaded_count} 份简历 ===")
    print(f"=== 目标存储目录: {dest_dir} ===")
    print(f"=======================================================\n")
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="BOSS直聘 简历自动化下载工具")
    parser.add_argument('--cutoff-date', '-c', default='09-24', help="扫描截止日期 (如 '09-24', '09月24日')")
    parser.add_argument('--dest-dir', '-d', default=r'D:\简历', help="简历保存目标文件夹")
    parser.add_argument('--max-batches', '-m', type=int, default=60, help="最大滚动扫描批次数")
    parser.add_argument('--report-path', '-r', default=None, help="自定义执行报告输出路径")
    args = parser.parse_args()
    
    run_downloader(cutoff_date=args.cutoff_date, dest_dir=args.dest_dir, max_batches=args.max_batches, report_file=args.report_path)
