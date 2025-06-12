import streamlit as st
import openai
import os
from datetime import datetime
from gtts import gTTS
import base64
from pydub import AudioSegment
import io

# --- 함수 정의 ---
def STT(audio_segment, api_key):
    filename = 'input.mp3'
    audio_segment.export(filename, format="mp3")

    if os.path.getsize(filename) == 0:
        os.remove(filename)
        return ""

    with open(filename, "rb") as audio_file:
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
        return response.choices[0].message.content.strip()
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

def main():
    st.set_page_config(page_title="음성 비서 프로그램", layout="wide")
    st.header("음성 비서 프로그램")
    st.markdown("---")

    with st.expander("음성비서 프로그램에 관하여", expanded=True):
        st.write("""
        - STT: OpenAI Whisper 사용
        - GPT: OpenAI ChatGPT 사용
        - TTS: Google TTS 사용
        - 텍스트 또는 음성으로 질문 가능
        """)

    if "chat" not in st.session_state:
        st.session_state["chat"] = []

    if "OPENAI_API" not in st.session_state:
        st.session_state["OPENAI_API"] = ""

    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "system", "content": "You are a helpful assistant. Respond to all input in 25 words and answer in Korean."}
        ]

    if "check_reset" not in st.session_state:
        st.session_state["check_reset"] = False

    with st.sidebar:
        st.session_state["OPENAI_API"] = st.text_input("OpenAI API 키", type="password", placeholder="sk-...")
        st.markdown("---")
        model = st.radio("GPT 모델 선택", ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"], index=0)
        st.markdown("---")
        if st.button("대화 초기화"):
            st.session_state["chat"] = []
            st.session_state["messages"] = [
                {"role": "system", "content": "You are a helpful assistant. Respond to all input in 25 words and answer in Korean."}
            ]
            st.session_state["check_reset"] = True
            st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("질문하기")
        text_question = st.text_input("텍스트로 질문하기", placeholder="여기에 질문을 입력하세요.")
        text_submit = st.button("질문 전송")
        st.markdown("---")
        audio_file = st.file_uploader("음성 파일 업로드 (wav, mp3)", type=["wav", "mp3"])

    with col2:
        st.subheader("대화 내용")

    question = ""
    if st.session_state["check_reset"]:
        st.session_state["check_reset"] = False
    elif text_submit and text_question:
        question = text_question
    elif audio_file is not None:
        audio_segment = AudioSegment.from_file(audio_file)
        st.audio(audio_file)
        question = STT(audio_segment, st.session_state["OPENAI_API"])

    if question:
        if not st.session_state["OPENAI_API"]:
            st.error("먼저 사이드바에서 OpenAI API 키를 입력해주세요.")
        else:
            now = datetime.now().strftime("%H:%M")
            st.session_state["chat"].append(("user", now, question))
            st.session_state["messages"].append({"role": "user", "content": question})
            response = ask_gpt(st.session_state["messages"], model, st.session_state["OPENAI_API"])
            if response:
                st.session_state["messages"].append({"role": "assistant", "content": response})
                st.session_state["chat"].append(("bot", now, response))
                TTS(response)

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
            else:
                st.write(f'''
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <div style="background-color: lightgray; color: black; border-radius: 15px; padding: 10px;">
                            {message}
                        </div>
                        <div style="font-size:0.8rem; color:gray; margin-left: 5px;">{time}</div>
                    </div>''', unsafe_allow_html=True)
        st.write("")

if __name__ == "__main__":
    main()
    st.markdown("---")
    st.markdown("""
    <p style="text-align: center;">
        © 2024 Voice Assistant Program. All rights reserved.
    </p>
    """, unsafe_allow_html=True)
