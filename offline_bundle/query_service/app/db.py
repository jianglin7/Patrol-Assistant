from contextlib import contextmanager
from typing import Iterator

import pymysql
from pymysql.cursors import DictCursor

from app.config import settings


def _connect_business():
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
def get_business_connection() -> Iterator[pymysql.connections.Connection]:
    conn = _connect_business()
    try:
        yield conn
    finally:
        conn.close()


def _connect_control():
    return pymysql.connect(
        host=settings.control_mysql_host or settings.mysql_host,
        port=settings.control_mysql_port or settings.mysql_port,
        user=settings.control_mysql_user or settings.mysql_user,
        password=settings.control_mysql_password or settings.mysql_password,
        database=settings.control_mysql_database or settings.mysql_database,
        charset=settings.control_mysql_charset or settings.mysql_charset,
        cursorclass=DictCursor,
        autocommit=True,
    )


@contextmanager
def get_control_connection() -> Iterator[pymysql.connections.Connection]:
    conn = _connect_control()
    try:
        yield conn
    finally:
        conn.close()


def _connect_schedule():
    return pymysql.connect(
        host=settings.schedule_mysql_host or settings.mysql_host,
        port=settings.schedule_mysql_port or settings.mysql_port,
        user=settings.schedule_mysql_user or settings.mysql_user,
        password=settings.schedule_mysql_password or settings.mysql_password,
        database=settings.schedule_mysql_database or settings.mysql_database,
        charset=settings.schedule_mysql_charset or settings.mysql_charset,
        cursorclass=DictCursor,
        autocommit=True,
    )


@contextmanager
def get_schedule_connection() -> Iterator[pymysql.connections.Connection]:
    conn = _connect_schedule()
    try:
        yield conn
    finally:
        conn.close()


# 向后兼容：旧调用默认走业务库。
def get_connection() -> Iterator[pymysql.connections.Connection]:
    return get_business_connection()
