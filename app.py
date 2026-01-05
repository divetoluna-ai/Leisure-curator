import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
from datetime import datetime

# --- 1. 페이지 설정 (반드시 최상단) ---
st.set_page_config(page_title="Leisure DNA: Premium", layout="wide", page_icon="🧬")

# --- 2. 프리미엄 디자인 CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .stApp { background-color: #F5F5F7; }
    h1 { color: #0E1A40; font-weight: 700; text-align: center; padding-bottom: 20px; border-bottom: 1px solid #E5E5EA; }
    .stChatFloatingInputContainer, .stForm, div[data-testid="stExpander"] {
        background-color: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #E5E5EA;
    }
    .stButton > button {
        background: linear-gradient(135deg, #0E1A40 0%, #2C3E50 100%); color: white; border-radius: 10px; padding: 12px 24px; border: none; font-weight: 600; width: 100%;
    }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(14, 26, 64, 0.3); }
    .stTextInput > div > div > input { border-radius: 10px; border: 1px solid #D1D1D6; padding: 10px; }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: white; border-radius: 0 15px 15px 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border: 1px solid #E5E5EA; padding: 15px; }
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #E8F1F8; border-radius: 15px 0 15px 15px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 보안 및 API 설정 ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("🚨 API 키 설정이 필요합니다.")
        st.stop()
    ADMIN_ID = st.secrets.get("ADMIN_ID", "admin") 
    ADMIN_PW = st.secrets.get("ADMIN_PW", "0000")
except Exception as e:
    st.error(f"설정 오류: {e}")
    st.stop()

# --- 4. 데이터 저장 함수 ---
DATA_FILE = "user_data_log.csv"

def save_to_csv(contact_info, chat_history, satisfaction=None):
    full_conversation = ""
    for msg in chat_history:
        role = "AI" if msg['role'] == 'model' else "User"
        full_conversation += f"[{role}] {msg['parts'][0]}\n"

    new_data = {
        "timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "contact_info": [contact_info], # 전화번호/이메일
        "full_conversation": [full_conversation],
        "satisfaction_score": [satisfaction if satisfaction else "N/A"]
    }
    df_new = pd.DataFrame(new_data)
    
    if not os.path.exists(DATA_FILE):
        df_new.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(DATA_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

# --- 5. 페르소나 (자연스러운 수집) ---
SYSTEM_INSTRUCTION = """
당신은 'AI 프리미엄 라이프스타일 큐레이터'입니다.
기계적인 설문조사가 아닌, **자연스러운 대화**를 통해 사용자의 취향을 파악하고 최적의 장소를 추천하십시오.

[대화 프로세스] - 반드시 순서대로 진행하며 한 번에 하나의 질문만 하십시오.
1. **오프닝:** 날씨, 시간대, 기분에 맞춘 따뜻한 인사로 시작 (정보를 바로 묻지 말 것).
2. **Phase 1 (기본):** 대화 흐름 속에서 자연스럽게 성별, 연령대, 거주/활동 지역을 물어보십시오.
3. **Phase 2 (취향):** 누구와 함께하는지, 어떤 분위기(힐링/액티비티)를 원하는지 물어보십시오.
4. **Phase 3 (예산):** 실례가 안 된다면 예산대는 어느 정도 생각하시는지 정중히 물어보십시오.
5. **Phase 4 (추천):** 모든 정보가 파악되면, 구글 맵 평점 4.5 이상의 실존 장소를 추천하십시오.

[주의사항]
- 사용자가 질문에 답하면 반드시 "아, 그렇군요", "좋은 선택이시네요"와 같이 공감한 후 다음 질문을 하십시오.
- 절대 리스트 형식으로 질문을 나열하지 마십시오. 친구와 대화하듯 하십시오.
"""

# --- 6. 상태 초기화 ---
if "step" not in st.session_state:
    st.session_state.step = "login" # 초기 상태: 로그인/동의
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_contact" not in st.session_state:
    st.session_state.user_contact = ""
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# --- 7. 사이드바 (관리자) ---
with st.sidebar:
    st.title("⚙️ SYSTEM")
    st.markdown("---")
    admin_mode = st.checkbox("관리자 모드 접속")
    if admin_mode:
        st.info("🔒 관리자 인증")
        input_id = st.text_input("Admin ID", key="admin_id")
        input_pw = st.text_input("Password", type="password", key="admin_pw")
        if st.button("LOGIN"):
            if input_id == ADMIN_ID and input_pw == ADMIN_PW:
                st.session_state.is_admin = True
                st.success("Access Granted")
                st.rerun()
            else:
                st.error("Access Denied")
    if st.session_state.is_admin:
        st.markdown("---")
        if st.button("LOGOUT"):
            st.session_state.is_admin = False
            st.rerun()

# --- 8. 메인 화면 로직 ---

# [모드 A] 관리자 대시보드
if st.session_state.is_admin:
    st.title("🔐 Administrator Dashboard")
    st.success("관리자 권한으로 접속 중입니다.")
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        st.write("### 📊 User Data Logs")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 데이터 다운로드 (CSV)", csv, "leisure_data.csv", "text/csv")
    else:
        st.warning("수집된 데이터가 없습니다.")

# [모드 B] 일반 사용자 화면
else:
    # 1. 로그인 및 동의 단계
    if st.session_state.step == "login":
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🧩 Leisure DNA")
        st.markdown("<h4 style='text-align: center; color: #555;'>당신만의 여가 큐레이션을 시작합니다.</h4>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.markdown("### 🔐 시작하기")
            contact = st.text_input("휴대폰 번호 또는 이메일", placeholder="010-1234-5678 or email@example.com")
            
            st.markdown("---")
            st.markdown("#### 개인정보 수집 및 이용 동의 (필수)")
            st.caption("1. 수집 목적: AI 맞춤형 여가 큐레이션 제공 및 상담 이력 관리")
            st.caption("2. 수집 항목: 연락처, 대화 내용")
            st.caption("3. 보유 기간: 서비스 종료 또는 사용자 파기 요청 시까지")
            agree = st.checkbox("위 내용을 확인하였으며, 개인정보 수집 및 이용에 동의합니다.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("Start Curation ✨"):
                if contact and agree:
                    st.session_state.user_contact = contact
                    st.session_state.step = "chat_mode"
                    st.rerun()
                elif not contact:
                    st.error("연락처를 입력해주세요.")
                elif not agree:
                    st.error("개인정보 수집에 동의해야 서비스를 이용할 수 있습니다.")

    # 2. 채팅 단계 (자연스러운 수집)
    elif st.session_state.step == "chat_mode":
        st.title("🏛️ Lifestyle Curator")
        st.caption("AI Curator is ready based on your agreement.")
        st.markdown("---")
        
        # 모델 초기화 (안정적인 gemini-pro 사용)
        if "chat_session" not in st.session_state:
            try:
                # 404 에러 방지를 위해 표준 모델 사용
                model = genai.GenerativeModel("gemini-pro") 
                st.session_state.chat_session = model.start_chat(history=[])
                
                # AI가 먼저 말을 걸도록 시스템 프롬프트 주입
                # gemini-pro는 system_instruction을 직접 지원 안 할 수 있어 첫 메시지로 컨텍스트 전달
                initial_context = f"{SYSTEM_INSTRUCTION}\n\n(시스템: 지금 바로 사용자의 상황에 맞는 따뜻한 첫 인사를 건네며 대화를 시작하세요.)"
                response = st.session_state.chat_session.send_message(initial_context)
                
                # 첫 인사 저장
                st.session_state.messages.append({"role": "model", "parts": [response.text]})
                
            except Exception as e:
                st.error(f"시스템 연결 오류: {e}")
                st.stop()

        # 채팅 기록 표시
        for msg in st.session_state.messages:
            role = "assistant" if msg['role'] == 'model' else "user"
            with st.chat_message(role):
                st.markdown(msg['parts'][0])

        # 사용자 입력
        if prompt := st.chat_input("메시지 입력..."):
            st.session_state.messages.append({"role": "user", "parts": [prompt]})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                # 로딩 효과 대신 깔끔하게 결과 출력
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "model", "parts": [response.text]})
                
                # 대화할 때마다 로그 업데이트 (연락처 정보 포함)
                save_to_csv(st.session_state.user_contact, st.session_state.messages)

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("상담 종료 및 평가하기 🏁"):
            st.session_state.step = "feedback"
            st.rerun()

    # 3. 피드백 단계
    elif st.session_state.step == "feedback":
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("⭐ Satisfaction Check")
        st.markdown("### 이번 큐레이션은 만족스러우셨나요?")
        
        with st.form("feedback_form"):
            score = st.slider("점수를 선택해주세요", 1, 5, 5)
            if st.form_submit_button("제출하기 (Submit)"):
                save_to_csv(st.session_state.user_contact, st.session_state.messages, score)
                st.success("감사합니다. 초기 화면으로 돌아갑니다.")
                st.session_state.clear()
                st.rerun()
