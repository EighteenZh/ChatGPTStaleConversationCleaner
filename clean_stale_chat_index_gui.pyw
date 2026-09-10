"""双击运行的 ChatGPT 桌面端本地对话索引清理工具。"""

import datetime as dt
import locale
import os
import sqlite3
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


DB = Path(os.environ.get("USERPROFILE", "")) / ".codex" / "sqlite" / "codex-dev.db"
CHECKED = "☑"
UNCHECKED = "☐"
LANGUAGE_MODES = ("auto", "zh", "en")

TEXTS = {
    "zh": {
        "window_title": "清理 ChatGPT 残留对话",
        "language_label": "界面语言：",
        "auto": "跟随系统",
        "chinese": "中文",
        "english": "English",
        "description": "勾选要从桌面端本地索引中清理的 ChatGPT 对话：",
        "filter_label": "筛选标题：",
        "checked": "选择",
        "title": "对话标题",
        "updated": "更新时间",
        "thread_id": "对话 ID",
        "loading": "正在读取 ChatGPT 对话目录……",
        "list_updated": "列表已更新。双击一行或点击“选择”列可以勾选。",
        "read_failed_status": "读取失败。",
        "count": "当前显示 {visible} 条，已勾选 {selected} 条",
        "refresh": "刷新列表",
        "select_all": "全选当前列表",
        "clear_all": "取消全选",
        "backup": "删除前创建备份（默认不勾选）",
        "choose_backup": "选择备份位置…",
        "confirm_delete": "确认清理所选对话",
        "no_selection_title": "没有选择",
        "no_selection": "请先勾选至少一条对话。",
        "confirm_title": "确认清理",
        "confirm_text": "确认清理已勾选的 {count} 条桌面端本地索引吗？\n\n{titles}\n\n只会删除本地索引，不会修改网页端数据。",
        "read_error_title": "读取失败",
        "failed_title": "清理失败",
        "locked_error": "数据库可能仍被 ChatGPT/Codex 占用。\n请完全退出桌面端（包括托盘后台）后重试。\n\n{error}",
        "completed_title": "清理完成",
        "completed_backup": "已清理 {count} 条对话。\n\n备份：\n{backup}",
        "completed_no_backup": "已清理 {count} 条对话。\n\n本次未创建备份。",
        "backup_dialog_title": "选择备份位置",
        "db_not_found": "找不到客户端索引数据库：\n{path}",
        "changed_before_delete": "删除前索引内容发生变化：{title}\n请刷新列表后重试。",
        "backup_integrity": "备份数据库完整性检查失败。",
        "delete_count_error": "实际删除行数异常：{title}，已回滚。",
    },
    "en": {
        "window_title": "Clean Stale ChatGPT Conversations",
        "language_label": "Language:",
        "auto": "Follow system",
        "chinese": "中文",
        "english": "English",
        "description": "Select ChatGPT conversations to remove from the desktop app's local index:",
        "filter_label": "Filter titles:",
        "checked": "Select",
        "title": "Conversation title",
        "updated": "Updated",
        "thread_id": "Conversation ID",
        "loading": "Reading the ChatGPT conversation index...",
        "list_updated": "List updated. Double-click a row or click the Select column to check it.",
        "read_failed_status": "Reading failed.",
        "count": "Showing {visible}; selected {selected}",
        "refresh": "Refresh",
        "select_all": "Select all shown",
        "clear_all": "Clear selection",
        "backup": "Create a backup before deletion (off by default)",
        "choose_backup": "Choose backup location...",
        "confirm_delete": "Delete selected conversations",
        "no_selection_title": "Nothing selected",
        "no_selection": "Select at least one conversation first.",
        "confirm_title": "Confirm cleanup",
        "confirm_text": "Delete the selected {count} local index entries?\n\n{titles}\n\nOnly the local index will be changed; web data will not be modified.",
        "read_error_title": "Read failed",
        "failed_title": "Cleanup failed",
        "locked_error": "The database may still be in use by ChatGPT/Codex.\nFully quit the desktop app, including the tray process, and try again.\n\n{error}",
        "completed_title": "Cleanup complete",
        "completed_backup": "Removed {count} conversations.\n\nBackup:\n{backup}",
        "completed_no_backup": "Removed {count} conversations.\n\nNo backup was created.",
        "backup_dialog_title": "Choose backup location",
        "db_not_found": "Local index database not found:\n{path}",
        "changed_before_delete": "The index changed before deletion: {title}\nRefresh the list and try again.",
        "backup_integrity": "The backup database failed its integrity check.",
        "delete_count_error": "Unexpected number of rows deleted: {title}. The operation was rolled back.",
    },
}


