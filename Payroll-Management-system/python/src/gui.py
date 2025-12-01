import calendar
import csv
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import List

DEFAULT_ENV_FILE = ".env"


def _read_env_file(path: Path) -> dict[str, str]:
    """Simple key=value reader for local default credentials."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}

    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from db_service import (
    delete_row,
    fetch_table_constraints,
    fetch_unsettled_totals,
    fetch_record_by_column,
    fetch_table_rows,
    fetch_table_schema,
    insert_row,
    list_tables,
    normalize_records,
    update_row,
)
from employee_service import (
    add_employee,
    delete_employee,
    export_employees_to_csv,
    fetch_employees,
    gen_employee_records,
    gen_random_indices,
    import_employees_from_csv,
    insert_into_mysql,
    read_jobs,
    read_lines,
    update_employee,
)


class DataManagerGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("员工生成与表管理工具")
        self.root.geometry("1920x1080")

        self.base_dir = BASE_DIR
        self._set_icon()
        static_dir = BASE_DIR / "static"
        self.names_path = tk.StringVar(value=str(static_dir / "names.txt"))
        self.jobs_path = tk.StringVar(value=str(static_dir / "jobs.csv"))
        self.count_var = tk.StringVar(value="64")
        self.insert_var = tk.BooleanVar(value=False)

        self.host_var = tk.StringVar(value="localhost")
        self.port_var = tk.StringVar(value="3306")
        self.user_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        self.db_var = tk.StringVar()
        self.db_entries: list[ttk.Entry] = []
        self._load_default_db_credentials()

        self.employees: list[dict] = []
        self.db_records: list[dict] = []
        self.filtered_records: list[dict] = []
        self.table_mode: str = "generator"
        self.status_var = tk.StringVar(value="就绪。")

        self.emp_id_var = tk.StringVar()
        self.emp_name_var = tk.StringVar()
        self.emp_dept_var = tk.StringVar()
        self.emp_pos_var = tk.StringVar()
        self.emp_salary_var = tk.StringVar()
        self.emp_join_var = tk.StringVar()

        self.tables: list[str] = []
        self.table_var = tk.StringVar()
        self.table_columns: list[str] = []
        self.table_schema: list[dict] = []
        self.field_vars: dict[str, tk.StringVar] = {}
        self.key_column: str | None = None
        self.sort_state: dict[str, bool] = {}
        self.search_var = tk.StringVar()
        self.foreign_keys: dict[str, tuple[str, str]] = {}
        self.fk_tooltip: tk.Toplevel | None = None
        self.fk_hover_target: tuple[str, str] | None = None
        self.fk_cache: dict[tuple[str, str, str], dict] = {}
        self.fk_option_records: dict[str, dict[str, dict]] = {}
        self.field_types: dict[str, str] = {}
        self.payroll_cache: dict[str, float | None] = {
            "basic_salary":None,
            "bonus_total":None,
            "deduction_total":None,
        }

        self._build_generator_form()
        self._build_db_config()
        self._build_table_toolbar()
        self._build_table()
        self._build_record_form()
        self._build_status_bar()

    # 生成器部分
    def _build_generator_form(self) -> None:
        frm = ttk.LabelFrame(self.root, text="员工随机生成", padding=10)
        frm.pack(fill="x", padx=10, pady=(10, 5))

        ttk.Label(frm, text="姓名文件").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.names_path, width=60).grid(row=0, column=1, sticky="we", padx=5)
        ttk.Button(frm, text="浏览", command=self._choose_names).grid(row=0, column=2, padx=5)

        ttk.Label(frm, text="岗位文件").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.jobs_path, width=60).grid(row=1, column=1, sticky="we", padx=5)
        ttk.Button(frm, text="浏览", command=self._choose_jobs).grid(row=1, column=2, padx=5)

        ttk.Label(frm, text="生成数量").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.count_var, width=10).grid(row=2, column=1, sticky="w", padx=5)

        ttk.Checkbutton(frm, text="生成后写入 MySQL", variable=self.insert_var, command=self._toggle_db_fields).grid(
            row=3, column=0, sticky="w"
        )

        ttk.Button(frm, text="生成员工", command=self._on_generate).grid(row=4, column=0, pady=10, sticky="w")
        self.save_btn = ttk.Button(frm, text="保存为 CSV", command=self._save_csv)
        self.save_btn.state(["disabled"])
        self.save_btn.grid(row=4, column=1, pady=10, sticky="w", padx=5)

    # 数据库配置与表管理
    def _build_db_config(self) -> None:
        frm = ttk.LabelFrame(self.root, text="数据库连接与表切换", padding=10)
        frm.pack(fill="x", padx=10, pady=5)

        ttk.Label(frm, text="主机").grid(row=0, column=0, sticky="w")
        host_entry = ttk.Entry(frm, textvariable=self.host_var, width=18)
        host_entry.grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(frm, text="端口").grid(row=0, column=2, sticky="e")
        port_entry = ttk.Entry(frm, textvariable=self.port_var, width=8)
        port_entry.grid(row=0, column=3, sticky="w")

        ttk.Label(frm, text="用户名").grid(row=0, column=4, sticky="e")
        user_entry = ttk.Entry(frm, textvariable=self.user_var, width=18)
        user_entry.grid(row=0, column=5, sticky="w", padx=5)

        ttk.Label(frm, text="密码").grid(row=0, column=6, sticky="e")
        pass_entry = ttk.Entry(frm, textvariable=self.pass_var, width=18, show="*")
        pass_entry.grid(row=0, column=7, sticky="w")

        ttk.Label(frm, text="数据库").grid(row=0, column=8, sticky="e")
        db_entry = ttk.Entry(frm, textvariable=self.db_var, width=18)
        db_entry.grid(row=0, column=9, sticky="w", padx=5)

        self.db_entries = [host_entry, port_entry, user_entry, pass_entry, db_entry]
        ttk.Button(frm, text="刷新表列表", command=self._refresh_tables).grid(row=1, column=0, padx=5, pady=5)
        ttk.Label(frm, text="当前表").grid(row=1, column=1, sticky="e")
        self.table_combo = ttk.Combobox(frm, textvariable=self.table_var, width=26, state="readonly")
        self.table_combo.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        ttk.Button(frm, text="加载当前表", command=self._load_table_data).grid(row=1, column=3, padx=5, pady=5)
        frm.grid_columnconfigure(4, weight=1)

    def _set_icon(self) -> None:
        icon_path = self.base_dir / "static" / "icon.png"
        if not icon_path.exists():
            return
        try:
            icon = tk.PhotoImage(file=str(icon_path))
        except tk.TclError:
            return
        self.root.iconphoto(True, icon)
        self._icon_image = icon  # keep a reference to avoid GC

    def _load_default_db_credentials(self) -> None:
        env_path = self.base_dir / "static" / DEFAULT_ENV_FILE
        env_values = _read_env_file(env_path)
        if not env_values:
            return

        self.user_var.set(env_values.get("USR", self.user_var.get()))

        self.db_var.set(env_values.get("DB", self.db_var.get()))

    def _build_table_toolbar(self) -> None:
        frm = ttk.Frame(self.root, padding=(10, 0))
        frm.pack(fill="x")

        ttk.Label(frm, text="搜索关键词").grid(row=0, column=0, sticky="e")
        ttk.Entry(frm, textvariable=self.search_var, width=30).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Button(frm, text="应用搜索", command=self._apply_search).grid(row=0, column=2, padx=5)
        ttk.Button(frm, text="清除筛选", command=self._clear_filters).grid(row=0, column=3, padx=5)
        ttk.Button(frm, text="查看属性", command=self._show_table_attributes).grid(row=0, column=4, padx=5)
        ttk.Button(frm, text="查看约束", command=self._show_table_constraints).grid(row=0, column=5, padx=5)
        frm.grid_columnconfigure(6, weight=1)

    def _build_table(self) -> None:
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(container, show="headings")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Motion>", self._on_tree_motion)
        self.tree.bind("<Leave>", lambda _:self._hide_fk_tooltip())

        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, rowspan=2, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

    def _build_record_form(self) -> None:
        self.form_frame = ttk.LabelFrame(self.root, text="表记录 CRUD（随选表动态更新）", padding=20)
        self.form_frame.pack(fill="x", padx=12, pady=(8, 22), ipady=28)

        self.dynamic_fields = ttk.Frame(self.form_frame)
        self.dynamic_fields.pack(fill="x", pady=14, ipady=14)

        db_btns = ttk.Frame(self.form_frame)
        db_btns.pack(fill="x", pady=5)
        ttk.Button(db_btns, text="新增记录", command=self._create_record).grid(row=0, column=0, padx=5)
        ttk.Button(db_btns, text="更新记录", command=self._update_record).grid(row=0, column=1, padx=5)
        ttk.Button(db_btns, text="删除记录", command=self._delete_record).grid(row=0, column=2, padx=5)
        ttk.Button(db_btns, text="CSV 导入", command=self._import_table_csv).grid(row=0, column=3, padx=5)
        ttk.Button(db_btns, text="CSV 导出", command=self._export_table_csv).grid(row=0, column=4, padx=5)

    def _build_status_bar(self) -> None:
        self.status_label = ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=5)
        self.status_label.pack(fill="x", side="bottom")

    # 辅助方法
    def _toggle_db_fields(self) -> None:
        for entry in self.db_entries:
            entry.configure(state="normal")

    def _choose_jobs(self) -> None:
        path = filedialog.askopenfilename(
            title="选择岗位 CSV", initialdir=self.base_dir, filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.jobs_path.set(path)
            self._set_status(f"选择岗位文件: {Path(path).name}")

    def _choose_names(self) -> None:
        path = filedialog.askopenfilename(
            title="选择姓名 TXT", initialdir=self.base_dir, filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.names_path.set(path)
            self._set_status(f"选择姓名文件: {Path(path).name}")

    def _on_generate(self) -> None:
        try:
            names, jobs, count = self._validate_inputs()

            random_indices = gen_random_indices(count, max_index=len(names))
            selected_names = [names[i - 1] for i in random_indices]
            employees = gen_employee_records(selected_names, jobs)

            self.employees = employees
            self.filtered_records = employees
            self.table_mode = "generator"
            self.save_btn.state(["!disabled"])
            self._render_table(employees)
            self._set_status(f"已生成 {len(employees)} 条员工记录。")

            if self.insert_var.get():
                cfg = self._get_db_config()
                insert_into_mysql(employees, **cfg)
                messagebox.showinfo("成功", "已写入 MySQL。")
                self._set_status(f"已向数据库插入 {len(employees)} 条记录。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("错误", str(exc))

    def _render_table(self, records: List[dict]) -> None:
        columns: list[str] = []
        if records:
            columns = list(records[0].keys())
        elif self.table_columns:
            columns = self.table_columns
        self.tree.configure(columns=columns)

        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col:self._on_heading_click(c))
            self.tree.column(col, width=140, anchor="center")

        for row in self.tree.get_children():
            self.tree.delete(row)

        for record in records:
            values = [record.get(col, "") for col in columns]
            self.tree.insert("", "end", values=values)

        if records:
            self.save_btn.state(["!disabled"])
        else:
            self.save_btn.state(["disabled"])

    def _render_type_hints(self, columns: list[str]) -> None:
        frame = getattr(self, "type_hint_frame", None)
        if frame:
            for child in frame.winfo_children():
                child.destroy()
        if not frame or not columns or not self.field_types:
            return
        for idx, col in enumerate(columns):
            hint = self.field_types.get(col, "")
            label = ttk.Label(
                frame,
                text=f"{col}: {hint}",
                foreground="#555",
                anchor="w",
                padding=(4, 2),
            )
            label.grid(row=idx // 4, column=idx % 4, sticky="w", padx=4, pady=2)
        for i in range(4):
            frame.columnconfigure(i, weight=1)

    def _validate_inputs(self) -> tuple[list[str], list[tuple[str, str]], int]:
        names_path = Path(self.names_path.get()).expanduser()
        jobs_path = Path(self.jobs_path.get()).expanduser()
        if not names_path.is_file():
            raise FileNotFoundError(f"姓名文件不存在: {names_path}")
        if not jobs_path.is_file():
            raise FileNotFoundError(f"岗位文件不存在: {jobs_path}")

        try:
            count = int(self.count_var.get())
        except ValueError as exc:
            raise ValueError("数量必须是正整数。") from exc
        if count <= 0:
            raise ValueError("数量必须大于 0。")

        names = read_lines(names_path)
        jobs = read_jobs(jobs_path)
        if not names:
            raise ValueError("姓名文件为空。")
        if not jobs:
            raise ValueError("岗位文件为空。")
        return names, jobs, count

    def _save_csv(self) -> None:
        records = self.filtered_records or self._get_active_records()
        if not records:
            messagebox.showinfo("无数据", "请先生成或加载数据。")
            return

        path = filedialog.asksaveasfilename(
            title="保存 CSV", defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=self.base_dir
        )
        if not path:
            return

        columns = list(records[0].keys())
        with Path(path).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(records)
        messagebox.showinfo("已保存", f"已保存 {len(records)} 条记录到 {path}。")
        self._set_status(f"已保存 {len(records)} 条记录为 CSV。")

    def _get_db_config(self) -> dict:
        cfg = {
            "host":self.host_var.get() or "localhost",
            "port":int(self.port_var.get() or 3306),
            "user":self.user_var.get(),
            "password":self.pass_var.get(),
            "database":self.db_var.get(),
        }
        missing = [k for k, v in cfg.items() if k not in {"port", "host"} and not v]
        if missing:
            raise ValueError(f"缺少数据库字段: {', '.join(missing)}")
        return cfg

    def _collect_form_data(self) -> dict:
        emp_id = self.emp_id_var.get().strip()
        name = self.emp_name_var.get().strip()
        dept = self.emp_dept_var.get().strip()
        position = self.emp_pos_var.get().strip()
        salary_raw = self.emp_salary_var.get().strip()
        join_date_raw = self.emp_join_var.get().strip()

        if not all([emp_id, name, dept, position, salary_raw, join_date_raw]):
            raise ValueError("员工表单所有字段均为必填。")
        try:
            salary = float(salary_raw)
        except ValueError as exc:
            raise ValueError("薪资必须为数字。") from exc
        try:
            join_date = datetime.strptime(join_date_raw, "%Y-%m-%d").date().isoformat()
        except ValueError as exc:
            raise ValueError("入职日期格式应为 YYYY-MM-DD。") from exc

        return {
            "id":emp_id,
            "name":name,
            "dept":dept,
            "position":position,
            "salary":salary,
            "join_date":join_date,
        }

    def _load_employees(self) -> None:
        try:
            cfg = self._get_db_config()
            self.db_records = fetch_employees(**cfg)
            self.filtered_records = self.db_records
            self.table_mode = "db"
            self.table_columns = list(self.db_records[0].keys()) if self.db_records else []
            self._render_table(self.db_records)
            self._set_status(f"已从数据库加载 {len(self.db_records)} 条员工记录。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("数据库错误", str(exc))

    def _create_employee(self) -> None:
        try:
            record = self._collect_form_data()
            cfg = self._get_db_config()
            add_employee(record, **cfg)
            self._clear_form_fields()
            self._load_employees()
            messagebox.showinfo("成功", "新增员工成功。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("数据库错误", str(exc))

    def _update_employee(self) -> None:
        try:
            record = self._collect_form_data()
            cfg = self._get_db_config()
            update_employee(record, **cfg)
            self._load_employees()
            messagebox.showinfo("成功", "更新员工成功。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("数据库错误", str(exc))

    def _delete_employee(self) -> None:
        emp_id = self.emp_id_var.get().strip()
        if not emp_id:
            messagebox.showinfo("提示", "请选择要删除的员工。")
            return
        if not messagebox.askyesno("确认", f"确定删除员工 {emp_id}?"):
            return
        try:
            cfg = self._get_db_config()
            delete_employee(emp_id, **cfg)
            self._clear_form_fields()
            self._load_employees()
            messagebox.showinfo("成功", "删除员工成功。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("数据库错误", str(exc))

    def _import_csv_to_db(self) -> None:
        path = filedialog.askopenfilename(
            title="选择要导入的 CSV", initialdir=self.base_dir, filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            cfg = self._get_db_config()
            imported = import_employees_from_csv(Path(path), **cfg)
            self._load_employees()
            messagebox.showinfo("成功", f"成功导入 {imported} 条记录。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("导入失败", str(exc))

    def _export_csv_from_db(self) -> None:
        if not self.db_records:
            self._load_employees()
        if not self.db_records:
            messagebox.showinfo("提示", "数据库中暂无可导出的记录。")
            return
        path = filedialog.asksaveasfilename(
            title="导出员工 CSV", defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        export_employees_to_csv(self.db_records, Path(path))
        messagebox.showinfo("已保存", f"已导出 {len(self.db_records)} 条记录到 {path}。")
        self._set_status(f"导出 {len(self.db_records)} 条记录。")

    # 通用表 CRUD
    def _refresh_tables(self) -> None:
        try:
            cfg = self._get_db_config()
            self.tables = list_tables(**cfg)
            self.table_combo["values"] = self.tables
            if self.tables and not self.table_var.get():
                self.table_var.set(self.tables[0])
            self._set_status(f"已加载表列表: {', '.join(self.tables)}")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("数据库错误", str(exc))

    def _load_table_data(self) -> None:
        table = self.table_var.get()
        if not table:
            messagebox.showinfo("提示", "请选择需要加载的表。")
            return
        try:
            cfg = self._get_db_config()
            self.table_schema = fetch_table_schema(table, **cfg)
            self.table_columns = [c["Field"] for c in self.table_schema]
            self.field_types = {c["Field"]:c.get("Type", "") for c in self.table_schema}
            self.key_column = next((c["Field"] for c in self.table_schema if c.get("Key") == "PRI"),
                                   self.table_columns[0])
            self.foreign_keys = self._extract_foreign_keys(fetch_table_constraints(table, **cfg))
            self.fk_option_records = {}
            rows = normalize_records(fetch_table_rows(table, **cfg))
            self.db_records = rows
            self.filtered_records = rows
            self.table_mode = "db"
            self._render_table(rows)
            self._build_dynamic_fields()
            self._set_status(f"已加载表 {table} 的 {len(rows)} 条记录。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("数据库错误", str(exc))

    def _extract_foreign_keys(self, constraints: list[dict]) -> dict[str, tuple[str, str]]:
        foreign_keys: dict[str, tuple[str, str]] = {}
        for item in constraints:
            if item.get("constraint_type") != "FOREIGN KEY":
                continue
            column = item.get("column_name")
            target_table = item.get("referenced_table")
            target_column = item.get("referenced_column")
            if column and target_table and target_column:
                foreign_keys[column] = (target_table, target_column)
        return foreign_keys

    def _build_dynamic_fields(self) -> None:
        for child in self.dynamic_fields.winfo_children():
            child.destroy()
        self.field_vars = {}
        self.payroll_cache = {"basic_salary":None, "bonus_total":None, "deduction_total":None}
        columns_per_row = 4
        for idx, col in enumerate(self.table_columns):
            var = tk.StringVar()
            self.field_vars[col] = var
            cell = ttk.Frame(self.dynamic_fields)
            cell.grid(row=idx // columns_per_row, column=idx % columns_per_row, sticky="nsew", padx=8, pady=6)
            ttk.Label(cell, text=col).pack(anchor="w")
            holder = ttk.Frame(cell)
            holder.pack(fill="x", pady=4)

            if self._should_use_fk_selector(col):
                options = self._get_fk_options(col)
                combo = ttk.Combobox(
                    holder, textvariable=var, state="readonly", width=16, values=[opt["key"] for opt in options]
                )
                combo.pack(side="left")
                preview = ttk.Label(holder, text="预览", relief="groove", padding=(4, 2))
                preview.pack(side="left", padx=4)
                preview.bind("<Enter>", lambda e, c=col:self._show_field_preview(e, c))
                preview.bind("<Leave>", lambda _ :self._hide_fk_tooltip())
            elif self._is_date_field(col):
                entry = ttk.Entry(holder, textvariable=var, width=16, state="readonly")
                entry.pack(side="left")
                ttk.Button(holder, text="选日期", command=lambda v=var:self._open_date_picker(v)).pack(side="left", padx=4)
            else:
                entry = ttk.Entry(holder, textvariable=var, width=18)
                entry.pack(side="left")

            if self.table_var.get() == "Payroll_Record" and col in {"BasicSalary", "TotalBonus", "TotalDeduction"}:
                ttk.Button(holder, text="获取数据", command=lambda c=col:self._populate_payroll_field(c)).pack(side="left", padx=4)
            if self.table_var.get() == "Payroll_Record" and col == "NetSalary":
                ttk.Button(holder, text="计算", command=self._calculate_net_salary).pack(side="left", padx=4)

        for i in range(columns_per_row):
            self.dynamic_fields.columnconfigure(i, weight=1)

    def _get_clean_value(self, var: tk.StringVar) -> str:
        return var.get().strip()

    def _collect_dynamic_data(self) -> dict:
        if not self.field_vars:
            raise ValueError("请先加载表以生成动态表单。")
        data: dict[str, str] = {}
        for col, var in self.field_vars.items():
            data[col] = self._get_clean_value(var)
        if self.table_var.get() == "Payroll_Record":
            basic_salary = self._get_basic_salary_value(fetch_if_missing=True)
            bonus_total, deduction_total = self._get_bonus_deduction_values(fetch_if_missing=True)
            net_salary = basic_salary + bonus_total - deduction_total
            data["BasicSalary"] = f"{basic_salary:.2f}"
            data["TotalBonus"] = f"{bonus_total:.2f}"
            data["TotalDeduction"] = f"{deduction_total:.2f}"
            data["NetSalary"] = f"{net_salary:.2f}"
            if "TotalBonus" in self.field_vars:
                self.field_vars["TotalBonus"].set(data["TotalBonus"])
            if "TotalDeduction" in self.field_vars:
                self.field_vars["TotalDeduction"].set(data["TotalDeduction"])
            if "NetSalary" in self.field_vars:
                self.field_vars["NetSalary"].set(data["NetSalary"])
        return data

    def _should_use_fk_selector(self, column: str) -> bool:
        if column == "EmployeeId":
            return False
        return column in self.foreign_keys

    def _is_date_field(self, column: str) -> bool:
        type_info = self.field_types.get(column, "").lower()
        return type_info.startswith("date") or "datetime" in type_info

    def _get_fk_options(self, column: str) -> list[dict]:
        ref_table, ref_column = self.foreign_keys[column]
        cfg = self._get_db_config()
        records = fetch_table_rows(ref_table, **cfg)
        if ref_table == "Event":
            expected = 1 if "Overtime" in column else 0
            records = [r for r in records if int(r.get("EventType", 0)) == expected]
        if ref_table == "Payroll_Item":
            expected = 1 if "Bonus" in column else 0
            records = [r for r in records if int(r.get("ItemType", 0)) == expected]
        options: list[dict] = []
        for record in records:
            value = str(record.get(ref_column, ""))
            if not value:
                continue
            label = record.get("EventName") or record.get("ItemName") or record.get("PaymentMethodName") or value
            display = value if label == value else f"{value} - {label}"
            options.append({"value":display if display else value, "record":record, "key":value})
        self.fk_option_records[column] = {opt["key"]:opt["record"] for opt in options}
        return options

    def _get_payroll_context(self) -> tuple[str, str]:
        employee_id = self._get_clean_value(self.field_vars.get("EmployeeId", tk.StringVar()))
        payroll_date = self._get_clean_value(self.field_vars.get("PayrollDate", tk.StringVar()))
        if not employee_id or not payroll_date:
            raise ValueError("Payroll_Record 需要先填写 EmployeeId 与 PayrollDate。")
        try:
            datetime.strptime(payroll_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("PayrollDate 格式应为 YYYY-MM-DD。") from exc
        return employee_id, payroll_date

    def _pull_basic_salary(self) -> float:
        employee_id, _ = self._get_payroll_context()
        cfg = self._get_db_config()
        record = fetch_record_by_column("Employee", "EmployeeId", employee_id, **cfg)
        if not record or "BasicSalary" not in record:
            raise ValueError("未在 Employee 表中找到对应的 BasicSalary。")
        try:
            salary = float(record.get("BasicSalary", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("BasicSalary 数据无法解析为数字。") from exc
        self.payroll_cache["basic_salary"] = salary
        return salary

    def _pull_bonus_deduction(self) -> tuple[float, float]:
        employee_id, payroll_date = self._get_payroll_context()
        cfg = self._get_db_config()
        bonus_total, deduction_total = fetch_unsettled_totals(employee_id, payroll_date, **cfg)
        self.payroll_cache["bonus_total"] = bonus_total
        self.payroll_cache["deduction_total"] = deduction_total
        return bonus_total, deduction_total

    def _get_basic_salary_value(self, *, fetch_if_missing: bool = False) -> float:
        raw_value = self._get_clean_value(self.field_vars.get("BasicSalary", tk.StringVar()))
        if raw_value:
            try:
                salary = float(raw_value)
            except ValueError as exc:
                raise ValueError("BasicSalary 必须为数字。") from exc
            self.payroll_cache["basic_salary"] = salary
            return salary
        if self.payroll_cache["basic_salary"] is not None:
            return float(self.payroll_cache["basic_salary"])
        if fetch_if_missing:
            return self._pull_basic_salary()
        raise ValueError("请先填写或获取 BasicSalary。")

    def _get_bonus_deduction_values(self, *, fetch_if_missing: bool = False) -> tuple[float, float]:
        raw_bonus = self._get_clean_value(self.field_vars.get("TotalBonus", tk.StringVar()))
        raw_deduction = self._get_clean_value(self.field_vars.get("TotalDeduction", tk.StringVar()))
        bonus_val: float | None = None
        deduction_val: float | None = None
        if raw_bonus:
            try:
                bonus_val = float(raw_bonus)
            except ValueError as exc:
                raise ValueError("TotalBonus 必须为数字。") from exc
        if raw_deduction:
            try:
                deduction_val = float(raw_deduction)
            except ValueError as exc:
                raise ValueError("TotalDeduction 必须为数字。") from exc
        if bonus_val is None and self.payroll_cache["bonus_total"] is not None:
            bonus_val = float(self.payroll_cache["bonus_total"])
        if deduction_val is None and self.payroll_cache["deduction_total"] is not None:
            deduction_val = float(self.payroll_cache["deduction_total"])
        if (bonus_val is None or deduction_val is None) and fetch_if_missing:
            bonus_val, deduction_val = self._pull_bonus_deduction()
        if bonus_val is None or deduction_val is None:
            raise ValueError("请先计算待结算的奖金和扣款。")
        self.payroll_cache["bonus_total"] = bonus_val
        self.payroll_cache["deduction_total"] = deduction_val
        return bonus_val, deduction_val

    def _populate_payroll_field(self, field_name: str) -> None:
        if self.table_var.get() != "Payroll_Record":
            return
        try:
            if field_name == "BasicSalary":
                salary = self._pull_basic_salary()
                self.field_vars.get("BasicSalary", tk.StringVar()).set(f"{salary:.2f}")
                self._set_status("已从 Employee 获取 BasicSalary。")
            else:
                bonus_total, deduction_total = self._pull_bonus_deduction()
                if "TotalBonus" in self.field_vars:
                    self.field_vars["TotalBonus"].set(f"{bonus_total:.2f}")
                if "TotalDeduction" in self.field_vars:
                    self.field_vars["TotalDeduction"].set(f"{deduction_total:.2f}")
                self._set_status("已计算待结算的奖金与扣款。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("获取失败", str(exc))

    def _calculate_net_salary(self) -> None:
        try:
            basic_salary = self._get_basic_salary_value(fetch_if_missing=True)
            bonus_total, deduction_total = self._get_bonus_deduction_values(fetch_if_missing=True)
            net_salary = basic_salary + bonus_total - deduction_total
            if "NetSalary" in self.field_vars:
                self.field_vars["NetSalary"].set(f"{net_salary:.2f}")
            self.payroll_cache.update({
                "basic_salary":basic_salary,
                "bonus_total":bonus_total,
                "deduction_total":deduction_total,
            })
            self._set_status("已根据缓存数据计算 NetSalary。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("计算失败", str(exc))

    def _open_date_picker(self, target_var: tk.StringVar) -> None:
        current = target_var.get()
        try:
            now_date = datetime.strptime(current, "%Y-%m-%d").date()
        except ValueError:
            now_date = datetime.now().date()

        top = tk.Toplevel(self.root)
        top.title("选择日期")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        top.grab_set()

        nav_frame = ttk.Frame(top, padding=6)
        nav_frame.pack(fill="x")
        body = ttk.Frame(top, padding=(6, 0, 6, 6))
        body.pack()

        header_var = tk.StringVar()
        year = tk.IntVar(value=now_date.year)
        month = tk.IntVar(value=now_date.month)

        def _render_calendar() -> None:
            for child in body.winfo_children():
                child.destroy()
            header_var.set(f"{year.get()}年 {month.get()}月")
            days = ["一", "二", "三", "四", "五", "六", "日"]
            for idx, name in enumerate(days):
                ttk.Label(body, text=name, width=4, anchor="center").grid(row=0, column=idx, padx=2, pady=2)
            month_days = calendar.monthcalendar(year.get(), month.get())
            for wk, week in enumerate(month_days, start=1):
                for idx, day in enumerate(week):
                    if day == 0:
                        ttk.Label(body, text="", width=4).grid(row=wk, column=idx, padx=1, pady=1)
                        continue
                    btn = ttk.Button(
                        body,
                        text=str(day),
                        width=4,
                        command=lambda d=day: _set_date(d),
                    )
                    btn.grid(row=wk, column=idx, padx=1, pady=1)

        def _set_date(day: int) -> None:
            try:
                date_obj = datetime(year.get(), month.get(), day).date()
                target_var.set(date_obj.isoformat())
                top.destroy()
            except ValueError:
                messagebox.showerror("日期错误", "无效的日期。")

        def _shift_month(offset: int) -> None:
            new_month = month.get() + offset
            new_year = year.get()
            if new_month < 1:
                new_month = 12
                new_year -= 1
            elif new_month > 12:
                new_month = 1
                new_year += 1
            year.set(new_year)
            month.set(new_month)
            _render_calendar()

        ttk.Button(nav_frame, text="<", width=3, command=lambda: _shift_month(-1)).pack(side="left")
        ttk.Label(nav_frame, textvariable=header_var, width=14, anchor="center").pack(side="left", expand=True)
        ttk.Button(nav_frame, text=">", width=3, command=lambda: _shift_month(1)).pack(side="right")

        _render_calendar()

    def _show_field_preview(self, event: tk.Event, column: str) -> None:
        value = self.field_vars.get(column, tk.StringVar()).get().strip()
        if not value:
            return
        record = self.fk_option_records.get(column, {}).get(value)
        ref_table, ref_column = self.foreign_keys.get(column, (column, ""))
        if record is None and column in self.foreign_keys:
            try:
                cfg = self._get_db_config()
                record = fetch_record_by_column(ref_table, ref_column, value, **cfg)
            except Exception:
                record = None
        if not record:
            return
        self._show_fk_tooltip(event, ref_table, record)

    def _create_record(self) -> None:
        if not self.table_var.get():
            messagebox.showinfo("提示", "请选择表后再新增记录。")
            return
        try:
            data = self._collect_dynamic_data()
            cfg = self._get_db_config()
            insert_row(self.table_var.get(), data, **cfg)
            self._load_table_data()
            messagebox.showinfo("成功", "新增记录成功。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("数据库错误", str(exc))

    def _update_record(self) -> None:
        if not self.table_var.get():
            messagebox.showinfo("提示", "请选择表后再更新记录。")
            return
        if not self.key_column:
            messagebox.showinfo("提示", "当前表缺少主键，无法更新。")
            return
        try:
            data = self._collect_dynamic_data()
            if self.key_column not in data or not data[self.key_column]:
                raise ValueError(f"请填写主键字段 {self.key_column}。")
            key_value = data.pop(self.key_column)
            cfg = self._get_db_config()
            update_row(self.table_var.get(), data, self.key_column, key_value, **cfg)
            self._load_table_data()
            messagebox.showinfo("成功", "更新记录成功。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("数据库错误", str(exc))

    def _delete_record(self) -> None:
        if not self.table_var.get():
            messagebox.showinfo("提示", "请选择表后再删除记录。")
            return
        if not self.key_column:
            messagebox.showinfo("提示", "当前表缺少主键，无法删除。")
            return
        try:
            data = self._collect_dynamic_data()
            key_value = data.get(self.key_column)
            if not key_value:
                raise ValueError(f"请先在主键 {self.key_column} 中输入要删除的值。")
            if not messagebox.askyesno("确认", f"确定删除 {self.key_column}={key_value} 的记录吗？"):
                return
            cfg = self._get_db_config()
            delete_row(self.table_var.get(), self.key_column, key_value, **cfg)
            self._load_table_data()
            messagebox.showinfo("成功", "删除记录成功。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("数据库错误", str(exc))

    def _export_table_csv(self) -> None:
        if self.table_mode != "db" or not self.table_columns:
            messagebox.showinfo("提示", "请先加载数据库表后再导出。")
            return
        records = self.filtered_records or self.db_records
        if not records:
            messagebox.showinfo("提示", "当前表没有可导出的记录。")
            return
        path = filedialog.asksaveasfilename(
            title="导出当前表 CSV", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        with Path(path).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.table_columns)
            writer.writeheader()
            for record in records:
                writer.writerow({col:record.get(col, "") for col in self.table_columns})
        self._set_status(f"导出 {len(records)} 条记录到 {path}。")
        messagebox.showinfo("已保存", f"已导出 {len(records)} 条记录。")

    def _import_table_csv(self) -> None:
        if self.table_mode != "db" or not self.table_columns:
            messagebox.showinfo("提示", "请先加载数据库表后再导入。")
            return
        path = filedialog.askopenfilename(
            title="选择要导入的 CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            cfg = self._get_db_config()
            imported = 0
            with Path(path).open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row:
                        continue
                    payload = {col:row.get(col, "") for col in self.table_columns if col in row}
                    insert_row(self.table_var.get(), payload, **cfg)
                    imported += 1
            self._load_table_data()
            messagebox.showinfo("导入完成", f"成功导入 {imported} 条记录。")
            self._set_status(f"已导入 {imported} 条记录。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("导入失败", str(exc))

    def _apply_search(self) -> None:
        keyword = self.search_var.get().strip().lower()
        records = self._get_active_records()
        if not keyword:
            self.filtered_records = records
        else:
            self.filtered_records = [
                r for r in records if any(keyword in str(value).lower() for value in r.values())
            ]
        self._render_table(self.filtered_records)
        self._set_status(f"筛选结果 {len(self.filtered_records)} 条。")

    def _clear_filters(self) -> None:
        self.search_var.set("")
        self.filtered_records = self._get_active_records()
        self._render_table(self.filtered_records)
        self._set_status("已清除筛选。")

    def _show_table_attributes(self) -> None:
        table = self.table_var.get()
        if not table:
            messagebox.showinfo("提示", "请选择表后再查看属性。")
            return
        try:
            cfg = self._get_db_config()
            schema = fetch_table_schema(table, **cfg)
            if not schema:
                messagebox.showinfo("提示", "未找到表结构信息。")
                return
            rows = [
                {
                    "Field":col.get("Field", ""),
                    "Type":col.get("Type", ""),
                    "Null":col.get("Null", ""),
                    "Key":col.get("Key", ""),
                    "Default":"" if col.get("Default") is None else col.get("Default"),
                    "Extra":col.get("Extra", ""),
                    "Comment":col.get("Comment", ""),
                }
                for col in schema
            ]
            columns = [
                ("Field", "字段名"),
                ("Type", "数据类型"),
                ("Null", "允许空值"),
                ("Key", "键类型"),
                ("Default", "默认值"),
                ("Extra", "附加"),
                ("Comment", "注释"),
            ]
            self._open_info_dialog(f"{table} 的列属性", columns, rows)
            self._set_status(f"已展示 {table} 的字段属性。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("数据库错误", str(exc))

    def _show_table_constraints(self) -> None:
        table = self.table_var.get()
        if not table:
            messagebox.showinfo("提示", "请选择表后再查看约束。")
            return
        try:
            cfg = self._get_db_config()
            constraints = fetch_table_constraints(table, **cfg)
            if not constraints:
                messagebox.showinfo("提示", "当前表未定义约束。")
                self._set_status("未查询到约束。")
                return
            rows = []
            for item in constraints:
                reference = ""
                if item.get("referenced_table"):
                    ref_col = item.get("referenced_column") or ""
                    reference = (
                        f"{item['referenced_table']}.{ref_col}" if ref_col else item["referenced_table"]
                    )
                rows.append(
                    {
                        "constraint_name":item.get("constraint_name", ""),
                        "constraint_type":item.get("constraint_type", ""),
                        "column_name":item.get("column_name", "") or "",
                        "reference":reference,
                        "check_clause":item.get("check_clause", "") or "",
                    }
                )
            columns = [
                ("constraint_name", "约束名"),
                ("constraint_type", "类型"),
                ("column_name", "列"),
                ("reference", "引用/目标"),
                ("check_clause", "检查条件"),
            ]
            self._open_info_dialog(f"{table} 的约束", columns, rows)
            self._set_status(f"已展示 {table} 的约束信息。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("数据库错误", str(exc))

    def _on_heading_click(self, column: str) -> None:
        records = self.filtered_records or self._get_active_records()
        if not records:
            return
        ascending = not self.sort_state.get(column, True)
        self.sort_state[column] = ascending
        sorted_records = sorted(records, key=lambda r:str(r.get(column, "")), reverse=not ascending)
        self.filtered_records = sorted_records
        self._render_table(sorted_records)
        arrow = "↑" if ascending else "↓"
        self._set_status(f"按 {column} {arrow} 排序。")

    def _on_tree_select(self, event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        columns = self.tree["columns"]
        if self.table_mode == "db" and self.field_vars:
            for col, value in zip(columns, values):
                if col in self.field_vars:
                    self.field_vars[col].set(value)

    def _on_tree_double_click(self, event: tk.Event) -> None:
        if self.table_mode != "db" or not self.foreign_keys:
            return
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return
        try:
            col_index = int(col_id.replace("#", "")) - 1
        except ValueError:
            return
        columns = list(self.tree["columns"])
        if col_index < 0 or col_index >= len(columns):
            return
        column_name = columns[col_index]
        if column_name not in self.foreign_keys:
            return
        values = self.tree.item(row_id, "values")
        if col_index >= len(values):
            return
        value = values[col_index]
        if value in (None, ""):
            return
        target_table, target_column = self.foreign_keys[column_name]
        try:
            self.table_var.set(target_table)
            self._load_table_data()
            columns = list(self.tree["columns"])
            if target_column in columns:
                target_idx = columns.index(target_column)
                for item in self.tree.get_children():
                    vals = self.tree.item(item, "values")
                    if target_idx < len(vals) and str(vals[target_idx]) == str(value):
                        self.tree.selection_set(item)
                        self.tree.focus(item)
                        self.tree.see(item)
                        break
            self._set_status(f"已跳转到 {target_table}，匹配 {target_column}={value}。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("数据库错误", str(exc))

    def _on_tree_motion(self, event: tk.Event) -> None:
        if self.table_mode != "db" or not self.foreign_keys:
            self._hide_fk_tooltip()
            return
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            self._hide_fk_tooltip()
            return
        try:
            col_index = int(col_id.replace("#", "")) - 1
        except ValueError:
            self._hide_fk_tooltip()
            return
        columns = list(self.tree["columns"])
        if col_index < 0 or col_index >= len(columns):
            self._hide_fk_tooltip()
            return
        column_name = columns[col_index]
        if column_name not in self.foreign_keys:
            self._hide_fk_tooltip()
            return
        values = self.tree.item(row_id, "values")
        if col_index >= len(values):
            self._hide_fk_tooltip()
            return
        value = values[col_index]
        if value in (None, ""):
            self._hide_fk_tooltip()
            return
        target = (row_id, column_name)
        if self.fk_hover_target == target:
            return
        self.fk_hover_target = target
        ref_table, ref_column = self.foreign_keys[column_name]
        cache_key = (ref_table, ref_column, str(value))
        record = self.fk_cache.get(cache_key)
        if record is None:
            try:
                cfg = self._get_db_config()
                record = fetch_record_by_column(ref_table, ref_column, value, **cfg)
                self.fk_cache[cache_key] = record or {}
            except Exception as exc:
                self._set_status(str(exc), is_error=True)
                self._hide_fk_tooltip()
                return
        if not record:
            self._hide_fk_tooltip()
            return
        self._show_fk_tooltip(event, ref_table, record)

    def _show_fk_tooltip(self, event: tk.Event, table: str, record: dict) -> None:
        self._hide_fk_tooltip()
        tip = tk.Toplevel(self.root)
        tip.wm_overrideredirect(True)
        tip.configure(background="#f7f7f7")
        tip.attributes("-topmost", True)
        x = self.root.winfo_pointerx() + 12
        y = self.root.winfo_pointery() + 12
        tip.wm_geometry(f"+{x}+{y}")
        content = "\n".join(f"{k}: {v}" for k, v in record.items())
        label = tk.Label(
            tip,
            text=f"{table} 记录\n{content}",
            justify="left",
            background="#f7f7f7",
            foreground="#111",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6,
        )
        label.pack()
        self.fk_tooltip = tip

    def _hide_fk_tooltip(self) -> None:
        if self.fk_tooltip and self.fk_tooltip.winfo_exists():
            self.fk_tooltip.destroy()
        self.fk_tooltip = None
        self.fk_hover_target = None

    def _clear_form_fields(self) -> None:
        for var in (
                self.emp_id_var,
                self.emp_name_var,
                self.emp_dept_var,
                self.emp_pos_var,
                self.emp_salary_var,
                self.emp_join_var,
        ):
            var.set("")
        for var in self.field_vars.values():
            var.set("")

    def _open_info_dialog(self, title: str, columns: list[tuple[str, str]], rows: list[dict]) -> None:
        win = tk.Toplevel(self.root)
        win.title(title)
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill="both", expand=True)

        col_ids = [col_id for col_id, _ in columns]
        tree = ttk.Treeview(frame, columns=col_ids, show="headings", height=12)
        for col_id, heading in columns:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=150, anchor="w")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        for row in rows:
            tree.insert("", "end", values=[row.get(col_id, "") for col_id in col_ids])

        ttk.Button(frame, text="关闭", command=win.destroy).grid(row=2, column=0, sticky="e", pady=8)

    def _get_active_records(self) -> list[dict]:
        return self.db_records if self.table_mode == "db" else self.employees

    def _set_status(self, text: str, *, is_error: bool = False) -> None:
        self.status_var.set(text)
        if hasattr(self, "status_label"):
            color = "red" if is_error else ""
            self.status_label.configure(foreground=color)


def main() -> None:
    root = tk.Tk()
    DataManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
