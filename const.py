# 役割：定数を格納する

tools = [
    {
        "type": "function",
        "name": "file_search",
        "description": "ファイルの格納先を検索します",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "検索したいファイルに関連のあるキーワード",
                },
                "file_path": {
                    "type": "string",
                    "description": "検索したいファイルパス",
                },
            },
            "required": ["keyword", "file_path"],
        },
    },
    {
        "type": "function",
        "name": "extract_text_from_docx",
        "description": "Wordファイルの中身を取得します",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "中身をみたいファイルのファイルパス",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "type": "function",
        "name": "extract_text_from_excel",
        "description": "Excelファイルの中身を取得します",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "中身をみたいファイルのファイルパス",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "type": "function",
        "name": "extract_text_from_pdf",
        "description": "PDFファイルの中身を取得します",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "中身をみたいファイルのファイルパス",
                },
            },
            "required": ["file_path"],
        },
    },
]


INSERT_QUERY = """
INSERT INTO chat_messages(
conversation_id,
role,
content,
token_count,
model,
input_tokens,
output_tokens,
total_tokens
)
VALUES(?,?,?,?,?,?,?,?)
"""
