"""
Config module for storing api keys, model names, and other configuration variables.
"""
import os
from dotenv import load_dotenv
load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
