import os
from groq import Groq
import datetime
from moviepy import *
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.video.io.VideoFileClip import VideoFileClip

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
client = Groq(api_key=GROQ_API_KEY)


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
        print(transcription.words)
        return transcription.words

def add_subtitles(verbose_json, width, fontsize):
    text_clips = []

    for segment in verbose_json:
        text_clips.append(
            TextClip(text=segment["word"],
                     font_size=fontsize,
                     stroke_width=5, 
                     stroke_color="black", 
                     font="./Roboto-Condensed-Bold.otf",
                     color="white",
                     size=(width, None),
                     method="caption",
                     text_align="center",
                     margin=(30, 0)
                     )
            .with_start(segment["start"])
            .with_end(segment["end"])   
            .with_position("center")
        )
    return text_clips

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
            "content": "Translate this English text into arabic."
        },
        # Set a user message for the assistant to respond to.
        {
            "role": "user",
            "content": text,
        }
    ],
    max_completion_tokens=1024,
    top_p=1,
    )

    for chunk in completion:
        print(chunk.choices[0].delta.content or "", end="")


def convert_text_into_audio(text):
    completion = client.chat.completions.create(
        model="playai-tts-arabic",
        messages=text,
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=True,
        stop=None,
    )

    for chunk in completion:
        print(chunk.choices[0].delta.content or "", end="")


# Run the Process
video_file = "../input.mp4"
output_file = "output_with_subtitles.mp4"

# Loading the video as a VideoFileClip
original_clip = VideoFileClip(video_file)
width = original_clip.w
print(width)

mp3_file = "../output.mp3"
convert_mp4_to_mp3(video_file, mp3_file)
segments = transcribe_audio(mp3_file)
text_clip_list = add_subtitles(segments, width, fontsize=40)

# Create a CompositeVideoClip that we write to a file
final_clip = CompositeVideoClip([original_clip] + text_clip_list)

final_clip.write_videofile("final.mp4", codec="libx264")
print("Subtitled video saved as:", output_file)
