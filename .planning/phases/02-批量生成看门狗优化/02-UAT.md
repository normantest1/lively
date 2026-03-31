---
status: testing
phase: 02-批量生成看门狗优化
source: 02-批量生成看门狗优化-SUMMARY.md
started: 2026-03-31T00:00:00Z
updated: 2026-03-31T00:00:00Z
---

## Current Test

number: 3
name: RTF>0.8时自动恢复
expected: |
  当RTF（显存使用率）>0.8时，系统自动执行恢复流程：1)暂停任务 2)停止VoxCPM服务 3)等待60秒 4)重载模型 5)等待120秒 6)恢复任务。
  观察点：日志应显示完整的恢复流程。
awaiting: user response

## Tests

### 1. 看门狗任务立即执行
expected: 添加看门狗任务后，任务会立即开始执行，不等待 cron 触发时间。观察点：添加任务后，日志应立即出现"立即开始执行批量生成任务"或类似记录。
result: issue
reported: "执行报错了 [ERROR] ❌ 多线程批量生成任务执行失败: cannot access local variable 'task_cancel_event' where it is not associated with a value"
severity: blocker

### 2. Cron触发只检查RTF
expected: Cron触发时，系统只执行RTF检查（检查GPU显存使用率），不执行完整的语音生成。观察点：Cron触发的日志应只显示RTF检查结果，不应有章节生成相关日志。
result: pass

### 3. RTF>0.8时自动恢复
expected: 当RTF（显存使用率）>0.8时，系统自动执行恢复流程：1)暂停任务 2)停止VoxCPM服务 3)等待60秒 4)重载模型 5)等待120秒 6)恢复任务。观察点：日志应显示完整的恢复流程。
result: pending

## Summary

total: 3
passed: 1
issues: 1
pending: 1
skipped: 0
blocked: 0

## Gaps

- truth: "添加看门狗任务后，任务会立即开始执行，不等待 cron 触发时间"
  status: failed
  reason: "User reported: 执行报错了 [ERROR] ❌ 多线程批量生成任务执行失败: cannot access local variable 'task_cancel_event' where it is not associated with a value"
  severity: blocker
  test: 1
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
