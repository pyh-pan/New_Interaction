# New Interaction Agent 指南

## 文档边界

`AGENTS.md` 只记录开发规范、工程边界和协作规则。产品定位、交互细节、路线图和功能取舍以 `docs/prd.md` 为准；不要把具体产品实现方案重复写进本文件。

## 项目结构

- 运行入口：`src/new_interaction/app.py`
- 手势状态机：`src/new_interaction/gestures.py`
- 摄像头与 MediaPipe 集成：`src/new_interaction/camera.py`
- 鼠标事件注入：`src/new_interaction/input_controller.py`
- 测试目录：`tests/`
- 产品文档：`docs/prd.md`
- 架构说明：`docs/architecture.md`
- 运行手册：`docs/runbook.md`

## 本地开发

- 使用 Python 3.11。本地默认解释器是 Homebrew Python：`/opt/homebrew/bin/python3.11`。
- 安装依赖：`.venv/bin/python -m pip install -e ".[dev]"`。
- 运行测试：`.venv/bin/python -m pytest -v`。
- 提交前至少运行相关测试；涉及共享行为、状态机或输入注入时，运行完整测试。

## 工程边界

- 摄像头画面、手部关键点和鼠标事件都必须保持本地处理。
- 没有明确产品批准时，不要加入上传、遥测、截图、视频或关键点持久化。
- 真实鼠标控制必须由显式配置开启，默认路径应保持可观察、低风险。
- 保留传统鼠标/触控板接管能力，不能阻止用户重新取得系统控制权。
- 涉及 macOS 权限、PyAutoGUI 注入或摄像头访问的改动，必须同步检查 `docs/runbook.md`。

## 测试要求

- 修改 CLI 参数或运行入口时，更新并运行 `tests/test_app.py`。
- 修改摄像头适配时，更新并运行 `tests/test_camera.py`。
- 修改手势状态机时，更新并运行 `tests/test_gestures.py`。
- 修改输入注入时，更新并运行 `tests/test_input_controller.py`。
- 对跨模块行为改动，运行 `.venv/bin/python -m pytest -v`。

## 文档规则

- 命令、安装流程或面向用户的运行方式变化时，更新 `README.md`。
- 数据流、状态机边界或模块职责变化时，更新 `docs/architecture.md`。
- 权限、常用参数、失败模式或排障步骤变化时，更新 `docs/runbook.md`。
- 产品方向、交互语义、路线图和商业化阶段决策写入 `docs/prd.md`。
- 不要在项目文档中使用“今天”“刚刚”“最近”等相对时间。
