# 🔥 火柴人绘制工具 (Stickman Drawer)

一款 Windows 原生多窗口桌面应用，通过 AI（DeepSeek）生成火柴人坐标数据，自动渲染为 PNG、GIF 动画或 PNG 序列。

---

## ✨ 功能特性

- 🎨 **AI 辅助生成**：内置 DeepSeek Prompt 模板，一键复制粘贴获取坐标
- 🖼️ **三种输出格式**：单图 PNG / GIF 动画 / PNG 序列
- 📐 **自定义关节点**：头部朝向、左右臂腿、髋膝踝完整建模
- 🏋️ **手持物品支持**：可绘制哑铃（dumbbell）和杠铃（barbell）
- 💾 **历史记录管理**：所有生成结果自动归档，支持预览 / 删除 / 复制 JSON
- 🪟 **多窗口架构**：主窗口 + 新建窗口 + 历史浏览 + 提示词窗口独立 Toplevel
- 🌐 **原生 Windows 体验**：DPI 感知、任务栏分组、无控制台启动

---

## 📸 界面预览

### 主窗口
- 菜单栏：文件 / 工具 / 帮助
- 三个快速入口：新建火柴人 / 浏览历史 / 查看 Prompt
- 底部状态栏：显示历史保存路径

### 新建火柴人窗口
- 工具栏：加载文件 / 粘贴 / 清空 / 示例数据
- JSON 输入区（占据中间主要空间）
- 输出格式：自动 / GIF 动画 / PNG 序列 / 单图 PNG
- 操作按钮：生成 / 关闭

### 历史浏览窗口
- 左侧记录列表（按时间倒序）
- 右侧图片预览 + JSON 原始数据
- 操作：打开文件夹 / 复制 JSON / 删除 / 刷新

### 启动画面
- 火柴人走路动画 + 挥手告别
- 自动关闭后进入主流程

---

## 🚀 快速开始

### 环境要求

- **操作系统**：Windows 10/11
- **Python**：3.8 或更高版本
- **依赖包**：
  - `matplotlib` ≥ 3.5
  - `numpy` ≥ 1.20
  - `Pillow` ≥ 9.0

### 安装

```powershell
# 克隆仓库
git clone https://github.com/fatblue/stickman-drawer.git
cd stickman-drawer

# 安装依赖
pip install -r requirements.txt
```

### 启动

**方式一**（推荐，无控制台）：
```powershell
# 双击 启动.bat
```

**方式二**（命令行）：
```powershell
pythonw drawstickman.py
```

**方式三**（带控制台，可看错误信息）：
```powershell
python drawstickman.py
```

### 环境诊断

如遇启动问题，运行诊断：
```powershell
启动.bat --diagnose
```
或：
```powershell
python drawstickman.py --diagnose
```

会检查 Python / tkinter / matplotlib / Pillow / numpy / Windows API 等环境并写入 `diagnose.log`。

---

## 📖 使用流程

### 第一次使用

1. 启动程序 → 出现启动画面（火柴人走路动画，约 5 秒）
2. 自动弹出 **Prompt 提示窗口**
   - 点击「📋 复制全部」复制 Prompt 模板
   - 点击「🔗 打开 DeepSeek」打开浏览器
   - 在 DeepSeek 中粘贴 Prompt，**替换最下方的动作描述**为你想要的动作（例：一个火柴人跑步）
   - 发送后，复制 DeepSeek 返回的 **JSON 数据**
3. 关闭 Prompt 窗口 → 进入主窗口
4. 菜单「文件」→「新建火柴人」（或按 `Ctrl+N`）
5. 在新窗口中 **粘贴 JSON 数据**
6. 输入动作描述（便于以后查找）
7. 选择输出格式（默认自动）
8. 点击「🎨 生成」
9. 完成后询问是否打开保存目录

### 后续使用

- 菜单「文件」→「浏览历史」查看已生成的作品
- 菜单「工具」→「查看 Prompt 模板」随时调出提示词
- `Ctrl+N` 快捷键打开新建窗口

---

## 📐 JSON 数据格式

### 坐标字段说明

画布尺寸：**800 × 1000**（左上角为原点 `(0,0)`，x 向右，y 向下）

