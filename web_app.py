import streamlit as st
from groq import Groq
import os
import json
import psutil
from datetime import datetime
from pypdf import PdfReader
from docx import Document
import pandas as pd
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
DOCS_FILE = "uploaded_docs.json"

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

def load_docs():
    if os.path.exists(DOCS_FILE):
        try:
            with open(DOCS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_docs(docs):
    try:
        with open(DOCS_FILE, "w", encoding="utf-8") as f:
            json.dump(docs, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Lỗi lưu file: {e}")

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

# Hàm hỗ trợ chia nhỏ và lọc đoạn văn bản liên quan (RAG nhẹ)
def get_relevant_context(query, docs_dict, max_chars=8000):
    combined_context = ""
    query_words = set(query.lower().split())
    
    for fname, data in docs_dict.items():
        if not data.get("active", True):
            continue
        text = data.get("content", "")
        
        # Chia tài liệu thành các đoạn nhỏ (khoảng 1000 ký tự/đoạn)
        chunk_size = 1000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        relevant_chunks = []
        for chunk in chunks:
            chunk_lower = chunk.lower()
            # Đếm số từ khóa xuất hiện trong đoạn
            score = sum(1 for word in query_words if word in chunk_lower)
            relevant_chunks.append((score, chunk))
        
        # Sắp xếp các đoạn có điểm cao nhất lên đầu
        relevant_chunks.sort(key=lambda x: x[0], reverse=True)
        
        file_extracted = ""
        current_len = 0
        for score, chunk in relevant_chunks:
            if current_len + len(chunk) < max_chars:
                file_extracted += chunk + "\n...\n"
                current_len += len(chunk)
            else:
                break
                
        if file_extracted:
            combined_context += f"\n--- TÀI LIỆU: {fname} ---\n{file_extracted}\n"
            
    return combined_context

# ==================== GIAO DIỆN & QUẢN LÝ ĐA TÀI LIỆU SIDEBAR ====================

if "messages" not in st.session_state:
    st.session_state.messages = load_history()

if "uploaded_docs" not in st.session_state:
    st.session_state.uploaded_docs = load_docs()

with st.sidebar:
    st.header("📚 Quản lý tài liệu")
    
    # Hỗ trợ thêm các định dạng file mới: .docx, .xlsx
    uploaded_files = st.file_uploader(
        "Tải lên tài liệu (PDF, TXT, DOCX, XLSX)", 
        type=["pdf", "txt", "docx", "xlsx"], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        has_new = False
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            if file_name not in st.session_state.uploaded_docs:
                try:
                    text = ""
                    if file_name.endswith(".pdf"):
                        reader = PdfReader(uploaded_file)
                        for page in reader.pages:
                            extracted = page.extract_text()
                            if extracted:
                                text += extracted + "\n"
                    elif file_name.endswith(".docx"):
                        doc = Document(uploaded_file)
                        for para in doc.paragraphs:
                            if para.text:
                                text += para.text + "\n"
                    elif file_name.endswith(".xlsx"):
                        df_dict = pd.read_excel(uploaded_file, sheet_name=None)
                        for sheet_name, df in df_dict.items():
                            text += f"\n[Sheet: {sheet_name}]\n" + df.to_string(index=False) + "\n"
                    else:  # .txt hoặc mặc định
                        text = uploaded_file.getvalue().decode("utf-8")
                        
                    st.session_state.uploaded_docs[file_name] = {"content": text, "active": True}
                    has_new = True
                except Exception as e:
                    st.error(f"Lỗi đọc file {file_name}: {str(e)}")
        
        if has_new:
            save_docs(st.session_state.uploaded_docs)
            st.success("Đã thêm và xử lý file thành công!")
            st.rerun()

    if st.session_state.uploaded_docs:
        st.markdown("### 📄 Danh sách file hiện có:")
        st.write("Tích chọn file để phân tích & bấm 🗑️ để xóa:")
        
        files_to_delete = []
        updated_docs = {}
        
        for fname, data in list(st.session_state.uploaded_docs.items()):
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                is_active = st.checkbox(fname, value=data["active"], key=f"chk_{fname}")
            with col2:
                if st.button("🗑️", key=f"del_btn_{fname}", help=f"Xóa file {fname}"):
                    files_to_delete.append(fname)
            
            updated_docs[fname] = {"content": data["content"], "active": is_active}
        
        if updated_docs != st.session_state.uploaded_docs:
            st.session_state.uploaded_docs = updated_docs
            save_docs(st.session_state.uploaded_docs)

        if files_to_delete:
            for fname in files_to_delete:
                if fname in st.session_state.uploaded_docs:
                    del st.session_state.uploaded_docs[fname]
                    st.success(f"Đã xóa thành công file: {fname}")
            save_docs(st.session_state.uploaded_docs)
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
            
            # Sử dụng thuật toán trích xuất đoạn văn bản thông minh thay vì cắt cụt thô sơ
            combined_docs = get_relevant_context(user_input, st.session_state.uploaded_docs)

            if combined_docs.strip():
                prompt_messages = [
                    {"role": "system", "content": "Bạn là trợ lý chuyên phân tích tài liệu. Hãy trả lời câu hỏi dựa hoàn toàn và chính xác vào các đoạn tài liệu được trích xuất dưới đây."},
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
