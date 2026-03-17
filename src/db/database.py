import pyodbc
from core.config import CONN_STR

def get_db_connection():
    return pyodbc.connect(CONN_STR)