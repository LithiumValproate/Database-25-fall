import csv
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from employee import (  # type: ignore
    gen_employee_records,
    gen_random_indices,
    add_employee,
    delete_employee,
    export_employees_to_csv,
    fetch_employees,
    import_employees_from_csv,
    insert_into_mysql,
    read_jobs,
    read_lines,
    update_employee,
)


class EmployeeGeneratorGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Employee Generator")
        self.root.geometry("900x600")

        self.base_dir = BASE_DIR
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
        self.employees: list[dict] = []
        self.db_records: list[dict] = []
        self.table_mode: str = "generator"
        self.status_var = tk.StringVar(value="Ready.")

        self.emp_id_var = tk.StringVar()
        self.emp_name_var = tk.StringVar()
        self.emp_dept_var = tk.StringVar()
        self.emp_pos_var = tk.StringVar()
        self.emp_salary_var = tk.StringVar()
        self.emp_join_var = tk.StringVar()

        self._build_form()
        self._build_db_controls()
        self._build_table()
        self._build_status_bar()

    def _build_form(self) -> None:
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill="x")

        # Names file
        ttk.Label(frm, text="Names file").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.names_path, width=60).grid(row=0, column=1, sticky="we", padx=5)
        ttk.Button(frm, text="Browse", command=self._choose_names).grid(row=0, column=2, padx=5)

        # Jobs file
        ttk.Label(frm, text="Jobs file").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.jobs_path, width=60).grid(row=1, column=1, sticky="we", padx=5)
        ttk.Button(frm, text="Browse", command=self._choose_jobs).grid(row=1, column=2, padx=5)

        # Count
        ttk.Label(frm, text="Count").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.count_var, width=10).grid(row=2, column=1, sticky="w", padx=5)

        # Insert checkbox
        ttk.Checkbutton(frm, text="Insert into MySQL", variable=self.insert_var, command=self._toggle_db_fields).grid(
            row=3, column=0, sticky="w"
        )

        # DB fields
        ttk.Label(frm, text="Host").grid(row=4, column=0, sticky="w")
        host_entry = ttk.Entry(frm, textvariable=self.host_var, width=20)
        host_entry.grid(row=4, column=1, sticky="w", padx=5)

        ttk.Label(frm, text="Port").grid(row=4, column=2, sticky="e")
        port_entry = ttk.Entry(frm, textvariable=self.port_var, width=8)
        port_entry.grid(row=4, column=3, sticky="w")

        ttk.Label(frm, text="User").grid(row=5, column=0, sticky="w")
        user_entry = ttk.Entry(frm, textvariable=self.user_var, width=20)
        user_entry.grid(row=5, column=1, sticky="w", padx=5)

        ttk.Label(frm, text="Password").grid(row=5, column=2, sticky="e")
        pass_entry = ttk.Entry(frm, textvariable=self.pass_var, width=20, show="*")
        pass_entry.grid(row=5, column=3, sticky="w")

        ttk.Label(frm, text="Database").grid(row=6, column=0, sticky="w")
        db_entry = ttk.Entry(frm, textvariable=self.db_var, width=20)
        db_entry.grid(row=6, column=1, sticky="w", padx=5)

        self.db_entries = [host_entry, port_entry, user_entry, pass_entry, db_entry]

        ttk.Button(frm, text="Generate", command=self._on_generate).grid(row=7, column=0, pady=10, sticky="w")
        self.save_btn = ttk.Button(frm, text="Save CSV", command=self._save_csv)
        self.save_btn.state(["disabled"])
        self.save_btn.grid(row=7, column=1, pady=10, sticky="w", padx=5)

    def _build_db_controls(self) -> None:
        frm = ttk.LabelFrame(self.root, text="数据库管理", padding=10)
        frm.pack(fill="x", padx=10)

        ttk.Label(frm, text="使用上方的数据库配置进行 CRUD 操作和导入导出").grid(row=0, column=0, columnspan=8, sticky="w")

        ttk.Label(frm, text="Employee ID").grid(row=1, column=0, sticky="w", pady=(8, 2))
        ttk.Entry(frm, textvariable=self.emp_id_var, width=12).grid(row=1, column=1, sticky="w", padx=5, pady=(8, 2))

        ttk.Label(frm, text="Name").grid(row=1, column=2, sticky="e", pady=(8, 2))
        ttk.Entry(frm, textvariable=self.emp_name_var, width=18).grid(row=1, column=3, sticky="w", padx=5, pady=(8, 2))

        ttk.Label(frm, text="Department").grid(row=1, column=4, sticky="e", pady=(8, 2))
        ttk.Entry(frm, textvariable=self.emp_dept_var, width=18).grid(row=1, column=5, sticky="w", padx=5, pady=(8, 2))

        ttk.Label(frm, text="Position").grid(row=1, column=6, sticky="e", pady=(8, 2))
        ttk.Entry(frm, textvariable=self.emp_pos_var, width=18).grid(row=1, column=7, sticky="w", padx=5, pady=(8, 2))

        ttk.Label(frm, text="Salary").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.emp_salary_var, width=12).grid(row=2, column=1, sticky="w", padx=5)

        ttk.Label(frm, text="Join Date (YYYY-MM-DD)").grid(row=2, column=2, sticky="e")
        ttk.Entry(frm, textvariable=self.emp_join_var, width=18).grid(row=2, column=3, sticky="w", padx=5)

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=8, sticky="w", pady=8)

        ttk.Button(btns, text="加载数据库", command=self._load_from_db).grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="新增", command=self._create_employee).grid(row=0, column=1, padx=5)
        ttk.Button(btns, text="更新", command=self._update_employee).grid(row=0, column=2, padx=5)
        ttk.Button(btns, text="删除", command=self._delete_employee).grid(row=0, column=3, padx=5)
        ttk.Button(btns, text="导入CSV", command=self._import_csv_to_db).grid(row=0, column=4, padx=5)
        ttk.Button(btns, text="导出CSV", command=self._export_csv_from_db).grid(row=0, column=5, padx=5)

    def _build_table(self) -> None:
        columns = ("id", "name", "dept", "position", "salary", "join_date")
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(container, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130 if col != "name" else 150, anchor="center")
        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

    def _build_status_bar(self) -> None:
        self.status_label = ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=5)
        self.status_label.pack(fill="x", side="bottom")

    def _toggle_db_fields(self) -> None:
        # Keep database字段处于可编辑状态，方便 CRUD 和导入导出操作。
        for entry in self.db_entries:
            entry.configure(state="normal")

    def _choose_jobs(self) -> None:
        path = filedialog.askopenfilename(
            title="Select jobs file", initialdir=self.base_dir, filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.jobs_path.set(path)
            self._set_status(f"Selected jobs file: {Path(path).name}")

    def _choose_names(self) -> None:
        path = filedialog.askopenfilename(
            title="Select names file", initialdir=self.base_dir, filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.names_path.set(path)
            self._set_status(f"Selected names file: {Path(path).name}")

    def _on_generate(self) -> None:
        try:
            names, jobs, count = self._validate_inputs()

            random_indices = gen_random_indices(count, max_index=len(names))
            selected_names = [names[i - 1] for i in random_indices]
            employees = gen_employee_records(selected_names, jobs)

            self.employees = employees
            self.table_mode = "generator"
            self.save_btn.state(["!disabled"])
            self._render_table(employees)
            self._set_status(f"Generated {len(employees)} employees.")

            if self.insert_var.get():
                cfg = self._get_db_config()
                insert_into_mysql(employees, **cfg)
                messagebox.showinfo("Success", "Inserted into MySQL successfully.")
                self._set_status(f"Inserted {len(employees)} records into MySQL.")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("Error", str(exc))

    def _render_table(self, employees: List[dict]) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        for emp in employees:
            self.tree.insert(
                "", "end", values=(emp["id"], emp["name"], emp["dept"], emp["position"], emp["salary"], emp["join_date"])
            )
        if employees:
            self.save_btn.state(["!disabled"])
        else:
            self.save_btn.state(["disabled"])

    def _validate_inputs(self) -> tuple[list[str], list[tuple[str, str]], int]:
        names_path = Path(self.names_path.get()).expanduser()
        jobs_path = Path(self.jobs_path.get()).expanduser()
        if not names_path.is_file():
            raise FileNotFoundError(f"Names file not found: {names_path}")
        if not jobs_path.is_file():
            raise FileNotFoundError(f"Jobs file not found: {jobs_path}")

        try:
            count = int(self.count_var.get())
        except ValueError as exc:
            raise ValueError("Count must be a positive integer.") from exc
        if count <= 0:
            raise ValueError("Count must be greater than zero.")

        names = read_lines(names_path)
        jobs = read_jobs(jobs_path)
        if not names:
            raise ValueError("Names file is empty.")
        if not jobs:
            raise ValueError("Jobs file is empty.")
        return names, jobs, count

    def _save_csv(self) -> None:
        records = self._get_active_records()
        if not records:
            messagebox.showinfo("No data", "Generate or加载数据后再保存。")
            return

        path = filedialog.asksaveasfilename(
            title="Save employees as CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=self.base_dir,
        )
        if not path:
            return
        export_employees_to_csv(records, Path(path))
        messagebox.showinfo("Saved", f"Saved {len(records)} records to {path}.")
        self._set_status(f"Saved {len(records)} records to CSV.")

    def _get_db_config(self) -> dict:
        cfg = {
            "host": self.host_var.get() or "localhost",
            "port": int(self.port_var.get() or 3306),
            "user": self.user_var.get(),
            "password": self.pass_var.get(),
            "database": self.db_var.get(),
        }
        missing = [k for k, v in cfg.items() if k not in {"port", "host"} and not v]
        if missing:
            raise ValueError(f"Missing database fields: {', '.join(missing)}")
        return cfg

    def _collect_form_data(self) -> dict:
        emp_id = self.emp_id_var.get().strip()
        name = self.emp_name_var.get().strip()
        dept = self.emp_dept_var.get().strip()
        position = self.emp_pos_var.get().strip()
        salary_raw = self.emp_salary_var.get().strip()
        join_date_raw = self.emp_join_var.get().strip()

        if not all([emp_id, name, dept, position, salary_raw, join_date_raw]):
            raise ValueError("所有字段均为必填项。")
        try:
            salary = float(salary_raw)
        except ValueError as exc:
            raise ValueError("Salary 必须为数字。") from exc
        try:
            join_date = datetime.strptime(join_date_raw, "%Y-%m-%d").date().isoformat()
        except ValueError as exc:
            raise ValueError("Join Date 格式应为 YYYY-MM-DD。") from exc

        return {
            "id": emp_id,
            "name": name,
            "dept": dept,
            "position": position,
            "salary": salary,
            "join_date": join_date,
        }

    def _load_from_db(self) -> None:
        try:
            cfg = self._get_db_config()
            self.db_records = fetch_employees(**cfg)
            self.table_mode = "db"
            self._render_table(self.db_records)
            self._set_status(f"Loaded {len(self.db_records)} employees from database.")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("DB Error", str(exc))

    def _create_employee(self) -> None:
        try:
            record = self._collect_form_data()
            cfg = self._get_db_config()
            add_employee(record, **cfg)
            self._clear_form_fields()
            self._load_from_db()
            messagebox.showinfo("Success", "新增员工成功。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("DB Error", str(exc))

    def _update_employee(self) -> None:
        try:
            record = self._collect_form_data()
            cfg = self._get_db_config()
            update_employee(record, **cfg)
            self._load_from_db()
            messagebox.showinfo("Success", "更新员工成功。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("DB Error", str(exc))

    def _delete_employee(self) -> None:
        emp_id = self.emp_id_var.get().strip()
        if not emp_id:
            messagebox.showinfo("提示", "请选择要删除的员工。")
            return
        if not messagebox.askyesno("确认", f"确定删除员工 {emp_id} ?"):
            return
        try:
            cfg = self._get_db_config()
            delete_employee(emp_id, **cfg)
            self._clear_form_fields()
            self._load_from_db()
            messagebox.showinfo("Success", "删除员工成功。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("DB Error", str(exc))

    def _import_csv_to_db(self) -> None:
        path = filedialog.askopenfilename(
            title="选择要导入的 CSV",
            initialdir=self.base_dir,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            cfg = self._get_db_config()
            imported = import_employees_from_csv(Path(path), **cfg)
            self._load_from_db()
            messagebox.showinfo("Success", f"成功导入 {imported} 条记录。")
        except Exception as exc:
            self._set_status(str(exc), is_error=True)
            messagebox.showerror("导入失败", str(exc))

    def _export_csv_from_db(self) -> None:
        if not self.db_records:
            self._load_from_db()
        if not self.db_records:
            messagebox.showinfo("提示", "数据库中暂无可导出的记录。")
            return
        path = filedialog.asksaveasfilename(
            title="导出数据库员工", defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        export_employees_to_csv(self.db_records, Path(path))
        messagebox.showinfo("Saved", f"已导出 {len(self.db_records)} 条记录到 {path}。")
        self._set_status(f"导出 {len(self.db_records)} 条记录。")

    def _on_tree_select(self, event: tk.Event) -> None:
        if self.table_mode != "db":
            return
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        if not values:
            return
        self.emp_id_var.set(values[0])
        self.emp_name_var.set(values[1])
        self.emp_dept_var.set(values[2])
        self.emp_pos_var.set(values[3])
        self.emp_salary_var.set(values[4])
        self.emp_join_var.set(values[5])

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

    def _get_active_records(self) -> list[dict]:
        return self.db_records if self.table_mode == "db" else self.employees

    def _set_status(self, text: str, *, is_error: bool = False) -> None:
        self.status_var.set(text)
        if hasattr(self, "status_label"):
            color = "red" if is_error else ""
            self.status_label.configure(foreground=color)


def main() -> None:
    root = tk.Tk()
    EmployeeGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
