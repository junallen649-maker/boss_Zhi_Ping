---
name: boss-resume-downloader
description: >-
  Automated resume fetching and downloading workflow for BOSS直聘 client. Traverses candidate lists, detects attachment resumes via chat cards or top-right header preview modals, handles Save As dialogs, and downloads resumes to a target directory with customizable cutoff dates and anti-skipping scroll optimization.
---

# BOSS直聘 简历自动化下载 Skill

本 Skill 为 AI 助手提供“有手有脚”的完整工具能力，专门用于在 Windows 桌面自动化批量获取 BOSS 直聘客户端的应聘者简历，支持自定义日期范围、精准三级下载优先级，以及彻底杜绝漏检的防跳动滑动重叠算法。

---

## 核心能力与工具箱

Skill 包含以下可直接在终端调用的辅助工具（位于 `scripts/`）：

| 工具脚本 | 作用说明 | 典型调用命令 |
| :--- | :--- | :--- |
| [download_resumes.py](./scripts/download_resumes.py) | **主执行工具**：自动遍历候选人、下载简历至目标目录并支持截止日期 | `python download_resumes.py --cutoff-date 09-24 --dest-dir D:\简历` |
| [diagnose.py](./scripts/diagnose.py) | **环境诊断工具**：检查分辨率、BOSS窗口状态、按钮色块检测与模板 | `python diagnose.py` |
| [list_resumes.py](./scripts/list_resumes.py) | **归档统计工具**：查看已下载简历列表、大小、岗位分类及下载时间 | `python list_resumes.py --dir D:\简历` |

资源文件：
* [download_btn_crop.png](./resources/download_btn_crop.png)：聊天卡片下载图标匹配模板。
* [workflow_guide.md](./references/workflow_guide.md)：完整技术参数、坐标与防漏检滚动数学模型。

---

## 执行规程与三级规则

### 1. 三级优先级判定流程
1. **优先级 1（聊天卡片）**：检查右侧聊天流中是否包含附件卡片。若包含，直接点击卡片右侧下载按钮。
2. **优先级 2（右上角【附件简历】弹窗）**：
   * 检查右上角区域（坐标 `(2435, 85)` 周围）是否为激活紫蓝色（RGB `115, 131, 255`）；
   * 点击弹出预览大图；
   * 点击大图右上角下载件图标 `[↓]`（坐标 `(1580, 59)`）；
   * 捕获另存为窗口并确认，随后发送 `Esc` 关闭弹窗。
3. **优先级 3（跳过）**：若无附件卡片且右上角为浅灰色（RGB `245, 246, 255`），直接跳过。

### 2. 防漏检重叠滑动机制 (Anti-Skipping)
* 每批扫描 **12 个槽位**（Y=138 至 Y=952）。
* 滚动步长控制为 **2 次 `scroll(-600)`**（位移约 9.7 个候选人）。
* 批次之间保留 **约 2.3 个候选人的重叠安全缓冲**，绝不进行大跨步跳跃。
* 配合右侧标题栏候选人姓名 OCR 去重，重叠项瞬间识别跳过，杜绝遗漏与重复下载。

---

## AI 调度与使用指南

当用户要求“下载简历到某月某号”或“批量获取某范围简历”时，AI 应按照以下步骤执行：

### 步骤 1：运行环境诊断
在执行下载前，建议运行自检脚本确保 BOSS 客户端就绪：
```bash
python .agents/skills/boss-resume-downloader/scripts/diagnose.py
```

### 步骤 2：启动自动化下载
根据用户指定的目标截止日期与保存目录执行：
```bash
# 示例 1: 扫描下载至 9月24日（超出 9月24日 自动停止）
python .agents/skills/boss-resume-downloader/scripts/download_resumes.py --cutoff-date 09-24 --dest-dir D:\简历

# 示例 2: 扫描下载至 10月01日
python .agents/skills/boss-resume-downloader/scripts/download_resumes.py --cutoff-date 10-01 --dest-dir D:\简历
```

### 步骤 3：验证与汇总交付
下载任务结束后，运行归档统计工具向用户报告：
```bash
python .agents/skills/boss-resume-downloader/scripts/list_resumes.py --dir D:\简历
```
