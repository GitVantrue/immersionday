<<<<<<< HEAD
=======
#app.py
>>>>>>> 9584f1b (템플릿)
import streamlit as st
from datetime import datetime
import time
import logging
from aws_utils import AWSClients
from config import AWS_CONFIG
from styles import CUSTOM_CSS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def initialize_session_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'use_knowledge_base' not in st.session_state:
        st.session_state.use_knowledge_base = False
    if 'aws_clients' not in st.session_state:
        try:
            st.session_state.aws_clients = AWSClients(
                region_name=AWS_CONFIG['region_name'],
                embedding_model_id=AWS_CONFIG['embedding_model_id'],
                chat_model_id=AWS_CONFIG['chat_model_id'],
                inference_profile_arn=AWS_CONFIG['inference_profile_arn']
            )
        except Exception as e:
            logger.error(f"AWS 클라이언트 초기화 실패: {str(e)}")
            st.error("AWS 서비스 초기화에 실패했습니다. 설정을 확인해 주세요.")
            return False
    if 'user_input' not in st.session_state:
        st.session_state.user_input = ""
    return True



def main():
    st.set_page_config(
        page_title="Claude 3.5 Sonnet 챗봇",
        page_icon="🤖",
        layout="wide"
    )

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if not initialize_session_state():
        return

    st.markdown('<div class="main-header"><h1>🤖 SaltWare BedRock Hands-on</h1></div>', 
                unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### 🔧 설정")
        use_knowledge_base = st.checkbox("지식 베이스 사용", 
                                       value=st.session_state.use_knowledge_base)

        if use_knowledge_base != st.session_state.use_knowledge_base:
            st.session_state.use_knowledge_base = use_knowledge_base
            logger.info(f"지식 베이스 사용 설정 변경: {use_knowledge_base}")
            st.rerun()

        if st.button("💫 대화 기록 지우기"):
            st.session_state.messages = []
            st.session_state.user_input = ""
            st.rerun()

        st.markdown("### ℹ️ 정보")
        st.markdown("""
            - 지식 베이스 모드: S3에 저장된 데이터를 활용하여 답변
            - 일반 모드: Claude의 일반적인 지식을 활용하여 답변
        """)

    for message in st.session_state.messages:
        message_class = "user-message" if message["role"] == "user" else "assistant-message"
        st.markdown(f"""
            <div class="chat-message {message_class}">
                <div class="message-timestamp">{message["timestamp"]}</div>
                <div class="message-content">{message["content"]}</div>
            </div>
        """, unsafe_allow_html=True)

    user_input = st.text_area("메시지를 입력하세요:", value=st.session_state.user_input, key="input", height=100)

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("전송", use_container_width=True):
            if user_input.strip():
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # 사용자 메시지 추가
                st.session_state.messages.append({
                    "role": "user",
                    "content": user_input,
                    "timestamp": timestamp
                })

                # 시스템 메시지 준비
                messages = []

                try:
                    if st.session_state.use_knowledge_base:
                        # 지식 베이스 검색
                        context = st.session_state.aws_clients.search_knowledge_base(
                            user_input,
                            AWS_CONFIG['collection_endpoint']
                        )
                        if context and len(context) > 0:
                            knowledge_text = "\n\n".join([f"문서 {i+1}:\n{text}" for i, text in enumerate(context)])
                            system_prompt = f"""다음은 사용자의 질문과 관련된 문서 내용입니다:

{knowledge_text}

위 문서 내용을 기반으로 사용자의 질문에 답변해주세요. 문서에 관련 내용이 없다면 일반적인 지식을 활용해 답변해주세요.
답변 시 불필요한 인사말은 생략하고, 질문에 대한 답변을 직접적으로 제공해주세요."""
                            messages = [{"role": "system", "content": system_prompt}]
                        else:
                            messages = [{"role": "system", "content": "질문에 직접 답변하세요."}]
                    else:
                        messages = [{"role": "system", "content": "질문에 직접 답변하세요."}]

                    # 이전 대화 기록 추가 (최대 5개, 사용자와 어시스턴트 메시지 번갈아가며)
                    for msg in st.session_state.messages[-10:]:
                        if msg["role"] in ["user", "assistant"]:
                            messages.append({"role": msg["role"], "content": msg["content"]})

                    # Claude 호출
                    with st.spinner("답변을 생성하고 있습니다..."):
                        response = st.session_state.aws_clients.call_claude(
                            messages,
                            use_knowledge_base=st.session_state.use_knowledge_base,
                            collection_endpoint=AWS_CONFIG['collection_endpoint'] if st.session_state.use_knowledge_base else None
                        )

                    if response:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })

                    # 입력 필드 비우기
                    st.session_state.user_input = ""
                    st.rerun()

                except Exception as e:
                    logger.error(f"오류 발생: {str(e)}")
                    st.error(f"오류가 발생했습니다: {str(e)}")

    # 입력 필드 상태 업데이트
    st.session_state.user_input = user_input

if __name__ == "__main__":
    main()