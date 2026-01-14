import win32com.client
from docx import Document
import os
import pythoncom


def file_search(search_root, keyword):
    """
    Windows Search APIを使用してファイルを検索する
    :param search_root: 検索対象のフォルダパス (例: C:\\Documents)
    :param keyword: 検索したいキーワード (中身も検索対象)
    :return: 検索結果のリスト
    """

    # COMライブラリの初期化
    pythoncom.CoInitialize()

    # 1. 接続の準備
    conn = win32com.client.Dispatch("ADODB.Connection")
    rs = win32com.client.Dispatch("ADODB.Recordset")

    # Windows Search プロバイダー
    conn_str = "Provider=Search.CollatorDSO;Extended Properties='Application=Windows';"

    # 2. SQLクエリの作成
    # SCOPE: 指定したフォルダ以下を対象にする
    # System.ItemPathDisplay: フルパス
    # System.ItemName: ファイル名
    # System.Search.Contents: ファイルの中身（Word/PDF/Excel等）

    # パスの区切り文字を正規化（Windows形式）
    normalized_path = os.path.normpath(search_root)

    # CONTAINS(System.Search.Contents, '"{keyword}"') で中身を検索
    sql = f"""
    SELECT 
        System.ItemPathDisplay, 
        System.ItemName, 
        System.Size, 
        System.DateModified 
    FROM SystemIndex 
    WHERE SCOPE = 'file:{normalized_path}' 
    AND CONTAINS(System.Search.Contents, '"{keyword}"')
    """

    results = []

    try:
        conn.Open(conn_str)
        rs.Open(sql, conn)

        if not rs.EOF:
            while not rs.EOF:
                results.append(
                    {
                        "Path": rs.Fields.Item("System.ItemPathDisplay").Value,
                        "FileName": rs.Fields.Item("System.ItemName").Value,
                        # Decimal型をint型に変換してJSONエラーを回避
                        "Size": int(rs.Fields.Item("System.Size").Value)
                        if rs.Fields.Item("System.Size").Value is not None
                        else 0,
                        # 日付型をstr型に
                        "LastModified": str(
                            rs.Fields.Item("System.DateModified").Value
                        ),
                    }
                )
                rs.MoveNext()

    except Exception as e:
        print(f"検索中にエラーが発生しました: {e}")
    finally:
        # リソースを確実に解放（業務利用では重要）
        if rs.State == 1:
            rs.Close()
        if conn.State == 1:
            conn.Close()

    # COMライブラリの初期化解除
    pythoncom.CoUninitialize()

    return results


def extract_text_from_docx(file_path):
    """
    Wordファイル(.docx)から全文を抽出する
    """
    # 【修正ポイント】"C:\ユーザー\" を "C:\Users\" に置換し、さらに正規化する
    normalized_path = file_path.replace("C:\\ユーザー\\", "C:\\Users\\")
    normalized_path = os.path.normpath(normalized_path)

    # デバッグ用：実際にPythonが探しているパスを表示
    print(f"DEBUG: Searching for -> {normalized_path}")

    if not os.path.exists(normalized_path):
        return f"エラー: ファイルが物理的に存在しません。OneDriveの同期を確認してください。({normalized_path})"

    try:
        # Wordドキュメントを読み込む
        doc = Document(normalized_path)
        full_text = []

        # 段落ごとにテキストを取得
        for para in doc.paragraphs:
            if para.text.strip():  # 空行は無視
                full_text.append(para.text)

        # 表（Table）の中身も取得したい場合は以下を追加
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    full_text.append(cell.text)

        return "\n".join(full_text)

    except Exception as e:
        return f"エラー: {file_path} の読み込みに失敗しました ({e})"
