# 架构说明

## 概览

New Interaction 是一个本地运行的 camera-to-mouse pipeline：

```text
macOS 摄像头
  -> OpenCV 帧捕获
  -> MediaPipe Hand Landmarker
  -> HandFrame 关键点
  -> GestureStateMachine
  -> InteractionEvent
  -> DryRunInputController 或 PyAutoGUIInputController
  -> macOS 鼠标事件
```

当前原型刻意采用 rule-based 方案。它先验证交互设计、权限行为和鼠标事件注入，再进入数据采集或模型训练阶段。

## 模块

| 文件 | 职责 |
| --- | --- |
| `src/new_interaction/app.py` | CLI 解析、配置组装、摄像头循环、debug-state 输出 |
| `src/new_interaction/camera.py` | OpenCV 摄像头访问、MediaPipe 手部检测、handedness 归一化 |
| `src/new_interaction/gestures.py` | 手势状态机与交互事件生成 |
| `src/new_interaction/input_controller.py` | Dry-run 日志与 PyAutoGUI 鼠标事件注入 |
| `tests/` | 覆盖 CLI 解析、摄像头转换、手势状态和输入注入的单元测试 |

## 数据模型

`HandFrame` 是手势状态机的归一化输入：

- `landmarks`：MediaPipe 的 21 个手部关键点，映射为归一化 `Point(x, y)`。
- `handedness`：经过镜像摄像头修正后的物理左右手标签。
- `confidence`：检测置信度。

`InteractionEvent` 是输出契约：

- absolute pointer event 使用 `position`。
- relative pointer event 使用 `dx` 和 `dy`。
- click event 携带 `click_count`。
- pause event 携带 `paused`。

## 手势状态机

状态机会先完成意图隔离，再发出鼠标事件。

核心状态：

- `active_move`：relative pointer movement 激活。
- `clutch`：食指放松；手可以重新定位而不移动指针。
- `edge_cruise`：手保持在舒适区边缘附近；指针继续向对应方向移动。
- `pinch_candidate`：严格 pinch 正在跨连续帧确认。
- `pinch_active`：严格 pinch 已保持，但尚未进入拖拽。
- `dragging`：pinch 保持时间超过拖拽阈值。
- `scrolling`：双指滚动模式激活。
- `paused`：张开手掌暂停模式激活。
- `ignored_hand`：检测到的手不是配置的目标手。
- `tracking_lost`：没有可信的手部画面。

## 指针映射

默认移动模式是 `relative`。

Relative mode 像 air trackpad 一样工作：

- 前几帧稳定画面用于建立参考点和舒适区中心。
- 食指指尖移动会发出归一化 delta。
- 食指放松进入 clutch，并在恢复时重置参考点。
- dynamic gain 会让快速动作获得比慢速动作更强的放大。
- `relative_max_delta` 限制单帧跳变。
- edge cruise 会在舒适区边缘附近增加小幅连续 delta。

Absolute mode 仍可通过 `--movement-mode absolute` 启用，主要用于调试。在 absolute mode 中，归一化食指位置会直接映射到屏幕坐标。

## Pinch 与拖拽

Pinch 判断刻意保持保守：

- 拇指和食指的绝对距离必须低于 `pinch_threshold`。
- 拇指和食指的手部缩放距离必须低于 `pinch_scale_threshold`。
- 该距离必须与中指聚拢保持隔离，避免误判。
- 激活前必须满足多帧连续确认。
- 释放阈值与进入阈值分离，形成 hysteresis。

在 relative mode 中，点击和拖拽发生在当前系统指针位置。在 absolute mode 中，点击和拖拽使用 hover anchor，避免 pinch 动作本身改变点击目标。

## 输入注入

只有设置 `--control` 后，`PyAutoGUIInputController` 才会注入真实鼠标事件。

- absolute move 使用 `moveTo`。
- relative move 使用 `moveRel`，必要时 fallback 到基于当前坐标的移动。
- macOS drag 使用 `dragTo` 或 `dragRel`，参数为 `button="left"` 和 `mouseDownUp=False`。
- 用户鼠标接管通过比较当前指针位置与上次注入位置判断。
- `tracking_lost` 和 `pause_changed` 会重新启用接管保护。

## 安全边界

- 应用默认是 dry-run mode，只打印事件。
- 真实输入注入必须显式设置 `--control`。
- PyAutoGUI fail-safe 保持开启；把指针移动到屏幕角落可以停止失控输入。
- 低置信度、非目标手、ignored hand 和 lost tracking 不会注入高风险事件。
- 摄像头数据在本地处理。当前原型不会持久化视频、截图、手部关键点或遥测数据。
