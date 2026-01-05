import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
from datetime import datetime

# --- 1. 페이지 설정 (최상단) ---
st.set_page_config(page_title="Leisure DNA: Premium", layout="wide", page_icon="🧬")

# --- 2. 디자인 CSS (강제 적용) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif !important; }
    .stApp { background-color: #F0F2F5 !important; }
    h1 { color: #0E1A40 !important; font-weight: 800 !important; text-align: center; border-bottom: 2px solid #E5E5EA; padding-bottom: 20px; }
    .stForm, div[data-testid="stExpander"] { background-color: white !important; border-radius: 20px !important; padding: 30px !important; box-shadow: 0 10px 25px rgba(0,0,0,0.05) !important; }
    div.stButton > button { background: linear-gradient(90deg, #0E1A40 0%, #1A237E 100%) !important; color: white !important; border: none !important; padding: 12px 0 !important; border-radius: 12px !important; font-weight: bold !important; transition: transform 0.2s; }
    div.stButton > button:hover { transform: scale(1.02); }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: #ffffff !important; border: 1px solid #E0E0E0 !important; border-radius: 4px 20px 20px 20px !important; padding: 15px !important; }
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #E3F2FD !important; border-radius: 20px 4px 20px 20px !important; padding: 15px !important; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 보안 설정 ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("🚨 API 키가 없습니다.")
        st.stop()
    ADMIN_ID = st.secrets.get("ADMIN_ID", "admin") 
    ADMIN_PW = st.secrets.get("ADMIN_PW", "0000")
except Exception as e:
    st.error(f"⚠️ 설정 오류: {str(e)}")
    st.stop()

# --- 4. 모델 연결 (디버깅 강화) ---
def get_chat_model(system_instruction):
    # 1순위: Flash (빠름/무료), 2순위: Pro (안정/무료)
    candidates = ["gemini-1.5-flash", "gemini-pro"]
    
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            chat = model.start_chat(history=[])
            return chat, model_name
        except Exception:
            continue
            
    return None, None

# --- 5. 데이터 저장 및 페르소나 ---
DATA_FILE = "user_data_log.csv"
def save_to_csv(contact, history, score=None):
    # (이전과 동일한 로직)
    conv = ""
    for msg in history:
        role = "AI" if msg['role'] == 'model' else "User"
        conv += f"[{role}] {msg['parts'][0]}\n"
    new_data = {"timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")], "contact": [contact], "conversation": [conv], "score": [score if score else "N/A"]}
    df = pd.DataFrame(new_data)
    if not os.path.exists(DATA_FILE): df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
    else: df.to_csv(DATA_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

SYSTEM_INSTRUCTION = "당신은 'AI 프리미엄 라이프스타일 큐레이터'입니다. 오프닝 인사 후, 대화 흐름 속에서 성별/연령, 지역, 동반자, 예산을 자연스럽게 파악하고 구글 맵 평점 4.5 이상 장소를 추천하십시오."

# --- 6. UI 로직 ---
if "step" not in st.session_state: st.session_state.step = "login"
if "messages" not in st.session_state: st.session_state.messages = []
if "user_contact" not in st.session_state: st.session_state.user_contact = ""
if "is_admin" not in st.session_state: st.session_state.is_admin = False

# 사이드바 (종료 버튼 이동)
with st.sidebar:
    st.title("Menu")
    if st.session_state.step == "chat_mode":
        if st.button("상담 종료 및 평가 🏁"):
            st.session_state.step = "feedback"
            st.rerun()
    st.markdown("---")
    with st.expander("Admin Login"):
        aid = st.text_input("ID", key="aid")
        apw = st.text_input("PW", type="password", key="apw")
        if st.button("Login"):
            if aid == ADMIN_ID and apw == ADMIN_PW:
                st.session_state.is_admin = True
                st.rerun()

# 메인 화면
if st.session_state.is_admin:
    st.title("🔐 Admin Dashboard")
    if os.path.exists(DATA_FILE):
        st.dataframe(pd.read_csv(DATA_FILE), use_container_width=True)
    else: st.warning("데이터 없음")
    if st.button("Logout"): st.session_state.is_admin = False; st.rerun()

else:
    if st.session_state.step == "login":
        st.markdown("<br>", unsafe_allow_html=True)
        st.title("🧩 Leisure DNA")
        with st.form("login"):
            st.markdown("### 👋 환영합니다")
            contact = st.text_input("연락처 (필수)", placeholder="010-XXXX-XXXX")
            agree = st.checkbox("개인정보 수집 및 이용 동의 (필수)")
            if st.form_submit_button("상담 시작"):
                if contact and agree:
                    st.session_state.user_contact = contact
                    st.session_state.step = "chat_mode"
                    st.rerun()
                else: st.error("동의 및 연락처 입력 필수")

    elif st.session_state.step == "chat_mode":
        st.title("🏛️ Lifestyle Curator")
        
        # 모델 연결 시도
        if "chat_session" not in st.session_state:
            with st.spinner("AI 엔진 가동 중..."):
                chat, model_name = get_chat_model(SYSTEM_INSTRUCTION)
                if chat:
                    st.session_state.chat_session = chat
                    try:
                        # 시스템 프롬프트 주입
                        msg = f"{SYSTEM_INSTRUCTION}\n\n(시스템: 따뜻한 첫 인사를 건네세요.)"
                        res = st.session_state.chat_session.send_message(msg)
                        st.session_state.messages.append({"role": "model", "parts": [res.text]})
                    except Exception as e:
                        st.error(f"첫 메시지 오류: {e}")
                else:
                    # [핵심] 연결 실패 시 사용 가능한 모델 목록을 보여줌 (디버깅용)
                    st.error("❌ 모든 AI 모델 연결 실패. 서버 라이브러리 버전이 낮습니다.")
                    st.write("▼ 현재 서버에서 인식하는 모델 목록:")
                    try:
                        for m in genai.list_models():
                            if 'generateContent' in m.supported_generation_methods:
                                st.write(f"- {m.name}")
                    except:
                        st.write("모델 목록조차 불러올 수 없음 (라이브러리 심각한 구버전)")
                    st.stop()

        for msg in st.session_state.messages:
            role = "assistant" if msg['role'] == 'model' else "user"
            with st.chat_message(role): st.markdown(msg['parts'][0])

        if prompt := st.chat_input("입력..."):
            st.session_state.messages.append({"role": "user", "parts": [prompt]})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                try:
                    res = st.session_state.chat_session.send_message(prompt)
                    st.markdown(res.text)
                    st.session_state.messages.append({"role": "model", "parts": [res.text]})
                    save_to_csv(st.session_state.user_contact, st.session_state.messages)
                except Exception as e: st.error(f"오류: {e}")

    elif st.session_state.step == "feedback":
        st.title("⭐ 만족도 평가")
        with st.form("fb"):
            score = st.slider("점수", 1, 5, 5)
            if st.form_submit_button("제출"):
                save_to_csv(st.session_state.user_contact, st.session_state.messages, score)
                st.success("완료되었습니다."); st.session_state.clear(); st.rerun()
