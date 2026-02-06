import pyodbc
import struct
from azure.identity import DefaultAzureCredential
from const import INSERT_QUERY


def insert_conversation(
    conversation_id,
    role,
    content,
    token_count,
    model,
    input_tokens,
    output_tokens,
    total_tokens,
):
    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=unirita-study.database.windows.net;"
        "DATABASE=unirita;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "LoginTimeout=60;"
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

    try:
        with pyodbc.connect(
            connection_string,
            attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct},
            timeout=5
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    INSERT_QUERY,
                    (
                        conversation_id,
                        role,
                        content,
                        token_count,
                        model,
                        input_tokens,
                        output_tokens,
                        total_tokens
                    )
                )
                conn.commit()
        return True

    except Exception as e:
        raise RuntimeError(f"DB登録失敗: {e}") from e








