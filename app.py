import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
from datetime import datetime

# --- 1. 페이지 설정 (반드시 코드 제일 윗줄에 있어야 함) ---
st.set_page_config(page_title="Leisure DNA: Premium", layout="wide", page_icon="🧬")

# --- 2. 디자인 CSS (강력 적용 버전) ---
st.markdown("""
    <style>
    /* 폰트 강제 적용 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    
    html, body, [class*="css"] { 
        font-family: 'Noto Sans KR', sans-serif !important; 
    }
    
    /* 전체 배경색 */
    .stApp { 
        background-color: #F5F7F9 !important; 
    }

    /* 헤더 스타일 */
    h1 { 
        color: #0E1A40 !important; 
        font-weight: 800 !important; 
        text-align: center; 
        border-bottom: 3px solid #E5E5EA; 
        padding-bottom: 25px; 
        margin-bottom: 30px;
    }

    /* 입력 폼(Form) 카드 디자인 */
    .stForm, div[data-testid="stExpander"] { 
        background-color: white !important; 
        border-radius: 20px !important; 
        padding: 40px !important; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.08) !important; 
        border: 1px solid #E1E4E8 !important;
    }

    /* 버튼 디자인 (그라데이션) */
    div.stButton > button { 
        background: linear-gradient(135deg, #0E1A40 0%, #293264 100%) !important; 
        color: white !important; 
        border: none !important; 
        padding: 15px 0 !important; 
        border-radius: 12px !important; 
        font-size: 16px !important; 
        font-weight: bold !important; 
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0 4px 15px rgba(14, 26, 64, 0.2) !important;
    }
    div.stButton > button:hover { 
        transform: translateY(-2px); 
        box-shadow: 0 6px 20px rgba(14, 26, 64, 0.3) !important;
    }
    
    /* 채팅 메시지 디자인 */
    .stChatMessage {
        background-color: transparent !important;
        padding: 10px 0 !important;
    }
    /* AI 메시지 (흰색 말풍선) */
    div[data-testid="stChatMessage"]:nth-child(even) { 
        background-color: #ffffff !important; 
        border: 1px solid #E0E0E0 !important; 
        border-radius: 4px 20px 20px 20px !important; 
        padding: 25px !important; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
    }
    /* 유저 메시지 (하늘색 말풍선) */
    div[data-testid="stChatMessage"]:nth-child(odd) { 
        background-color: #E3F2FD !important; 
        border-radius: 20px 4px 20px 20px !important; 
        padding: 20px !important; 
        border: none !important; 
        color: #0D47A1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 보안 및 API 설정 ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("🚨 치명적 오류: API 키가 없습니다. Streamlit Secrets를 확인하세요.")
        st.stop()
    ADMIN_ID = st.secrets.get("ADMIN_ID", "admin") 
    ADMIN_PW = st.secrets.get("ADMIN_PW", "0000")
except Exception as e:
    st.error(f"⚠️ 설정 오류: {str(e)}")
    st.stop()

# --- 4. 데이터 저장 함수 ---
DATA_FILE = "user_data_log.csv"

def save_to_csv(contact, history, score=None):
    conv = ""
    for msg in history:
        role = "AI" if msg['role'] == 'model' else "User"
        conv += f"[{role}] {msg['parts'][0]}\n"
    new_data = {"timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")], "contact": [contact], "conversation": [conv], "score": [score if score else "N/A"]}
    df = pd.DataFrame(new_data)
    if not os.path.exists(DATA_FILE): df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
    else: df.to_csv(DATA_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

SYSTEM_INSTRUCTION = "당신은 'AI 프리미엄 라이프스타일 큐레이터'입니다. 오프닝 인사 후, 대화 흐름 속에서 성별/연령, 지역, 동반자, 예산을 자연스럽게 파악하고 구글 맵 평점 4.5 이상 장소를 추천하십시오."

# --- 5. 상태 초기화 ---
if "step" not in st.session_state: st.session_state.step = "login"
if "messages" not in st.session_state: st.session_state.messages = []
if "user_contact" not in st.session_state: st.session_state.user_contact = ""
if "is_admin" not in st.session_state: st.session_state.is_admin = False

# --- 6. 사이드바 메뉴 ---
with st.sidebar:
    st.title("Menu")
    
    # [수정] 상담 종료 버튼은 채팅 중에만 보이도록 조건 추가
    if st.session_state.step == "chat_mode":
        st.info("상담을 마치시겠습니까?")
        if st.button("상담 종료 및 평가 🏁"):
            st.session_state.step = "feedback"
            st.rerun()
            
    st.markdown("---")
    with st.expander("관리자 로그인 (Admin)"):
        aid = st.text_input("ID", key="aid")
        apw = st.text_input("PW", type="password", key="apw")
        if st.button("Login"):
            if aid == ADMIN_ID and apw == ADMIN_PW:
                st.session_state.is_admin = True
                st.rerun()

    if st.session_state.is_admin:
        if st.button("Logout"): 
            st.session_state.is_admin = False
            st.rerun()

# --- 7. 메인 화면 로직 ---
if st.session_state.is_admin:
    st.title("🔐 Admin Dashboard")
    st.success("관리자 모드입니다.")
    if os.path.exists(DATA_FILE):
        st.dataframe(pd.read_csv(DATA_FILE), use_container_width=True)
        csv = pd.read_csv(DATA_FILE).to_csv(index=False).encode('utf-8-sig')
        st.download_button("데이터 다운로드 (CSV)", csv, "data.csv", "text/csv")
    else: st.warning("아직 데이터가 없습니다.")

else:
    # 1. 로그인 화면
    if st.session_state.step == "login":
        st.markdown("<br>", unsafe_allow_html=True)
        st.title("🧩 Leisure DNA")
        
        with st.form("login_form"):
            st.markdown("### 👋 환영합니다")
            st.write("나만의 여가 큐레이션을 위해 연락처를 입력해주세요.")
            contact = st.text_input("연락처 (전화번호/이메일)", placeholder="010-XXXX-XXXX")
            st.markdown("<br>", unsafe_allow_html=True)
            agree = st.checkbox("개인정보 수집 및 이용에 동의합니다 (필수)")
            
            if st.form_submit_button("상담 시작하기"):
                if contact and agree:
                    st.session_state.user_contact = contact
                    st.session_state.step = "chat_mode"
                    st.rerun()
                else: st.error("연락처 입력 및 동의가 필수입니다.")

    # 2. 채팅 화면
    elif st.session_state.step == "chat_mode":
        st.title("🏛️ Lifestyle Curator")
        
        # [수정] 무조건 gemini-pro 사용 (에러 방지)
        if "chat_session" not in st.session_state:
            with st.spinner("AI 큐레이터 연결 중..."):
                try:
                    # 404 에러의 주범인 flash 모델을 제거하고 pro로 고정
                    model = genai.GenerativeModel("gemini-pro")
                    chat = model.start_chat(history=[])
                    st.session_state.chat_session = chat
                    
                    # 시스템 프롬프트 전송
                    msg = f"{SYSTEM_INSTRUCTION}\n\n(시스템: 지금 바로 사용자의 상황에 맞는 따뜻한 첫 인사를 건네세요.)"
                    res = st.session_state.chat_session.send_message(msg)
                    st.session_state.messages.append({"role": "model", "parts": [res.text]})
                except Exception as e:
                    st.error(f"❌ 연결 오류: {e}")
                    st.stop()

        for msg in st.session_state.messages:
            role = "assistant" if msg['role'] == 'model' else "user"
            with st.chat_message(role): st.markdown(msg['parts'][0])

        if prompt := st.chat_input("메시지 입력..."):
            st.session_state.messages.append({"role": "user", "parts": [prompt]})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                try:
                    res = st.session_state.chat_session.send_message(prompt)
                    st.markdown(res.text)
                    st.session_state.messages.append({"role": "model", "parts": [res.text]})
                    save_to_csv(st.session_state.user_contact, st.session_state.messages)
                except Exception as e: st.error(f"오류: {e}")

    # 3. 평가 화면
    elif st.session_state.step == "feedback":
        st.title("⭐ 서비스 평가")
        with st.form("fb_form"):
            st.write("오늘 큐레이션은 어떠셨나요?")
            score = st.slider("만족도 점수", 1, 5, 5)
            if st.form_submit_button("제출 및 종료"):
                save_to_csv(st.session_state.user_contact, st.session_state.messages, score)
                st.success("감사합니다! 다음에 또 이용해주세요.")
                st.session_state.clear()
                st.rerun()
