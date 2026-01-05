import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
from datetime import datetime

# --- 1. 페이지 설정 (반드시 최상단) ---
st.set_page_config(page_title="Leisure DNA: Premium", layout="wide", page_icon="🧬")

# --- 2. 강력한 디자인 CSS (강제 적용) ---
st.markdown("""
    <style>
    /* 폰트 및 기본 설정 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    
    html, body, [class*="css"] { 
        font-family: 'Noto Sans KR', sans-serif !important; 
    }
    
    /* 배경색 변경 (적용 확인용) */
    .stApp { 
        background-color: #F0F2F5 !important; 
    }

    /* 헤더 디자인 */
    h1 { 
        color: #0E1A40 !important; 
        font-weight: 800 !important; 
        text-align: center; 
        padding: 20px 0;
        border-bottom: 2px solid #E5E5EA;
        margin-bottom: 30px;
    }

    /* 입력 폼 디자인 */
    .stForm, div[data-testid="stExpander"] {
        background-color: white !important;
        border-radius: 20px !important;
        padding: 30px !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05) !important;
        border: 1px solid #E5E5EA !important;
    }

    /* 버튼 디자인 (그라데이션) */
    div.stButton > button {
        background: linear-gradient(90deg, #0E1A40 0%, #1A237E 100%) !important;
        color: white !important;
        border: none !important;
        padding: 15px 30px !important;
        border-radius: 12px !important;
        font-size: 16px !important;
        font-weight: bold !important;
        width: 100%;
        transition: transform 0.2s;
    }
    div.stButton > button:hover {
        transform: scale(1.02);
    }
    
    /* 채팅 메시지 디자인 */
    .stChatMessage {
        background-color: transparent !important;
    }
    /* AI 메시지 (흰색) */
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #ffffff !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 4px 20px 20px 20px !important;
        padding: 20px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
    }
    /* 유저 메시지 (남색) */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #E3F2FD !important;
        border-radius: 20px 4px 20px 20px !important;
        padding: 20px !important;
        border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 보안 및 API 설정 ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("🚨 치명적 오류: API 키가 설정되지 않았습니다.")
        st.stop()
    ADMIN_ID = st.secrets.get("ADMIN_ID", "admin") 
    ADMIN_PW = st.secrets.get("ADMIN_PW", "0000")
except Exception as e:
    st.error(f"⚠️ 설정 로드 중 오류 발생: {str(e)}")
    st.stop()

# --- 4. 모델 자동 연결 (상세 에러 출력 모드) ---
def get_chat_model(system_instruction):
    # Pro -> Flash -> 1.0 순서로 시도
    model_candidates = ["gemini-pro", "gemini-1.5-flash", "gemini-1.0-pro"]
    last_error = ""
    
    for model_name in model_candidates:
        try:
            model = genai.GenerativeModel(model_name)
            chat = model.start_chat(history=[])
            return chat, model_name # 성공하면 즉시 반환
        except Exception as e:
            last_error = str(e)
            continue # 실패하면 다음 모델 시도
            
    # 모든 모델 실패 시 에러 내용 반환
    return None, last_error

# --- 5. 데이터 저장 함수 ---
DATA_FILE = "user_data_log.csv"

def save_to_csv(contact_info, chat_history, satisfaction=None):
    full_conversation = ""
    for msg in chat_history:
        role = "AI" if msg['role'] == 'model' else "User"
        full_conversation += f"[{role}] {msg['parts'][0]}\n"

    new_data = {
        "timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "contact_info": [contact_info],
        "full_conversation": [full_conversation],
        "satisfaction_score": [satisfaction if satisfaction else "N/A"]
    }
    df_new = pd.DataFrame(new_data)
    
    if not os.path.exists(DATA_FILE):
        df_new.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(DATA_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

# --- 6. 페르소나 ---
SYSTEM_INSTRUCTION = """
당신은 'AI 프리미엄 라이프스타일 큐레이터'입니다.
[대화 프로세스]
1. 오프닝: 상황에 맞는 따뜻한 인사 (정보 묻지 말 것).
2. 정보 수집: 대화 흐름 속에서 성별/연령, 지역, 동반자, 예산을 자연스럽게 파악.
3. 추천: 구글 맵 평점 4.5 이상 장소 추천.
"""

# --- 7. 상태 초기화 ---
if "step" not in st.session_state:
    st.session_state.step = "login"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_contact" not in st.session_state:
    st.session_state.user_contact = ""
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# --- 8. 사이드바 (메뉴 및 종료 버튼) ---
with st.sidebar:
    st.title("메뉴 (Menu)")
    
    # [수정됨] 상담 종료 버튼을 여기로 이동
    if st.session_state.step == "chat_mode":
        st.info("상담을 마치시겠습니까?")
        if st.button("상담 종료 및 평가하기 🏁"):
            st.session_state.step = "feedback"
            st.rerun()
            
    st.markdown("---")
    
    # 관리자 로그인
    with st.expander("관리자 접속 (Admin Only)"):
        input_id = st.text_input("ID", key="admin_id")
        input_pw = st.text_input("PW", type="password", key="admin_pw")
        if st.button("로그인"):
            if input_id == ADMIN_ID and input_pw == ADMIN_PW:
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("접속 거부")

    if st.session_state.is_admin:
        if st.button("로그아웃"):
            st.session_state.is_admin = False
            st.rerun()

# --- 9. 메인 로직 ---

# [A] 관리자 대시보드
if st.session_state.is_admin:
    st.title("🔐 Administrator Dashboard")
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("데이터 다운로드", csv, "leisure_data.csv", "text/csv")
    else:
        st.warning("데이터 없음")

# [B] 일반 사용자
else:
    # 1. 로그인
    if st.session_state.step == "login":
        st.markdown("<br>", unsafe_allow_html=True)
        st.title("🧩 Leisure DNA")
        
        with st.form("login_form"):
            st.markdown("### 👋 환영합니다")
            contact = st.text_input("연락처 (전화번호/이메일)", placeholder="필수 입력")
            agree = st.checkbox("개인정보 수집 및 이용에 동의합니다 (필수)")
            
            if st.form_submit_button("상담 시작하기"):
                if contact and agree:
                    st.session_state.user_contact = contact
                    st.session_state.step = "chat_mode"
                    st.rerun()
                else:
                    st.error("연락처 입력 및 동의가 필요합니다.")

    # 2. 채팅
    elif st.session_state.step == "chat_mode":
        st.title("🏛️ Lifestyle Curator")
        
        # 모델 연결 (에러나면 그대로 보여줌)
        if "chat_session" not in st.session_state:
            with st.spinner("AI 연결 중..."):
                chat_session, error_msg = get_chat_model(SYSTEM_INSTRUCTION)
                
                if chat_session:
                    st.session_state.chat_session = chat_session
                    try:
                        # 첫 인사
                        initial_msg = f"{SYSTEM_INSTRUCTION}\n\n(시스템: 따뜻한 첫 인사를 건네세요.)"
                        response = st.session_state.chat_session.send_message(initial_msg)
                        st.session_state.messages.append({"role": "model", "parts": [response.text]})
                    except Exception as e:
                        # 여기서 에러나면 바로 보여줌
                        st.error(f"❌ 첫 메시지 생성 실패: {str(e)}")
                else:
                    # 연결 자체가 안 되면 에러 보여줌
                    st.error(f"❌ AI 서버 연결 실패. 상세 에러: {error_msg}")
                    st.stop()

        # 메시지 표시
        for msg in st.session_state.messages:
            role = "assistant" if msg['role'] == 'model' else "user"
            with st.chat_message(role):
                st.markdown(msg['parts'][0])

        # 입력
        if prompt := st.chat_input("메시지 입력..."):
            st.session_state.messages.append({"role": "user", "parts": [prompt]})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    response = st.session_state.chat_session.send_message(prompt)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "model", "parts": [response.text]})
                    save_to_csv(st.session_state.user_contact, st.session_state.messages)
                except Exception as e:
                    # 채팅 중 에러도 숨기지 않고 보여줌
                    st.error(f"⚠️ 답변 생성 중 에러 발생: {str(e)}")

    # 3. 피드백
    elif st.session_state.step == "feedback":
        st.title("⭐ 만족도 평가")
        with st.form("feedback_form"):
            score = st.slider("만족도", 1, 5, 5)
            if st.form_submit_button("제출하기"):
                save_to_csv(st.session_state.user_contact, st.session_state.messages, score)
                st.success("감사합니다.")
                st.session_state.clear()
                st.rerun()
