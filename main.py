import wave
import asyncio
import tempfile
import os
import traceback
from fastapi import FastAPI, WebSocket
import speech_recognition as sr
from deep_translator import GoogleTranslator

app = FastAPI()

@app.websocket("/ws/speech")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    recognizer = sr.Recognizer()
    raw_audio = b""

    try:
        while True:
            # Receive audio data from the WebSocket
            data = await websocket.receive_bytes()
            raw_audio += data

            # Process audio when 1 second of audio has been collected (~16000 samples)
            if len(raw_audio) >= 16000 * 2 * 1:  # ~1 second of audio
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                    # Write proper WAV file header + raw PCM data
                    with wave.open(f, 'wb') as wf:
                        wf.setnchannels(1)              # mono
                        wf.setsampwidth(2)              # 16-bit
                        wf.setframerate(16000)          # 16kHz
                        wf.writeframes(raw_audio)
                    temp_path = f.name

                try:
                    # Recognize speech from the temporary WAV file
                    with sr.AudioFile(temp_path) as source:
                        audio = recognizer.record(source)
                        english = recognizer.recognize_google(audio, language="en-US")
                        
                        # Translate the English text to Myanmar
                        myanmar = GoogleTranslator(source='en', target='my').translate(english)
                        await websocket.send_text(myanmar)
                except sr.UnknownValueError:
                    await websocket.send_text("[Unrecognized speech]")
                except Exception as e:
                    await websocket.send_text(f"[Error in speech recognition: {str(e)}]")
                finally:
                    # Clean up temporary file
                    os.remove(temp_path)
                raw_audio = b""  # Reset the raw_audio buffer

    except Exception as e:
        # Print and log the full error traceback for debugging
        print(f"[Connection closed: {str(e)}]")
        traceback.print_exc()
        await websocket.send_text(f"[Connection closed: {str(e)}]")
        await websocket.close()
