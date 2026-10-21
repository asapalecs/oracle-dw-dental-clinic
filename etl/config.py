"""Configurarea conexiunilor Oracle, citita din variabile de mediu (.env)."""

from __future__ import annotations

import os
from contextlib import contextmanager

import oracledb
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

DB_HOST = os.getenv("ORACLE_HOST", "localhost")
DB_PORT = int(os.getenv("ORACLE_PORT", "1521"))
DB_SERVICE = os.getenv("ORACLE_SERVICE", "FREEPDB1")

SYS_USER = os.getenv("ORACLE_SYS_USER", "sys")
SYS_PASSWORD = os.getenv("ORACLE_SYS_PASSWORD", "Oracle123")

OLTP_USER = os.getenv("ORACLE_OLTP_USER", "stoma_oltp")
OLTP_PASSWORD = os.getenv("ORACLE_OLTP_PASSWORD", "stoma123")

DW_USER = os.getenv("ORACLE_DW_USER", "stoma_dw")
DW_PASSWORD = os.getenv("ORACLE_DW_PASSWORD", "dw123")


def dsn() -> str:
    return f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"


def connect_oltp() -> oracledb.Connection:
    return oracledb.connect(user=OLTP_USER, password=OLTP_PASSWORD, dsn=dsn())


def connect_dw() -> oracledb.Connection:
    return oracledb.connect(user=DW_USER, password=DW_PASSWORD, dsn=dsn())


def connect_sys() -> oracledb.Connection:
    return oracledb.connect(
        user=SYS_USER,
        password=SYS_PASSWORD,
        dsn=dsn(),
        mode=oracledb.AUTH_MODE_SYSDBA,
    )


@contextmanager
def oltp_connection():
    conn = connect_oltp()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def dw_connection():
    conn = connect_dw()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def sys_connection():
    conn = connect_sys()
    try:
        yield conn
    finally:
        conn.close()


def describe() -> str:
    """Rezumatul configuratiei active, fara parole."""
    return (
        f"Oracle        : {dsn()}\n"
        f"Schema OLTP   : {OLTP_USER}\n"
        f"Schema DW     : {DW_USER}\n"
        f"User SYSDBA   : {SYS_USER}"
    )


if __name__ == "__main__":
    print(describe())
