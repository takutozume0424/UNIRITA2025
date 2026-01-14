"""
実行前にすること
1：仮想環境（今回はvenv）の作成
コマンド⇒python -m venv venv
2：仮想環境のアクティベート
コマンド⇒. .\venv\Scripts\Activate.ps1
3：azureへログイン（azureの環境を無理やりローカルで使うため）
コマンド⇒az login --use-device-code（なぜかaz loginだけではできなかった）

【注意事項】
コマンドを終了するときは「quit()」

（謎）文字コードで怒られ続けたときの解決策
「# バイナリで読み込んで UTF-8 としてデコード
[System.Text.Encoding]::UTF8.GetString([System.IO.File]::ReadAllBytes("test_fixed.py")) | Set-Content -Encoding UTF8 "test.py"」
"""

# azure openaiの公式ドキュメント2つ（結局あまり使ってないかも）
# 1：https://azure.github.io/azure-sdk/releases/latest/python.html
# 2：https://learn.microsoft.com/ja-jp/python/api/overview/azure/ai-projects-readme?view=azure-python
import streamlit as st
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import json
from functions import file_search, extract_text_from_docx
from dotenv import load_dotenv
import os

# 環境変数を取得する
load_dotenv()
endpoint = os.getenv("AZURE_EXISTING_AIPROJECT_ENDPOINT")


deployment_name = "gpt-5.2-chat"
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)


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
        "description": "ファイルの中身を取得します",
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

# Entra ID を使用してクライアントを作成し認証する
client = OpenAI(base_url=endpoint, api_key=token_provider())

st.title("Azure AI チャットボット")

# 会話履歴/スレッドidを保持するための設定
if "messages" not in st.session_state:
    st.session_state.messages = []

# 過去のメッセージを画面に表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザーの入力エリア
# 参考リンク：
# https://qiita.com/syonon/items/ce208fb5b8ce37f1b575
# 公式ドキュメント：
# https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses?view=foundry-classic&tabs=python-secure
if prompt := st.chat_input("メッセージを入力してください"):
    # ユーザーの発言を表示
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append(
        {
            "type": "message",
            "role": "user",
            "content": prompt,
        }
    )
    # 中間にAIに投げるメッセージの領域を用意
    wk_messages = [
        {
            "type": "message",
            "role": "user",
            "content": prompt,
        }
    ]

    # --- Azure OpenAIの処理を呼び出す ---
    # ここでは過去の履歴もまとめて送信

    # responses VS Chat Completions：
    # ’組み込みツールや複数のモデル呼び出しに依存しない新しいモデルは、Chat Completionsにもリリースされる予定です。
    # 一方、エージェントワークフロー向けに特別に設計された機能については、Responses APIが推奨されています。’
    # 参考URL：https://qiita.com/Tadataka_Takahashi/items/8678970abd324122085c
    response = client.responses.create(
        model=deployment_name,
        input=st.session_state.messages,
        tools=tools,
        tool_choice="auto",
    )

    print(
        json.dumps(
            response.model_dump(),
            ensure_ascii=False,
            indent=2,
        )
    )

    response_message = response.output
    wk_messages += response_message

    func_flg = 0

    # 参考リンク：
    # https://platform.openai.com/docs/guides/function-calling
    # https://zenn.dev/headwaters/articles/13316d641c9555
    # aiの返答を受け、使う関数があるかチェック⇒あったら関数を呼び出す
    for item in response_message:
        if item.type == "function_call":
            function_name = item.name
            function_args = json.loads(item.arguments)
            print(f"Function call: {function_name}")
            print(f"Function arguments: {function_args}")
            if function_name == "file_search":
                function_response = file_search(
                    search_root=function_args.get("file_path"),
                    keyword=function_args.get("keyword"),
                )
                func_flg = 1
                wk_messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(function_response, ensure_ascii=False),
                    }
                )

            elif function_name == "extract_text_from_docx":
                function_response = extract_text_from_docx(
                    file_path=function_args.get("file_path")
                )
                func_flg = 1
                wk_messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(function_response, ensure_ascii=False),
                    }
                )

    # 関数を呼び出した場合に、再度aiを呼び出す（このときにwk_messageを利用）
    if func_flg == 1:
        final_response = client.responses.create(
            instructions="検索結果や抽出されたテキストに基づいて、ユーザーに分かりやすく回答してください。",
            tools=tools,
            model=deployment_name,
            input=wk_messages,
        )
    else:
        final_response = response

    print(
        json.dumps(
            final_response.model_dump(),
            ensure_ascii=False,
            indent=2,
        )
    )

    for item in final_response.output:
        # itemの中に 'content' があり、さらにその中にテキストがあったら
        if hasattr(item, "content") and item.content is not None:
            # response_textにテキストを格納する
            response_text = item.content[0].text
            break  # 見つかったらループを終了

    # AIの回答を表示
    with st.chat_message("assistant"):
        st.markdown(response_text)
    st.session_state.messages.append(
        {
            "type": "message",
            "role": "assistant",
            "content": response_text,
        }
    )
