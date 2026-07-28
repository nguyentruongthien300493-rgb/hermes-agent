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
st.write("Trợ lý thông minh tích hợp công cụ hệ thống, quản lý tài liệu và phân tích đa luồng chuyên sâu.")

# Lấy Groq API Key
groq_api_key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")

if not groq_api_key:
    st.error("Chưa cấu hình GROQ_API_KEY! Vui lòng thêm API Key vào phần Secrets của Streamlit Cloud.")
    st.stop()

client = Groq(api_key=groq_api_key)

DOCS_FILE = "uploaded_docs.json"
SESSIONS_DIR = "chat_sessions"

if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

def get_all_sessions():
    files = [f.replace(".json", "") for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")]
    if not files:
        default_session = "Mặc định"
        save_session_messages(default_session, [{
            "role": "system", 
            "content": "Bạn là Hermes Agent - một trợ lý ảo thông minh, nói chuyện ngắn gọn, súc tích, chuẩn xác bằng tiếng Việt."
        }])
        return [default_session]
    return sorted(files)

def load_session_messages(session_name):
    file_path = os.path.join(SESSIONS_DIR, f"{session_name}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [{
        "role": "system", 
        "content": "Bạn là Hermes Agent - một trợ lý ảo thông minh, nói chuyện ngắn gọn, súc tích, chuẩn xác bằng tiếng Việt."
    }]

