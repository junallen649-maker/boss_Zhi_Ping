#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOSS直聘 简历归档查询与统计工具
用于快速查看已下载简历的清单、分类统计与时间覆盖情况。
"""

import os
import sys
import time
import argparse

sys.stdout.reconfigure(encoding='utf-8')

def list_resumes(dest_dir=r'D:\简历', category_filter=None):
    if not os.path.exists(dest_dir):
        print(f"[错误] 目录不存在: {dest_dir}")
        return
        
    files = [f for f in os.listdir(dest_dir) if os.path.isfile(os.path.join(dest_dir, f))]
    if category_filter:
        files = [f for f in files if category_filter in f]
        
    files_sorted = sorted(files, key=lambda f: os.path.getmtime(os.path.join(dest_dir, f)), reverse=True)
    
    # 统计分类
    categories = {}
    for f in files_sorted:
        cat = "其他"
        if f.startswith("【") and "】" in f:
            cat = f[1:f.index("】")].split("_")[0]
        categories[cat] = categories.get(cat, 0) + 1
        
    print(f"\n=== [D:\\简历] 简历存储归档统计 ===")
    print(f"总简历数: {len(files_sorted)} 份")
    print("分类分布:")
    for cat, count in categories.items():
        print(f"  - {cat}: {count} 份")
        
    print(f"\n| 序号 | 简历文件名 | 大小 | 下载保存时间 |")
    print(f"| :--- | :--- | :--- | :--- |")
    for i, f in enumerate(files_sorted, 1):
        fp = os.path.join(dest_dir, f)
        size_kb = os.path.getsize(fp) / 1024
        mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(fp)))
        print(f"| {i} | {f} | {size_kb:.1f} KB | {mtime} |")
    print("")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="查询已下载简历统计")
    parser.add_argument('--dir', '-d', default=r'D:\简历', help="简历目录")
    parser.add_argument('--category', '-c', default=None, help="按分类过滤 (如 'AI工程师', '人事行政')")
    args = parser.parse_args()
    
    list_resumes(dest_dir=args.dir, category_filter=args.category)
