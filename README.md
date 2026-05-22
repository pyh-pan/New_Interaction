# New Interaction

基于电脑摄像头的手势鼠标工程验证原型。当前目标是验证两件事：

1. 能否成功调用 macOS 摄像头能力。
2. 能否识别基础手势并完成鼠标移动、单击、双击、拖拽、滚动、暂停等基础交互。

## 环境准备

MediaPipe 与 OpenCV 对 Python 版本比较敏感。本项目建议使用 macOS Homebrew Python 3.11：

```bash
/opt/homebrew/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

## 运行测试

```bash
.venv/bin/python -m pytest -v
```

## 运行工程验证脚本

默认是 dry-run，只打开摄像头、识别手势并在终端打印事件，不会控制鼠标：

```bash
.venv/bin/python -m new_interaction.app --show-preview --debug-state --max-frames 300
```

确认识别稳定后，再显式打开真实鼠标控制：

```bash
.venv/bin/python -m new_interaction.app --control --show-preview
```

macOS 需要授权：

- Camera：允许终端或运行该脚本的 App 使用摄像头。
- Accessibility：使用 `--control` 时，需要允许终端控制电脑。

Camera 权限列表通常没有“手动添加应用”的按钮。应用只有在第一次请求摄像头后，才会出现在 `System Settings > Privacy & Security > Camera` 列表里。建议先从 macOS 自带 Terminal.app 运行脚本：

```bash
cd /Users/panyihang/Code/New_Interaction
.venv/bin/python -m new_interaction.app --show-preview --max-frames 300
```

如果看到 `not authorized to capture video`，但系统没有弹出授权框，可以重置 Terminal 的摄像头权限后再运行：

```bash
tccutil reset Camera com.apple.Terminal
```

如果从 Codex 内部运行，实际请求摄像头的是 Codex.app，bundle id 是 `com.openai.codex`。可以重置后重启 Codex 再试：

```bash
tccutil reset Camera com.openai.codex
```

如果鼠标开始失控，把鼠标移动到屏幕角落可触发 PyAutoGUI fail-safe，或在终端按 `Ctrl+C` 停止。

## 当前手势

当前默认只接受物理右手。摄像头预览是镜像画面，程序会把 MediaPipe 的左右手标签转换回物理左右手。

| 手势 | 行为 |
| --- | --- |
| 食指移动 | 移动鼠标 |
| 拇指食指严格捏合并释放 | 左键单击 |
| 拇指食指快速严格捏合两次 | 左键双击状态，后端执行第二次点击 |
| 拇指食指严格捏合并保持超过阈值后移动 | 拖拽 |
| 食指中指伸出并移动 | 滚动 |
| 张开手掌保持 | 暂停或恢复 |

默认指针移动已经切到 Phase 1.5 的相对移动模式：食指位置不再直接等于屏幕坐标，而是像空中触控板一样，用手指位移推动当前鼠标继续移动。首次伸出食指会先经过短暂稳定期，只建立参考点，不会把鼠标吸到手指附近；食指收回或手自然放松会进入 `clutch`，此时可以把手移回舒服位置，鼠标不动；再次伸出食指后继续移动。需要调试旧行为时可用 `--movement-mode absolute`。

严格捏合不是单帧距离判断。程序需要先看到右手处于打开或中性状态，再连续多帧确认拇指食指靠近，并且同时满足“画面绝对距离足够近”和“相对手部尺度足够近”，且食指和中指没有挤在一起。这样可以降低摸脸、握拳、遮挡、手离镜头远近变化和单帧抖动带来的误触。

相对移动模式下，点击发生在当前系统鼠标位置，捏合动作不会再把鼠标吸到食指的摄像头坐标。绝对映射调试模式下，点击和拖拽仍使用“悬停锚点”逻辑：当你把食指移动到目标位置后，系统会在捏合候选开始时锁定最后一个正常悬停位置。后续捏合动作即使带动食指轻微偏移，单击/双击仍然发生在锁定位置。

拖拽在 macOS 上使用系统可识别的 drag event 注入，而不是简单地“鼠标按下后移动指针”。验证窗口拖动时，需要先把食指悬停在窗口标题栏或其他可拖动区域，再捏住并保持超过拖拽阈值后移动。松开捏合时会立即结束拖拽，不再补发最后一次拖拽坐标，避免窗口释放延迟。

指针移动和拖拽移动默认做轨迹平滑，降低摄像头关键点抖动带来的鼠标抖动。平滑只作用于移动轨迹，不作用于捏合释放判断，因此不会拖慢松手。

## 状态调试

如果鼠标没有按预期移动，先不要开 `--control`，用 dry-run 看状态：

```bash
.venv/bin/python -m new_interaction.app --show-preview --debug-state
```

常见状态：

| 状态 | 含义 |
| --- | --- |
| `active_move` | 相对移动模式已建立参考点，食指位移正在控制当前鼠标 |
| `clutch` | 食指收回或手放松，允许重置手位，鼠标不动 |
| `edge_cruise` | 手指保持在舒适区边缘，鼠标持续向对应方向移动 |
| `move` | 绝对映射调试模式下，食指正在控制指针 |
| `ignored_hand` | 识别到的不是目标手，默认只接受右手 |
| `pinch_candidate` | 已看到疑似捏合，正在等待连续帧确认 |
| `pinch_active` | 严格捏合已经确认 |
| `dragging` | 长按捏合进入拖拽 |
| `scrolling` | 双指滚动模式 |
| `paused` | 已暂停，不注入任何事件 |
| `tracking_lost` | 没有可信手部识别 |
| `pinch_blocked` | 手一进入画面就是捏合形态，系统等待先回到打开/中性状态 |

## 常用参数

```bash
.venv/bin/python -m new_interaction.app \
  --show-preview \
  --debug-state \
  --camera-index 0 \
  --max-frames 300 \
  --movement-mode relative \
  --pinch-threshold 0.06 \
  --pinch-release-threshold 0.09 \
  --pinch-scale-threshold 0.30 \
  --pinch-release-scale-threshold 0.45 \
  --pinch-confirm-frames 3 \
  --pinch-isolation-distance 0.04 \
  --target-hand Right \
  --drag-hold 0.35 \
  --pause-hold 0.45 \
  --scroll-sensitivity 900 \
  --pointer-smoothing-alpha 0.35 \
  --relative-sensitivity 1.2 \
  --relative-min-gain 0.8 \
  --relative-max-gain 2.4 \
  --relative-gain-motion-threshold 0.08 \
  --relative-max-delta 0.08 \
  --relative-warmup-frames 3 \
  --comfort-zone-width 0.36 \
  --comfort-zone-height 0.30 \
  --edge-cruise-margin 0.15 \
  --edge-cruise-speed 0.006
