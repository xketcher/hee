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

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio_path = temp_audio.name

    audio_buffer = b""

    try:
        while True:
            data = await websocket.receive_bytes()
            audio_buffer += data

            # ~3 seconds of 16kHz 16-bit mono PCM audio
            if len(audio_buffer) > 16000 * 2 * 3:
                with open(temp_audio_path, "wb") as f:
                    f.write(audio_buffer)

                try:
                    with sr.AudioFile(temp_audio_path) as source:
                        audio = recognizer.record(source)
                        english = recognizer.recognize_google(audio, language="en-US")
                        myanmar = GoogleTranslator(source='en', target='my').translate(english)
                        await websocket.send_text(myanmar)
                except sr.UnknownValueError:
                    await websocket.send_text("[Unrecognized speech]")
                except Exception as e:
                    await websocket.send_text(f"[Error: {str(e)}]")

                audio_buffer = b""

    except Exception as e:
        await websocket.send_text(f"[Connection closed: {str(e)}]")
    finally:
        os.remove(temp_audio_path)
        await websocket.close()
