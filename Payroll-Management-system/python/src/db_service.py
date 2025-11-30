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


def fetch_column_attributes(
    table: str, *, host: str, port: int, user: str, password: str, database: str
) -> list[dict]:
    sql = """
        SELECT
            column_name,
            column_type,
            is_nullable,
            column_default,
            column_key,
            extra,
            column_comment
        FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s
        ORDER BY ordinal_position
    """
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, (database, table))
            return cursor.fetchall()


def fetch_table_constraints(
    table: str, *, host: str, port: int, user: str, password: str, database: str
) -> list[dict]:
    constraint_sql = """
        SELECT
            tc.constraint_name,
            tc.constraint_type,
            kcu.column_name,
            kcu.referenced_table_name,
            kcu.referenced_column_name,
            rc.update_rule,
            rc.delete_rule
        FROM information_schema.table_constraints tc
        LEFT JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
            AND tc.table_name = kcu.table_name
        LEFT JOIN information_schema.referential_constraints rc
            ON tc.constraint_name = rc.constraint_name
            AND tc.constraint_schema = rc.constraint_schema
        WHERE tc.table_schema=%s AND tc.table_name=%s
        ORDER BY tc.constraint_name, kcu.ordinal_position
    """
    check_sql = """
        SELECT tc.constraint_name, cc.check_clause
        FROM information_schema.table_constraints tc
        JOIN information_schema.check_constraints cc
            ON tc.constraint_name = cc.constraint_name
            AND tc.constraint_schema = cc.constraint_schema
        WHERE tc.table_schema=%s AND tc.table_name=%s AND tc.constraint_type='CHECK'
    """
    constraints: dict[str, dict[str, Any]] = {}
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(constraint_sql, (database, table))
            for row in cursor.fetchall():
                name = row.get("constraint_name") or ""
                if name not in constraints:
                    constraints[name] = {
                        "constraint_name": name,
                        "constraint_type": row.get("constraint_type"),
                        "columns": [],
                        "details": None,
                    }
                if row.get("column_name"):
                    constraints[name]["columns"].append(row["column_name"])
                if row.get("constraint_type") == "FOREIGN KEY":
                    target = f"{row.get('referenced_table_name')}({row.get('referenced_column_name')})"
                    rules = []
                    if row.get("update_rule"):
                        rules.append(f"ON UPDATE {row['update_rule']}")
                    if row.get("delete_rule"):
                        rules.append(f"ON DELETE {row['delete_rule']}")
                    details = ", ".join(rules)
                    if target or details:
                        constraint_details = target if target else ""
                        if details:
                            constraint_details = f"{constraint_details} {details}".strip()
                        constraints[name]["details"] = constraint_details

            cursor.execute(check_sql, (database, table))
            for row in cursor.fetchall():
                name = row.get("constraint_name") or ""
                if name not in constraints:
                    constraints[name] = {
                        "constraint_name": name,
                        "constraint_type": "CHECK",
                        "columns": [],
                        "details": None,
                    }
                if row.get("check_clause"):
                    constraints[name]["details"] = row["check_clause"]

    return list(constraints.values())


def fetch_table_rows(table: str, *, host: str, port: int, user: str, password: str, database: str) -> list[dict]:
    with mysql_connection(host=host, port=port, user=user, password=password, database=database) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM `{table}`")
            return cursor.fetchall()


def insert_row(table: str, data: dict[str, Any], *, host: str, port: int, user: str, password: str, database: str) -> None:
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
        normalized.append({k: row[k] for k in row})
    return normalized
