# New Interaction Agent 指南

## 项目定位

New Interaction 是一个本地运行、macOS 优先的工程验证原型，用摄像头识别手势并控制鼠标。产品方向是短期作为辅助输入方式，长期形成可商用的手势交互系统，逐步替代传统鼠标。

## 当前实现

- 运行入口：`src/new_interaction/app.py`
- 手势状态机：`src/new_interaction/gestures.py`
- 摄像头与 MediaPipe 集成：`src/new_interaction/camera.py`
- 鼠标事件注入：`src/new_interaction/input_controller.py`
- 测试：`tests/`
- 产品事实来源：`docs/prd.md`
- 架构说明：`docs/architecture.md`
- 运行手册与排障：`docs/runbook.md`

## 开发规则

- 使用 Python 3.11。本地默认解释器是 Homebrew Python：`/opt/homebrew/bin/python3.11`。
- 安装依赖：`.venv/bin/python -m pip install -e ".[dev]"`。
- 运行测试：`.venv/bin/python -m pytest -v`。
- 摄像头画面、手部关键点和鼠标事件都必须保持本地处理。没有明确产品批准时，不要加入上传、遥测、截图、视频或关键点持久化。
- 保留传统鼠标/触控板接管能力。手势控制不能阻止用户重新取得控制权。
- 默认指针移动方式是 relative mode，不是绝对屏幕映射。保留 `--movement-mode absolute` 作为调试 fallback。

## 手势语义

- 默认目标手是物理右手。
- 食指伸出代表 relative mode 下的指针控制。
- 食指放松代表 `clutch`：用户可以重新摆放手的位置，鼠标保持不动。
- 张开手掌并保持代表暂停/恢复；不要复用张开手掌作为 clutch。
- 拇指和食指严格捏合代表点击或拖拽。Pinch 判断同时使用绝对距离、手部缩放距离、连续帧确认，以及与其他手指的隔离关系。
- 双指模式用于滚动，必须与 pinch drag 保持意图隔离。

## Phase 1.5 指针模型

当前默认指针模型是 air-trackpad 风格的相对映射：

- 开始追踪后的前几帧只建立参考点，不移动指针。
- 食指指尖的相对位移驱动当前系统指针。
- Dynamic gain 让快速移动比慢速移动产生更长的屏幕位移。
- `relative_max_delta` 限制单帧跳变，避免摄像头或关键点抖动把指针甩到远处。
- 当手保持在舒适区边缘附近时，edge cruise 会让指针持续向对应方向移动。

修改这一块时，必须保留或补充以下测试：

- 追踪开始时指针不跳动
- clutch 重新定位时不移动鼠标
- dynamic gain
- 单帧跳变限制
- edge cruise
- 点击、拖拽、滚动、暂停的意图隔离

## 文档规则

- 当命令、安装流程或面向用户的手势行为变化时，更新 `README.md`。
- 当数据流、状态机行为或模块边界变化时，更新 `docs/architecture.md`。
- 当权限、常用参数、失败模式或排障步骤变化时，更新 `docs/runbook.md`。
- 产品方向和路线图决策写入 `docs/prd.md`；不要把一次性 bug 历史写进 PRD。
