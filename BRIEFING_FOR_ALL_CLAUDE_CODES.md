# Briefing for All Claude Code Instances

**From:** Laptop Claude Code (Opus 4.6, nir-laptop, Debian 13)
**Date:** 2026-03-24
**Priority:** Important — affects user experience on Linux

---

## Who Should Read This

This briefing is for:
- **Desktop Windows Claude Code** (nir-desktop) — the Desktop computer running Windows
- **Laptop Windows Claude Code** (nir-laptop, Windows side) — the Laptop when booted into Windows
- **Any future Claude Code instance** working on this project

---

## Critical Finding: LM Studio Behaves Differently on Linux vs Windows

### What We Discovered

On 2026-03-24, while testing HoneycombOfAI on Debian 13 (Laptop), the backend detector could not find LM Studio even though it was running with a model loaded. After investigation, the root cause was identified:

**LM Studio on Windows:** Automatically starts its local API server on port 1234 when you load a model. HoneycombOfAI detects it with zero user action.

**LM Studio on Linux:** Does NOT auto-start the server. The user must manually go to the Developer tab (or Local Server tab) in LM Studio and click "Start Server." Only then does port 1234 become active and HoneycombOfAI can detect it.

### What This Means for You

1. **The HoneycombOfAI code is correct and platform-agnostic.** The detection logic in `backend_detector.py` works the same everywhere — it tries `http://localhost:1234/v1/models` with a 2-second timeout. No code changes are needed.

2. **This is a documentation/user-guidance issue, not a code issue.** When helping users set up LM Studio on Linux, always tell them to manually start the server.

3. **Do NOT modify the detection code** to try to "fix" this. The code is correct. The behavior difference is in LM Studio itself.

### Where This Is Now Documented

- **The Book (TheDistributedAIRevolution):** Chapter 7, in the "LM Studio — the visual alternative" section. A note for Linux users has been added.
- **HoneycombOfAI README.md:** The Supported AI Backends table now includes a note for Linux users.
- **HoneycombOfAI PLATFORM_NOTES.md:** New file with detailed troubleshooting steps for all backends on all platforms.
- **BeehiveOfAI PROJECT_STATUS.md:** Added under "Known Platform Findings."
- **Laptop Debian Claude Code memory:** Saved as a project memory for future conversations.

### Action Items for Each Claude Code Instance

**Desktop Windows Claude Code:**
- Be aware of this difference if a user asks about LM Studio not being detected
- If you're writing documentation or helping users, include the Linux server start instruction
- When the GUI is eventually built, consider adding a tooltip or help text about this

**Laptop Windows Claude Code:**
- You don't need to do anything — LM Studio works automatically on Windows
- But be aware that users on Linux will have this issue, in case you're writing docs or helping someone

**Any Claude Code instance writing user documentation or the book:**
- Always mention the Linux manual server start when discussing LM Studio setup
- The exact steps: Open LM Studio > Developer tab > Start Server > Verify port 1234

---

## The Three Repos — Reminder

All three repos are connected and should stay in sync:

1. **HoneycombOfAI** — The software (desktop client): https://github.com/strulovitz/HoneycombOfAI
2. **BeehiveOfAI** — The website (hub/marketplace): https://github.com/strulovitz/BeehiveOfAI
3. **TheDistributedAIRevolution** — The book: https://github.com/strulovitz/TheDistributedAIRevolution

When making findings or decisions that affect the project, update ALL relevant repos — not just the one you're working in. This briefing exists because important information needs to reach all Claude Code instances, regardless of which repo they happen to be working in.

---

Thank you! Let's keep the communication between all instances strong. The project works best when we all have the full picture.
