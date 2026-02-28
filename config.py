"""
Config module for storing api keys, model names, and other configuration variables.
"""
import os
from dotenv import load_dotenv
load_dotenv()

# Settings
DEFAULT_MODEL = "mistral-large-latest"
DEFAULT_TTS_MODEL = "voxtral-realtime-latest"
EMBED_MODEL = "mistral-embed"
SYSTEM_PROMPT = "You are Roku Nana, a helpful assistant that can answer questions and perform tasks based on user input."

DOWNLOAD_PATH = "download" # Where attachments goes (images)

# API Keys
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")