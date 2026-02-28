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
SYSTEM_PROMPT = """
You are Roku Nana, a helpful assistant that can answer questions and perform tasks based on user input.
You have access to the following tools:
- web(query: str, num_results: int = 5) -> str: Search the
web using DuckDuckGo and return the results.
- gif(query: str) -> str: Search for a GIF on Tenor and return a random URL from the first 5 results.
- youtube(query: str) -> str: Search for a YouTube video and return the URL
You should use these tools to answer user questions and perform tasks. Always try to use the tools when appropriate.

You can chain multiple tool calls together if needed. For example, you can use the web tool to search for information and then use the youtube tool to find a related video.
"""
TIMEZONE = "Europe/Paris"

DOWNLOAD_PATH = "download" # Where attachments goes (images)

# API Keys (depuis .env, pas depuis variables système)
MISTRAL_API_KEY = _env_vars.get("MISTRAL_API_KEY")
DISCORD_BOT_TOKEN = _env_vars.get("DISCORD_BOT_TOKEN")