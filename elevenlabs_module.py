from elevenlabs.client import ElevenLabs
import config
#from rvc_api import rvc_generate

client = ElevenLabs(
    base_url="https://api.elevenlabs.io",
    api_key=config.ELEVEN_LABS_API_KEY,
)

def generate_tts(msg: str, filename="output.mp3") -> str:
    # Generate audio stream
    response = client.text_to_speech.convert(
        text=msg,
        voice_id=config.ELEVENLABS_VOICE,
        output_format="mp3_44100_128"
    )

    # Save to file
    with open(filename, "wb") as f:
        for chunk in response:
            f.write(chunk)

    # Return the path
    return filename

def generate(msg: str, filename="output.mp3"):
    tts_path = generate_tts(msg, filename)
    return tts_path

if __name__ == "__main__":
    test_msg = "Salut tout le monde! Je me presente, je suis RokuNana, et euh... Roku Nana!"
    output_path = generate(test_msg, "output.mp3")
    print(f"Audio generated and saved to {output_path}")