from contextlib import contextmanager
from typing import Any, Iterable

import pymysql


@contextmanager
def mysql_connection(*, host: str, port: int, user: str, password: str, database: str):
    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        yield connection
    finally:
        connection.close()


def list_tables(*, host: str, port: int, user: str, password: str, database: str) -> list[str]:
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            key = f"Tables_in_{database}"
            return [row[key] for row in cursor.fetchall() if key in row]


def fetch_table_schema(table: str, *, host: str, port: int, user: str, password: str, database: str) -> list[dict]:
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW FULL COLUMNS FROM `{table}`")
            return cursor.fetchall()


def fetch_table_rows(table: str, *, host: str, port: int, user: str, password: str, database: str) -> list[dict]:
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM `{table}`")
            return cursor.fetchall()


def fetch_unsettled_totals(
        employee_id: str,
        payroll_date: str,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
) -> tuple[float, float]:
    """Sum unsettled bonus/deduction amounts before a given payroll date for an employee."""

    bonus_sql = (
        "SELECT COALESCE(SUM(BonusAmount), 0) AS total "
        "FROM `Bonus_Record` WHERE EmployeeId=%s AND IsSettled=0 AND BonusDate<=%s"
    )
    deduction_sql = (
        "SELECT COALESCE(SUM(DeductionAmount), 0) AS total "
        "FROM `Deduction_Record` WHERE EmployeeId=%s AND IsSettled=0 AND DeductionDate<=%s"
    )
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(bonus_sql, (employee_id, payroll_date))
            bonus_row = cursor.fetchone() or {"total":0}
            cursor.execute(deduction_sql, (employee_id, payroll_date))
            deduction_row = cursor.fetchone() or {"total":0}
    return float(bonus_row.get("total", 0)), float(deduction_row.get("total", 0))


def fetch_record_by_column(
        table: str,
        column: str,
        value: Any,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
) -> dict | None:
    """Fetch a single record by matching a specific column value."""

    sql = f"SELECT * FROM `{table}` WHERE `{column}`=%s LIMIT 1"
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, (value,))
            return cursor.fetchone()


def insert_row(table: str, data: dict[str, Any], *, host: str, port: int, user: str, password: str,
               database: str) -> None:
    columns = ", ".join(f"`{col}`" for col in data)
    placeholders = ", ".join(["%s"] * len(data))
    values = list(data.values())
    sql = f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders})"
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
        connection.commit()


def update_row(
        table: str,
        data: dict[str, Any],
        key_column: str,
        key_value: Any,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
) -> None:
    setters = ", ".join(f"`{col}`=%s" for col in data)
    values = list(data.values()) + [key_value]
    sql = f"UPDATE `{table}` SET {setters} WHERE `{key_column}`=%s"
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
        connection.commit()


def delete_row(
        table: str,
        key_column: str,
        key_value: Any,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
) -> None:
    sql = f"DELETE FROM `{table}` WHERE `{key_column}`=%s"
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, (key_value,))
        connection.commit()


def normalize_records(rows: Iterable[dict]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized.append({k:row[k] for k in row})
    return normalized


def fetch_table_constraints(
        table: str, *, host: str, port: int, user: str, password: str, database: str
) -> list[dict[str, Any]]:
    """
    获取指定表的约束信息，包括主键、唯一键、外键与检查约束。
    """
    sql = """
          select Tc.Constraint_Name as Constraint_Name, Tc.Constraint_Type as Constraint_Type,
                 Kcu.Column_Name as Column_Name, Kcu.Referenced_Table_Name as Referenced_Table,
                 Kcu.Referenced_Column_Name as Referenced_Column, Cc.Check_Clause as Check_Clause
          from Information_Schema.Table_Constraints Tc
                   left join Information_Schema.Key_Column_Usage Kcu on Tc.Constraint_Schema = Kcu.Constraint_Schema and
                                                                        Tc.Constraint_Name = Kcu.Constraint_Name and
                                                                        Tc.Table_Name = Kcu.Table_Name
                   left join Information_Schema.Check_Constraints Cc
                             on Tc.Constraint_Schema = Cc.Constraint_Schema and Tc.Constraint_Name = Cc.Constraint_Name
          where Tc.Table_Schema = %s and Tc.Table_Name = %s
          order by Tc.Constraint_Type, Tc.Constraint_Name, Kcu.Ordinal_Position; \
          """
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, (database, table))
            return cursor.fetchall()
