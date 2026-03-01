"""
Main module for the RokuNana's Project. This is where the main execution of the program will happen. It will import necessary modules and run the main loop for the llm agent.
"""

import discord
import asyncio
import time
import os
from dotenv import load_dotenv
from pydub import AudioSegment
import cv2
import numpy as np
import voice_utils
from core import LLM
import config
import rag_embedding

load_dotenv()

WAIT = 20

download_dir = config.DOWNLOAD_PATH
os.makedirs(download_dir, exist_ok=True) 

AI = LLM(
    model_name=config.DEFAULT_MODEL,
    client="https://api.mistral.ai",
    system_prompt=config.SYSTEM_PROMPT,
    api_key=config.MISTRAL_API_KEY, # type: ignore
)

intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)

chat_history = []
last_context_str = None
current_context = []
wait_time = WAIT
last_channel = None

new_message_event = asyncio.Event()

last_message_timestamp = None

def extract_frame(video_path, output_folder: str = config.PLACEHOLDER, framerate=5):
    """Exctracts frames from a video for given framerate."""
    vidcap = cv2.VideoCapture(video_path)
    success, image = vidcap.read()
    count = 0
    saved_frames = []
    
    #clean output folder first
    for f in os.listdir(output_folder):
        os.remove(os.path.join(output_folder, f))
    while success:
        if count % framerate == 0:
            output_path = os.path.join(output_folder, f"frame_{count}.jpg")
            cv2.imwrite(output_path, image)
            saved_frames.append(output_path)
        success, image = vidcap.read()
        count += 1
    
    return saved_frames



def convert_to_ogg(input_path, output_path):
    audio = AudioSegment.from_file(input_path)
    # Force mono, 48kHz
    audio = audio.set_channels(1).set_frame_rate(48000)
    # Export with Opus codec
    audio.export(
        output_path,
        format="ogg",
        codec="libopus",
        bitrate="32k"  # or "64k"
    )

def get_wait_time(activity: float, compliance: float, y_max: float = 43200.0) -> float:
    """
    Calculate wait time based on activity level and compliance.

    Args:
        activity:   Raw activity level (0–100).
        compliance: Compliance level (0–100).
        y_max:      Maximum wait time cap in seconds (default 43200s).

    Returns:
        Wait time in seconds.
    """
    x = activity * (compliance / 100.0)

    if x <= 0:
        return y_max

    y = 50_000.0 / (x ** 2)

    return min(y, y_max)

@client.event
async def on_ready():
    client.loop.create_task(main())
    print(f'Logged in as {client.user}')

# on message event
@client.event
async def on_message(msg):
    global last_message_timestamp
    global last_context_str
    global current_context
    global last_channel
    global download_dir

    if msg.author == client.user:
        return
    
    content = "" # Final message content placeholder for context

    last_message_timestamp = time.time()

    last_channel = msg.channel
    
    if msg.guild:
        current_context_str = f"{msg.guild.name} / {msg.channel.name}"
    else:
        # DM channel handling
        if isinstance(msg.channel, discord.DMChannel):
            recipient_name = msg.channel.recipient.name if msg.channel.recipient else msg.author.name
        elif isinstance(msg.channel, discord.GroupChannel):
            recipient_name = ", ".join(u.name for u in msg.channel.recipients if u)
        else:
            recipient_name = msg.author  # Fallback to message author
        current_context_str = f"DM / {recipient_name}"

    if last_context_str is not None and current_context_str != last_context_str:
        current_context.append({
            "role": "system",
            "content": f"Channel changed from ({last_context_str}) to ({current_context_str})"
        })
        print(current_context[-1])
    
    last_context_str = current_context_str

    timestamp_str = msg.created_at.strftime("%a %H:%M")

    image_paths = []

    if msg.attachments:
        for attachment in msg.attachments:
            # images
            if attachment.content_type and attachment.content_type.startswith('image/'):
                filename = f"{msg.id}_{attachment.filename}" 
                file_path = os.path.join(download_dir, filename)
                await attachment.save(file_path)
                
                image_paths.append(file_path)

            #audio
            if attachment.content_type and attachment.content_type.startswith('audio/'):
                filename = f"{msg.id}_{attachment.filename}" 
                file_path = os.path.join(download_dir, filename)
                await attachment.save(file_path)
                
                transcription = AI.transcribe_audio(file_path, msg.author.name)

                content += (f"send an audio file: {transcription}")

    if msg.mentions:
        for user in msg.mentions:
            mention_str = f"<@{user.id}>"
            if mention_str in msg.content:
                msg.content = msg.content.replace(mention_str, f"@{user.name}")

    content += msg.content

    message_data: dict = {
        "role": "user",
        "content": f"[{timestamp_str}] {msg.author.name}: {content}"
    }

    if image_paths:
        message_data["attachments"] = image_paths

    current_context.append(message_data)

    print("context updated")

    if wait_time > WAIT:
        new_message_event.set()

