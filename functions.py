import win32com.client
from docx import Document
import os
import pythoncom
from openpyxl import load_workbook
from pypdf import PdfReader
import xlrd

def file_search(search_root, keyword):
    """
    Windows Search APIを使用してファイルを検索する
    :param search_root: 検索対象のフォルダパス (例: C:\\Documents)
    :param keyword: 検索したいキーワード (中身も検索対象)
    :return: 検索結果のリスト
    """

    print("-----     file_search start     -----")

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
    if search_root:
        normalized_path = os.path.normpath(search_root)
        print(f"検索中: {search_root} から '{keyword}' を探しています...")
    else:
        normalized_path = ""
        print(f"検索中: PC全体から '{keyword}' を探しています...")

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

    print("-----     file_search end       -----")

    return results


def extract_text_from_docx(file_path):
    """
    Wordファイル(.docx)から全文を抽出する
    """

    print("-----     extract_text_from_docx start     -----")

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


        print("-----     extract_text_from_docx end       -----")

        return "\n".join(full_text)

    except Exception as e:
        return f"エラー: {file_path} の読み込みに失敗しました ({e})"



def extract_text_from_excel(file_path):
    """
    Excelファイル(.xlsx / .xls)から全文（全シート・全セル）を抽出する
    """

    print("----- extract_text_from_excel start -----")

    normalized_path = file_path.replace("C:\\ユーザー\\", "C:\\Users\\")
    normalized_path = os.path.normpath(normalized_path)

    print(f"DEBUG: Searching for -> {normalized_path}")

    if not os.path.exists(normalized_path):
        return f"エラー: ファイルが物理的に存在しません。({normalized_path})"

    ext = os.path.splitext(normalized_path)[1].lower()
    full_text = []

    try:
        # ======================
        # .xlsx
        # ======================
        if ext == ".xlsx":
            wb = load_workbook(normalized_path, data_only=True)

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                full_text.append(f"【シート名】{sheet_name}")

                for row in ws.iter_rows():
                    row_values = [
                        str(cell.value) for cell in row if cell.value is not None
                    ]
                    if row_values:
                        full_text.append(" ".join(row_values))

        # ======================
        # .xls
        # ======================
        elif ext == ".xls":
            wb = xlrd.open_workbook(normalized_path)

            for sheet in wb.sheets():
                full_text.append(f"【シート名】{sheet.name}")

                for r in range(sheet.nrows):
                    row_values = [
                        str(sheet.cell_value(r, c))
                        for c in range(sheet.ncols)
                        if sheet.cell_value(r, c) not in ("", None)
                    ]
                    if row_values:
                        full_text.append(" ".join(row_values))

        else:
            return f"未対応のファイル形式です: {ext}"

        print("----- extract_text_from_excel end -----")

        return "\n".join(full_text)

    except Exception as e:
        return f"エラー: Excel読み込み失敗 ({e})"


def extract_text_from_pdf(file_path):
    """
    Excelファイル(.xlsx)から全文（全シート・全セル）を抽出する
    """

    print("-----     extract_text_from_pdf start     -----")

    # パス正規化
    normalized_path = file_path.replace("C:\\ユーザー\\", "C:\\Users\\")
    normalized_path = os.path.normpath(normalized_path)

    # デバッグ用
    print(f"DEBUG: Searching for -> {normalized_path}")

    if not os.path.exists(normalized_path):
        return f"エラー: ファイルが物理的に存在しません。OneDriveの同期を確認してください。({normalized_path})"

    try:
        # PDFファイルの読み込み
        reader = PdfReader(normalized_path)
        full_text = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                full_text.append(f"【ページ {i + 1}】\n{text}")

        if not full_text:
            return "（PDFからテキストを抽出できませんでした）"


        print("-----     extract_text_from_pdf end       -----")

        return "\n\n".join(full_text)

    except Exception as e:
        return f"エラー: {file_path} の読み込みに失敗しました ({e})"