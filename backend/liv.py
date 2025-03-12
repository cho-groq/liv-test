import os
from groq import Groq
import requests
import json
import io
import base64
from dotenv import load_dotenv
import datetime
from moviepy import *
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.video.io.VideoFileClip import VideoFileClip

load_dotenv()  

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def convert_mp4_to_mp3(mp4_filepath, mp3_file):
    """
    Converts an MP4 file to MP3.

    Args:
        mp4_filepath: Path to the input MP4 file.
        mp3_filepath: Path to save the output MP3 file.
    """
    video_clip = VideoFileClip(mp4_filepath)

    # Extract audio from video
    video_clip.audio.write_audiofile(mp3_file)
    print("now is an mp3")
    video_clip.close()

# Step 1: Transcribe Audio
def transcribe_audio(mp3_file):

# Open the audio file
    with open(mp3_file, "rb") as file:
        # Create a transcription of the audio file
        transcription = client.audio.transcriptions.create(
            file=(mp3_file, file.read()), # Required audio file
            model="whisper-large-v3-turbo", # Required model to use for transcription
            response_format="verbose_json",  # Optional
            language="en",  # Optional
            temperature=0.0  # Optional
        )
        # Print the transcription text
        print(transcription.segments)
        return transcription.segments

# takes english text into arabic
def translate(text):
    completion = client.chat.completions.create(
        model="mistral-saba-24b",
        messages=[
        # Set an optional system message. This sets the behavior of the
        # assistant and can be used to provide specific instructions for
        # how it should behave throughout the conversation.
        {
            "role": "system",
            "content": "Translate this English text into arabic. Only return the arabic response."
        },
        # Set a user message for the assistant to respond to.
        {
            "role": "user",
            "content": f"Translate this into arabic: {text}",
        }
    ],
    max_completion_tokens=1024,
    )

    print(completion.choices[0].message.content)
    return completion.choices[0].message.content 

# would iterate through each timestamp and only pass in 
def convert_text_into_audio(text, index):
    url = "https://api.groq.com/openai/v1/audio/speech"
    
    headers = {
        "Authorization": f"Bearer {os.environ.get("GROQ_API_KEY")}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "playai-tts-arabic",
        "input": text,
        "voice": "Nasser-PlayAI",  # Change as needed
        "response_format": "wav"  # Explicitly set response format to WAV
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(response)
        if response.status_code == 200:
            filename = f"output_{index}.wav"
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"Audio saved as {filename}")
            return
        else:
            print("here")
            return None
    except Exception as e:
        print("exception"+ e)
        return None


video_file = "../input.mp4"
mp3_file = "../output.mp3"
output_file = "output_with_subtitles.mp4"

# take in video file, remove audio and get mp3 from it
convert_mp4_to_mp3(video_file, mp3_file)

# with mp3, transcribe with whisper and get sentence timestamps
segments = transcribe_audio(mp3_file)

# loop through segments and translate into language then make tts call for each.
for index, segment in enumerate(segments):
    english_sentence = segment["text"]

    # translate
    arabic_translated = translate(english_sentence)

    # make audio. # can make the function async in the future so it's faster since they're all going to get saved in a folder
    convert_text_into_audio(arabic_translated, index)

    start = segment["start"]
    end = segment["end"]
    # audio has to be within the start + (audio length) < end 
    # if longer, re-make audio with faster speed.
    # if shorter (or exact time, but unlikely), then add a mute blank audio

array_of_audio = []


# you could do them async to make it faster
# for seg in segments:
#     array_of_audio.append()