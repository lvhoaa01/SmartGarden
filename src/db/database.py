import pyodbc
from core.config import config


def get_db_connection() -> pyodbc.Connection:
    return pyodbc.connect(config.db.connection_string)
