#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火柴人绘制工具 - 原生 Windows 多窗口程序

启动方式（任选其一）：
  1. 双击 启动.bat
  2. 命令行执行: pythonw.exe drawstickman.py
  3. 命令行执行: python drawstickman.py （会显示控制台）
"""
import sys
import os
import json
import shutil
import webbrowser
from datetime import datetime
from pathlib import Path

# ============== Windows 特定设置 ==============
if sys.platform == 'win32':
    import ctypes
    # 让 Windows 7+ 任务栏正确分组（避免多个 Python 进程图标）
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Stickman.Drawer.Tool.1.0')
    except Exception:
        pass
    # 高 DPI 感知，避免界面模糊
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# matplotlib 用 Agg 后端（纯文件输出，无需显示）
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle, Wedge, Ellipse, Rectangle
import numpy as np

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ============== 常量 ==============
APP_TITLE = "火柴人绘制工具"
APP_VERSION = "1.0"

CANVAS_WIDTH = 800
CANVAS_HEIGHT = 1000
HEAD_RADIUS = 25
LINE_WIDTH = 4
COLOR = 'black'
ITEM_COLOR = 'gray'

APP_DIR = Path(__file__).resolve().parent
HISTORY_DIR = APP_DIR / 'history'
HISTORY_DIR.mkdir(exist_ok=True)
PROMPT_FILE = APP_DIR / 'drawstickman.prompt'
ICON_FILE = APP_DIR / 'stickman.ico'
LOG_FILE = APP_DIR / 'startup.log'


# 默认 Prompt（与 drawstickman.prompt 同步，作为 fallback）
DEFAULT_PROMPT = """你是一个火柴人动画数据生成助手。请严格按照以下规格，将用户描述的动作转换为 JSON 格式的火柴人姿势数据。

## 画布与坐标系
- 画布尺寸：宽 800，高 1000，左上角为原点 (0,0)，x 向右增加，y 向下增加。
- 所有坐标均为整数。

## 火柴人关键点定义
每一帧必须包含以下关键点（均为 [x, y] 数组）：
- head_center: 头部圆心坐标（半径固定为25，由绘图程序自动绘制）
- head_angle: 头部朝向角度（0=向右，90=向下，180=向左，270=向上）
- neck: 脖子点（连接头部与身体）
- hip: 髋部中心点
- left_shoulder, left_elbow, left_wrist: 左臂三关节点（肩、肘、腕）
- right_shoulder, right_elbow, right_wrist: 右臂三关节点
- left_hip, left_knee, left_ankle: 左腿三关节点（髋、膝、踝）
- right_hip, right_knee, right_ankle: 右腿三关节点
- left_hand_item: 左手持有物品，null 或物品名称（可选值：null, "dumbbell", "barbell"）
- right_hand_item: 右手持有物品，同上

## 身体连接规则（由绘图程序固定完成，你只需提供坐标）
- 头：以 head_center 为圆心画圆，根据 head_angle 绘制扇形指示面部朝向。
- 身体：neck 连 hip。
- 肩膀连接：neck 分别连 left_shoulder 和 right_shoulder。
- 手臂：肩→肘→腕，折线连接（可表现弯曲）。
- 腿：髋→膝→踝，折线连接（可表现弯曲）。
- 手持物品：若 hand_item 不为 null，在腕关节坐标处绘制对应物品图形。

## 输出要求
- 若用户需要单张静态图，输出一个帧对象 {}。
- 若用户需要多帧动画，输出帧数组 [{}, {}, ...]。
- 帧数建议 4-12 帧，帧间动作连贯，符合物理规律。
- **保持身体比例自然**：头部约占全身高度 1/7，上臂+前臂长度约等于躯干长度，大腿+小腿长度约等于躯干长度。
- **关节弯曲角度符合人体限度**：肘部弯曲角度不小于 30 度，膝盖弯曲角度不小于 45 度，不允许出现反关节（如膝盖向后弯）。
- **重心稳定**：站立时髋部应位于双脚支撑面中心的上方；运动过程中重心过渡平滑，避免瞬间跳动。
- **细节生动**：手腕和脚踝应随动作有微小的自然角度变化，避免所有关节完全僵直排列。
- 只输出纯 JSON，不要任何解释、不要 markdown 标记，不要前后缀文字。
- JSON 必须有效，可直接解析。

