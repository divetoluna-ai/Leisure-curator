import streamlit as st
import google.generativeai as genai
import time
from PIL import Image

# --- 1. 페이지 설정 (Premium Design) ---
st.set_page_config(page_title="Leisure DNA: Premium Curator", layout="wide", page_icon="🧬")

st.markdown("""
    <style>
    /* 전체 배경 및 폰트: 웜 그레이 & 딥 네이비 */
    .stApp { background-color: #F5F5F7; color: #1D1D1F; }
    
    /* 채팅창 스타일 */
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #E8E8ED; border: 1px solid #D2D2D7; }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: #ffffff; border: 1px solid #E5E5EA; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    
    /* 제목 및 링크 스타일 */
    h1 { color: #1D1D1F; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; letter-spacing: -0.5px; }
    a { color: #0071e3; text-decoration: none; font-weight: 600; }
    a:hover { text-decoration: underline; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Google Gemini API 설정 (보안 적용) ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception:
    st.error("⚠️ API 키가 설정되지 않았습니다. Streamlit 대시보드에서 Secrets를 설정해주세요.")

# --- 3. The Ultimate Protocol (시스템 프롬프트) ---
SYSTEM_INSTRUCTION = """
당신은 방대한 실데이터와 심리학 이론을 섭렵하고, 구글의 모든 기능(Maps, Music, Search)을 완벽하게 활용하는 **'AI 프리미엄 라이프스타일 큐레이터'**입니다.
기계적인 챗봇이 아닌, **전문 심리상담가 수준의 공감 능력**과 **유연한 대화 스킬**을 갖춘 **'궁극의 AI'**로서 행동하십시오.

### [핵심 운영 원칙]
1. **동적 라포 형성:** 기계적 인사 금지. 시간대/날씨/사용자 기분에 맞춰 매번 다른 따뜻한 인사로 시작.
2. **데이터 절대 우위:** '데이터셋' 용어 금지 -> "빅데이터 분석 결과", "트렌드 데이터" 표현 사용.
3. **구글 생태계 연동:**
   - Weather: 사용자 지역 날씨 반영.
   - Navigation: 이동 수단에 따른 Google 지도 길찾기 링크 제공.
   - Music: 분위기에 맞는 YouTube Music 링크 제공.
4. **핑퐁 대화:** 질문 나열 금지. 한 턴에 하나의 주제만 묻고, 답변에 깊이 공감 후 다음 단계로 진행.
5. **할루시네이션 제로:** 구글 지도 평점 4.5 이상의 **실존 업체**만 추천.

### [큐레이팅 프로세스]
반드시 아래 순서대로 대화를 진행하십시오. (사진이 업로드되면 사진 분석 결과를 대화에 녹여내십시오)
**Phase 0: 오프닝** (상황에 맞는 인사)
**Phase 1: 베이직 프로파일링** (성별/연령대 -> 지역)
**Phase 2: 날씨 및 환경 매칭** (실내/야외 선호)
**Phase 3: 이동성 및 접근성** (이동수단 & 출발지)
**Phase 4: 동반자 및 예산**
**Phase 5: 심리적 동기** (이완 vs 성취감)
**Phase 6: 더 리빌 (최종 결과)** - 마크다운으로 깔끔하게 출력, 구글 맵/유튜브 링크 포함.
"""

# --- 4. 사이드바 (이미지 업로드 & 설정) ---
with st.sidebar:
    st.header("📸 Vision Analysis")
    st.caption("공간 사진을 올리면 분위기를 분석해 큐레이션에 반영합니다.")
    uploaded_file = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])
    
    user_image = None
    if uploaded_file:
        user_image = Image.open(uploaded_file)
        st.image(user_image, caption="이미지 분석 준비 완료", use_container_width=True)
        st.success("AI가 이 사진을 참고합니다.")

    st.markdown("---")
    if st.button("대화 초기화 (Reset)"):
        st.session_state.messages = []
        st.session_state.chat_session = None
        st.rerun()

# --- 5. 세션 및 모델 관리 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_session" not in st.session_state:
    # Gemini 1.5 Pro 모델 사용 (고성능)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        system_instruction=SYSTEM_INSTRUCTION
    )
    st.session_state.chat_session = model.start_chat(history=[])
    
    # AI가 먼저 말을 걸도록 트리거
    response = st.session_state.chat_session.send_message("사용자가 접속했습니다. 오프닝 멘트를 시작하세요.")
    st.session_state.messages.append({"role": "assistant", "content": response.text})

# --- 6. 메인 채팅 인터페이스 ---
st.title("🏛️ Lifestyle Curator Pro")

# 대화 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("답변을 입력해주세요..."):
    # 사용자 메시지 표시
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # AI 응답 생성
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # 텍스트 + 이미지(있을 경우) 함께 전송
            inputs = [prompt]
            if user_image:
                inputs.append(user_image)
                inputs.append("(이 이미지는 사용자의 현재 공간 혹은 선호하는 분위기입니다. 큐레이션에 참고하세요.)")
            
            # Gemini에게 전송
            response = st.session_state.chat_session.send_message(inputs)
            full_response = response.text
            
            # 타이핑 효과
            display_text = ""
            for chunk in full_response.split():
                display_text += chunk + " "
                time.sleep(0.05)
                message_placeholder.markdown(display_text + "▌")
            message_placeholder.markdown(full_response)
            
        except Exception as e:
            error_msg = "죄송합니다. 잠시 연결이 불안정합니다. 다시 말씀해 주시겠습니까?"
            message_placeholder.markdown(error_msg)
            full_response = error_msg

    st.session_state.messages.append({"role": "assistant", "content": full_response})