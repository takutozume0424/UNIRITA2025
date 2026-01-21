import pyodbc
import struct
from azure.identity import DefaultAzureCredential

def test_connection():
    print(pyodbc.drivers())

    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=unirita-study.database.windows.net;"
        "DATABASE=unirita;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )

    credential = DefaultAzureCredential(
        exclude_interactive_browser_credential=False
    )

    token = credential.get_token(
        "https://database.windows.net/.default"
    ).token

    token_bytes = token.encode("utf-16-le")
    token_struct = struct.pack(
        f"<I{len(token_bytes)}s",
        len(token_bytes),
        token_bytes
    )

    SQL_COPT_SS_ACCESS_TOKEN = 1256

    conn = pyodbc.connect(
        connection_string,
        attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct},
        timeout=5
    )

    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    print("接続成功:", cursor.fetchone())

    conn.close()

if __name__ == "__main__":
    test_connection()
