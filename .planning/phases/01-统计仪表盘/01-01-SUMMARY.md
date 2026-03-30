---
phase: "01-统计仪表盘"
plan: "01"
type: "execute"
subsystem: "backend-api"
tags:
  - statistics
  - dashboard
  - api
dependency_graph:
  requires: []
  provides:
    - "/api/stats/overview"
    - "/api/stats/pending"
  affects:
    - admin/src/api/index.js
tech_stack:
  added:
    - FastAPI endpoint "/api/stats/overview"
    - FastAPI endpoint "/api/stats/pending"
    - Frontend API functions getStatsOverview, getStatsPending
  patterns:
    - Follows existing statistics API pattern from get_novels_summary()
key_files:
  created: []
  modified:
    - "api.py"
    - "admin/src/api/index.js"
decisions:
  - id: "01-01-D1"
    decision: "Use comma-count + 1 formula for total_chapters calculation"
    rationale: "chapter_names stores comma-separated values, consistent with existing codebase patterns"
  - id: "01-01-D2"
    decision: "ungenerated_chapters = novels in state 1 or 2"
    rationale: "State 1 = parsed, state 2 = awaiting synthesis, so both need audio generation"
metrics:
  duration: "~5 minutes"
  completed: "2026-03-30"
  tasks_completed: 3
---

# Phase 01 Plan 01: Statistics Dashboard API Endpoints Summary

## One-liner

Backend API endpoints providing global overview statistics and pending work counts for the statistics dashboard.

## Completed Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Create /api/stats/overview endpoint | 2856406 | api.py |
| 2 | Create /api/stats/pending endpoint | 2856406 | api.py |
| 3 | Add frontend API functions | a7613d3 | admin/src/api/index.js |

## What Was Built

### Backend Endpoints (api.py)

**GET /api/stats/overview** (line 1301)
- Returns: `{ total_novels, total_chapters, total_roles, total_audios }`
- `total_chapters` calculated as sum of (comma count + 1) per novel

**GET /api/stats/pending** (line 1323)
- Returns: `{ unparsed_novels, ungenerated_chapters }`
- `unparsed_novels`: Novel count where `current_state == 1`
- `ungenerated_chapters`: Novel count where `current_state in [1, 2]`

### Frontend API Functions (admin/src/api/index.js)

Added to apiClient export:
- `getStatsOverview()` - calls GET /api/stats/overview
- `getStatsPending()` - calls GET /api/stats/pending

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- api.py contains @app.get("/api/stats/overview") and @app.get("/api/stats/pending")
- admin/src/api/index.js exports getStatsOverview and getStatsPending
- Both commits verified in git log

## Self-Check

- [x] api.py modified with two new endpoints
- [x] admin/src/api/index.js modified with two new functions
- [x] git commits created: 2856406 (backend), a7613d3 (frontend)
- [x] No blocking issues or deviations
