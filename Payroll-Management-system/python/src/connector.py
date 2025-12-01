import pymysql
from contextlib import contextmanager


# 连接MySQL数据库的上下文管理器
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
