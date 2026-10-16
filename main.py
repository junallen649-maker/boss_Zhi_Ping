#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOSS直聘 招聘端简历批量自动化下载系统
项目主入口
"""

import sys
import argparse
from download_resumes import run_downloader

def main():
    parser = argparse.ArgumentParser(
        description="BOSS直聘 招聘端批量下载简历 (带三级优先级、防漏检滑动与自定义截止日期)"
    )
    parser.add_argument(
        '--cutoff-date', '-c',
        default='09-24',
        help="扫描截止日期，格式如 '09-24' 或 '09月24日' (默认: 09-24)"
    )
    parser.add_argument(
        '--dest-dir', '-d',
        default=r'D:\简历',
        help="简历文件保存目标目录 (默认: D:\\简历)"
    )
    parser.add_argument(
        '--max-batches', '-m',
        type=int,
        default=60,
        help="最大滚动批次数 (默认: 60)"
    )
    parser.add_argument(
        '--report-path', '-r',
        default=None,
        help="自定义生成执行报告路径 (默认: 存储目录下的 简历下载执行报告.md)"
    )
    args = parser.parse_args()

    run_downloader(
        cutoff_date=args.cutoff_date,
        dest_dir=args.dest_dir,
        max_batches=args.max_batches,
        report_file=args.report_path
    )

if __name__ == '__main__':
    main()
