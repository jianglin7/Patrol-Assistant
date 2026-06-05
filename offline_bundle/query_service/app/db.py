from contextlib import contextmanager
from typing import Iterator

import pymysql
from pymysql.cursors import DictCursor

from app.config import settings


def _connect():
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset=settings.mysql_charset,
        cursorclass=DictCursor,
        autocommit=True,
    )


@contextmanager
def get_connection() -> Iterator[pymysql.connections.Connection]:
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()
