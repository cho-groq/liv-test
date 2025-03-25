import os
from groq import Groq
import requests
import json
import io
import base64
from dotenv import load_dotenv
import datetime
import srt

load_dotenv()  

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


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


video_file = "../input.mp4"
mp3_file = "../output.mp3"
output_file = "output_with_subtitles.mp4"

# take in video file, remove audio and get mp3 from it
convert_mp4_to_mp3(video_file, mp3_file)

# with mp3, transcribe with whisper and get sentence timestamps
segments = transcribe_audio(mp3_file)

og_subs = []
translated_subs = []
# loop through segments and translate into language then make tts call for each. also make a srt file.
for index, segment in enumerate(segments):
    english_sentence = segment["text"]

    # translate
    arabic_translated = translate(english_sentence)

    # make audio. # can make the function async in the future so it's faster since they're all going to get saved in a folder
    convert_text_into_audio(arabic_translated, index)

    start = datetime.timedelta(seconds=segment["start"])
    end = datetime.timedelta(seconds=segment["end"])
    og_subs.append(srt.Subtitle(index=segment["id"], start=start, end=end, content=segment["text"]))
    translated_subs.append(srt.Subtitle(index=segment["id"], start=start, end=end, content=arabic_translated))
    print(start, end, "\n")

# Make an (translated).srt file from the whisper time stamps
srt_file1 = "../subtitles.srt"
srt_file2 = "../translated_subtitles.srt"
with open(srt_file1, "w", encoding="utf-8") as f:
    f.write(srt.compose(og_subs))

with open(srt_file2, "w", encoding="utf-8") as f:
    f.write(srt.compose(translated_subs))

def adjust_audio_speed(audio, max_duration_ms, speed_factor=1.01):
    """Increase speed by speed_factor until it fits within max_duration_ms."""
    while len(audio) > max_duration_ms:
        print("length of audio", len(audio))
        audio = speedup(audio, playback_speed=speed_factor)
    return audio

# once all audio are complete, merge them together.
def process_audio_segments(segments, output_filename="final_output.wav"):
    final_audio = AudioSegment.silent(duration=1)  # Start with small duration
    
    for index, segment in enumerate(segments):
        start_ms = int(float(segment["start"]) * 1000)  # Convert seconds to milliseconds
        end_ms = int(float(segment["end"]) * 1000)
        print(f"Segment {index}: Start: {start_ms} ms, End: {end_ms} ms")
        max_duration_ms = end_ms - start_ms  # Allowed duration

        # Load corresponding audio file
        file_name = f"output_{index}.wav"
        if not os.path.exists(file_name):
            print(f"File {file_name} not found, skipping...")
            continue
        
        audio = AudioSegment.from_wav(file_name)

        # # Adjust speed if too long
        if len(audio) > max_duration_ms:
            audio = adjust_audio_speed(audio, max_duration_ms)
        
        # Append the audio segment to final_audio
        if len(final_audio) < start_ms:
            final_audio += AudioSegment.silent(duration=start_ms - len(final_audio))  # Add silence before the segment if needed
        
        print(f"Final audio length before appending: {len(final_audio)} ms")
        final_audio += audio  # Append the audio

        # Append silence after the audio if the segment is too short
        remaining_duration_ms = max_duration_ms - len(audio)  # Calculate how much silence is needed
        if remaining_duration_ms > 0:
            silence = AudioSegment.silent(duration=remaining_duration_ms)
            final_audio += silence  # Append silence after the audio if the segment is too short

        print(f"Final audio length before overlay: {len(final_audio)} ms")
        print(f"Segment length: {len(audio)} ms")
        # Overlay the adjusted audio at the correct position
        final_audio = final_audio.overlay(audio, position=start_ms)

    # Export the final merged audio
    final_audio.export(output_filename, format="wav")
    print(f"Final audio saved as {output_filename}")

process_audio_segments(segments)


def replace_audio(mp4_file, wav_file, output_file="output_video.mp4"):
    # Load the video file (without audio)
    video = VideoFileClip(mp4_file).without_audio()

    # Load the new audio file
    new_audio = AudioFileClip(wav_file)

    # With new audio to the video
    final_video = video.with_audio(new_audio)

    # Export the final video with new audio
    final_video.write_videofile(output_file, codec="libx264", audio_codec="aac")

    print(f"New video saved as {output_file}")

# Example usage
replace_audio(video_file, "final_output.wav", "final.mp4")

# you could do them async to make the audio generation part faster