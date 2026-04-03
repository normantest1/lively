---
phase: quick-260403-msj
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - scheduler_tasks.py
  - admin/src/views/ScheduledTaskView.vue
autonomous: true
requirements: []
must_haves:
  truths:
    - "User can select '全部解析' from novel dropdown"
    - "Selecting '全部解析' disables the dropdown"
    - "Backend parses all current_state=1 novels when novel_name is empty"
    - "Job name displays as '定时解析任务_全部' for all-mode jobs"
  artifacts:
    - path: "scheduler_tasks.py"
      provides: "Modified execute_parse_task and add_parse_job functions"
      contains: "if not novel_name:"
    - path: "admin/src/views/ScheduledTaskView.vue"
      provides: "Modified parse form dropdown with all-option"
      contains: "全部解析"
  key_links:
    - from: "ScheduledTaskView.vue"
      to: "scheduler_tasks.py"
      via: "createScheduledParseTask API call with novel_name=''"
      pattern: "createScheduledParseTask.*novel_name"
---

<objective>
Add "全部解析" (parse all) option to the scheduled batch parse task. When selected, the system will parse ALL novels with current_state=1 in creation time ascending order, without distinguishing between previously parsed and never-parsed.
</objective>

<context>
@scheduler_tasks.py lines 257-380 (execute_parse_task), lines 1516-1569 (add_parse_job)
@admin/src/views/ScheduledTaskView.vue lines 32-87 (parse form), lines 619-632 (handleParseNovelChange)
@admin/src/api/index.js lines 183-184 (createScheduledParseTask API)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Modify backend to support all-novels parse mode</name>
  <files>scheduler_tasks.py</files>
  <action>
    Modify `execute_parse_task` function (around line 329) to handle empty novel_name as sentinel for "all novels":

    1. In the query section, add conditional:
       - If novel_name is truthy: existing query filtering by novel_name AND current_state=1
       - If novel_name is falsy (empty string): query ALL novels with current_state=1, ordered by create_time ascending

    2. Modify `add_parse_job` function (around line 1527) job name logic:
       - Change `name=f"定时解析任务_{novel_name}"` to use `novel_name or "全部"` so empty string produces "定时解析任务_全部"

    Per the locked decision: parse all current_state=1 novels in creation time ascending order.
  </action>
  <verify>
    <automated>grep -n "if not novel_name" scheduler_tasks.py && grep -n "定时解析任务_全部" scheduler_tasks.py</automated>
  </verify>
  <done>Backend handles empty novel_name as "parse all novels" mode, job name shows "定时解析任务_全部"</done>
</task>

<task type="auto">
  <name>Task 2: Add "全部解析" option to frontend dropdown</name>
  <files>admin/src/views/ScheduledTaskView.vue</files>
  <action>
    1. In the el-select for novel names (around line 40), add "全部解析" as the FIRST el-option with value="" (empty string)

    2. Add :disabled binding to the select so it's disabled when parseForm.novel_name === '' (all mode selected)

    3. After the el-select closing tag, add a small gray text span: "已选择全部解析" that only shows when parseForm.novel_name === ''

    4. In handleParseNovelChange function (around line 619), add guard: if parseForm.novel_name is empty string, set parseForm.max_chapters = 0 instead of fetching chapters

    Per the locked decision: keep dropdown but disable it when all-mode is selected.
  </action>
  <verify>
    <automated>grep -n "全部解析" admin/src/views/ScheduledTaskView.vue && grep -n "已选择全部解析" admin/src/views/ScheduledTaskView.vue</automated>
  </verify>
  <done>Frontend shows "全部解析" option, dropdown is disabled when selected, hint text appears</done>
</task>

</tasks>

<verification>
- Backend: `execute_parse_task` accepts empty novel_name and queries all current_state=1 novels
- Backend: `add_parse_job` uses "定时解析任务_全部" for empty novel_name
- Frontend: Dropdown has "全部解析" option as first entry
- Frontend: Dropdown disables when "全部解析" is selected
- Frontend: Hint text "已选择全部解析" shows when all-mode selected
</verification>

<success_criteria>
1. User can select "全部解析" from the scheduled task novel dropdown
2. When selected, dropdown is disabled and hint text appears
3. Backend parses all current_state=1 novels in creation time order
4. Job name stored/displayed as "定时解析任务_全部"
</success_criteria>

<output>
After completion, create `.planning/quick/260403-msj/260403-msj-SUMMARY.md`
</output>
