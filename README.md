# ChatGPT Stale Conversation Cleaner

[English](README.md) | [中文](README.zh-CN.md)

A Windows desktop utility for removing stale ChatGPT/Codex conversation entries from the local desktop index.

## Features

- Lists ChatGPT conversation titles from the local index on startup
- Filter, select individual rows, select all, or clear the selection
- Confirmation before deletion
- Chinese, English, or follow-system UI language
- Backups are off by default, with an optional custom backup location

## Usage

1. Fully quit the ChatGPT/Codex desktop app, including its tray process.
2. Double-click `ChatGPTStaleConversationCleaner_v4.exe`.
3. Select the conversations to clean up and confirm the operation.

The program only modifies the local desktop index. It does not delete cloud conversations from the web app.

## Privacy

The current version has no network, upload, or telemetry logic. It reads the following database under the current Windows user's profile:

`%USERPROFILE%\\.codex\\sqlite\\codex-dev.db`

The developer's database and username are not bundled with the program. Backups are disabled by default; if enabled, the program copies the local database to the directory selected by the user. Keep backup files secure.

## Notes

The included Windows standalone build does not require Python to be installed. The source code and icon are included so that users can inspect or rebuild the program.
