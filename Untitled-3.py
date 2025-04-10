import io
from io import BytesIO
import tempfile
import os
import json
import speech_recognition as sr
from pydub import AudioSegment
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
import filetype


def is_wav_file(content: bytes) -> bool:
    """
    Check if the given content is a WAV file based on the header.
    WAV files start with the 'RIFF' marker and 'WAVE' format.
    """
    if content[:4] != b"RIFF" or content[8:12] != b"WAVE":
        return False
    return True


def convert_to_wav(file_name: str, audio_file_content: bytes) -> str:
    if not is_wav_file(audio_file_content):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix="." + file_name.split(".")[-1]) as temp_file:
                temp_file.write(audio_file_content)
                temp_file_path = temp_file.name

            audio = AudioSegment.from_file(temp_file_path)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav_file:
                audio.export(temp_wav_file.name, format="wav")
                wav_file_path = temp_wav_file.name
        finally:
            os.remove(temp_file_path)  # Ensure the original temp file is deleted
    else:
        wav_file_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        with open(wav_file_path, "wb") as wav_file:
            wav_file.write(audio_file_content)

    return wav_file_path


def transcribe_audio(file_binary: bytes, lang: str) -> dict:
    recognizer = sr.Recognizer()
    try:
        audio_file = io.BytesIO(file_binary)
        with sr.AudioFile(audio_file) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)  # Adjust for ambient noise
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language=lang)  # Set to Persian
            return {"ok": True, "transcript": text}
    except sr.UnknownValueError:
        raise HTTPException(406, "Your voice is not recognizable!")
    except sr.RequestError as e:
        raise HTTPException(406, f"{e}")


async def prepare_text_from_path(file_path: str, lang="eng"):
    audio_file_content = convert_kind_type_from_path(file_path)
    
    # user = await get_user(audio_file_content, 0.5)
    #
    # if not user or user.user_id != int(token.sub):
    #     raise HTTPException(401, msg)
    
    result = await run_in_threadpool(transcribe_audio, audio_file_content, lang)
    return result


def convert_kind_type_from_path(file_path: str):
    """
    This function will receive a file path, read the file and process it.
    """
    # Open the file from the provided path and read it as binary
    with open(file_path, "rb") as f:
        file_content = f.read()
    
    kind = filetype.guess(file_content)
    
    if kind is None or (kind.mime.split('/')[0] != 'audio' and kind.mime.split('/')[0] != "video"):
        raise HTTPException(status_code=400, detail="Your file is not valid. Please upload a valid audio or video file.")
    
    if kind.mime.split('/')[0] == "video":
        # Extract audio in memory if the file is a video
        audio = AudioSegment.from_file(BytesIO(file_content), format="webm")
        audio_output = BytesIO()
        audio.export(audio_output, format="wav")
        file_content = audio_output.read()

    return file_content


import asyncio

async def main():
    file_path = "sample.wav"  
    result = await prepare_text_from_path(file_path, lang="fa-IR")
    
    transcript = result.get("transcript", "")
    with open("output.txt", "w", encoding="utf-8") as file:
        file.write(transcript)
    
    print("output saved.")

if __name__ == "__main__":
    asyncio.run(main())