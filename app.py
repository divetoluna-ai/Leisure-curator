import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
from datetime import datetime

# --- 1. 기본 설정 ---
st.set_page_config(page_title="Leisure DNA", layout="wide", page_icon="🧬")

# 디자인 적용
st.markdown("""
    <style>
    .stApp { background-color: #F5F5F7; color: #1D1D1F; }
    h1 { color: #1D1D1F; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }
    .stButton>button { background-color: #0071e3; color: white; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 보안 및 API 설정 ---
# API 키와 관리자 계정 정보를 Secrets에서 가져옵니다.
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("🚨 API 키 설정이 필요합니다.")
        st.stop()
        
    # 관리자 정보 로드 (없으면 기본값 경고)
    ADMIN_ID = st.secrets.get("ADMIN_ID", "admin") 
    ADMIN_PW = st.secrets.get("ADMIN_PW", "0000")
    
except Exception as e:
    st.error(f"설정 오류: {e}")
    st.stop()

# --- 3. 데이터 저장 함수 ---
DATA_FILE = "user_data_log.csv"

def save_to_csv(user_info, chat_history, satisfaction=None):
    full_conversation = ""
    for msg in chat_history:
        role = "AI" if msg['role'] == 'model' else "User"
        full_conversation += f"[{role}] {msg['parts'][0]}\n"

    new_data = {
        "timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "age_gender": [user_info.get("age_gender")],
        "location": [user_info.get("location")],
        "budget": [user_info.get("budget")],
        "companion": [user_info.get("companion")],
        "full_conversation": [full_conversation],
        "satisfaction_score": [satisfaction if satisfaction else "N/A"]
    }
    df_new = pd.DataFrame(new_data)
    
    if not os.path.exists(DATA_FILE):
        df_new.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(DATA_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

# --- 4. 페르소나 설정 ---
SYSTEM_INSTRUCTION = """
당신은 'AI 프리미엄 라이프스타일 큐레이터'입니다.
[원칙]
1. 사용자의 입력 정보(나이, 지역, 예산)를 바탕으로 맞춤형 대화를 시작하십시오.
2. 기계적인 질문 나열 금지. 전문 상담가처럼 공감하며 하나씩 대화하십시오.
3. 구글 맵 평점 4.5 이상의 실존 장소만 추천하십시오.
"""

# --- 5. 상태 초기화 ---
if "step" not in st.session_state:
    st.session_state.step = "input_form"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_info" not in st.session_state:
    st.session_state.user_info = {}
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# --- 6. 사이드바 (관리자 로그인) ---
with st.sidebar:
    st.header("🔧 Settings")
    
    # 관리자 모드 토글 (체크해야 로그인 창이 뜸)
    admin_mode = st.checkbox("관리자 모드 접속")
    
    if admin_mode:
        st.subheader("Admin Login")
        input_id = st.text_input("아이디", key="admin_id_input")
        input_pw = st.text_input("비밀번호", type="password", key="admin_pw_input")
        
        if st.button("로그인"):
            if input_id == ADMIN_ID and input_pw == ADMIN_PW:
                st.session_state.is_admin = True
                st.success("접속 성공!")
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 틀렸습니다.")
    
    # 로그아웃 버튼
    if st.session_state.is_admin:
        if st.button("로그아웃"):
            st.session_state.is_admin = False
            st.rerun()

# --- 7. 메인 화면 로직 ---

# [모드 A] 관리자 대시보드 (로그인 성공 시에만 보임)
if st.session_state.is_admin:
    st.title("🔐 관리자 전용 대시보드")
    st.info(f"관리자 '{ADMIN_ID}' 계정으로 접속 중입니다.")
    
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        st.write("### 📊 수집된 사용자 데이터")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("데이터 다운로드 (CSV)", csv, "leisure_data.csv", "text/csv")
    else:
        st.warning("아직 수집된 데이터가 없습니다.")

# [모드 B] 일반 사용자 화면 (정보 입력 -> 채팅)
else:
    # 1. 정보 입력 단계
    if st.session_state.step == "input_form":
        st.title("🧩 Leisure DNA: 시작하기")
        st.write("맞춤형 큐레이션을 위해 기본 정보를 입력해 주세요.")
        
        with st.form("user_info_form"):
            col1, col2 = st.columns(2)
            with col1:
                age_gender = st.text_input("성별 및 연령대", placeholder="예: 30대 남성")
                location = st.text_input("거주/활동 지역", placeholder="예: 서울 마포구")
            with col2:
                companion = st.text_input("함께하는 사람", placeholder="예: 혼자, 연인, 친구")
                budget = st.selectbox("인당 예산", ["3만원 이하", "3~7만원", "7~15만원", "15만원 이상", "상관없음"])
                
            if st.form_submit_button("큐레이션 시작하기"):
                if age_gender and location:
                    st.session_state.user_info = {"age_gender": age_gender, "location": location, "companion": companion, "budget": budget}
                    st.session_state.step = "chat_mode"
                    st.rerun()
                else:
                    st.error("성별/연령대와 지역은 필수입니다.")

    # 2. 채팅 단계
    elif st.session_state.step == "chat_mode":
        st.title("🏛️ Lifestyle Curator")
        
        if "chat_session" not in st.session_state:
            try:
                # [수정] 표준 모델 gemini-pro 사용 (안정성 최우선)
                model = genai.GenerativeModel("gemini-pro") 
                st.session_state.chat_session = model.start_chat(history=[])
                
                # 시스템 프롬프트 주입
                info = st.session_state.user_info
                initial_prompt = f"{SYSTEM_INSTRUCTION}\n[사용자 정보] {info['age_gender']}, {info['location']}, {info['budget']} 예산, {info['companion']} 동반."
                
                response = st.session_state.chat_session.send_message(initial_prompt)
                st.session_state.messages.append({"role": "model", "parts": [response.text]})
                
            except Exception as e:
                st.error(f"AI 연결 오류: {e}")
                st.stop()

        for msg in st.session_state.messages:
            role = "assistant" if msg['role'] == 'model' else "user"
            with st.chat_message(role):
                st.markdown(msg['parts'][0])

        if prompt := st.chat_input("메시지 입력..."):
            st.session_state.messages.append({"role": "user", "parts": [prompt]})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "model", "parts": [response.text]})
                save_to_csv(st.session_state.user_info, st.session_state.messages)

        if st.button("상담 종료"):
            st.session_state.step = "feedback"
            st.rerun()

    # 3. 피드백 단계
    elif st.session_state.step == "feedback":
        st.title("⭐ 만족도 평가")
        score = st.slider("만족도", 1, 5, 5)
        if st.button("제출"):
            save_to_csv(st.session_state.user_info, st.session_state.messages, score)
            st.success("감사합니다.")
            st.session_state.clear()
            st.rerun()
