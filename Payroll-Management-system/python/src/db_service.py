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
