import csv
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from employee import (  # type: ignore
    gen_employee_records,
    gen_random_indices,
    insert_into_mysql,
    read_jobs,
    read_lines,
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
        self.status_var = tk.StringVar(value="Ready.")

        self._build_form()
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
        host_entry = ttk.Entry(frm, textvariable=self.host_var, width=20, state="disabled")
        host_entry.grid(row=4, column=1, sticky="w", padx=5)

        ttk.Label(frm, text="Port").grid(row=4, column=2, sticky="e")
        port_entry = ttk.Entry(frm, textvariable=self.port_var, width=8, state="disabled")
        port_entry.grid(row=4, column=3, sticky="w")

        ttk.Label(frm, text="User").grid(row=5, column=0, sticky="w")
        user_entry = ttk.Entry(frm, textvariable=self.user_var, width=20, state="disabled")
        user_entry.grid(row=5, column=1, sticky="w", padx=5)

        ttk.Label(frm, text="Password").grid(row=5, column=2, sticky="e")
        pass_entry = ttk.Entry(frm, textvariable=self.pass_var, width=20, show="*", state="disabled")
        pass_entry.grid(row=5, column=3, sticky="w")

        ttk.Label(frm, text="Database").grid(row=6, column=0, sticky="w")
        db_entry = ttk.Entry(frm, textvariable=self.db_var, width=20, state="disabled")
        db_entry.grid(row=6, column=1, sticky="w", padx=5)

        self.db_entries = [host_entry, port_entry, user_entry, pass_entry, db_entry]

        ttk.Button(frm, text="Generate", command=self._on_generate).grid(row=7, column=0, pady=10, sticky="w")
        self.save_btn = ttk.Button(frm, text="Save CSV", command=self._save_csv)
        self.save_btn.state(["disabled"])
        self.save_btn.grid(row=7, column=1, pady=10, sticky="w", padx=5)

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

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

    def _build_status_bar(self) -> None:
        self.status_label = ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=5)
        self.status_label.pack(fill="x", side="bottom")

    def _toggle_db_fields(self) -> None:
        state = "normal" if self.insert_var.get() else "disabled"
        for entry in self.db_entries:
            entry.configure(state=state)

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
            self.save_btn.state(["!disabled"])
            self._render_table(employees)
            self._set_status(f"Generated {len(employees)} employees.")

            if self.insert_var.get():
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
        if not self.employees:
            messagebox.showinfo("No data", "Generate employees before saving.")
            return

        path = filedialog.asksaveasfilename(
            title="Save employees as CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=self.base_dir,
        )
        if not path:
            return
        fieldnames = ("id", "name", "dept", "position", "salary", "join_date")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.employees)
        messagebox.showinfo("Saved", f"Saved {len(self.employees)} records to {path}.")
        self._set_status(f"Saved {len(self.employees)} records to CSV.")

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