```

如果你发现拇指和食指还没真正贴合就进入 `pinch_active` 或 `dragging`，优先降低 `--pinch-scale-threshold`，例如：

```bash
.venv/bin/python -m new_interaction.app --control --show-preview --debug-state --pinch-scale-threshold 0.24 --pinch-release-scale-threshold 0.45 --pointer-smoothing-alpha 0.30 --relative-sensitivity 1.2 --relative-max-delta 0.08 --relative-warmup-frames 3
```

`--debug-state` 会输出 `pinch` 和 `pinch_scale`。默认 `pinch_scale` 需要小于等于 `0.30` 才可能进入严格捏合；数值越小，要求捏得越紧。

`--pointer-smoothing-alpha` 越小越稳定但越滞后，越大越跟手但抖动更多。建议先在 `0.25` 到 `0.45` 之间试。

如果一入镜就出现异常飘动，先提高 `--relative-warmup-frames` 或降低 `--relative-max-delta`。如果大屏移动不够远，再逐步提高 `--relative-sensitivity` 或 `--relative-max-gain`；如果精准点击变困难，降低 `--relative-min-gain` 或提高 `--pointer-smoothing-alpha`。如果你想临时回到旧的屏幕绝对映射，用：

```bash
.venv/bin/python -m new_interaction.app --control --show-preview --debug-state --movement-mode absolute
```

如果你确认自己只在用右手，但状态一直显示 `ignored_hand`，可以临时用下面的命令排查左右手标签问题：

```bash
.venv/bin/python -m new_interaction.app --show-preview --debug-state --target-hand Any
```

## 产品文档

PRD 持续维护在 [`docs/prd.md`](docs/prd.md)。
