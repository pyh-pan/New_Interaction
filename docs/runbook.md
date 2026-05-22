# 运行手册

## 环境

在 macOS 上使用 Python 3.11：

```bash
/opt/homebrew/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

运行测试：

```bash
.venv/bin/python -m pytest -v
```

## Dry-Run 验证

先在不注入真实鼠标事件的情况下启动：

```bash
.venv/bin/python -m new_interaction.app --show-preview --debug-state --max-frames 300
```

Dry-run 输出应能看到状态变化，以及 `move-rel`、`click`、`drag-*`、`scroll` 或 `pause` 事件。

## 真实鼠标控制

显式开启系统输入注入：

```bash
.venv/bin/python -m new_interaction.app --control --show-preview --debug-state
```

停止方式：

- 在终端按 `Ctrl+C`。
- 在 OpenCV 预览窗口按 `q`。
- 把鼠标移动到屏幕角落，触发 PyAutoGUI fail-safe。

## macOS 权限

摄像头权限授予的是发起摄像头请求的应用。如果从 Terminal 运行：

```bash
tccutil reset Camera com.apple.Terminal
```

如果从 Codex 运行：

```bash
tccutil reset Camera com.openai.codex
```

真实鼠标控制还需要给运行脚本的终端或应用授予 Accessibility 权限：

```text
System Settings > Privacy & Security > Accessibility
```

## 推荐 Phase 1.5 命令

```bash
.venv/bin/python -m new_interaction.app \
  --control \
  --show-preview \
  --debug-state \
  --movement-mode relative \
  --relative-sensitivity 1.2 \
  --relative-max-gain 2.4 \
  --relative-max-delta 0.08 \
  --relative-warmup-frames 3 \
  --edge-cruise-speed 0.006 \
  --pinch-scale-threshold 0.24 \
  --pinch-release-scale-threshold 0.45 \
  --pointer-smoothing-alpha 0.30
```

## 常用调参

| 现象 | 优先调整 |
| --- | --- |
| 手入镜时指针跳动 | 将 `--relative-warmup-frames` 提高到 `5`，或将 `--relative-max-delta` 降到 `0.05` |
| 大屏幕上指针移动太慢 | 逐步提高 `--relative-sensitivity` |
| 快速移动仍然不够强 | 逐步提高 `--relative-max-gain` |
| 精准点击困难 | 降低 `--relative-min-gain` 或降低 `--relative-sensitivity` |
| 指针抖动 | 将 `--pointer-smoothing-alpha` 降到接近 `0.25` |
| 手指未真正碰到就触发 pinch | 降低 `--pinch-scale-threshold` |
| 拖拽释放延迟明显 | 降低 `--pinch-release-scale-threshold` |
| 左手或摸脸触发事件 | 保持 `--target-hand Right`；查看 `ignored_hand` 状态 |

## 状态调试

重要状态：

- `active_move`：relative pointer movement 激活。
- `clutch`：食指放松；手可以重新定位而不移动指针。
- `edge_cruise`：保持在舒适区边缘；指针继续移动。
- `pinch_candidate`：严格 pinch 正在确认。
- `pinch_active`：pinch 正在保持。
- `dragging`：拖拽已激活。
- `scrolling`：双指滚动模式激活。
- `paused`：张开手掌暂停模式激活。
- `tracking_lost`：没有可信的手部画面。

## Fallback 调试

调试时可回到 absolute mapping：

```bash
.venv/bin/python -m new_interaction.app --control --show-preview --debug-state --movement-mode absolute
```

关闭真实鼠标注入，只查看事件输出：

```bash
.venv/bin/python -m new_interaction.app --show-preview --debug-state
```