def tr(lang, key, **values):
    text = TEXTS.get(lang, TEXTS["en"]).get(key, TEXTS["en"][key])
    return text.format(**values)


def detect_system_language():
    candidates = []
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name)
        if value:
            candidates.append(value)
    try:
        current = locale.getlocale()
        if current:
            candidates.extend(str(value) for value in current if value)
    except Exception:
        pass
    get_default = getattr(locale, "getdefaultlocale", None)
    if get_default:
        try:
            default = get_default()
            if default:
                candidates.extend(str(value) for value in default if value)
        except Exception:
            pass

    system_locale = " ".join(candidates).lower()
    chinese_markers = ("zh", "chinese", "中文", "中国", "台湾", "taiwan", "hong kong", "hongkong")
    if any(marker in system_locale for marker in chinese_markers):
        return "zh"
    return "en"


def table_exists(con, name):
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def read_rows(search_text="", lang="zh"):
    if not DB.exists():
        raise FileNotFoundError(tr(lang, "db_not_found", path=DB))
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        sql = """
            SELECT host_id, thread_id, display_title, source_kind,
                   missing_candidate, source_updated_at
            FROM local_thread_catalog
            WHERE source_kind = 'chatgpt'
        """
        params = []
        if search_text:
            sql += " AND display_title LIKE ?"
            params.append(f"%{search_text}%")
        sql += " ORDER BY source_updated_at DESC, display_title COLLATE NOCASE"
        return [dict(row) for row in con.execute(sql, params).fetchall()]
    finally:
        con.close()


def format_time(value):
    try:
        return dt.datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, OSError):
        return ""


def app_icon_path():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "ChatGPTStaleConversationCleaner.ico"
    return Path(__file__).with_name("ChatGPTStaleConversationCleaner.ico")


