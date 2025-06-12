import streamlit as st
from audiorecorder import audiorecorder
import openai
import os
from datetime import datetime
from gtts import gTTS
import base64
from pydub import AudioSegment
import io

# --- 함수 정의 (변경 없음) ---
def STT(audio, api_key):
    filename = 'input.mp3'
    audio.export(filename, format="mp3")
    
    # 파일 크기 확인 (0바이트 파일 오류 방지)
    if os.path.getsize(filename) == 0:
        os.remove(filename)
        return ""
        
    audio_file = open(filename, "rb")
    client = openai.OpenAI(api_key=api_key)
    try:
        response = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
        )
        os.remove(filename)
        return response.text
    except Exception as e:
        st.error(f"STT API 호출 중 오류가 발생했습니다: {e}")
        os.remove(filename)
        return ""


def ask_gpt(prompt, model, apikey):
    client = openai.OpenAI(api_key=apikey)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=prompt
        )
        gptResponse = response.choices[0].message.content.strip()
        return gptResponse
    except Exception as e:
        st.error(f"OpenAI API 호출 중 오류가 발생했습니다: {e}")
        return ""

def TTS(response):
    filename = "output.mp3"
    try:
        tts = gTTS(text=response, lang='ko')
        tts.save(filename)
        
        with open(filename, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
            st.markdown(md, unsafe_allow_html=True)
        os.remove(filename)
    except Exception as e:
        st.error(f"TTS 변환 중 오류가 발생했습니다: {e}")
        if os.path.exists(filename):
            os.remove(filename)

## 메인 함수
def main():
    # 기본 설정
    st.set_page_config(
        page_title="음성 비서 프로그램",
        layout="wide"
    )
    # 제목
    st.header("음성 비서 프로그램")
    # 구분선
    st.markdown("---")
    # 기본 설명
    with st.expander("음성비서 프로그램에 관하여", expanded=True):
        st.write(
            """
            - 음성비서 프로그램의 UI는 스트림릿을 활용하여 만들었습니다.
            - STT(speech-to-text)는 OpenAI의 Whisper AI모델을 사용합니다.
            - 답변은 OpenAI의 GPT 모델을 사용합니다.
            - TTS(text-to-speech)는 구글의 Google Translate TTS를 활용하였습니다.
            - **음성 녹음 또는 텍스트 입력으로 질문할 수 있습니다.**
            """
        )
        st.markdown("") 
    
    # --- Session State 초기화 (개선) ---
    if "chat" not in st.session_state:
        st.session_state["chat"] = []
    
    if "OPENAI_API" not in st.session_state:
        st.session_state["OPENAI_API"] = ""
    
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "system", "content": "You are a helpful assistant. Respond to all input in 25 words and answer in Korean."}
        ]
    
    # ## << 수정된 부분: check_reset 상태가 없을 경우 False로 초기화
    if "check_reset" not in st.session_state:
        st.session_state["check_reset"] = False

    # 사이드바 생성
    with st.sidebar:
        # OpenAI API 키 입력
        st.session_state["OPENAI_API"] = st.text_input(
            "OpenAI API 키",
            type="password",
            placeholder="sk-...",
        )
        
        st.markdown("---")
        
        # GPT 모델 선택
        model = st.radio(
            label="GPT 모델 선택",
            options=["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"], # ## << 수정된 부분: 최신 모델명으로 변경
            index=0,
        )
        
        st.markdown("---")

        # 초기화 버튼
        if st.button("대화 초기화"):
            st.session_state["chat"] = []
            st.session_state["messages"] = [
                {"role": "system", "content": "You are a helpful assistant. Respond to all input in 25 words and answer in Korean."}
            ]
            st.session_state["check_reset"] = True
            st.rerun() # ## << 추가된 부분: 상태를 즉시 반영하기 위해 새로고침

    # --- 질문과 답변 표시 영역 ---
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("질문하기")

        text_question = st.text_input("텍스트로 질문하기", placeholder="여기에 질문을 입력하세요.")
        text_submit = st.button("질문 전송")

        st.markdown("---")

        # 음성 녹음
        audio = audiorecorder("클릭하여 녹음 시작", "녹음 중...")

    with col2:
        st.subheader("대화 내용")

    # --- 로직 처리 (음성 또는 텍스트 입력) ---
    question = ""
    # ## << 수정된 부분: 초기화 버튼 클릭 후에는 입력 처리를 건너뜀
    if st.session_state["check_reset"]:
        st.session_state["check_reset"] = False
    
    # 텍스트 입력 처리
    elif text_submit and text_question:
        question = text_question
    
    # 음성 입력 처리
    elif len(audio) > 0:
        # numpy.ndarray → BytesIO → AudioSegment 변환
        audio_bytes = audio.tobytes()
        audio_segment = AudioSegment.from_raw(io.BytesIO(audio_bytes), sample_width=2, frame_rate=44100, channels=1)

        # 스트림릿에서 재생
        st.audio(audio_segment.export(format="mp3").read())

        # STT 호출
        question = STT(audio_segment, st.session_state["OPENAI_API"])

    # ## << 수정된 부분: 공통 로직 처리
    if question:
        # API 키가 있는지 확인
        if not st.session_state["OPENAI_API"]:
            st.error("먼저 사이드바에서 OpenAI API 키를 입력해주세요.")
        else:
            now = datetime.now().strftime("%H:%M")
            # 사용자 질문 저장
            st.session_state["chat"].append(("user", now, question))
            st.session_state["messages"].append({"role": "user", "content": question})

            # GPT 답변 요청
            response = ask_gpt(st.session_state["messages"], model, st.session_state["OPENAI_API"])
            
            if response:
                # GPT 답변 저장
                # ## << 수정된 부분: role을 'assistant'로 정확히 지정
                st.session_state["messages"].append({"role": "assistant", "content": response})
                # ## << 수정된 부분: 시간 정보를 포함하여 chat에 저장
                st.session_state["chat"].append(("bot", now, response))

                # TTS 실행
                TTS(response)

    # --- 대화 내용 표시 ---
    with col2:
        for sender, time, message in st.session_state["chat"]:
            if sender == "user":
                st.write(f'''
                    <div style="display: flex; align-items: center; justify-content: flex-end; margin-bottom: 10px;">
                        <div style="font-size:0.8rem; color:gray; margin-right: 5px;">{time}</div>
                        <div style="background-color: #007AFF; color: white; padding: 10px; border-radius: 15px;">
                            {message}
                        </div>
                    </div>''', unsafe_allow_html=True)
            else: # sender == "bot"
                st.write(f'''
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <div style="background-color: lightgray; color: black; border-radius: 15px; padding: 10px;">
                            {message}
                        </div>
                        <div style="font-size:0.8rem; color:gray; margin-left: 5px;">{time}</div>
                    </div>''', unsafe_allow_html=True)
        st.write("") # 여백

if __name__ == "__main__":
    main()
    
    # 페이지 하단에 구분선
    st.markdown("---")
    
    # 페이지 하단에 저작권 표시
    st.markdown(
        """
        <p style="text-align: center;">
            © 2024 Voice Assistant Program. All rights reserved.
        </p>
        """,
        unsafe_allow_html=True
    )