| 字段 | 类型 | 说明 |
|---|---|---|
| `head_center` | `[x, y]` | 头部圆心 |
| `head_angle` | `number` | 朝向角度（0=右，90=下，180=左，270=上）|
| `neck` | `[x, y]` | 脖子点 |
| `hip` | `[x, y]` | 髋部中心 |
| `left_shoulder` | `[x, y]` | 左肩 |
| `left_elbow` | `[x, y]` | 左肘 |
| `left_wrist` | `[x, y]` | 左腕 |
| `right_shoulder` | `[x, y]` | 右肩 |
| `right_elbow` | `[x, y]` | 右肘 |
| `right_wrist` | `[x, y]` | 右腕 |
| `left_hip` | `[x, y]` | 左髋 |
| `left_knee` | `[x, y]` | 左膝 |
| `left_ankle` | `[x, y]` | 左踝 |
| `right_hip` | `[x, y]` | 右髋 |
| `right_knee` | `[x, y]` | 右膝 |
| `right_ankle` | `[x, y]` | 右踝 |
| `left_hand_item` | `null \| "dumbbell" \| "barbell"` | 左手持物 |
| `right_hand_item` | `null \| "dumbbell" \| "barbell"` | 右手持物 |

### 单帧示例（静态图）

```json
{
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
  "left_hand_item": null,
  "right_hand_item": null
}
```

### 多帧示例（动画）

```json
[
  { "head_center": [400, 150], "head_angle": 0, ... },
  { "head_center": [400, 145], "head_angle": 5, ... },
  { "head_center": [400, 150], "head_angle": 0, ... },
  { "head_center": [400, 155], "head_angle": -5, ... }
]
```

帧数建议 4-12 帧，帧间动作连贯。

---

## 📁 项目结构

```
stickman-drawer/
├── drawstickman.py       # 主程序（45 KB）
├── drawstickman.prompt   # DeepSeek Prompt 模板
├── 启动.bat              # Windows 启动器
├── requirements.txt      # 依赖列表
├── README.md             # 本文件
├── LICENSE               # Apache 2.0 协议
├── .gitignore            # Git 忽略规则
└── history/              # 历史记录（运行时生成，已 gitignore）
    └── 20260601_120000/
        ├── data.json
        ├── description.txt
        └── stickman.png / stickman.gif / stickman_001.png ...
```

---

## 🛠️ 技术栈

- **GUI**：Python 内置 `tkinter`（含 ttk 主题）
- **渲染**：`matplotlib`（Agg 后端） + `Pillow`
- **动画**：`matplotlib.animation.FuncAnimation`
- **Windows 集成**：`ctypes` 调用 shell32（DPI 感知、任务栏分组）
- **Prompt 工程**：`drawstickman.prompt` 内置详细规格说明

---

## ❓ 常见问题

**Q: 双击 启动.bat 闪退？**
A: 改用 `python drawstickman.py` 看错误，或运行 `启动.bat --diagnose` 检查环境。

**Q: 启动后没有窗口？**
A: 检查是否有其他程序占用 tkinter 资源；或任务管理器中杀掉残留的 `pythonw.exe` 进程。

**Q: DeepSeek 返回的 JSON 无法解析？**
A: 通常是 DeepSeek 把 JSON 包在了 markdown 代码块里（```` ```json ````）。让 DeepSeek「只返回纯 JSON，不要 markdown」。

**Q: 生成的图片不符合预期？**
A: 调整 Prompt 中的动作描述，让 AI 更详细地说明各关节位置。

**Q: 想打包成 exe？**
A: 使用 PyInstaller：
```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name=stickman drawstickman.py
```

---

## 📜 开源协议

本项目基于 **Apache License 2.0** 开源，详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- [matplotlib](https://matplotlib.org/) - 强大的 Python 绘图库
- [Pillow](https://python-pillow.org/) - 友好的图像处理库
- [DeepSeek](https://chat.deepseek.com/) - 智能的 AI 对话助手
- [tkinter](https://docs.python.org/3/library/tkinter.html) - Python 标准 GUI 库

---

## 📮 反馈

欢迎提 Issue / PR 改进本项目！

- GitHub: <https://github.com/fatblue/stickman-drawer>
- Email: fatblue@qq.com
