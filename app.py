import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
from datetime import datetime

# --- 1. 기본 설정 및 디자인 ---
st.set_page_config(page_title="Leisure DNA: Data Curator", layout="wide", page_icon="🧬")

st.markdown("""
    <style>
    .stApp { background-color: #F5F5F7; color: #1D1D1F; }
    h1 { color: #1D1D1F; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }
    .stButton>button { background-color: #0071e3; color: white; border-radius: 8px; }
    .stTextInput>div>div>input { border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Google Gemini API 설정 ---
# 에러 핸들링 강화
if "GOOGLE_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    except Exception as e:
        st.error(f"API 키 설정 오류: {e}")
else:
    st.error("🚨 API 키가 없습니다. 설정이 필요합니다.")
    st.stop()

# --- 3. 데이터 저장 함수 (CSV) ---
DATA_FILE = "user_data_log.csv"

def save_to_csv(user_info, chat_history, satisfaction=None):
    """사용자 정보와 대화 내용을 CSV에 저장"""
    # 대화 내용 전체를 하나의 텍스트로 합침
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
사용자 정보를 이미 전달받았습니다. 이제부터 즉시 대화를 통해 최적의 여가 활동을 추천하십시오.

[원칙]
1. 사용자의 입력된 정보(나이, 지역, 예산 등)를 바탕으로 맞춤형 대화를 시작하십시오.
2. 기계적인 질문을 나열하지 말고, 전문 상담가처럼 공감하며 대화하십시오.
3. 구글 맵 평점 4.5 이상의 실존 장소만 추천하십시오.
"""

# --- 5. 세션 상태 초기화 ---
if "step" not in st.session_state:
    st.session_state.step = "input_form" # 초기 상태: 정보 입력
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_info" not in st.session_state:
    st.session_state.user_info = {}

# --- 6. 화면 구성 ---

# [화면 1] 관리자 모드 (사이드바)
with st.sidebar:
    st.header("⚙️ Admin")
    admin_pw = st.text_input("관리자 비밀번호", type="password")
    if admin_pw == "1234": # 원하는 비번으로 변경 가능
        st.success("관리자 접속")
        if os.path.exists(DATA_FILE):
            st.write("📊 수집된 데이터:")
            df = pd.read_csv(DATA_FILE)
            st.dataframe(df)
            
            # 다운로드 버튼
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("데이터 다운로드 (CSV)", csv, "leisure_data.csv", "text/csv")
        else:
            st.info("아직 수집된 데이터가 없습니다.")

# [화면 2] 사용자 정보 입력 (필수)
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
            
        submitted = st.form_submit_button("큐레이션 시작하기")
        
        if submitted:
            if age_gender and location:
                # 정보 저장
                st.session_state.user_info = {
                    "age_gender": age_gender,
                    "location": location,
                    "companion": companion,
                    "budget": budget
                }
                st.session_state.step = "chat_mode" # 채팅 모드로 전환
                st.rerun()
            else:
                st.error("성별/연령대와 지역은 필수 입력 사항입니다.")

# [화면 3] 채팅 모드
elif st.session_state.step == "chat_mode":
    st.title("🏛️ Lifestyle Curator")
    
    # 모델 초기화 (최초 1회)
    if "chat_session" not in st.session_state:
        try:
            # gemini-1.5-flash 모델 사용 (가성비)
            model = genai.GenerativeModel("gemini-1.5-flash") 
            st.session_state.chat_session = model.start_chat(history=[])
            
            # 시스템 프롬프트 + 유저 정보 주입 (System Injection)
            info = st.session_state.user_info
            initial_prompt = f"""
            {SYSTEM_INSTRUCTION}
            
            [사용자 프로필]
            - 성별/나이: {info['age_gender']}
            - 지역: {info['location']}
            - 동반자: {info['companion']}
            - 예산: {info['budget']}
            
            위 정보를 바탕으로 첫 인사를 건네며 상담을 시작하세요.
            """
            response = st.session_state.chat_session.send_message(initial_prompt)
            st.session_state.messages.append({"role": "model", "parts": [response.text]})
            
        except Exception as e:
            st.error(f"AI 연결 실패: {e}")
            if "404" in str(e): # Flash 모델 없으면 Pro로 자동 전환 시도
                 st.warning("Flash 모델 연결 실패. 표준 모델로 전환합니다.")
                 model = genai.GenerativeModel("gemini-pro")
                 st.session_state.chat_session = model.start_chat(history=[])

    # 채팅 기록 표시
    for msg in st.session_state.messages:
        role = "assistant" if msg['role'] == 'model' else "user"
        with st.chat_message(role):
            st.markdown(msg['parts'][0])

    # 사용자 입력
    if prompt := st.chat_input("답변을 입력해주세요..."):
        st.session_state.messages.append({"role": "user", "parts": [prompt]})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "model", "parts": [response.text]})
                
                # 대화할 때마다 로그 업데이트 (실시간 저장)
                save_to_csv(st.session_state.user_info, st.session_state.messages)
                
            except Exception as e:
                st.error(f"오류 발생: {e}")

    # 상담 종료 버튼 (만족도 평가용)
    if st.button("상담 종료 및 저장"):
        st.session_state.step = "feedback"
        st.rerun()

# [화면 4] 만족도 평가
elif st.session_state.step == "feedback":
    st.title("⭐ 만족도 평가")
    score = st.slider("이번 큐레이션은 어떠셨나요?", 1, 5, 5)
    if st.button("제출하기"):
        save_to_csv(st.session_state.user_info, st.session_state.messages, satisfaction=score)
        st.success("소중한 의견 감사합니다. 초기 화면으로 돌아갑니다.")
        st.session_state.clear()
        st.rerun()
