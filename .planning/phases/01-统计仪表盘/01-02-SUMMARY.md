---
phase: 01-统计仪表盘
plan: "02"
subsystem: backend
tags: [statistics, api, backend]
dependency_graph:
  requires: []
  provides:
    - endpoint: "/api/stats/novels"
      description: "Per-novel statistics with chapter_count and role_count"
    - endpoint: "/api/stats/roles/top"
      description: "Top N roles ordered by role_count descending"
  affects:
    - "admin/src/api/index.js"
tech_stack:
  added:
    - FastAPI endpoint: /api/stats/novels
    - FastAPI endpoint: /api/stats/roles/top
    - Frontend API: getStatsNovels()
    - Frontend API: getStatsTopRoles(limit)
key_files:
  created: []
  modified:
    - "api.py"
    - "admin/src/api/index.js"
decisions: []
metrics:
  duration: "~1 minute"
  completed: "2026-03-30T15:02:46Z"
---

# Phase 1 Plan 2: Backend API - Novels + Top Roles Endpoints

## One-liner
Backend API endpoints for per-novel statistics and top roles listing with frontend bindings.

## Completed Tasks

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create /api/stats/novels endpoint | d6c627c | api.py |
| 2 | Create /api/stats/roles/top endpoint | d6c627c | api.py |
| 3 | Add frontend API getStatsNovels/getStatsTopRoles | f13bcc1 | admin/src/api/index.js |

## What Was Built

### Backend Endpoints (api.py)

**GET /api/stats/novels** - Returns per-novel statistics:
- For each Novel record: id, novel_name, chapter_count, role_count, current_state, state_name
- chapter_count computed by splitting chapter_names on comma
- role_count computed by counting Role records matching the novel_name

**GET /api/stats/roles/top?limit=50** - Returns top roles by citation count:
- Returns top N roles ordered by role_count (引用次数) descending
- Fields: id, role_name, novel_name, role_count, gender, is_bind, presence_rate

### Frontend API Functions (admin/src/api/index.js)

- `getStatsNovels()` - calls GET /api/stats/novels
- `getStatsTopRoles(limit)` - calls GET /api/stats/roles/top with ?limit parameter

## Deviations from Plan

None - plan executed exactly as written.

## Auth Gates

None.

## Verification

- api.py contains @app.get("/api/stats/novels") and @app.get("/api/stats/roles/top")
- admin/src/api/index.js exports getStatsNovels and getStatsTopRoles
- Both endpoints return valid JSON with required arrays

## Deferred Issues

None.

## Self-Check: PASSED

- Commit d6c627c found in git log
- Commit f13bcc1 found in git log
- api.py contains both endpoints at lines 1340 and 1376
- admin/src/api/index.js contains getStatsNovels (line 164) and getStatsTopRoles (line 167)
