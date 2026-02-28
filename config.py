"""
Config module for storing api keys, model names, and other configuration variables.
"""
import os
from dotenv import load_dotenv
load_dotenv()

# Settings
DEFAULT_MODEL = "mistral-large-latest"
DEFAULT_TTS_MODEL = "voxtral-realtime-latest"

DOWNLOAD_PATH = "download" # Where attachments goes (images)

# API Keys
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")