def remove_rows(rows, create_backup, backup_dir, lang="zh"):
    con = sqlite3.connect(DB, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=15000")
    backup = None
    try:
        for row in rows:
            current = con.execute(
                """
                SELECT host_id, thread_id, display_title, source_kind
                FROM local_thread_catalog
                WHERE host_id=? AND thread_id=?
                  AND display_title=? AND source_kind='chatgpt'
                """,
                (row["host_id"], row["thread_id"], row["display_title"]),
            ).fetchone()
            if current is None:
                raise RuntimeError(
                    tr(lang, "changed_before_delete", title=row["display_title"])
                )

        if create_backup:
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_root = Path(backup_dir).expanduser().resolve()
            backup_root.mkdir(parents=True, exist_ok=True)
            backup = backup_root / f"codex-dev.db.backup-{stamp}"
            with sqlite3.connect(backup) as dest:
                con.backup(dest)
                if dest.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RuntimeError(tr(lang, "backup_integrity"))

        con.execute("BEGIN IMMEDIATE")
        try:
            host_counts = {}
            for row in rows:
                host_counts[row["host_id"]] = host_counts.get(row["host_id"], 0) + 1
                if table_exists(con, "local_thread_catalog_scan_checkpoints"):
                    checkpoint = con.execute(
                        "SELECT 1 FROM local_thread_catalog_scan_checkpoints WHERE host_id=?",
                        (row["host_id"],),
                    ).fetchone()
                    if checkpoint and table_exists(con, "local_thread_catalog_scan_entries"):
                        con.execute(
                            """
                            INSERT INTO local_thread_catalog_scan_entries(host_id, thread_id, removed)
                            VALUES (?, ?, 1)
                            ON CONFLICT(host_id, thread_id) DO UPDATE SET removed=1
                            """,
                            (row["host_id"], row["thread_id"]),
                        )

                removed = con.execute(
                    """
                    DELETE FROM local_thread_catalog
                    WHERE host_id=? AND thread_id=?
                      AND display_title=? AND source_kind='chatgpt'
                    """,
                    (row["host_id"], row["thread_id"], row["display_title"]),
                ).rowcount
                if removed != 1:
                    raise RuntimeError(
                        tr(lang, "delete_count_error", title=row["display_title"])
                    )

            if table_exists(con, "local_thread_catalog_sync_state"):
                for host_id, count in host_counts.items():
                    con.execute(
                        """
                        UPDATE local_thread_catalog_sync_state
                        SET observation_sequence = observation_sequence + ?
                        WHERE host_id = ?
                        """,
                        (count, host_id),
                    )
            if table_exists(con, "local_thread_catalog_metadata"):
                con.execute(
                    """
                    UPDATE local_thread_catalog_metadata
                    SET catalog_revision = catalog_revision + ?
                    WHERE id = 1
                    """,
                    (len(rows),),
                )

            if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise RuntimeError(tr(lang, "backup_integrity"))
            con.commit()
        except BaseException:
            con.rollback()
            raise
    finally:
        con.close()
    return backup


def main():
    root = tk.Tk()
    state = {
        "language_mode": "auto",
        "language": detect_system_language(),
        "rows": {},
        "selected": set(),
        "item_to_key": {},
    }
    root.title(tr(state["language"], "window_title"))
    try:
        root.iconbitmap(default=str(app_icon_path()))
    except tk.TclError:
        pass
    root.geometry("980x680")
    root.minsize(760, 500)

    backup_var = tk.BooleanVar(value=False)
    backup_dir_var = tk.StringVar(value=str(DB.parent))
    search_var = tk.StringVar()
    status_var = tk.StringVar()
    count_var = tk.StringVar()

    outer = ttk.Frame(root, padding=16)
    outer.pack(fill="both", expand=True)

    language_line = ttk.Frame(outer)
    language_line.pack(fill="x", pady=(0, 8))
    language_combo = ttk.Combobox(language_line, state="readonly", width=16)
    language_combo.pack(side="right")
    language_label = ttk.Label(language_line)
    language_label.pack(side="right", padx=(0, 8))

    description_label = ttk.Label(outer)
    description_label.pack(anchor="w")

    search_line = ttk.Frame(outer)
    search_line.pack(fill="x", pady=(10, 8))
    filter_label = ttk.Label(search_line)
    filter_label.pack(side="left")
    search_entry = ttk.Entry(search_line, textvariable=search_var)
    search_entry.pack(side="left", fill="x", expand=True, padx=(6, 8))

    list_frame = ttk.Frame(outer)
    list_frame.pack(fill="both", expand=True)
    columns = ("checked", "title", "updated", "thread_id")
    tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.column("checked", width=58, minwidth=58, anchor="center", stretch=False)
    tree.column("title", width=430, minwidth=180, anchor="w")
    tree.column("updated", width=145, minwidth=120, anchor="center", stretch=False)
    tree.column("thread_id", width=300, minwidth=180, anchor="w")
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def update_count():
        count_var.set(
            tr(
                state["language"],
                "count",
                visible=len(tree.get_children()),
                selected=len(state["selected"]),
            )
        )

    def populate(rows):
        tree.delete(*tree.get_children())
        state["rows"] = {}
        state["item_to_key"] = {}
        for index, row in enumerate(rows):
            key = (row["host_id"], row["thread_id"])
            state["rows"][key] = row
            item = f"row-{index}"
            state["item_to_key"][item] = key
            mark = CHECKED if key in state["selected"] else UNCHECKED
            tree.insert(
                "",
                "end",
                iid=item,
                values=(
                    mark,
                    row["display_title"],
                    format_time(row["source_updated_at"]),
                    row["thread_id"],
                ),
            )
        update_count()

    def refresh_list(show_errors=True):
        try:
            rows = read_rows(search_var.get().strip(), state["language"])
            visible_keys = {(row["host_id"], row["thread_id"]) for row in rows}
            state["selected"] &= visible_keys
            populate(rows)
            status_var.set(tr(state["language"], "list_updated"))
        except Exception as exc:
            status_var.set(tr(state["language"], "read_failed_status"))
            if show_errors:
                messagebox.showerror(
                    tr(state["language"], "read_error_title"), str(exc), parent=root
                )

    def toggle_item(item):
        key = state["item_to_key"].get(item)
        if key is None:
            return
        if key in state["selected"]:
            state["selected"].remove(key)
        else:
            state["selected"].add(key)
        values = list(tree.item(item, "values"))
        values[0] = CHECKED if key in state["selected"] else UNCHECKED
        tree.item(item, values=values)
        update_count()

    def on_click(event):
        item = tree.identify_row(event.y)
        column = tree.identify_column(event.x)
        if item and column == "#1":
            toggle_item(item)
            return "break"

    tree.bind("<Button-1>", on_click)
    tree.bind("<Double-1>", lambda event: toggle_item(tree.identify_row(event.y)))

    def select_all():
        state["selected"].update(state["rows"])
        populate(list(state["rows"].values()))

    def clear_all():
        state["selected"].clear()
        populate(list(state["rows"].values()))

    def choose_backup_dir():
        selected = filedialog.askdirectory(
            parent=root,
            title=tr(state["language"], "backup_dialog_title"),
            initialdir=backup_dir_var.get(),
        )
        if selected:
            backup_dir_var.set(selected)

    def delete_selected():
        lang = state["language"]
        rows = [
            state["rows"][key]
            for key in state["selected"]
            if key in state["rows"]
        ]
        if not rows:
            messagebox.showwarning(
                tr(lang, "no_selection_title"), tr(lang, "no_selection"), parent=root
            )
            return
        rows.sort(key=lambda row: (row["display_title"], row["thread_id"]))
        if len(rows) <= 12:
            titles = "\n".join(f"• {row['display_title']}" for row in rows)
        else:
            titles = "\n".join(f"• {row['display_title']}" for row in rows[:12])
            titles += f"\n• ……以及另外 {len(rows) - 12} 条" if lang == "zh" else f"\n• ...and {len(rows) - 12} more"
        if not messagebox.askyesno(
            tr(lang, "confirm_title"),
            tr(lang, "confirm_text", count=len(rows), titles=titles),
            parent=root,
        ):
            return
        try:
            backup = remove_rows(rows, backup_var.get(), backup_dir_var.get(), lang)
        except sqlite3.OperationalError as exc:
            messagebox.showerror(
                tr(lang, "failed_title"),
                tr(lang, "locked_error", error=str(exc)),
                parent=root,
            )
            return
        except Exception as exc:
            messagebox.showerror(tr(lang, "failed_title"), str(exc), parent=root)
            return

        state["selected"].clear()
        refresh_list(show_errors=False)
        if backup:
            messagebox.showinfo(
                tr(lang, "completed_title"),
                tr(lang, "completed_backup", count=len(rows), backup=backup),
                parent=root,
            )
        else:
            messagebox.showinfo(
                tr(lang, "completed_title"),
                tr(lang, "completed_no_backup", count=len(rows)),
                parent=root,
            )

    def apply_language(mode):
        state["language_mode"] = mode
        state["language"] = detect_system_language() if mode == "auto" else mode
        lang = state["language"]
        root.title(tr(lang, "window_title"))
        language_label.configure(text=tr(lang, "language_label"))
        language_combo.configure(
            values=[tr(lang, "auto"), tr(lang, "chinese"), tr(lang, "english")]
        )
        language_combo.current(LANGUAGE_MODES.index(mode))
        description_label.configure(text=tr(lang, "description"))
        filter_label.configure(text=tr(lang, "filter_label"))
        tree.heading("checked", text=tr(lang, "checked"))
        tree.heading("title", text=tr(lang, "title"))
        tree.heading("updated", text=tr(lang, "updated"))
        tree.heading("thread_id", text=tr(lang, "thread_id"))
        refresh_button.configure(text=tr(lang, "refresh"))
        select_all_button.configure(text=tr(lang, "select_all"))
        clear_all_button.configure(text=tr(lang, "clear_all"))
        backup_checkbutton.configure(text=tr(lang, "backup"))
        backup_button.configure(text=tr(lang, "choose_backup"))
        delete_button.configure(text=tr(lang, "confirm_delete"))
        status_var.set(
            tr(lang, "list_updated") if state["rows"] else tr(lang, "loading")
        )
        update_count()

    language_combo.bind(
        "<<ComboboxSelected>>",
        lambda _event: apply_language(LANGUAGE_MODES[language_combo.current()]),
    )

    action_line = ttk.Frame(outer)
    action_line.pack(fill="x", pady=(9, 0))
    refresh_button = ttk.Button(action_line, command=refresh_list)
    refresh_button.pack(side="left")
    select_all_button = ttk.Button(action_line, command=select_all)
    select_all_button.pack(side="left", padx=(8, 0))
    clear_all_button = ttk.Button(action_line, command=clear_all)
    clear_all_button.pack(side="left", padx=(8, 0))
    ttk.Label(action_line, textvariable=count_var).pack(side="left", padx=(14, 0))

    backup_line = ttk.Frame(outer)
    backup_line.pack(fill="x", pady=(9, 0))
    backup_checkbutton = ttk.Checkbutton(backup_line, variable=backup_var)
    backup_checkbutton.pack(side="left")
    backup_button = ttk.Button(backup_line, command=choose_backup_dir)
    backup_button.pack(side="left", padx=(10, 0))
    ttk.Label(backup_line, textvariable=backup_dir_var, foreground="#666666").pack(
        side="left", padx=(8, 0)
    )

    bottom_line = ttk.Frame(outer)
    bottom_line.pack(fill="x", pady=(9, 0))
    ttk.Label(bottom_line, textvariable=status_var, foreground="#555555").pack(side="left")
    delete_button = ttk.Button(bottom_line, command=delete_selected)
    delete_button.pack(side="right")

    apply_language(state["language_mode"])
    search_var.trace_add("write", lambda *_args: refresh_list(show_errors=False))
    search_entry.bind("<Return>", lambda _event: refresh_list())
    root.after(100, lambda: refresh_list(show_errors=True))
    root.mainloop()


if __name__ == "__main__":
    main()