def save_session_messages(session_name, messages):
    try:
        file_path = os.path.join(SESSIONS_DIR, f"{session_name}.json")
        clean_msgs = [m for m in messages if m.get("role") in ["user", "assistant", "system"]]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(clean_msgs, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Lỗi lưu phiên chat: {e}")

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

@st.cache_data
def parse_uploaded_file(file_bytes, file_name):
    text = ""
    try:
        if file_name.endswith(".pdf"):
            import io
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        elif file_name.endswith(".docx"):
            import io
            doc = Document(io.BytesIO(file_bytes))
            for para in doc.paragraphs:
                if para.text:
                    text += para.text + "\n"
        elif file_name.endswith(".xlsx"):
            import io
            df_dict = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
            for sheet_name, df in df_dict.items():
                text += f"\n[Sheet: {sheet_name}]\n" + df.to_string(index=False) + "\n"
        else:
            text = file_bytes.decode("utf-8")
    except Exception as e:
        text = f"Lỗi đọc file: {str(e)}"
    return text

def get_relevant_context(query, docs_dict, max_chars=8000):
    combined_context = ""
    query_words = set(query.lower().split())
    
    for fname, data in docs_dict.items():
        if not data.get("active", True):
            continue
        text = data.get("content", "")
        
        chunk_size = 1000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        relevant_chunks = []
        for chunk in chunks:
            chunk_lower = chunk.lower()
            score = sum(1 for word in query_words if word in chunk_lower)
            relevant_chunks.append((score, chunk))
        
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

# ==================== GIAO DIỆN & CÀI ĐẶT SIDEBAR ====================

if "current_session" not in st.session_state:
    sessions = get_all_sessions()
    st.session_state.current_session = sessions[0]

if "messages" not in st.session_state:
    st.session_state.messages = load_session_messages(st.session_state.current_session)

if "uploaded_docs" not in st.session_state:
    st.session_state.uploaded_docs = load_docs()

with st.sidebar:
    st.header("💬 Quản lý Đoạn Chat")
    
    sessions = get_all_sessions()
    selected_session = st.selectbox("Chọn đoạn chat", sessions, index=sessions.index(st.session_state.current_session) if st.session_state.current_session in sessions else 0)
    
    if selected_session != st.session_state.current_session:
        st.session_state.current_session = selected_session
        st.session_state.messages = load_session_messages(selected_session)
        st.rerun()
        
    new_chat_name = st.text_input("Tên đoạn chat mới:")
    if st.button("➕ Tạo đoạn chat mới"):
        if new_chat_name.strip():
            safe_name = new_chat_name.strip()
            save_session_messages(safe_name, [{
                "role": "system", 
                "content": "Bạn là Hermes Agent - một trợ lý ảo thông minh, nói chuyện ngắn gọn, súc tích, chuẩn xác bằng tiếng Việt."
            }])
            st.session_state.current_session = safe_name
            st.session_state.messages = load_session_messages(safe_name)
            st.rerun()

    st.markdown("---")
    st.header("⚙️ Cài đặt AI & Tối ưu")
    
    model_options = {
        "llama-3.3-70b-versatile": "llama-3.3-70b-versatile (Thông minh nhất, phân tích sâu)",
        "llama-3.1-8b-instant": "llama-3.1-8b-instant (Siêu nhanh, gọn nhẹ)",
        "mixtral-8x7b-32768": "mixtral-8x7b-32768 (Xử lý văn bản cực dài)"
    }
    
    selected_label = st.selectbox(
        "Chọn Model AI",
        options=list(model_options.values()),
        index=0
    )
    MODEL_NAME = [k for k, v in model_options.items() if v == selected_label][0]
    
    # Hướng dẫn tận dụng: Tùy chỉnh Temperature linh hoạt tùy theo tác vụ
    temperature = st.slider(
        "Độ sáng tạo (Temperature)", 
        min_value=0.0, 
        max_value=1.0, 
        value=0.3, 
        step=0.1, 
        help="0.0 - 0.3: Phù hợp phân tích tài liệu, code, số liệu chính xác.\n0.7 - 1.0: Phù hợp viết văn, sáng tạo ý tưởng."
    )

    st.markdown("---")
    st.header("📚 Quản lý tài liệu")
    
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
                file_bytes = uploaded_file.getvalue()
                text = parse_uploaded_file(file_bytes, file_name)
                st.session_state.uploaded_docs[file_name] = {"content": text, "active": True}
                has_new = True
        
        if has_new:
            save_docs(st.session_state.uploaded_docs)
            st.success("Đã thêm và tối ưu hóa file thành công!")
            st.rerun()

    if st.session_state.uploaded_docs:
        st.markdown("### 📄 Danh sách file & Thống kê:")
        
        files_to_delete = []
        updated_docs = {}
        
        for fname, data in list(st.session_state.uploaded_docs.items()):
            char_count = len(data["content"])
            col1, col2, col3 = st.columns([0.5, 0.25, 0.25])
            with col1:
                is_active = st.checkbox(f"{fname[:12]}...", value=data["active"], key=f"chk_{fname}", help=fname)
            with col2:
                if st.button("👁️ Xem", key=f"prev_{fname}", help=f"Xem nhanh nội dung {fname}"):
                    st.session_state[f"show_preview_{fname}"] = not st.session_state.get(f"show_preview_{fname}", False)
            with col3:
                if st.button("🗑️ Xóa", key=f"del_btn_{fname}", help=f"Xóa file {fname}"):
                    files_to_delete.append(fname)
            
            st.caption(f"Trạng thái: {'🟢 Bật' if is_active else '⚪ Tắt'} | Ký tự: {char_count:,}")

            if st.session_state.get(f"show_preview_{fname}", False):
                with st.expander(f"📖 Nội dung: {fname}", expanded=True):
                    st.text_area("Văn bản trích xuất:", data["content"][:2000] + ("\n...[Đã lược bớt nội dung dài]..." if len(data["content"]) > 2000 else ""), height=150, key=f"txt_prev_{fname}")
            
            updated_docs[fname] = {"content": data["content"], "active": is_active}
        
        if updated_docs != st.session_state.uploaded_docs:
            st.session_state.uploaded_docs = updated_docs
            save_docs(st.session_state.uploaded_docs)

        if files_to_delete:
            for fname in files_to_delete:
                if fname in st.session_state.uploaded_docs:
                    del st.session_state.uploaded_docs[fname]
                    if f"show_preview_{fname}" in st.session_state:
                        del st.session_state[f"show_preview_{fname}"]
                    st.success(f"Đã xóa thành công file: {fname}")
            save_docs(st.session_state.uploaded_docs)
            st.rerun()

    st.markdown("---")
    chat_export_text = ""
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            chat_export_text += f"{msg['role'].upper()}: {msg['content']}\n\n"
            
    st.download_button(
        label="📥 Tải xuống lịch sử chat (.txt)",
        data=chat_export_text,
        file_name=f"chat_history_{st.session_state.current_session}.txt",
        mime="text/plain"
    )

    if st.button("🗑️ Xóa đoạn chat hiện tại"):
        file_path = os.path.join(SESSIONS_DIR, f"{st.session_state.current_session}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
        sessions = get_all_sessions()
        st.session_state.current_session = sessions[0]
        st.session_state.messages = load_session_messages(sessions[0])
        st.rerun()

# ==================== KHU VỰC GỢI Ý NHANH (QUICK PROMPTS) ====================
st.markdown("💡 **Gợi ý tác vụ nhanh:**")
cols_quick = st.columns(3)
quick_query = None
with cols_quick[0]:
    if st.button("📑 Tóm tắt tài liệu bật"):
        quick_query = "Hãy tóm tắt ngắn gọn các điểm chính của toàn bộ các tài liệu đang bật."
with cols_quick[1]:
    if st.button("🔍 Tìm ý chính/Điều khoản"):
        quick_query = "Hãy chỉ ra các điều khoản hoặc thông tin quan trọng nhất có trong tài liệu."
with cols_quick[2]:
    if st.button("📈 Phân tích số liệu"):
        quick_query = "Hãy phân tích các số liệu cốt lõi hoặc bảng dữ liệu có trong tài liệu."

for msg in st.session_state.messages:
    if msg["role"] not in ["tool", "system"]:
        if "content" in msg and msg["content"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

# Nhận input từ khung chat hoặc nút gợi ý nhanh
user_input = st.chat_input("Nhập yêu cầu hoặc câu hỏi về tài liệu...")
if quick_query:
    user_input = quick_query

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_session_messages(st.session_state.current_session, st.session_state.messages)
    
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.status("Đang xử lý...", expanded=False) as status:
            
            combined_docs = get_relevant_context(user_input, st.session_state.uploaded_docs)
            
            if combined_docs.strip():
                st.write(f"📊 Đã trích xuất ngữ cảnh tài liệu (~{len(combined_docs)} ký tự) để phân tích.")
                prompt_messages = [
                    {"role": "system", "content": "Bạn là trợ lý chuyên phân tích tài liệu. Hãy trả lời câu hỏi dựa hoàn toàn và chính xác vào các đoạn tài liệu được trích xuất dưới đây."},
                    {"role": "user", "content": f"{combined_docs}\n\nCâu hỏi: {user_input}"}
                ]
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=prompt_messages,
                    temperature=temperature
                )
                final_content = response.choices[0].message.content
            else:
                api_messages = list(st.session_state.messages)
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=api_messages,
                    tools=tools_definition,
                    tool_choice="auto",
                    temperature=temperature
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
                        messages=api_messages,
                        temperature=temperature
                    )
                    final_content = final_response.choices[0].message.content
                else:
                    final_content = response_message.content
            
            st.session_state.messages.append({"role": "assistant", "content": final_content})
            save_session_messages(st.session_state.current_session, st.session_state.messages)
            status.update(label="Hoàn thành!", state="complete", expanded=False)
        
        st.markdown(final_content)
