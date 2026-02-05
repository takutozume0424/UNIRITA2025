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

【streamlitを公開する方法】
https://note.com/keen_roses9273/n/n1c0dd8297ee1


【Open AI】
https://platform.openai.com/docs/guides/structured-outputs



"""

# azure openaiの公式ドキュメント2つ（結局あまり使ってないかも）
# 1：https://azure.github.io/azure-sdk/releases/latest/python.html
# 2：https://learn.microsoft.com/ja-jp/python/api/overview/azure/ai-projects-readme?view=azure-python
import streamlit as st
from openai import OpenAI
# from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import json
from functions import (
    file_search,
    extract_text_from_docx,
    extract_text_from_excel,
    extract_text_from_pdf,
    )
from const import tools
from chat_service import (
    chat,
    re_chat,
)
from dotenv import load_dotenv
import os
import time
from db_access import insert_conversation


# 環境変数を取得する
load_dotenv()
endpoint = os.getenv("AZURE_EXISTING_AIPROJECT_ENDPOINT")


deployment_name = "gpt-5.2-chat"
# token_provider = get_bearer_token_provider(
#     DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
# )


# # Entra ID を使用してクライアントを作成し認証する
# client = OpenAI(base_url=endpoint, api_key=token_provider())

st.title("Azure AI チャットボット")

# 会話履歴/スレッドidを保持するための設定
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.conversation_id = str(time.time() * 1000)

@st.cache_resource
def get_client():
    from azure.identity import AzureCliCredential, get_bearer_token_provider
    credential = AzureCliCredential()
    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default"
    )
    return OpenAI(
        base_url=os.getenv("AZURE_EXISTING_AIPROJECT_ENDPOINT"),
        api_key=token_provider()
    )

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
    print("-----     app start     -----")
    client = get_client()
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

    insert_conversation(
        conversation_id=st.session_state.conversation_id,
        role="user",
        content=prompt,
        token_count=0,
        model=None,
        input_tokens=0,
        output_tokens=0,
        total_tokens=0
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

    # print(
    #     f"""messages:{
    #         st.session_state.messages
    #     }
    #     """
    # )

    response = chat(
        client=client,
        deployment_name=deployment_name,
        messages=st.session_state.messages,
        tools=tools,
    )


    # print(
    #     json.dumps(
    #         response.model_dump(),
    #         ensure_ascii=False,
    #         indent=2,
    #     )
    # )

    func_flg = 0
    func_count = 0

    # 参考リンク：
    # https://platform.openai.com/docs/guides/function-calling
    # https://zenn.dev/headwaters/articles/13316d641c9555
    # aiの返答を受け、使う関数があるかチェック⇒あったら関数を呼び出す
    while func_count < 5:

        response_message = response.output
        wk_messages += response_message
        function_calls =[]

        for item in response_message:
            if item.type == "function_call":
                function_calls.append(item)

        if not function_calls:
            break

        for item in function_calls:

            function_name = item.name
            function_args = json.loads(item.arguments)
            print(f"Function call: {function_name}")
            print(f"Function arguments: {function_args}")
            if function_name == "file_search":
                function_response = file_search(
                    search_root=function_args.get("file_path"),
                    keyword=function_args.get("keyword"),
                )
            elif function_name == "extract_text_from_docx":
                function_response = extract_text_from_docx(
                    file_path=function_args.get("file_path")
                )
            elif function_name == "extract_text_from_excel":
                function_response = extract_text_from_excel(
                    file_path=function_args.get("file_path"),
                )
            elif function_name == "extract_text_from_pdf":
                function_response = extract_text_from_pdf(
                    file_path=function_args.get("file_path")
                )
            wk_messages.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(function_response, ensure_ascii=False),
                }
            )

        # 次のAI呼び出し
        response = re_chat(
            client=client,
            deployment_name=deployment_name,
            messages=wk_messages,
            tools=tools,
        )

        func_count += 1

    # print(
    #     f"""wk_message:{
    #         wk_messages
    #     }
    #     """
    # )

    # print(
    #     f"""final_response:{
    #         response
    #     }
    #     """
    # )

    for item in response.output:
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

    insert_conversation(
        conversation_id=st.session_state.conversation_id,
        role="assistant",
        content=response_text,
        token_count=0,
        model=deployment_name,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        total_tokens=response.usage.total_tokens,
    )

    print("-----     app end       -----")
