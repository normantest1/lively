# Phase 3: 修改看门狗功能/添加设置功能 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 03-修改看门狗功能-添加设置功能
**Areas discussed:** 任务持久化, 恢复提示, 开关默认, 清理时机

---

## 任务持久化

| Option | Description | Selected |
|--------|-------------|----------|
| 扩展 ScheduledTask 表 | 在现有 ScheduledTask 表中添加 completed_chapters、is_running 等字段 | |
| 新建 watchdog_tasks 表 | 创建独立的看门狗任务状态表，专门存储任务进度 | ✓ |
| 新建 batch_generate_state 表 | 与批量生成模块命名一致，创建 batch_generate_state 表 | |

**User's choice:** 新建 watchdog_tasks 表
**Notes:** 用户选择独立的 watchdog_tasks 表来专门存储看门狗任务状态

---

## 恢复提示

| Option | Description | Selected |
|--------|-------------|----------|
| WebSocket 实时推送 | 系统启动时通过 WebSocket 推送消息到前端，实时显示恢复进度 | ✓ |
| 前端轮询 API | 前端页面加载后每5秒轮询一次 API 检查是否有恢复任务 | |
| 仅日志和弹窗 | 控制台打印 + 前端 ElMessage 弹窗提示 | |

**User's choice:** WebSocket 实时推送
**Notes:** 使用 WebSocket 实现实时推送

---

## 开关默认

| Option | Description | Selected |
|--------|-------------|----------|
| 默认关闭 | 开关默认关闭，用户主动开启才启用持久化 | |
| 默认开启 | 开关默认开启，任务自动持久化和恢复 | ✓ |

**User's choice:** 默认开启
**Notes:** 看门狗生成任务自动重启开关默认开启

---

## 清理时机

| Option | Description | Selected |
|--------|-------------|----------|
| 仅启动时清理 | 仅在系统启动时自动清理一次，不提供手动清理 | ✓ |
| 启动 + 设置页手动清理按钮 | 启动时自动清理 + 在设置页面添加"清理 temp"按钮 | |
| 启动 + API 接口手动清理 | 启动时自动清理 + 提供 API 接口供前端调用 | |

**User's choice:** 仅启动时清理
**Notes:** temp 目录下的 wav 文件仅在系统启动时自动清理

---

## Claude's Discretion

无 — 所有决策均由用户明确选择

---

## Deferred Ideas

无 — 讨论保持在阶段范围内

