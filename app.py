import ollama

def tinh_toan(bieu_thuc: str):
    """Thực hiện tính toán biểu thức toán học."""
    try:
        return str(eval(bieu_thuc))
    except Exception as e:
        return f"Lỗi: {str(e)}"

tools_map = {'tinh_toan': tinh_toan}
print("=== TRỢ LÝ HERMES AGENT ĐÃ SẴN SÀNG (Gõ 'exit' để thoát) ===")

chat_history = []

while True:
    user_input = input("\nBạn: ")
    if user_input.lower() == 'exit':
        break

    chat_history.append({'role': 'user', 'content': user_input})

    # Gửi request lần 1
    res = ollama.chat(model='hermes3:8b', messages=chat_history, tools=[tinh_toan])
    chat_history.append(res['message'])

    # Kiểm tra tool call
    if res.get('message', {}).get('tool_calls'):
        for tool in res['message']['tool_calls']:
            fn = tools_map.get(tool['function']['name'])
            if fn:
                args = tool['function']['arguments']
                print(f"[Hệ thống đang chạy công cụ...]")
                tool_res = fn(**args)

                chat_history.append({'role': 'tool', 'content': tool_res})

        # Phản hồi lần 2 sau khi có kết quả tool
        final_res = ollama.chat(model='hermes3:8b', messages=chat_history)
        print(f"Agent: {final_res['message']['content']}")
        chat_history.append(final_res['message'])
    else:
        print(f"Agent: {res['message']['content']}")