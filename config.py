"""
Config module for storing api keys, model names, and other configuration variables.
"""
import os
from dotenv import dotenv_values

# Charge les variables directement depuis .env (contourne les variables système)
_env_vars = dotenv_values(".env")

# Settings
DEFAULT_MODEL = "mistral-large-latest"
DEFAULT_TTS_MODEL = "voxtral-realtime-latest"
EMBED_MODEL = "mistral-embed"
SYSTEM_PROMPT = "You are Roku Nana, a helpful assistant that can answer questions and perform tasks based on user input."
TIMEZONE = "Europe/Paris"

DOWNLOAD_PATH = "download" # Where attachments goes (images)

# API Keys (depuis .env, pas depuis variables système)
MISTRAL_API_KEY = _env_vars.get("MISTRAL_API_KEY")
DISCORD_BOT_TOKEN = _env_vars.get("DISCORD_BOT_TOKEN")