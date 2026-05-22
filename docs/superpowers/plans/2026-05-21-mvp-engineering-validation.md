# MVP 工程验证实现计划

> **给 agentic workers：** 必须使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans，按任务逐步执行本计划。步骤使用 checkbox（`- [ ]`）语法追踪。

**目标：** 构建一个 Python 工程验证原型，验证 macOS 摄像头访问、实时手势识别和基础鼠标交互。

**架构：** 将 computer vision、手势状态和鼠标注入解耦。可测试核心是纯手势状态机；运行循环负责把摄像头帧接到 MediaPipe 关键点，再接到输入 backend。

**技术栈：** Python 3.11、OpenCV、MediaPipe、PyAutoGUI、pytest。

---

## 文件结构

- `pyproject.toml`：项目元数据、依赖和 pytest 配置。
- `README.md`：本地安装、权限说明和运行命令。
- `src/new_interaction/__init__.py`：package marker。
- `src/new_interaction/gestures.py`：纯手部关键点模型、手势分类和交互状态机。
- `src/new_interaction/input_controller.py`：dry-run 与 PyAutoGUI 鼠标 backend。
- `src/new_interaction/camera.py`：摄像头捕获和 MediaPipe 手部关键点 adapter。
- `src/new_interaction/app.py`：工程验证原型的 CLI 运行循环。
- `tests/test_gestures.py`：覆盖点击、双击、拖拽、滚动、暂停和手部丢失行为的 TDD 测试。

## 任务

### Task 1：手势状态机

**文件：**
- 创建：`tests/test_gestures.py`
- 创建：`src/new_interaction/gestures.py`

- [ ] 为单击、双击、拖拽、滚动、暂停和手部丢失行为编写失败测试。
- [ ] 运行 `PYTHONPATH=src /opt/homebrew/bin/python3.11 -m pytest tests/test_gestures.py -v`，确认测试因 `new_interaction.gestures` 不存在而失败。
- [ ] 在 `gestures.py` 中实现最小纯状态机。
- [ ] 再次运行测试并确认通过。

### Task 2：输入 Backend

**文件：**
- 创建：`src/new_interaction/input_controller.py`

- [ ] 添加 dry-run backend，在不控制系统的情况下记录或打印鼠标事件。
- [ ] 添加 PyAutoGUI backend，在显式启用时支持移动、点击、双击、拖拽和滚动。
- [ ] 保持 dry-run 为默认运行路径。

### Task 3：摄像头与手部关键点

**文件：**
- 创建：`src/new_interaction/camera.py`

- [ ] 添加 OpenCV 摄像头捕获。
- [ ] 添加 MediaPipe Hand Landmarker 集成。
- [ ] 将 MediaPipe landmarks 转换成状态机使用的纯 `HandFrame` 结构。
- [ ] 当摄像头访问或依赖缺失时，打印清晰错误。

### Task 4：CLI 运行时

**文件：**
- 创建：`src/new_interaction/app.py`
- 创建：`src/new_interaction/__init__.py`
- 创建：`pyproject.toml`
- 创建：`README.md`

- [ ] 添加 `python -m new_interaction.app` 入口。
- [ ] 默认支持 `--dry-run`，并通过 `--control` 启用真实鼠标事件注入。
- [ ] 支持 `--camera-index`、`--show-preview`、`--max-fps` 和手势调参选项。
- [ ] 记录 macOS Camera 与 Accessibility 权限说明。

### Task 5：验证

**文件：**
- 根据失败情况按需修改。

- [ ] 使用 Python 3.11 运行测试。
- [ ] 运行 CLI help。
- [ ] 运行依赖导入检查。
- [ ] 如果无法访问硬件，记录用于摄像头验证的精确手动命令。
