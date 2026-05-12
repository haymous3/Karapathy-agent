# Scripts Agent Guide

## Purpose

`pm/scripts` contains operating-system specific scripts to start and stop the PM MVP locally in a predictable way.

## Required Script Coverage

- Windows PowerShell start script
- Windows PowerShell stop script
- macOS/Linux shell start script
- macOS/Linux shell stop script

Current script files:

- `scripts/start-windows.ps1`
- `scripts/stop-windows.ps1`
- `scripts/start-unix.sh`
- `scripts/stop-unix.sh`

## Script Responsibilities

- Start command should:
  - verify required tooling where practical
  - start the app stack (containerized flow for MVP)
  - print a concise success message with local URLs
- Stop command should:
  - stop the app stack cleanly
  - avoid deleting user data unless explicitly requested
  - print concise completion status

## Script Design Rules

- Scripts must be idempotent where reasonable (safe to rerun).
- Keep logic simple and readable; avoid hidden side effects.
- Prefer explicit commands over complex abstractions.
- Use clear error messages that identify root cause and next action.

## Validation Expectations

Each script update should be verified manually:

- Start from clean stopped state -> start script works.
- Run start again -> behavior is safe and understandable.
- Run stop script -> services stop cleanly.
- Run stop again -> behavior is safe and understandable.

## Runtime Notes

- Default local port is `8000`.
- If that port is busy, set `PM_MVP_PORT` before running start scripts:
  - PowerShell: `$env:PM_MVP_PORT=\"8001\"`
  - Bash: `export PM_MVP_PORT=8001`

## Documentation Expectations

- Every new script should include:
  - expected usage
  - assumptions (required tools, ports)
  - quick troubleshooting notes
- Keep this guide updated if script names or startup flow changes.