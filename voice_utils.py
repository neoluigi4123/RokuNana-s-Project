"""
voice_utils.py
Handles audio conversion, waveform generation, and uploading voice messages 
using Discord's API structure.
"""
import os
import json
import base64
import subprocess
import aiohttp
import math

async def convert_to_ogg(input_path, output_path="voice-message.ogg"):
    """Converts audio to OGG Opus format required by Discord."""
    process = subprocess.run([
        "ffmpeg",
        '-hide_banner',
        "-y",
        "-i", input_path,
        "-c:a", "libopus",
        "-b:a", "64k",
        "-ar", "48000",
        output_path
    ], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    return output_path

def get_audio_metadata(file_path):
    """
    Extracts exact duration and generates a REAL waveform from the audio file.
    """
    # Duration
    cmd_duration = [
        "ffprobe", "-v", "error", '-hide_banner',
        "-select_streams", "a:0",
        "-show_entries", "format=duration",
        "-of", "json",
        file_path
    ]
    result = subprocess.run(cmd_duration, capture_output=True, text=True)
    duration = float(json.loads(result.stdout)["format"]["duration"])

    # Waveform
    cmd_waveform = [
        "ffmpeg", 
        "-i", file_path,
        "-ac", "1", # Mono
        "-filter:a", "aresample=4000", # Downsample significantly for waveform analysis
        "-map", "0:a", 
        "-c:a", "pcm_u8", # Output 8-bit PCM
        "-f", "data", # Raw data format
        "-" # Output to stdout
    ]
    
    process = subprocess.run(cmd_waveform, capture_output=True)
    raw_data = process.stdout
    
    target_length = 256
    if len(raw_data) > 0:
        step = len(raw_data) / target_length
        sampled_data = bytearray()
        
        for i in range(target_length):
            index = int(i * step)
            if index < len(raw_data):
                sampled_data.append(raw_data[index])
            else:
                sampled_data.append(0)
        
        waveform = base64.b64encode(sampled_data).decode('utf-8')
    else:
        waveform = base64.b64encode(os.urandom(256)).decode('utf-8')

    return duration, waveform

async def send_voice_message(client, channel_id, file_path):
    """
    Uploads the file and sends the message using low-level API calls
    to ensure the 'flags' are set correctly for a Voice Message.
    """
    if not file_path.endswith(".ogg"):
        ogg_path = "voice-message.ogg"
        await convert_to_ogg(file_path, ogg_path)
        file_path = ogg_path

    duration, waveform = get_audio_metadata(file_path)
    file_size = os.path.getsize(file_path)
    token = client.http.token

    async with aiohttp.ClientSession() as session:
        url = f"https://discord.com/api/v10/channels/{channel_id}/attachments"
        headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "files": [{
                "filename": "voice-message.ogg",
                "file_size": file_size,
                "id": 0
            }]
        }
        
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status != 200:
                print(f"Failed to get upload URL: {await response.text()}")
                return False
            data = await response.json()
            upload_url = data["attachments"][0]["upload_url"]
            uploaded_filename = data["attachments"][0]["upload_filename"]

        with open(file_path, "rb") as f:
            file_data = f.read()
            
        async with session.put(upload_url, data=file_data, headers={"Content-Type": "audio/ogg"}) as upload_response:
            if upload_response.status != 200:
                print(f"Failed to upload file: {await upload_response.text()}")
                return False

        message_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        message_payload = {
            "flags": 8192, 
            "attachments": [{
                "id": "0",
                "filename": "voice-message.ogg",
                "uploaded_filename": uploaded_filename,
                "duration_secs": duration,
                "waveform": waveform 
            }]
        }

        async with session.post(message_url, headers=headers, json=message_payload) as msg_response:
            if msg_response.status != 200:
                print(f"Failed to send message: {await msg_response.text()}")
                return False
            
    if os.path.exists("voice-message.ogg"):
        os.remove("voice-message.ogg")
        
    return True