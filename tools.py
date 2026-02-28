"""
tool file
"""
from ddgs import DDGS
import requests
import random
import yt_dlp
import trafilatura

import config
# import scripting
# from elevenlabs_module import generate_audio

def web(query: str, num_results: int = 5) -> str:
    """
    Browse the web or search using DuckDuckGo.
    """
    query = query.strip()

    if query.lower().startswith(("http://", "https://")):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(query, headers=headers, timeout=10)
            response.raise_for_status()

            # Use trafilatura - much better extraction
            text = trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=False,
                no_fallback=False
            )

            if text:
                # Clean up and limit
                text = ' '.join(text.split())  # Normalize whitespace
                return text[:2000]  # More reasonable limit
            
            return "Could not extract content from page."

        except Exception as e:
            return f"Error: {e}"

    else:
        results = DDGS().text(query, max_results=num_results)
        return results

def gif(query: str) -> str:
    """
    Searches for a GIF on Giphy and returns a random URL from the first 5 results.
    
    Args:
        query (str): The search query for the GIF.
    
    Returns:
        str: URL of a random GIF from the search results or an error message.
    """
    API_KEY = config.GIF_TOKEN
    url = "https://api.giphy.com/v1/gifs/search"
    
    params = {
        "q": query,
        "api_key": API_KEY,
        "limit": 5,
        "rating": "g"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                print("Success: Here is a GIF URL:")
                print(data["data"][0]["images"]["original"]["url"])
                return data["data"][0]["images"]["original"]["url"]
            else:
                print("No GIFs found for the query.")
        else:
            print(f"Error: Received status code {response.status_code} from Giphy API.")
            print(response.text

    except Exception as e:
        print(f"An error occurred: {e}")

def youtube(query: str) -> str:
    """
    Search for a YouTube video and return the URL for the first result.
    """
    try:
        ydl_opts: dict = {
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1',
            'skip_download': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type:ignore
            info = ydl.extract_info(query, download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                return info['entries'][0]['webpage_url']
            return "No YouTube video found."
    
    except Exception as e:
        return f"Error: {e}"

def python_execution(script: str):
    pass
    # return scripting.run_script(script)

def voice_message_generation(input):
    pass
    # return generate_audio(input)

if __name__ == "__main__":
    # Example usage
    print(web("https://en.wikipedia.org/wiki/OpenAI"))
    print(gif("cute cat"))
    print(youtube("funny dog videos"))
