import streamlit as st
from groq import Groq
import os
import json
import psutil
from datetime import datetime
from pypdf import PdfReader
from duckduckgo_search import DDGS

st.set_page_config(page_title="Hermes Agent - Advanced Cloud", page_icon="⚡", layout="centered")

st.title("⚡ Hermes AI Agent - Advanced Cloud")
st.write("Trợ lý thông minh tích hợp công cụ hệ thống và quản lý tài liệu chuyên sâu.")

# Lấy Groq API Key
groq_api_key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")

if not groq_api_key:
    st.error("Chưa cấu hình GROQ_API_KEY! Vui lòng thêm API Key vào phần Secrets của Streamlit Cloud.")
    st.stop()

client = Groq(api_key=groq_api_key)
MODEL_NAME = "llama-3.3-70b-versatile"

HISTORY_FILE = "chat_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return [{
        "role": "system", 
        "content": "Bạn là Hermes Agent - một trợ lý ảo thông minh, nói chuyện ngắn gọn, súc tích, chuẩn xác bằng tiếng Việt."
    }]

def save_history(messages):
    try:
        clean_msgs = [m for m in messages if m.get("role") in ["user", "assistant", "system"]]
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(clean_msgs, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Lỗi lưu lịch sử: {e}")

# ==================== CÁC CÔNG CỤ (TOOLS) ====================

def tinh_toan(bieu_thuc: str):
    """Thực hiện tính toán biểu thức toán học."""
    try:
        return str(eval(bieu_thuc))
    except Exception as e:
        return f"Lỗi tính toán: {str(e)}"

def doc_noi_dung_file(ten_file: str):
    """Đọc và trả về nội dung của một file văn bản (.txt)."""
    try:
        if not os.path.exists(ten_file):
            return f"Không tìm thấy file: {ten_file}"
        with open(ten_file, "r", encoding="utf-8") as f:
            return f"Nội dung file {ten_file}:\n{f.read()}"
    except Exception as e:
        return f"Lỗi đọc file: {str(e)}"

def ghi_file_log(ten_file: str, noi_dung: str):
    """Ghi nội dung vào file log."""
    try:
        with open(ten_file, "a", encoding="utf-8") as f:
            f.write(noi_dung + "\n")
        return f"Đã ghi thành công vào file {ten_file}"
    except Exception as e:
        return f"Lỗi ghi file: {str(e)}"

def tim_kiem_web(tu_khoa: str):
    """Tìm kiếm thông tin mới trên Internet."""
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(tu_khoa, max_results=3)]
            if not results:
                return "Không tìm thấy kết quả."
            return "\n".join([f"- [{r.get('title')}]: {r.get('body')} ({r.get('href')})" for r in results])
    except Exception as e:
        return f"Lỗi tìm kiếm: {str(e)}"

def kiem_tra_tai_nguyen():
    """Kiểm tra CPU và RAM hệ thống."""
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        return f"CPU: {cpu}%, RAM: {ram.percent}% (Tổng: {round(ram.total / (1024**3), 2)} GB)"
    except Exception as e:
        return f"Lỗi: {str(e)}"

tools_map = {
    'tinh_toan': tinh_toan,
    'doc_noi_dung_file': doc_noi_dung_file,
    'ghi_file_log': ghi_file_log,
    'tim_kiem_web': tim_kiem_web,
    'kiem_tra_tai_nguyen': kiem_tra_tai_nguyen
}

tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "tinh_toan",
            "description": "Thực hiện tính toán biểu thức toán học",
            "parameters": {
                "type": "object",
                "properties": {"bieu_thuc": {"type": "string", "description": "Biểu thức toán học"}},
                "required": ["bieu_thuc"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "doc_noi_dung_file",
            "description": "Đọc nội dung file văn bản",
            "parameters": {
                "type": "object",
                "properties": {"ten_file": {"type": "string", "description": "Tên file cần đọc"}},
                "required": ["ten_file"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tim_kiem_web",
            "description": "Tìm kiếm thông tin trên Internet",
            "parameters": {
                "type": "object",
                "properties": {"tu_khoa": {"type": "string", "description": "Từ khóa tìm kiếm"}},
                "required": ["tu_khoa"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kiem_tra_tai_nguyen",
            "description": "Kiểm tra CPU và RAM hệ thống",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

# ==================== GIAO DIỆN & QUẢN LÝ ĐA TÀI LIỆU SIDEBAR ====================

if "messages" not in st.session_state:
    st.session_state.messages = load_history()

# Lưu trữ file tạm thời trong phiên làm việc (F5 sẽ tự mất sạch)
if "uploaded_docs" not in st.session_state:
    st.session_state.uploaded_docs = {}

with st.sidebar:
    st.header("📚 Quản lý tài liệu")
    
    uploaded_files = st.file_uploader("Tải lên tài liệu (chọn nhiều file PDF hoặc TXT)", type=["pdf", "txt"], accept_multiple_files=True)
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            if file_name not in st.session_state.uploaded_docs:
                try:
                    if file_name.endswith(".pdf"):
                        reader = PdfReader(uploaded_file)
                        text = ""
                        for page in reader.pages:
                            extracted = page.extract_text()
                            if extracted:
                                text += extracted + "\n"
                        st.session_state.uploaded_docs[file_name] = {"content": text, "active": True}
                    else:
                        content_str = uploaded_file.getvalue().decode("utf-8")
                        st.session_state.uploaded_docs[file_name] = {"content": content_str, "active": True}
                except Exception as e:
                    st.error(f"Lỗi đọc file {file_name}: {str(e)}")

    if st.session_state.uploaded_docs:
        st.markdown("### 📄 Danh sách file hiện có:")
        st.write("Tích chọn file để đưa vào phân tích:")
        
        updated_docs = {}
        for fname, data in list(st.session_state.uploaded_docs.items()):
            is_active = st.checkbox(fname, value=data["active"], key=f"chk_{fname}")
            updated_docs[fname] = {"content": data["content"], "active": is_active}
        
        st.session_state.uploaded_docs = updated_docs

        st.markdown("---")
        selected_file_to_remove = st.selectbox("Chọn file để xóa", ["-- Chọn file --"] + list(st.session_state.uploaded_docs.keys()), key="sel_remove_file")
        
        if selected_file_to_remove != "-- Chọn file --":
            if st.button("🗑️ Xóa file đã chọn", key="btn_remove_file_action"):
                if selected_file_to_remove in st.session_state.uploaded_docs:
                    del st.session_state.uploaded_docs[selected_file_to_remove]
                    st.success(f"Đã xóa thành công file: {selected_file_to_remove}")
                    st.rerun()

    st.markdown("---")
    if st.button("🗑️ Xóa toàn bộ lịch sử chat"):
        st.session_state.messages = [st.session_state.messages[0]] if st.session_state.messages else []
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.rerun()

for msg in st.session_state.messages:
    if msg["role"] not in ["tool", "system"]:
        if "content" in msg and msg["content"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

if user_input := st.chat_input("Nhập yêu cầu hoặc câu hỏi về tài liệu..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_history(st.session_state.messages)
    
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.status("Đang xử lý...", expanded=False) as status:
            
            combined_docs = ""
            if st.session_state.uploaded_docs:
                for fname, data in st.session_state.uploaded_docs.items():
                    if data["active"]:
                        combined_docs += f"\n--- TÀI LIỆU: {fname} ---\n{data['content'][:4000]}\n"

            if combined_docs:
                prompt_messages = [
                    {"role": "system", "content": "Bạn là trợ lý chuyên phân tích tài liệu, hãy trả lời câu hỏi dựa hoàn toàn vào các tài liệu được tích chọn cung cấp dưới đây."},
                    {"role": "user", "content": f"{combined_docs}\n\nCâu hỏi: {user_input}"}
                ]
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=prompt_messages
                )
                final_content = response.choices[0].message.content
            else:
                api_messages = list(st.session_state.messages)
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=api_messages,
                    tools=tools_definition,
                    tool_choice="auto"
                )
                
                response_message = response.choices[0].message
                
                if response_message.tool_calls:
                    api_messages.append(response_message)
                    for tool_call in response_message.tool_calls:
                        func_name = tool_call.function.name
                        func_args = json.loads(tool_call.function.arguments)
                        
                        st.write(f"⚙️ Gọi công cụ: `{func_name}`")
                        
                        fn = tools_map.get(func_name)
                        if fn:
                            tool_result = fn(**func_args)
                            st.write(f"📥 Kết quả: `{tool_result}`")
                            
                            api_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": func_name,
                                "content": str(tool_result)
                            })
                    
                    final_response = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=api_messages
                    )
                    final_content = final_response.choices[0].message.content
                else:
                    final_content = response_message.content
            
            st.session_state.messages.append({"role": "assistant", "content": final_content})
            save_history(st.session_state.messages)
            status.update(label="Hoàn thành!", state="complete", expanded=False)
        
        st.markdown(final_content)
