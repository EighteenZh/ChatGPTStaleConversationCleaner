# ChatGPT 残留对话清理工具

[English](README.md) | [中文](README.zh-CN.md)

一个用于清理 ChatGPT/Codex Windows 桌面端本地残留对话索引的图形工具。

## 功能

- 启动后列出本机 ChatGPT 对话标题
- 支持筛选、逐条勾选、全选和取消全选
- 删除前二次确认
- 支持中文、English 和跟随系统
- 备份选项默认关闭，也可以手动选择备份位置

## 使用方法

1. 完全退出 ChatGPT/Codex 桌面端，包括托盘后台。
2. 双击 `ChatGPTStaleConversationCleaner_v4.exe`。
3. 选择要清理的对话，确认后执行清理。

程序只修改本机的桌面端对话索引，不会删除网页端的云端对话。

## 隐私

当前版本没有联网、上传或遥测逻辑。程序读取当前 Windows 用户目录下的：

`%USERPROFILE%\\.codex\\sqlite\\codex-dev.db`

程序不会把开发者电脑上的数据库或用户名打包进去。备份功能默认关闭；如果手动开启，程序会把本地数据库复制到用户选择的目录，请妥善保管备份文件。

## 说明

当前提供的是 Windows 独立版，不要求另外安装 Python。源码和图标文件也一并提供，便于检查和自行打包。