## 动作描述（用户提供）
{在这里输入你对火柴人动作的自然语言描述}
"""


def log_exception(exc):
    """将异常写入日志文件（pythonw.exe 静默崩溃时用于排查）"""
    try:
        import traceback
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n[{datetime.now().isoformat()}] 未捕获异常:\n")
            traceback.print_exc(file=f)
    except Exception:
        pass

CN_FONT = ('Microsoft YaHei', 10)
CN_FONT_BOLD = ('Microsoft YaHei', 10, 'bold')
CN_FONT_TITLE = ('Microsoft YaHei', 14, 'bold')
CN_FONT_HEADER = ('Microsoft YaHei', 12, 'bold')
CN_FONT_BIG = ('Microsoft YaHei', 18, 'bold')
CODE_FONT = ('Consolas', 10)
CODE_FONT_SMALL = ('Consolas', 9)


# ============== 渲染函数 ==============
def draw_dumbbell(ax, center, size=22):
    """美化哑铃：金属横杠 + 两端球体（渐变高光）"""
    x, y = center
    r = size / 4
    bar_len = size * 1.1

    # 金属横杠
    ax.add_patch(Rectangle((x - bar_len / 2, y - r * 0.25), bar_len, r * 0.5,
                           facecolor='#888', edgecolor='#333', lw=1, zorder=2))
    # 横杠高光
    ax.add_patch(Rectangle((x - bar_len / 2, y - r * 0.15), bar_len, r * 0.12,
                           facecolor='#bbb', edgecolor='none', zorder=3))

    # 两端球体
    for sign in (-1, 1):
        bx, by = x + sign * bar_len / 2, y
        # 球体主体
        ax.add_patch(Circle((bx, by), r, facecolor='#1a1a1a',
                            edgecolor='black', lw=1.2, zorder=4))
        # 球体反光（渐变层）
        ax.add_patch(Circle((bx - r * 0.25, by - r * 0.25), r * 0.6,
                            facecolor='#555', edgecolor='none', alpha=0.85, zorder=5))
        # 高光点
        ax.add_patch(Circle((bx - r * 0.4, by - r * 0.4), r * 0.25,
                            facecolor='white', edgecolor='none', alpha=0.6, zorder=6))


def draw_barbell(ax, center, size=30):
    """美化杠铃：金属横杠 + 两端杠铃片（多层 + 纹路）"""
    x, y = center
    bar_len = size * 1.8
    weight_r = size / 3

    # 金属横杠
    ax.add_patch(Rectangle((x - bar_len / 2, y - weight_r * 0.2), bar_len, weight_r * 0.4,
                           facecolor='#999', edgecolor='#444', lw=1, zorder=2))
    # 横杠高光
    ax.add_patch(Rectangle((x - bar_len / 2, y - weight_r * 0.1), bar_len, weight_r * 0.1,
                           facecolor='#ccc', edgecolor='none', zorder=3))

    # 两端杠铃片
    for sign in (-1, 1):
        bx, by = x + sign * bar_len / 2, y
        # 杠铃片外圈
        ax.add_patch(Circle((bx, by), weight_r, facecolor='#1a1a1a',
                            edgecolor='black', lw=1.5, zorder=4))
        # 杠铃片中圈（亮一些模拟金属光泽）
        ax.add_patch(Circle((bx, by), weight_r * 0.75, facecolor='#666',
                            edgecolor='#333', lw=0.8, zorder=5))
        # 中心轴孔
        ax.add_patch(Circle((bx, by), weight_r * 0.15, facecolor='#1a1a1a',
                            edgecolor='black', lw=0.5, zorder=6))
        # 纹路：4 条短刻度线
        for ang_deg in (0, 90, 180, 270):
            rad = np.radians(ang_deg)
            r1 = weight_r * 0.4
            r2 = weight_r * 0.88
            x1 = bx + r1 * np.cos(rad)
            y1 = by + r1 * np.sin(rad)
            x2 = bx + r2 * np.cos(rad)
            y2 = by + r2 * np.sin(rad)
            ax.plot([x1, x2], [y1, y2], color='black', lw=0.7, zorder=7)


def draw_shadow(ax, frame):
    """地面阴影：在双脚下方画半透明椭圆"""
    left_ankle = frame.get('left_ankle')
    right_ankle = frame.get('right_ankle')
    if not (left_ankle and right_ankle):
        return
    # 阴影中心：两脚中点
    cx = (left_ankle[0] + right_ankle[0]) / 2
    cy = max(left_ankle[1], right_ankle[1]) + 12
    # 阴影大小
    foot_span = abs(left_ankle[0] - right_ankle[0])
    w = max(120, foot_span + 60)
    h = w * 0.18
    shadow = Ellipse((cx, cy), w, h, facecolor='black',
                     edgecolor='none', alpha=0.12, zorder=0)
    ax.add_patch(shadow)


def draw_joint(ax, center, size=5, color='#2c3e50', alpha=0.8):
    """画关节点小圆"""
    x, y = center
    ax.add_patch(Circle((x, y), size, facecolor=color, edgecolor='none', alpha=alpha))


def draw_head(ax, center, angle=0):
    """升级头部：圆 + 眼睛 + 鼻子"""
    x, y = center
    # 头部圆
    head = Circle((x, y), HEAD_RADIUS, edgecolor='#2c3e50', facecolor='white', lw=3)
    ax.add_patch(head)
    # 眼睛：两个小圆，根据角度偏移
    dx = 8 * np.cos(np.radians(angle))
    dy = -8 * np.sin(np.radians(angle))  # 坐标系y向下，角度0向右
    eye_offset = np.array([dx, dy])
    perp = np.array([-dy, dx]) * 0.4  # 垂直方向偏移
    eye_left = np.array([x, y]) + eye_offset + perp
    eye_right = np.array([x, y]) + eye_offset - perp
    ax.add_patch(Circle(eye_left, 3, color='#2c3e50'))
    ax.add_patch(Circle(eye_right, 3, color='#2c3e50'))
    # 鼻子（短线）
    nose_tip = np.array([x, y]) + eye_offset * 1.5
    ax.plot([x + dx*1.2, nose_tip[0]], [y + dy*1.2, nose_tip[1]], color='#2c3e50', lw=2)


def draw_stickman(ax, frame):
    # 阴影（最底层）
    draw_shadow(ax, frame)

    # 身体主干（最深色）
    neck = frame.get('neck')
    hip = frame.get('hip')
    if neck and hip:
        ax.plot([neck[0], hip[0]], [neck[1], hip[1]],
                color='#1a252f', lw=6, solid_capstyle='round', zorder=2)

    # 四肢通用函数（稍浅色）
    def draw_limb(joints, is_leg=False):
        xs, ys = zip(*joints)
        ax.plot(xs, ys, color='#34495e', lw=5, solid_capstyle='round', zorder=2)
        for j in joints[1:-1]:  # 中间关节
            draw_joint(ax, j, color='#1a252f')
        if is_leg:
            # 脚：在末端画小椭圆 + 方向短线（脚趾朝向）
            end_x, end_y = joints[-1]
            ax.add_patch(Ellipse((end_x, end_y + 2), 12, 6, angle=0,
                                 facecolor='#1a252f', edgecolor='none', zorder=3))
            # 脚趾方向
            knee = joints[-2]
            toe_dx = end_x - knee[0]
            toe_dy = end_y - knee[1]
            toe_len = 8
            tx2 = end_x + toe_dx * 0.3
            ty2 = end_y + toe_dy * 0.3
            ax.plot([end_x, tx2], [end_y, ty2], color='#1a252f', lw=4,
                    solid_capstyle='round', zorder=3)
        else:
            # 手：小圆点（带方向感，size 稍大）
            draw_joint(ax, joints[-1], size=6, color='#1a252f')

    # 左臂
    left_shoulder = frame.get('left_shoulder')
    left_elbow = frame.get('left_elbow')
    left_wrist = frame.get('left_wrist')
    if left_shoulder and left_elbow and left_wrist:
        draw_limb([left_shoulder, left_elbow, left_wrist], is_leg=False)
        item = frame.get('left_hand_item')
        if item == 'dumbbell':
            draw_dumbbell(ax, left_wrist)
        elif item == 'barbell':
            draw_barbell(ax, left_wrist)

    # 右臂
    right_shoulder = frame.get('right_shoulder')
    right_elbow = frame.get('right_elbow')
    right_wrist = frame.get('right_wrist')
    if right_shoulder and right_elbow and right_wrist:
        draw_limb([right_shoulder, right_elbow, right_wrist], is_leg=False)
        item = frame.get('right_hand_item')
        if item == 'dumbbell':
            draw_dumbbell(ax, right_wrist)
        elif item == 'barbell':
            draw_barbell(ax, right_wrist)

    # 左腿
    left_hip = frame.get('left_hip')
    left_knee = frame.get('left_knee')
    left_ankle = frame.get('left_ankle')
    if left_hip and left_knee and left_ankle:
        draw_limb([left_hip, left_knee, left_ankle], is_leg=True)

    # 右腿
    right_hip = frame.get('right_hip')
    right_knee = frame.get('right_knee')
    right_ankle = frame.get('right_ankle')
    if right_hip and right_knee and right_ankle:
        draw_limb([right_hip, right_knee, right_ankle], is_leg=True)

    # 肩部连接
    if neck and left_shoulder:
        ax.plot([neck[0], left_shoulder[0]], [neck[1], left_shoulder[1]],
                color='#34495e', lw=3, solid_capstyle='round', zorder=2)
    if neck and right_shoulder:
        ax.plot([neck[0], right_shoulder[0]], [neck[1], right_shoulder[1]],
                color='#34495e', lw=3, solid_capstyle='round', zorder=2)

    # 头部
    head_center = frame.get('head_center', [400, 300])
    head_angle = frame.get('head_angle', 0)
    draw_head(ax, head_center, head_angle)


def create_canvas():
    fig, ax = plt.subplots(figsize=(CANVAS_WIDTH / 100, CANVAS_HEIGHT / 100), dpi=100)
    ax.set_xlim(0, CANVAS_WIDTH)
    ax.set_ylim(CANVAS_HEIGHT, 0)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.tight_layout(pad=0)
    return fig, ax


def generate_static_image(frame, output_path='stickman.png'):
    fig, ax = create_canvas()
    draw_stickman(ax, frame)
    fig.savefig(output_path, bbox_inches='tight', pad_inches=0.1,
                dpi=150, transparent=True)
    plt.close(fig)
    return output_path


def generate_animation(frames, output_path='stickman.gif', fps=10):
    fig, ax = create_canvas()

    def update(i):
        ax.clear()
        ax.set_xlim(0, CANVAS_WIDTH)
        ax.set_ylim(CANVAS_HEIGHT, 0)
        ax.set_aspect('equal')
        ax.axis('off')
        draw_stickman(ax, frames[i])

    anim = animation.FuncAnimation(fig, update, frames=len(frames),
                                   interval=1000 / fps, repeat=True)
    anim.save(output_path, writer='pillow', fps=fps, dpi=100)
    plt.close(fig)
    return output_path


def generate_png_sequence(frames, output_dir, base_name='stickman'):
    paths = []
    for i, frame in enumerate(frames):
        path = os.path.join(output_dir, f"{base_name}_{i + 1:03d}.png")
        generate_static_image(frame, path)
        paths.append(path)
    return paths


# ============== 工具函数 ==============
def center_window(win, w, h):
    """将窗口居中显示"""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


def try_set_icon(win):
    """尝试设置窗口图标（如果有 .ico 文件）"""
    if ICON_FILE.exists():
        try:
            win.iconbitmap(str(ICON_FILE))
        except Exception:
            pass


# ============== 启动画面 ==============
class SplashWindow:
    def __init__(self, parent, on_close):
        self.on_close = on_close

        self.win = tk.Toplevel(parent)
        self.win.title(APP_TITLE)
        self.win.overrideredirect(True)  # 无边框
        self.win.attributes('-topmost', True)

        w, h = 600, 400

        self.canvas = tk.Canvas(self.win, width=w, height=h,
                                bg='#87CEEB', highlightthickness=0)
        self.canvas.pack()

        # 内容创建后再设几何（确保窗口管理器接受该尺寸）
        self.win.update_idletasks()
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        # 地面
        self.canvas.create_rectangle(0, h - 50, w, h, fill='#8B4513', outline='')
        # 房子
        self.canvas.create_rectangle(200, 150, 350, 300, fill='saddlebrown',
                                     outline='black', width=3)
        self.canvas.create_rectangle(300, 200, 340, 290, fill='tan',
                                     outline='black', width=2)
        self.canvas.create_oval(325, 220, 335, 230, fill='gold', outline='black')

        # 动画状态
        self.stickman_x = 180
        self.wave_angle = 0
        self.wave_dir = 1
        self.frame = 0

        self._draw_figure()
        self._animate()

    def _draw_figure(self):
        self.canvas.delete('stickman')
        x, y = self.stickman_x, 200
        # 头
        self.canvas.create_oval(x - 15, y - 60, x + 15, y - 30,
                                outline='black', width=3, fill='white',
                                tags='stickman')
        # 躯干
        self.canvas.create_line(x, y - 30, x, y + 50, width=4,
                                fill='black', tags='stickman')
        # 左臂
        self.canvas.create_line(x, y - 20, x - 40, y + 10, width=3,
                                fill='black', tags='stickman')
        self.canvas.create_line(x - 40, y + 10, x - 50 + self.wave_angle,
                                y + 40, width=3, fill='black', tags='stickman')
        # 右臂
        self.canvas.create_line(x, y - 20, x + 40, y + 10, width=3,
                                fill='black', tags='stickman')
        self.canvas.create_line(x + 40, y + 10, x + 50, y + 40, width=3,
                                fill='black', tags='stickman')
        # 左腿
        self.canvas.create_line(x, y + 50, x - 20, y + 100, width=3,
                                fill='black', tags='stickman')
        self.canvas.create_line(x - 20, y + 100, x - 30, y + 140, width=3,
                                fill='black', tags='stickman')
        # 右腿
        self.canvas.create_line(x, y + 50, x + 20, y + 100, width=3,
                                fill='black', tags='stickman')
        self.canvas.create_line(x + 20, y + 100, x + 30, y + 140, width=3,
                                fill='black', tags='stickman')
        # 欢迎语
        if self.stickman_x >= 380:
            self.canvas.create_text(300, 50, text="欢迎使用火柴人绘制工具！",
                                    font=CN_FONT_BIG, fill='darkblue',
                                    tags='stickman')

    def _animate(self):
        if self.stickman_x < 380:
            self.stickman_x += 8
        else:
            self.wave_angle += 3 * self.wave_dir
            if abs(self.wave_angle) > 20:
                self.wave_dir *= -1

        self._draw_figure()
        self.frame += 1

        if self.frame < 40:
            self.win.after(50, self._animate)
        else:
            self.win.after(500, self._close)

    def _close(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        if self.on_close:
            self.on_close()


# ============== Prompt 提示窗口 ==============
class PromptWindow:
    def __init__(self, parent, on_close=None):
        self.on_close = on_close

        self.win = tk.Toplevel(parent)
        self.win.title("生成火柴人 - Prompt 提示")
        self.win.geometry("800x600")
        center_window(self.win, 800, 600)
        self.win.resizable(True, True)
        try_set_icon(self.win)

        self._build_ui()
        self.win.protocol("WM_DELETE_WINDOW", self._close)

    def _build_ui(self):
        main = ttk.Frame(self.win, padding="15")
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="📋 复制以下内容发送给 DeepSeek",
                  font=CN_FONT_TITLE, foreground='darkblue').pack(pady=10)

        # 使用流程
        hint_frame = ttk.LabelFrame(main, text="使用流程", padding="10")
        hint_frame.pack(fill=tk.X, pady=5)
        hint = ("1. 替换最下方【动作描述】一行的内容（如：一个火柴人跑步）\n"
                "2. 点击「复制全部」按钮\n"
                "3. 点击「打开 DeepSeek」，把复制的内容粘贴进去发送\n"
                "4. 复制 DeepSeek 返回的 JSON 数据\n"
                "5. 关闭此窗口 → 菜单「文件」→「新建火柴人」 → 粘贴 JSON 生成")
        ttk.Label(hint_frame, text=hint, font=CN_FONT, justify=tk.LEFT).pack(fill=tk.X)

        # Prompt 内容
        prompt_frame = ttk.LabelFrame(main, text="Prompt 模板（可编辑）", padding="10")
        prompt_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.prompt_text = scrolledtext.ScrolledText(
            prompt_frame, font=CODE_FONT, wrap=tk.WORD)
        self.prompt_text.pack(fill=tk.BOTH, expand=True)
        self._load_prompt()

        # 按钮
        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="📋 复制全部",
                   command=self._copy_all).grid(row=0, column=0, padx=8)
        ttk.Button(btn_frame, text="🔗 打开 DeepSeek",
                   command=self._open_deepseek).grid(row=0, column=1, padx=8)
        ttk.Button(btn_frame, text="✓ 我已准备好，关闭窗口",
                   command=self._close).grid(row=0, column=2, padx=8)
        ttk.Button(btn_frame, text="⏭ 跳过",
                   command=self._close).grid(row=0, column=3, padx=8)

        self.status = ttk.Label(main, text="", foreground='green')
        self.status.pack(pady=5)

    def _load_prompt(self):
        if PROMPT_FILE.exists():
            content = PROMPT_FILE.read_text(encoding='utf-8')
        else:
            # 文件丢失时使用内置默认（与 drawstickman.prompt 同步）
            content = DEFAULT_PROMPT
        self.prompt_text.insert('1.0', content)

    def _copy_all(self):
        content = self.prompt_text.get('1.0', tk.END).strip()
        self.win.clipboard_clear()
        self.win.clipboard_append(content)
        self.status.config(text="✓ 已复制到剪贴板", foreground='green')

    def _open_deepseek(self):
        webbrowser.open('https://chat.deepseek.com')

    def _close(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        if self.on_close:
            self.on_close()


# ============== 主窗口 ==============
class MainWindow:
    def __init__(self, parent, controller):
        self.controller = controller

        self.win = tk.Toplevel(parent)
        self.win.title(APP_TITLE)
        self.win.geometry("720x520")
        center_window(self.win, 720, 520)
        self.win.minsize(600, 400)
        try_set_icon(self.win)

        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_menu()
        self._build_content()

        # 主窗口显示时，结束 root 的隐藏状态
        self.win.lift()
        self.win.focus_force()

    def _build_menu(self):
        menubar = tk.Menu(self.win)
        self.win.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="新建火柴人...", command=self.open_new_stickman,
                              accelerator="Ctrl+N")
        file_menu.add_command(label="浏览历史", command=self.open_history)
        file_menu.add_separator()
        file_menu.add_command(label="打开历史文件夹", command=self.open_history_folder)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._on_close,
                              accelerator="Alt+F4")

        tool_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tool_menu)
        tool_menu.add_command(label="查看 Prompt 模板", command=self.open_prompt)
        tool_menu.add_command(label="重新查看使用流程", command=self.open_prompt)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)

        # 快捷键
        self.win.bind('<Control-n>', lambda e: self.open_new_stickman())

    def _build_content(self):
        main = ttk.Frame(self.win, padding="20")
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="🔥 火柴人绘制工具",
                  font=CN_FONT_BIG, foreground='darkorange').pack(pady=15)

        info = ("欢迎使用！\n\n"
                "使用流程：\n"
                "  1. 菜单 文件 → 新建火柴人\n"
                "  2. 粘贴坐标数据 (JSON 格式)\n"
                "  3. 选择输出格式 → 点击生成\n\n"
                "或点击下方按钮开始：")
        ttk.Label(main, text=info, font=CN_FONT, justify=tk.LEFT).pack(pady=10)

        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=15)
        ttk.Button(btn_frame, text="📝 新建火柴人",
                   command=self.open_new_stickman).grid(row=0, column=0, padx=12)
        ttk.Button(btn_frame, text="📚 浏览历史",
                   command=self.open_history).grid(row=0, column=1, padx=12)
        ttk.Button(btn_frame, text="📋 查看 Prompt",
                   command=self.open_prompt).grid(row=0, column=2, padx=12)

        # 提示框
        tip = ttk.LabelFrame(main, text="💡 提示", padding="10")
        tip.pack(fill=tk.X, pady=15)
        ttk.Label(tip,
                  text="首次使用建议先点击「查看 Prompt」复制模板，发给 DeepSeek 获取 JSON。",
                  font=CN_FONT, foreground='gray').pack()

        # 状态栏
        self.status = ttk.Label(self.win, text=f"历史记录保存位置: {HISTORY_DIR}",
                                font=CN_FONT, foreground='gray', relief=tk.SUNKEN,
                                anchor=tk.W, padding=(8, 2))
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    # ----- 菜单命令 -----
    def open_new_stickman(self):
        NewStickmanWindow(self.win, self.controller)

    def open_history(self):
        HistoryWindow(self.win, self.controller)

    def open_prompt(self):
        PromptWindow(self.win, on_close=None)

    def open_history_folder(self):
        webbrowser.open(str(HISTORY_DIR))

    def show_help(self):
        text = ("火柴人绘制工具 - 使用说明\n\n"
                "1. 获取 JSON 数据\n"
                "   • 菜单「工具」→「查看 Prompt 模板」\n"
                "   • 替换最下方【动作描述】为你想要的动作\n"
                "   • 复制全部内容，发送给 DeepSeek\n"
                "   • 复制 DeepSeek 返回的纯 JSON 数据\n\n"
                "2. 生成图片\n"
                "   • 菜单「文件」→「新建火柴人」\n"
                "   • 在打开的窗口中粘贴 JSON\n"
                "   • 输入动作描述（便于以后查找）\n"
                "   • 选择输出格式：单图 PNG / GIF 动画 / PNG 序列\n"
                "   • 点击「生成」按钮\n\n"
                "3. 浏览历史\n"
                "   • 菜单「文件」→「浏览历史」\n"
                "   • 可预览图片、查看 JSON、打开文件夹、删除记录\n\n"
                "4. 坐标字段说明（关键点）\n"
                "   • head_center: 头部中心 [x, y]\n"
                "   • head_angle: 朝向角度（0=右，90=下，180=左，270=上）\n"
                "   • neck, hip: 脖子、髋部\n"
                "   • left/right_shoulder, elbow, wrist: 手臂三关节\n"
                "   • left/right_hip, knee, ankle: 腿部三关节\n"
                "   • left/right_hand_item: 手持物（null/dumbbell/barbell）\n"
                "   • 画布尺寸: 800 × 1000，原点在左上，y 向下")
        messagebox.showinfo("使用说明", text, parent=self.win)

    def show_about(self):
        text = (f"{APP_TITLE}\n"
                f"版本: {APP_VERSION}\n\n"
                f"通过 AI 生成火柴人动画/图片\n"
                f"渲染引擎: matplotlib + Pillow\n"
                f"GUI: tkinter\n\n"
                f"历史记录: {HISTORY_DIR}")
        messagebox.showinfo("关于", text, parent=self.win)

    def _on_close(self):
        self.controller.shutdown()


# ============== 新建火柴人窗口 ==============
class NewStickmanWindow:
    def __init__(self, parent, controller):
        self.controller = controller

        self.win = tk.Toplevel(parent)
        self.win.title("新建火柴人 - 粘贴坐标数据")
        self.win.geometry("860x800")
        center_window(self.win, 860, 800)
        self.win.minsize(720, 600)
        try_set_icon(self.win)
        # 关联到主窗口：最小化/关闭时一起动作
        self.win.transient(parent)

        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self.win, padding="15")
        main.pack(fill=tk.BOTH, expand=True)

        # ===== 1. 底部固定区域（先 pack 到 BOTTOM，固定在窗口底部）=====
        # 状态栏
        self.status = ttk.Label(main, text="就绪 - 请粘贴 JSON 数据后点击「生成」",
                                foreground='green', font=CN_FONT)
        self.status.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

        # 操作按钮
        btn_frame = ttk.Frame(main)
        btn_frame.pack(side=tk.BOTTOM, pady=10)
        ttk.Button(btn_frame, text="🎨 生成", command=self._generate
                   ).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="关闭", command=self.win.destroy
                   ).pack(side=tk.LEFT, padx=10)

        # ===== 2. 输出格式（放底部上方）=====
        opt_frame = ttk.LabelFrame(main, text="输出格式", padding="10")
        opt_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=8)

        self.output_type = tk.StringVar(value='auto')
        ttk.Radiobutton(opt_frame, text="自动（单帧→PNG，多帧→GIF）",
                        variable=self.output_type, value='auto'
                        ).grid(row=0, column=0, sticky='w', padx=10, pady=3)
        ttk.Radiobutton(opt_frame, text="GIF 动画（推荐多帧）",
                        variable=self.output_type, value='gif'
                        ).grid(row=0, column=1, sticky='w', padx=10, pady=3)
        ttk.Radiobutton(opt_frame, text="PNG 序列（多张图片）",
                        variable=self.output_type, value='png'
                        ).grid(row=1, column=0, sticky='w', padx=10, pady=3)
        ttk.Radiobutton(opt_frame, text="单图 PNG（强制单帧）",
                        variable=self.output_type, value='single'
                        ).grid(row=1, column=1, sticky='w', padx=10, pady=3)

        # ===== 3. 描述输入（放底部上方）=====
        desc_frame = ttk.Frame(main)
        desc_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=8)
        ttk.Label(desc_frame, text="动作描述：", font=CN_FONT).pack(side=tk.LEFT)
        self.desc_entry = ttk.Entry(desc_frame, font=CN_FONT)
        self.desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

        # ===== 4. 中间可扩展区域（JSON 输入）=====
        input_frame = ttk.LabelFrame(main, text="JSON 数据", padding="8")
        input_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.json_text = scrolledtext.ScrolledText(input_frame, font=CODE_FONT,
                                                   wrap=tk.WORD)
        self.json_text.pack(fill=tk.BOTH, expand=True)

        # ===== 5. 顶部固定区域 =====
        ttk.Label(main, text="📝 粘贴火柴人坐标数据 (JSON)",
                  font=CN_FONT_TITLE).pack(pady=(5, 10))

        # 工具栏
        toolbar = ttk.Frame(main)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(toolbar, text="📂 从文件加载",
                   command=self._load_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📋 从剪贴板粘贴",
                   command=self._paste).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑 清空",
                   command=self._clear).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📑 示例数据",
                   command=self._load_example).pack(side=tk.LEFT, padx=2)
        ttk.Label(toolbar, text="（粘贴 DeepSeek 返回的 JSON 即可）",
                  foreground='gray').pack(side=tk.LEFT, padx=10)

    # ----- 工具栏命令 -----
    def _load_file(self):
        path = filedialog.askopenfilename(
            title="选择 JSON 文件",
            filetypes=[("JSON 文件", "*.json"), ("文本文件", "*.txt"),
                       ("所有文件", "*.*")],
            parent=self.win)
        if not path:
            return
        try:
            content = Path(path).read_text(encoding='utf-8')
            self.json_text.delete('1.0', tk.END)
            self.json_text.insert('1.0', content)
            self.status.config(text=f"✓ 已加载: {os.path.basename(path)}",
                               foreground='green')
        except Exception as e:
            messagebox.showerror("加载失败", str(e), parent=self.win)

    def _paste(self):
        try:
            content = self.win.clipboard_get()
        except tk.TclError:
            self.status.config(text="剪贴板为空", foreground='orange')
            return
        self.json_text.delete('1.0', tk.END)
        self.json_text.insert('1.0', content)
        self.status.config(text="✓ 已从剪贴板粘贴", foreground='green')

    def _clear(self):
        self.json_text.delete('1.0', tk.END)
        self.desc_entry.delete(0, tk.END)
        self.status.config(text="已清空", foreground='green')

    def _load_example(self):
        example = {
            "head_center": [400, 150],
            "head_angle": 0,
            "neck": [400, 200],
            "hip": [400, 600],
            "left_shoulder": [350, 220],
            "left_elbow": [310, 360],
            "left_wrist": [270, 480],
            "right_shoulder": [450, 220],
            "right_elbow": [490, 360],
            "right_wrist": [530, 480],
            "left_hip": [370, 600],
            "left_knee": [350, 780],
            "left_ankle": [330, 950],
            "right_hip": [430, 600],
            "right_knee": [450, 780],
            "right_ankle": [470, 950],
            "left_hand_item": None,
            "right_hand_item": None
        }
        text = json.dumps(example, ensure_ascii=False, indent=2)
        self.json_text.delete('1.0', tk.END)
        self.json_text.insert('1.0', text)
        self.desc_entry.delete(0, tk.END)
        self.desc_entry.insert(0, "示例：站姿火柴人")
        self.status.config(text="✓ 已加载示例数据", foreground='green')

    # ----- 生成 -----
    def _generate(self):
        json_text = self.json_text.get('1.0', tk.END).strip()
        if not json_text:
            messagebox.showwarning("提示", "请输入 JSON 数据",
                                   parent=self.win)
            return
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON 格式错误",
                                 f"无法解析 JSON:\n\n{e}",
                                 parent=self.win)
            return

        desc = self.desc_entry.get().strip() or "未命名"
        output_type = self.output_type.get()

        self.status.config(text="⏳ 正在生成...", foreground='orange')
        self.win.update()

        # 创建保存目录
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        save_dir = HISTORY_DIR / timestamp
        save_dir.mkdir(exist_ok=True)

        # 保存元数据
        (save_dir / 'data.json').write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        (save_dir / 'description.txt').write_text(desc, encoding='utf-8')

        try:
            if isinstance(data, list):
                if not data:
                    raise ValueError("数据为空数组")
                if output_type == 'png':
                    paths = generate_png_sequence(data, str(save_dir))
                    msg = f"✓ PNG 序列已生成（{len(paths)} 张）\n\n保存位置:\n{save_dir}"
                elif output_type == 'gif':
                    path = generate_animation(data, str(save_dir / 'stickman.gif'))
                    msg = f"✓ GIF 动画已生成\n\n保存位置:\n{save_dir}"
                elif output_type == 'single':
                    path = generate_static_image(data[0], str(save_dir / 'stickman.png'))
                    msg = f"✓ PNG 已生成（取第一帧）\n\n保存位置:\n{save_dir}"
                else:  # auto
                    path = generate_animation(data, str(save_dir / 'stickman.gif'))
                    msg = f"✓ GIF 动画已生成（自动）\n\n保存位置:\n{save_dir}"
            elif isinstance(data, dict):
                path = generate_static_image(data, str(save_dir / 'stickman.png'))
                msg = f"✓ PNG 已生成\n\n保存位置:\n{save_dir}"
            else:
                raise ValueError("数据必须是 dict 或 list")

            self.status.config(text="✓ 生成成功", foreground='green')
            # 询问是否打开文件夹
            if messagebox.askyesno("成功", msg + "\n\n是否打开所在文件夹？",
                                   parent=self.win):
                webbrowser.open(str(save_dir))
        except Exception as e:
            self.status.config(text="✗ 生成失败", foreground='red')
            messagebox.showerror("生成失败", str(e), parent=self.win)


# ============== 历史浏览窗口 ==============
class HistoryWindow:
    def __init__(self, parent, controller):
        self.controller = controller

        self.win = tk.Toplevel(parent)
        self.win.title("历史记录浏览")
        self.win.geometry("950x720")
        center_window(self.win, 950, 720)
        self.win.minsize(800, 600)
        try_set_icon(self.win)
        self.win.transient(parent)

        self.current_path = None
        self.photo = None
        self._entry_paths = {}

        self._build_ui()
        self._load_history()

    def _build_ui(self):
        main = ttk.Frame(self.win, padding="10")
        main.pack(fill=tk.BOTH, expand=True)

        paned = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # 左侧：列表
        left = ttk.Frame(paned)
        paned.add(left, weight=1)

        ttk.Label(left, text="历史记录列表", font=CN_FONT_HEADER).pack(pady=5, anchor='w')

        list_frame = ttk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True)
        self.listbox = tk.Listbox(list_frame, font=CN_FONT, activestyle='dotbox')
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                  command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.bind('<<ListboxSelect>>', self._on_select)

        # 右侧：详情
        right = ttk.Frame(paned)
        paned.add(right, weight=3)

        ttk.Label(right, text="详细信息", font=CN_FONT_HEADER).pack(pady=5, anchor='w')
        self.desc_label = ttk.Label(right, text="动作描述：（未选择）",
                                    font=CN_FONT_BOLD, wraplength=600)
        self.desc_label.pack(pady=5, anchor='w')

        # 图片预览
        img_frame = ttk.LabelFrame(right, text="图片预览", padding="5")
        img_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        self.img_canvas = tk.Canvas(img_frame, bg='white', highlightthickness=1,
                                    highlightbackground='#cccccc')
        self.img_canvas.pack(fill=tk.BOTH, expand=True)
        self.img_canvas.bind('<Configure>', lambda e: self._show_image())

        # JSON 数据
        json_frame = ttk.LabelFrame(right, text="原始 JSON 数据", padding="5")
        json_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        self.json_text = scrolledtext.ScrolledText(json_frame, font=CODE_FONT_SMALL,
                                                   wrap=tk.WORD)
        self.json_text.pack(fill=tk.BOTH, expand=True)

        # 按钮
        btn_frame = ttk.Frame(right)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="📂 打开文件夹",
                   command=self._open_folder).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="📋 复制 JSON",
                   command=self._copy_json).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="🗑 删除",
                   command=self._delete).grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text="🔄 刷新",
                   command=self._load_history).grid(row=0, column=3, padx=5)

    def _load_history(self):
        self.listbox.delete(0, tk.END)
        self._entry_paths = {}

        if not HISTORY_DIR.exists():
            return

        entries = []
        for entry in HISTORY_DIR.iterdir():
            if entry.is_dir():
                desc_file = entry / 'description.txt'
                desc = "未命名"
                if desc_file.exists():
                    try:
                        desc = desc_file.read_text(encoding='utf-8').strip() or "未命名"
                    except Exception:
                        pass
                entries.append((entry.name, desc))

        # 按时间倒序
        for i, (name, desc) in enumerate(sorted(entries, key=lambda x: x[0],
                                                reverse=True)):
            display = f"{name}  |  {desc}"
            self.listbox.insert(tk.END, display)
            self._entry_paths[i] = HISTORY_DIR / name

    def _on_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel or sel[0] not in self._entry_paths:
            return
        self.current_path = self._entry_paths[sel[0]]

        # 描述
        desc_file = self.current_path / 'description.txt'
        if desc_file.exists():
            try:
                desc = desc_file.read_text(encoding='utf-8').strip() or "未命名"
            except Exception:
                desc = "未命名"
        else:
            desc = "未命名"
        self.desc_label.config(text=f"动作描述：{desc}")

        # JSON
        json_file = self.current_path / 'data.json'
        self.json_text.delete('1.0', tk.END)
        if json_file.exists():
            try:
                self.json_text.insert('1.0', json_file.read_text(encoding='utf-8'))
            except Exception as e:
                self.json_text.insert('1.0', f"(无法读取: {e})")

        self._show_image()

    def _show_image(self):
        self.img_canvas.delete('all')
        if not self.current_path:
            return
        if not HAS_PIL:
            self.img_canvas.create_text(
                self.img_canvas.winfo_width() // 2,
                self.img_canvas.winfo_height() // 2,
                text="需要安装 Pillow 才能预览图片\npip install Pillow",
                fill='gray', font=CN_FONT, justify=tk.CENTER)
            return

        # 优先 PNG（静态图），其次 GIF
        img_files = sorted([f.name for f in self.current_path.iterdir()
                            if f.suffix.lower() in ('.png', '.gif')])
        # 优先取 PNG
        pngs = [f for f in img_files if f.lower().endswith('.png')]
        target = pngs[0] if pngs else (img_files[0] if img_files else None)
        if not target:
            self.img_canvas.create_text(
                self.img_canvas.winfo_width() // 2,
                self.img_canvas.winfo_height() // 2,
                text="（无图片）", fill='gray', font=CN_FONT)
            return

        try:
            img = Image.open(self.current_path / target)
            cw = max(self.img_canvas.winfo_width(), 100)
            ch = max(self.img_canvas.winfo_height(), 100)
            scale = min(cw / img.width, ch / img.height) * 0.95
            new_size = (max(1, int(img.width * scale)),
                        max(1, int(img.height * scale)))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(img)
            self.img_canvas.create_image(cw // 2, ch // 2, image=self.photo)
        except Exception as e:
            self.img_canvas.create_text(
                self.img_canvas.winfo_width() // 2,
                self.img_canvas.winfo_height() // 2,
                text=f"无法加载: {e}", fill='red', font=CN_FONT)

    def _open_folder(self):
        if self.current_path:
            webbrowser.open(str(self.current_path))
        else:
            messagebox.showwarning("提示", "请先选择一条记录", parent=self.win)

    def _copy_json(self):
        content = self.json_text.get('1.0', tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "没有可复制的 JSON", parent=self.win)
            return
        self.win.clipboard_clear()
        self.win.clipboard_append(content)
        messagebox.showinfo("已复制", "JSON 已复制到剪贴板", parent=self.win)

    def _delete(self):
        if not self.current_path:
            messagebox.showwarning("提示", "请先选择一条记录", parent=self.win)
            return
        if messagebox.askyesno("确认删除",
                               f"确定删除此记录？\n\n{self.current_path}",
                               parent=self.win):
            try:
                shutil.rmtree(self.current_path)
                self._load_history()
                self.img_canvas.delete('all')
                self.json_text.delete('1.0', tk.END)
                self.desc_label.config(text="动作描述：（未选择）")
                self.current_path = None
            except Exception as e:
                messagebox.showerror("删除失败", str(e), parent=self.win)


# ============== 应用控制器 ==============
class App:
    """应用主控制器，管理所有窗口的生命周期与启动流程"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # 隐藏 root，所有窗口都用 Toplevel
        self.root.title(APP_TITLE)
        try_set_icon(self.root)

        self.splash = None
        self.prompt = None
        self.main = None

        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def start(self):
        """启动应用：Splash → Prompt → 主窗口"""
        self._show_splash()

    def _show_splash(self):
        self.splash = SplashWindow(self.root, on_close=self._show_prompt)

    def _show_prompt(self):
        self.splash = None
        self.prompt = PromptWindow(self.root, on_close=self._show_main)

    def _show_main(self):
        self.prompt = None
        self.main = MainWindow(self.root, controller=self)

    def shutdown(self):
        """关闭所有窗口并退出"""
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def run(self):
        self.start()
        self.root.mainloop()


