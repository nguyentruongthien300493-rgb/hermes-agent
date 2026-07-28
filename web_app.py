import streamlit as st
from groq import Groq
import os
import json
import shutil
import psutil
import pyautogui
from datetime import datetime
from duckduckgo_search import DDGS

st.set_page_config(page_title="Hermes Agent - Cloud Version", page_icon="⚡", layout="centered")

st.title("⚡ Hermes AI Agent - Cloud")
st.write("Trợ lý thông minh tích hợp đa công cụ chạy trên nền tảng đám mây.")

# Lấy Groq API Key bảo mật từ Streamlit Secrets
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
        "content": "Bạn là Hermes Agent - một chuyên gia kỹ sư IT và trợ lý ảo thông minh, nói chuyện ngắn gọn, súc tích, chuẩn xác bằng tiếng Việt và luôn tận dụng tối đa các công cụ được cung cấp."
    }]

def save_history(messages):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Lỗi lưu lịch sử: {e}")

# ==================== CÁC CÔNG CỤ (TOOLS) ====================

def tinh_toan(bieu_thuc: str):
    """Thực hiện tính toán biểu thức toán học dạng chuỗi."""
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

def chup_man_hinh():
    """Chụp lại màn hình máy tính hiện tại và lưu thành file ảnh."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ten_file = f"screenshot_{timestamp}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(ten_file)
        return f"Đã chụp màn hình thành công và lưu tại file: {ten_file}"
    except Exception as e:
        return f"Lỗi chụp màn hình: {str(e)}"

def sap_xep_file(thu_muc: str = ".", **kwargs):
    """Tự động phân loại và di chuyển các file trong thư mục."""
    if not thu_muc and kwargs:
        thu_muc = list(kwargs.values())[0]
    if not thu_muc:
        thu_muc = "."
        
    try:
        if not os.path.exists(thu_muc):
            return f"Không tìm thấy đường dẫn thư mục: {thu_muc}"
        
        extensions = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
            "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv"],
            "Videos": [".mp4", ".mkv", ".avi", ".mov"],
            "Archives": [".zip", ".rar", ".7z", ".tar"],
            "Code": [".py", ".js", ".html", ".css", ".cpp", ".java"]
        }
        
        count = 0
        for filename in os.listdir(thu_muc):
            file_path = os.path.join(thu_muc, filename)
            if os.path.isfile(file_path):
                ext = os.path.splitext(filename)[1].lower()
                for folder_name, ext_list in extensions.items():
                    if ext in ext_list:
                        target_folder = os.path.join(thu_muc, folder_name)
                        os.makedirs(target_folder, exist_ok=True)
                        shutil.move(file_path, os.path.join(target_folder, filename))
                        count += 1
                        break
        return f"Đã sắp xếp thành công {count} tệp tin trong thư mục '{thu_muc}'."
    except Exception as e:
        return f"Lỗi sắp xếp file: {str(e)}"

tools_map = {
    'tinh_toan': tinh_toan,
    'doc_noi_dung_file': doc_noi_dung_file,
    'ghi_file_log': ghi_file_log,
    'tim_kiem_web': tim_kiem_web,
    'kiem_tra_tai_nguyen': kiem_tra_tai_nguyen,
    'chup_man_hinh': chup_man_hinh,
    'sap_xep_file': sap_xep_file
}

# Khai báo cấu trúc JSON Schema cho Groq Tools gọi hàm
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
    },
    {
        "type": "function",
        "function": {
            "name": "chup_man_hinh",
            "description": "Chụp lại màn hình máy tính hiện tại",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sap_xep_file",
            "description": "Sắp xếp các file trong thư mục",
            "parameters": {
                "type": "object",
                "properties": {"thu_muc": {"type": "string", "description": "Đường dẫn thư mục cần sắp xếp"}},
                "required": ["thu_muc"]
            }
        }
    }
]

# ==================== GIAO DIỆN CHAT ====================

if "messages" not in st.session_state:
    st.session_state.messages = load_history()

with st.sidebar:
    st.header("⚙️ Quản lý")
    if st.button("🗑️ Xóa bộ nhớ"):
        st.session_state.messages = [st.session_state.messages[0]] if st.session_state.messages else []
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.rerun()

for msg in st.session_state.messages:
    if msg["role"] not in ["tool", "system"]:
        if "content" in msg and msg["content"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

if user_input := st.chat_input("Nhập yêu cầu của bạn..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_history(st.session_state.messages)
    
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.status("Đang xử lý...", expanded=False) as status:
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=st.session_state.messages,
                tools=tools_definition,
                tool_choice="auto"
            )
            
            response_message = response.choices[0].message
            st.session_state.messages.append(response_message.model_dump())
            
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    
                    st.write(f"⚙️ Gọi công cụ: `{func_name}`")
                    
                    fn = tools_map.get(func_name)
                    if fn:
                        tool_result = fn(**func_args)
                        st.write(f"📥 Kết quả: `{tool_result}`")
                        
                        st.session_state.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": func_name,
                            "content": str(tool_result)
                        })
                
                final_response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=st.session_state.messages
                )
                final_content = final_response.choices[0].message.content
                st.session_state.messages.append(final_response.choices[0].message.model_dump())
            else:
                final_content = response_message.content
            
            save_history(st.session_state.messages)
            status.update(label="Hoàn thành!", state="complete", expanded=False)
        
        st.markdown(final_content)