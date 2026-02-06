# 役割：AIとのやり取りの処理を格納

def chat(client,
        deployment_name,
        messages,
        tools,
        ):
    response = client.responses.create(
        model=deployment_name,
        input=messages,
        tools=tools,
        tool_choice="auto",
    )
    return response


def re_chat(client,
        deployment_name,
        messages,
        tools,
        ):
    response = client.responses.create(
        model=deployment_name,
        input=messages,
        tools=tools,
        tool_choice="auto",
    )
    return response



