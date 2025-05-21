import mysql.connector # type: ignore

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        port=3307,
        user='root',    
        password='admin123*',
        database='gestordocu',
    )