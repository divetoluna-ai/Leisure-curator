import streamlit as st
import google.generativeai as genai
import time
from PIL import Image

# --- 1. 페이지 및 디자인 설정 ---
st.set_page_config(page_title="Leisure DNA: Premium Curator", layout="wide", page_icon="🧬")

st.markdown("""
    <style>
    /* 전체 배경: 웜 그레이 */
    .stApp { background-color: #F5F5F7; }
    
    /* 헤더 스타일: 딥 네이비 */
    h1 { 
        color: #1D1D1F; 
        font-family: 'Helvetica Neue', sans-serif; 
        font-weight: 800; 
        letter-spacing: -1px;
        padding-bottom: 20px;
        border-bottom: 2px solid #E5E5EA;
    }
    
    /* 채팅창 디자인 개선 */
    .stChatMessage { 
        border-radius: 20px; 
        padding: 15px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #ffffff; 
        border: 1px solid #E5E5EA;
    }
    div[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #E8F0FE; 
        border: none;
        color: #1A73E8;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Google Gemini API 설정 ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("🚨 API 키가 없습니다. Streamlit Secrets 설정을 확인해주세요.")
        st.stop()
except Exception as e:
    st.error(f"⚠️ API 키 설정 중 오류 발생: {e}")
    st.stop()

# --- 3. 페르소나 (시스템 프롬프트) ---
SYSTEM_INSTRUCTION = """
당신은 'AI 프리미엄 라이프스타일 큐레이터'입니다.
기계적인 챗봇이 아닌, **전문 심리상담가 수준의 공감 능력**과 **유연한 대화 스킬**을 갖추십시오.

[대화 원칙]
1. 첫 인사는 사용자의 상황(시간, 날씨 등)에 맞춰 따뜻하게 건네십시오. ("안녕하세요" 금지 -> "햇살이 좋은 오후네요" 등)
2. 질문은 한 번에 하나만 하십시오. (정보 수집 순서: 기분/상태 -> 동반자 -> 스타일 -> 예산)
3. 사용자의 답변에 깊이 공감한 뒤 다음 질문을 하십시오.
4. 구글 맵 평점 4.5 이상의 실존 장소만 추천하십시오.

지금 당장 첫 인사를 건네며 대화를 시작하십시오.
"""

# --- 4. 세션 초기화 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 5. 모델 초기화 (에러 방지 로직 포함) ---
if "chat_session" not in st.session_state:
    try:
        # 모델을 가장 안정적인 'gemini-1.5-flash'로 설정
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction=SYSTEM_INSTRUCTION
        )
        st.session_state.chat_session = model.start_chat(history=[])
        
        # 첫 인사 생성
        response = st.session_state.chat_session.send_message("첫 인사를 시작하세요.")
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        
    except Exception as e:
        st.error(f"❌ AI 연결 실패: {e}")
        st.info("💡 팁: API Key가 올바른지 확인하거나, 잠시 후 다시 시도해보세요.")

# --- 6. UI 구성 ---
st.title("🏛️ Lifestyle Curator")
st.caption("공간 사진을 올리거나, 대화를 통해 당신만의 휴식을 설계해 드립니다.")

# 사이드바 (사진 업로드)
with st.sidebar:
    st.header("📸 Space Analysis")
    uploaded_file = st.file_uploader("공간 사진 분석", type=["jpg", "png", "jpeg"])
    user_image = None
    if uploaded_file:
        user_image = Image.open(uploaded_file)
        st.image(user_image, caption="이미지 로드됨", use_container_width=True)

# 대화 내용 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 입력창
if prompt := st.chat_input("대화를 입력하세요..."):
    # 사용자 메시지 저장 및 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI 응답 생성
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        try:
            # 이미지 있으면 같이 전송
            if user_image:
                response = st.session_state.chat_session.send_message([prompt, user_image])
            else:
                response = st.session_state.chat_session.send_message(prompt)
                
            # 타이핑 효과
            full_response = response.text
            for chunk in full_response.split():
                display_text = full_response[:full_response.find(chunk)+len(chunk)]
                message_placeholder.markdown(full_response + "▌") 
                time.sleep(0.02)
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"대화 중 오류 발생: {str(e)}")
            st.session_state.messages.append({"role": "assistant", "content": " 죄송합니다. 잠시 오류가 발생했습니다."})
