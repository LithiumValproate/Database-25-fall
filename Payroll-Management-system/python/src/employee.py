import csv
import pymysql
import random
import string
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Sequence


def ask_use_defaults() -> bool:
    choice = input('Use default names and jobs files? (Y/n): ').strip().lower()
    return choice not in {'n', 'not'}


def get_file_path(default_path: Path, label: str) -> Path:
    path_str = input(f'Path to {label} file (default {default_path.name}): ').strip()
    path = Path(path_str) if path_str else default_path
    if not path.is_file():
        raise FileNotFoundError(f'File not found: {path}')
    return path


def ask_insert_db() -> bool:
    choice = input('Insert generated records into MySQL? (y/N): ').strip().lower()
    return choice in {'y', 'yes'}


def get_db_config() -> dict:
    host = input('MySQL host (default localhost): ').strip() or 'localhost'
    port_str = input('MySQL port (default 3306): ').strip() or '3306'
    user = input('MySQL user: ').strip()
    password = input('MySQL password: ').strip()
    database = input('MySQL database name: ').strip()

    if not user or not password or not database:
        raise ValueError('MySQL user, password, and database are required.')

    try:
        port = int(port_str)
    except ValueError:
        raise ValueError('MySQL port must be an integer.')

    return {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'database': database,
    }


def get_row_count(default: int = 64) -> int:
    rows = input(f'Amount of rows to read (default {default}): ').strip()
    return int(rows) if rows else default


def gen_random_indices(count: int, *, max_index: int) -> list[int]:
    if count > max_index:
        raise ValueError(f'Requested {count} rows but file has only {max_index} lines.')
    return random.sample(range(1, max_index + 1), count)


def read_lines(path: Path) -> list[str]:
    # Strip trailing newlines but preserve original order.
    with path.open(encoding='utf-8') as f:
        return [line.rstrip('\n') for line in f]


def read_jobs(path: Path) -> list[tuple[str, str]]:
    with path.open(encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        rows = [tuple(row) for row in reader if row]

    if rows and rows[0] and rows[0][0].lower() == 'dept':
        rows = rows[1:]

    jobs = [row for row in rows if len(row) >= 2]
    if not jobs:
        raise ValueError('jobs.csv is empty or invalid.')
    return jobs


def gen_unique_ids(count: int, length: int = 8) -> list[str]:
    alphabet = string.digits
    ids: set[str] = set()
    while len(ids) < count:
        ids.add(''.join(random.choices(alphabet, k=length)))
    return list(ids)


def gen_random_date(start: date, end: date) -> date:
    if end < start:
        raise ValueError('End date must not be before start date.')
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, delta_days))


def gen_employee_records(names: list[str], jobs: list[tuple[str, str]]) -> list[dict]:
    join_start = date(2012, 1, 1)
    today = date.today()
    ids = gen_unique_ids(len(names))
    salaries = [float(f'{random.randrange(3000, 100001, 100):.2f}') for _ in names]

    records = []
    for i, name in enumerate(names):
        dept, position = random.choice(jobs)
        records.append(
            {
                'id': ids[i],
                'name': name,
                'dept': dept,
                'position': position,
                'salary': salaries[i],
                'join_date': gen_random_date(join_start, today).isoformat(),
            }
        )
    return records


@contextmanager
def mysql_connection(*, host: str, port: int, user: str, password: str, database: str):
    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4',
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        yield connection
    finally:
        connection.close()


def insert_into_mysql(
    records: Iterable[dict], *, host: str, port: int, user: str, password: str, database: str
) -> None:
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            sql = (
                'INSERT INTO Employee (EmployeeId, EmployeeName, Department, Position, BasicSalary, JoinDate) '
                'VALUES (%s, %s, %s, %s, %s, %s)'
            )
            payload = [
                (
                    r['id'],
                    r['name'],
                    r['dept'],
                    r['position'],
                    r['salary'],
                    r['join_date'],
                )
                for r in records
            ]
            cursor.executemany(sql, payload)
        connection.commit()


def fetch_employees(*, host: str, port: int, user: str, password: str, database: str) -> list[dict]:
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT EmployeeId AS id, EmployeeName AS name, Department AS dept, '
                'Position AS position, BasicSalary AS salary, JoinDate AS join_date '
                'FROM Employee ORDER BY EmployeeId'
            )
            rows = cursor.fetchall()
    return [dict(row) for row in rows]


def add_employee(
    record: dict, *, host: str, port: int, user: str, password: str, database: str
) -> None:
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'INSERT INTO Employee (EmployeeId, EmployeeName, Department, Position, BasicSalary, JoinDate) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                (
                    record['id'],
                    record['name'],
                    record['dept'],
                    record['position'],
                    record['salary'],
                    record['join_date'],
                ),
            )
        connection.commit()


def update_employee(
    record: dict, *, host: str, port: int, user: str, password: str, database: str
) -> None:
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'UPDATE Employee SET EmployeeName=%s, Department=%s, Position=%s, BasicSalary=%s, JoinDate=%s '
                'WHERE EmployeeId=%s',
                (
                    record['name'],
                    record['dept'],
                    record['position'],
                    record['salary'],
                    record['join_date'],
                    record['id'],
                ),
            )
        connection.commit()


def delete_employee(employee_id: str, *, host: str, port: int, user: str, password: str, database: str) -> None:
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM Employee WHERE EmployeeId=%s', (employee_id,))
        connection.commit()


def import_employees_from_csv(
    path: Path, *, host: str, port: int, user: str, password: str, database: str
) -> int:
    with path.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        required = {'id', 'name', 'dept', 'position', 'salary', 'join_date'}
        missing_cols = required - {col.strip() for col in reader.fieldnames or []}
        if missing_cols:
            raise ValueError(f'Missing required columns: {", ".join(sorted(missing_cols))}')
        rows = [
            {
                'id': row['id'].strip(),
                'name': row['name'].strip(),
                'dept': row['dept'].strip(),
                'position': row['position'].strip(),
                'salary': float(row['salary']),
                'join_date': datetime.fromisoformat(row['join_date']).date().isoformat(),
            }
            for row in reader
            if any(row.values())
        ]

    if not rows:
        return 0

    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                'INSERT INTO Employee (EmployeeId, EmployeeName, Department, Position, BasicSalary, JoinDate) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                [
                    (r['id'], r['name'], r['dept'], r['position'], r['salary'], r['join_date'])
                    for r in rows
                ],
            )
        connection.commit()
    return len(rows)


def export_employees_to_csv(records: Sequence[dict], path: Path) -> None:
    fieldnames = ('id', 'name', 'dept', 'position', 'salary', 'join_date')
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def main():
    default_names_path = Path(__file__).with_name('static') / 'names.txt'
    default_jobs_path = Path(__file__).with_name('static') / 'jobs.csv'

    use_defaults = ask_use_defaults()
    names_path = default_names_path if use_defaults else get_file_path(default_names_path, 'names')
    jobs_path = default_jobs_path if use_defaults else get_file_path(default_jobs_path, 'jobs')

    jobs = read_jobs(jobs_path)
    lines = read_lines(names_path)
    count = get_row_count()
    random_indices = gen_random_indices(count, max_index=len(lines))
    selected_lines = [lines[i - 1] for i in random_indices]

    employees = gen_employee_records(selected_lines, jobs)

    print('Employee records:', employees)

    if employees and ask_insert_db():
        cfg = get_db_config()
        insert_into_mysql(employees, **cfg)
        print('Inserted records into MySQL successfully.')


if __name__ == "__main__":
    main()
