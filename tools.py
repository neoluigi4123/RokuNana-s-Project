"""
tool file
"""
from ddgs import DDGS
import requests
import yt_dlp
import trafilatura

from elevenlabs_module import generate_tts
import scripting

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

def python_execution(script: str) -> str:
    return scripting.run_script(script)

def voice_message_generation(input):
    pass
    return generate_tts(input)

if __name__ == "__main__":
    # Example usage
    print(web("https://en.wikipedia.org/wiki/OpenAI"))
    print(youtube("funny dog videos"))
