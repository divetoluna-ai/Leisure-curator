import streamlit as st
import google.generativeai as genai
import time
from PIL import Image

# --- 1. 프리미엄 디자인 설정 (강제 적용) ---
st.set_page_config(page_title="Leisure DNA: Premium Curator", layout="wide", page_icon="🧬")

# CSS로 디자인 강제 주입
st.markdown("""
    <style>
    /* 전체 배경: 웜 그레이 */
    .stApp { background-color: #F5F5F7; }
    
    /* 헤더 스타일: 딥 네이비 */
    h1 { 
        color: #1D1D1F !important; 
        font-family: 'Helvetica Neue', sans-serif; 
        font-weight: 800; 
        letter-spacing: -1px;
        padding-bottom: 20px;
        border-bottom: 2px solid #E5E5EA;
    }
    
    /* 채팅창 디자인 개선 */
    .stChatMessage { 
        border-radius: 20px !important; 
        padding: 15px !important; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    /* AI 메시지 배경 (흰색 + 그림자) */
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #ffffff !important; 
        border: 1px solid #E5E5EA;
    }
    /* 사용자 메시지 배경 (연한 네이비) */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #E8F0FE !important; 
        border: none;
        color: #1A73E8;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Google Gemini API 설정 (디버깅 모드) ---
# Secrets에서 키를 가져오되, 없으면 에러를 띄움
if "GOOGLE_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    except Exception as e:
        st.error(f"⚠️ API 키 설정 오류: {e}")
else:
    st.error("🚨 치명적 오류: Streamlit Secrets에 'GOOGLE_API_KEY'가 없습니다.")
    st.stop() # 키가 없으면 여기서 멈춤

# --- 3. 페르소나 (사용자 정보 수집 로직) ---
SYSTEM_INSTRUCTION = """
당신은 'AI 프리미엄 라이프스타일 큐레이터'입니다.
절대로 한 번에 추천 결과를 주지 마십시오. 반드시 사용자와 대화하며 정보를 수집해야 합니다.

[대화 원칙]
1. 첫 인사는 사용자의 상황(시간, 날씨 등)에 맞춰 따뜻하게 건네십시오.
2. 질문은 한 번에 하나만 하십시오.
3. 순서대로 정보를 수집하십시오: 성별/연령 -> 지역 -> 이동수단 -> 동반자 -> 예산 -> 선호 스타일.
4. 사용자의 답변에 공감한 뒤 다음 질문을 하십시오.

지금 당장 첫 인사를 건네며 대화를 시작하십시오.
"""

# --- 4. 세션 초기화 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# 모델 초기화 (에러 확인용)
if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", # 속도가 빠른 Flash 모델 사용
            system_instruction=SYSTEM_INSTRUCTION
        )
        st.session_state.chat_session = model.start_chat(history=[])
        
        # 강제로 첫 인사 생성 시도
        response = st.session_state.chat_session.send_message("첫 인사를 시작하세요.")
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        
    except Exception as e:
        # 여기가 핵심입니다. 에러가 나면 화면에 빨갛게 표시합니다.
        st.error(f"❌ AI 연결 실패 (상세 에러): {str(e)}")
        st.warning("팁: API Key가 올바른지, Google Cloud 결제 설정이 필요한지 확인하세요.")

# --- 5. UI 구성 ---
st.title("🏛️ Lifestyle Curator")
st.caption("공간 사진을 올리거나, 대화를 통해 당신만의 휴식을 설계해 드립니다.")

# 사이드바 (사진 업로드)
with st.sidebar:
    st.header("📸 Space Analysis")
    uploaded_file = st.file_uploader("공간 사진 분석", type=["jpg", "png"])
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
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            # 이미지 있으면 같이 전송
            if user_image:
                response = st.session_state.chat_session.send_message([prompt, user_image])
            else:
                response = st.session_state.chat_session.send_message(prompt)
                
            full_response = response.text
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"대화 중 오류 발생: {str(e)}")