# ============== 命令行测试模式 ==============
def test_render():
    """命令行测试：生成示例火柴人"""
    frame = {
        "head_center": [400, 150],
        "head_angle": 0,
        "neck": [400, 200],
        "hip": [400, 600],
        "left_shoulder": [350, 220],
        "left_elbow": [310, 360],
        "left_wrist": [270, 480],
        "right_shoulder": [450, 220],
        "right_elbow": [490, 360],
        "right_wrist": [530, 480],
        "left_hip": [370, 600],
        "left_knee": [350, 780],
        "left_ankle": [330, 950],
        "right_hip": [430, 600],
        "right_knee": [450, 780],
        "right_ankle": [470, 950],
        "left_hand_item": "dumbbell",
        "right_hand_item": None
    }
    out = APP_DIR / 'test_output.png'
    generate_static_image(frame, str(out))
    print(f"[OK] Generated: {out} ({out.stat().st_size} bytes)")


def diagnose():
    """诊断模式：检查环境并写入日志"""
    out = APP_DIR / 'diagnose.log'
    lines = []
    def p(s=''):
        print(s)
        lines.append(s)
    p('=' * 50)
    p('火柴人绘制工具 - 环境诊断')
    p('=' * 50)
    p(f'时间: {datetime.now().isoformat()}')
    p(f'Python: {sys.version}')
    p(f'平台: {sys.platform}')
    p(f'工作目录: {os.getcwd()}')
    p(f'脚本目录: {APP_DIR}')
    p('')

    # 检查 Python 路径
    p('[1] Python 可执行文件:')
    p(f'    {sys.executable}')
    p('')

    # 检查 tkinter
    p('[2] tkinter 检查:')
    try:
        import tkinter as tk
        from tkinter import ttk
        root = tk.Tk()
        root.withdraw()
        p(f'    [OK] tkinter 可用, Tcl 版本: {root.tk.eval("info patchlevel")}')
        root.destroy()
    except Exception as e:
        p(f'    [FAIL] tkinter 错误: {e}')
        p('    解决: 重新安装 Python 时勾选 "tcl/tk and IDLE"')
    p('')

    # 检查 matplotlib
    p('[3] matplotlib 检查:')
    try:
        import matplotlib
        p(f'    [OK] matplotlib {matplotlib.__version__}')
        p(f'    后端: {matplotlib.get_backend()}')
    except Exception as e:
        p(f'    [FAIL] matplotlib 错误: {e}')
        p('    解决: pip install matplotlib')
    p('')

    # 检查 Pillow
    p('[4] Pillow 检查:')
    try:
        from PIL import Image, ImageTk
        p(f'    [OK] Pillow {Image.__version__}')
    except Exception as e:
        p(f'    [WARN] Pillow 错误: {e}')
        p('    解决（可选）: pip install Pillow')
    p('')

    # 检查 numpy
    p('[5] numpy 检查:')
    try:
        import numpy as np
        p(f'    [OK] numpy {np.__version__}')
    except Exception as e:
        p(f'    [FAIL] numpy 错误: {e}')
        p('    解决: pip install numpy')
    p('')

    # 检查 Windows API
    if sys.platform == 'win32':
        p('[6] Windows API 检查:')
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('test')
            p('    [OK] shell32 可访问')
        except Exception as e:
            p(f'    [WARN] shell32 错误: {e}')

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            p('    [OK] DPI 感知 (Win10/11) 已启用')
        except Exception as e:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                p('    [OK] DPI 感知 (Win8.1) 已启用')
            except Exception as e2:
                p(f'    [INFO] DPI 感知不可用: {e2}')
        p('')

    # 渲染测试
    p('[7] 渲染功能测试:')
    try:
        frame = {"head_center": [400, 150], "head_angle": 0,
                 "neck": [400, 200], "hip": [400, 600],
                 "left_shoulder": [350, 220], "left_elbow": [310, 360],
                 "left_wrist": [270, 480],
                 "right_shoulder": [450, 220], "right_elbow": [490, 360],
                 "right_wrist": [530, 480],
                 "left_hip": [370, 600], "left_knee": [350, 780],
                 "left_ankle": [330, 950],
                 "right_hip": [430, 600], "right_knee": [450, 780],
                 "right_ankle": [470, 950]}
        out_img = APP_DIR / 'diagnose_test.png'
        generate_static_image(frame, str(out_img))
        p(f'    [OK] PNG 渲染成功: {out_img} ({out_img.stat().st_size} bytes)')
    except Exception as e:
        p(f'    [FAIL] 渲染错误: {e}')
    p('')

    p('=' * 50)
    p('诊断完成')

    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'\n诊断结果已保存到: {out}')


# ============== 入口 ==============
def main():
    app = App()
    app.run()


if __name__ == '__main__':
    # 全局异常钩子：pythonw.exe 静默崩溃时写入日志
    def _excepthook(exc_type, exc_value, exc_tb):
        log_exception(exc_value)
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.excepthook = _excepthook

    try:
        if '--test' in sys.argv:
            test_render()
        elif '--diagnose' in sys.argv or '--diag' in sys.argv:
            diagnose()
        else:
            main()
    except Exception as e:
        log_exception(e)
        # 写一个错误标记文件让 启动.bat 能检测到
        try:
            with open(APP_DIR / 'startup_failed.flag', 'w', encoding='utf-8') as f:
                f.write(f"启动失败: {e}\n")
                f.write(f"详细日志: {LOG_FILE}\n")
        except Exception:
            pass
        raise
