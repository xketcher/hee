import wave
from fastapi import FastAPI, WebSocket
import speech_recognition as sr
import tempfile
import os
from deep_translator import GoogleTranslator

app = FastAPI()

@app.websocket("/ws/speech")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    recognizer = sr.Recognizer()
    raw_audio = b""

    try:
        while True:
            data = await websocket.receive_bytes()
            raw_audio += data

            if len(raw_audio) >= 16000 * 2 * 3:  # ~3 sec buffer
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                    with wave.open(f.name, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(16000)
                        wf.writeframes(raw_audio)

                    temp_path = f.name

                try:
                    with sr.AudioFile(temp_path) as source:
                        audio = recognizer.record(source)
                        english_text = recognizer.recognize_google(audio, language="en-US")
                        myanmar_text = GoogleTranslator(source='en', target='my').translate(english_text)
                        await websocket.send_text(myanmar_text)
                except sr.UnknownValueError:
                    await websocket.send_text("[Unrecognized speech]")
                except Exception as e:
                    await websocket.send_text(f"[Error: {str(e)}]")

                os.remove(temp_path)
                raw_audio = b""

    except Exception as e:
        await websocket.send_text(f"[Connection closed: {str(e)}]")
        await websocket.close()