@client.event
async def on_reaction_add(reaction, user):
    if user == client.user:
        return

    AI.add_to_context(content=f"{user} reacted with {reaction.emoji} to message: {reaction.message.content}", role="system")

async def main():
    global last_message_timestamp
    global current_context
    global chat_history
    global last_channel
    global wait_time

    await client.wait_until_ready()

    while True:
        # Default values
        RAG_results = ""
        print(wait_time)
        # Wait for timeout or new message
        try:
            await asyncio.wait_for(new_message_event.wait(), timeout=wait_time)
            print(f"New message interrupted wait, reset to {wait_time} seconds.")
        except asyncio.TimeoutError:
            print(f"Wait completed after {wait_time} seconds.")
        
        new_message_event.clear()

        # Summary
        if len(AI.context) > 15:
            AI.summarize_chat(10)

        new_messages = current_context[len(chat_history):]
        
        chat_history = current_context.copy()

        if not new_messages:
            if AI.state.get('Avg_room_activity'):
                wait_time = get_wait_time(AI.state.get('Avg_room_activity'), AI.state.get('Compliance')) # type: ignore
            else:
                wait_time = min(wait_time * 2.75, 43200)  # Double, Cap at 12 hours
            print(wait_time)
        else:
            wait_time = WAIT  # Reset wait time on new message

        # Only add NEW messages to context
        for msg in new_messages:
            # if image:
            if 'attachments' in msg and msg['attachments']:
                AI.add_to_context(msg['content'], msg['role'], images=msg['attachments'])

            else:
                AI.add_to_context(msg['content'], msg['role'])

        if new_messages:
            RAG_results_pre = rag_embedding.read_memory(4, str(new_messages))
            for content in RAG_results_pre:
                RAG_results += f"{content}, "

        time_diff = int(time.time() - last_message_timestamp if last_message_timestamp else 0)
        
        try:
            await asyncio.to_thread(AI.generate, rag = f"{RAG_results}Last activity {time_diff} sec ago." if RAG_results else f"Last activity {time_diff} sec ago.")
        except Exception as e:
            print(f"Error generating response: {e}")
            pass

        while AI.state['thinking']:
            await asyncio.sleep(1)
        
        if last_channel:
            async with last_channel.typing():
                await asyncio.sleep(1)

        while AI.state['done'] is False:
            await asyncio.sleep(1)
        
        # Send reply
        print(AI.reply)
        reply_content = AI.reply.get('message', None)
        tar_user = AI.reply.get('tar_usr', None)
        attachment = AI.reply.get('attachments', None)

        reply_channel = None

        if reply_content or attachment:
            # 1. Check if we are in Private Messages (or the last channel was one)
            if isinstance(last_channel, discord.DMChannel):
                if tar_user:
                    # Look for the specific target user requested
                    found_user = discord.utils.find(lambda u: u.name == tar_user, client.users)
                    if found_user:
                        try:
                            reply_channel = await found_user.create_dm()
                        except Exception as e:
                            print(f"Failed to create DM with {tar_user}: {e}")
                            reply_channel = last_channel # Fallback to current DM
                    else:
                        # Target user not found in cache, stay in current DM
                        reply_channel = last_channel
                else:
                    # No specific target user mentioned, stay in current DM
                    reply_channel = last_channel

            # 2. Else: If we are in a public channel
            elif isinstance(last_channel, discord.TextChannel):
                reply_channel = last_channel

            # 3. Else: No last_channel exists (bot just started / idle)
            elif last_channel is None:
                if tar_user:
                    found_user = discord.utils.find(lambda u: u.name == tar_user, client.users)
                    if found_user:
                        try:
                            reply_channel = await found_user.create_dm()
                        except Exception as e:
                            print(f"Failed to initiate DM with {tar_user}: {e}")

            if AI.reply.get('type', None) == "voiceMessageGeneration" and attachment:
                vocal_attachment_path = attachment[0]  # Assuming the TTS tool returns a single file path in attachments
                convert_to_ogg(vocal_attachment_path, "voice-message.ogg")
                try:
                    await voice_utils.send_voice_message(client, reply_channel.id, "voice-message.ogg") # type: ignore
                    attachment.pop[0]
                except Exception as e:
                    print(f"Error sending voice message: {e}")
                    AI.add_to_context(role="tool", content=f"Failed to send voice message: {e}")

            # Final Sending Logic
            if reply_channel:
                try:
                    if attachment:
                        files = [discord.File(fp) for fp in attachment]
                        await reply_channel.send(content=reply_content, files=files)
                    else:
                        await reply_channel.send(reply_content)
                    print(f"Sent response to {reply_channel}")
                except discord.Forbidden:
                    print(f"Missing permissions to send to {reply_channel}")
                except Exception as e:
                    print(f"Error sending message: {e}")
            else:
                print("Could not determine a valid channel to reply to.")


if __name__ == "__main__":
    client.run(config.DISCORD_BOT_TOKEN) # type: ignore