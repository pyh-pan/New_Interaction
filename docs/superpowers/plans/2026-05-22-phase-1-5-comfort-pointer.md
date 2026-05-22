# Phase 1.5 舒适指针实现计划

> **给 agentic workers：** 必须使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans，按任务逐步执行本计划。步骤使用 checkbox（`- [ ]`）语法追踪。

**目标：** 实现 Phase 1.5：relative pointer movement、comfort zone、clutch repositioning、dynamic gain 和 edge cruise，同时保持现有点击、拖拽、滚动和暂停意图识别的准确性。

**架构：** 手势意图仍放在 `src/new_interaction/gestures.py`；legacy mode 输出 absolute pointer event，comfort mode 输出 relative delta event。系统输入注入仍放在 `src/new_interaction/input_controller.py`；在不改变摄像头追踪的前提下，新增 relative move 与 drag injection。

**技术栈：** Python dataclasses、现有 pytest suite、PyAutoGUI event injection。

---

### Task 1：Relative Pointer Events

**文件：**
- 修改：`src/new_interaction/gestures.py`
- 修改：`tests/test_gestures.py`

- [ ] 为 no-jump relative tracking、relative delta movement 和 clutch reset 添加失败测试。
- [ ] 添加 `movement_mode`、relative sensitivity、dynamic gain、comfort zone 和 edge cruise 配置。
- [ ] 实现 `active_move`、`clutch` 和 `edge_cruise` 状态行为。
- [ ] 确认相关手势测试通过。

### Task 2：Relative System Injection

**文件：**
- 修改：`src/new_interaction/input_controller.py`
- 修改：`tests/test_input_controller.py`

- [ ] 为 relative move、当前位置 relative click、relative drag 和 drag release 添加失败测试。
- [ ] 为 `InteractionEvent.dx/dy` 实现 `moveRel` 与 `dragRel` 处理。
- [ ] 保留 absolute move/click/drag 行为。
- [ ] 确认 input controller 测试通过。

### Task 3：CLI 与文档

**文件：**
- 修改：`src/new_interaction/app.py`
- 修改：`tests/test_app.py`
- 修改：`README.md`
- 修改：`docs/prd.md`

- [ ] 添加 movement mode、relative sensitivity、dynamic gain、comfort zone size 和 edge cruise 的 CLI 参数。
- [ ] 将 CLI 参数传入 `GestureConfig`。
- [ ] 在 README 中更新推荐 Phase 1.5 命令。
- [ ] 运行完整 pytest 和 compileall。
