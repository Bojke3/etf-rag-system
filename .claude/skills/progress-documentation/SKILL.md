---
name: progress-documentation
description: Use when a meaningful unit of work is finished — a feature, phase, bug fix, refactor or experiment — and the state should be recorded so a later session can pick it up. Ask the user first, then write a dated progress document to AI/docs/. Do not use after every individual command or trivial fix.
---

# Progress Documentation Skill

## Purpose

Keep a persistent record of project progress so that work can be easily resumed later, even in a new Claude Code session.

## Rules

After completing a meaningful task, feature, phase, bug fix, refactor, or other significant piece of work, STOP before moving on to unrelated work and ask the user:

> "We've finished this part. Do you want me to create a progress `.md` file in `AI/docs/` documenting where we left off?"

Do **not** create the file automatically unless the user agrees.

If the user agrees:

1. Check the existing contents of `AI/docs/`.
2. Create a new `.md` file documenting the completed work.
3. Put the file inside `AI/docs/`.
4. Make sure the documentation accurately reflects the current state of the project.

## File naming

Every progress document must follow this naming format:

`day-date-year {short descriptive name of what we accomplished}.md`

For example:

`14-09-2026 Phase B File Operations Completed.md`

or:

`14-09-2026 Fixed VM File Descriptor Handling.md`

The descriptive part should clearly summarize what was accomplished during that work session.

Use the actual current date when creating the file.

Do not use vague names such as `update.md`, `progress2.md`, or `notes.md`.

## What the documentation should contain

Include:

- **Current status** — what state the project is in.
- **What was accomplished** — concrete features, fixes, or changes completed.
- **What was tested** — commands/tests/checks that were run and their results.
- **Files changed** — important files and what changed in them.
- **What remains** — unfinished work, known issues, TODOs, or missing requirements.
- **Next steps** — the most logical things to do when work resumes.
- **Important implementation details** — decisions, assumptions, or things that would otherwise be easy to forget.
- **How to continue** — anything Claude or the user needs to know to safely resume the work.

Do not claim something is complete if it was not actually implemented or tested.

## Keep it useful

The document should be written so that another Claude Code session can read it and immediately understand:

> "Where are we, what did we do, what works, what doesn't, and what should I do next?"

Do not fill the document with unnecessary explanations or repeat the entire codebase. Focus on information that is useful for continuing development.

## Important

This skill is a documentation checkpoint, not a reason to interrupt the user constantly.

Only ask after a **meaningful completed unit of work**, not after every individual command, edit, or trivial fix.

If the user declines, continue working normally without repeatedly asking about the same completed task.