
# RokuNana's Project
Allowing LLMs to naturally participate in Multi-Party Chat environments.

# Table of Contents

- [Project presentation](#project-presentation)
   - [The Architecture: Single-Pass Generation](#the-architecture-single-pass-generation)
   - [Real-Time Stream Parsing for Authentic UX](#real-time-stream-parsing-for-authentic-ux)
   - [Seamless Multimedia & Tool Chaining](#seamless-multimedia--tool-chaining)
   - [Autonomous Memory & Prefill Injection (RAG)](#autonomous-memory--prefill-injection-rag)
- [Setup Instructions](#setup-instructions)
- [Keys and configuration](#keys-and-configuration)


## Project Presentation

RokuNana isn't just another chatbot that mindlessly replies to every single prompt in a channel. It is a fully integrated team assistant designed specifically for multi-party group chats. It reads the room, maintains an internal monologue, processes multimedia in the background, and only chimes in when it actually has something valuable to add.

Presentation video:

https://www.youtube.com/watch?v=hPal1W1e6o4

Pipeline chart:

<img width="3219" height="3273" alt="image" src="https://github.com/user-attachments/assets/8d625780-db2a-4f01-950c-97d9bae0df4d" />

### The Architecture: Single-Pass Generation
Most AI agents rely on clunky, multi-step loops to function in a group chat. They usually run one prompt to decide if they should reply, another to pick a tool, and a third to generate the text. RokuNana strips all that overhead away.

We built a single-pass generation architecture. By leveraging dynamic Pydantic schemas (as seen in `core.py`), the model generates its entire state in one continuous JSON stream. In a single execution, RokuNana evaluates the social context, calculates its own "compliance willingness," updates its internal thoughts, proposes tools, and decides whether to output a reply. There is no looped agent constantly polling itself—just one clean, efficient generation that dictates the bot's entire behavior for that interaction.

### Real-Time Stream Parsing for Authentic UX
To make RokuNana feel truly alive, the Discord integration in `main.py` relies on a real-time JSON stream parser. 

When a conversation updates, RokuNana quietly starts processing. As the LLM streams its response, our parser hunts for specific fields on the fly. RokuNana takes time to "think" and evaluate the context in the background, but the moment the stream hits the `target_user` and `reply` fields, the Discord typing indicator is instantly triggered. If the model decides to stay silent and ignore the conversation, the typing animation never fires. From the user's perspective, this eliminates the robotic instant-reply feel; it acts exactly like a human reading the chat, deciding to weigh in, and typing out their thoughts.

### Seamless Multimedia & Tool Chaining
RokuNana handles context richly and natively. 

When someone drops a YouTube link or uploads a video, the system doesn't just read the URL or file name. It actively downloads the media using `yt_dlp`, extracts evenly spaced visual frames using OpenCV, and transcribes the audio track using Mistral's transcription API. This combined audiovisual data is injected straight into the conversation context.

The assistant is also fully equipped to interact with the real world. It can run Python scripts (not in an isolated environment yet, but it can be solved using docker) to solve math equations or analyze data, browse the web for up-to-date context, generate voice messages via ElevenLabs, and integrate with the Google Calendar API to manage your team's schedule. Everything RokuNana learns is indexed into a custom RAG (Retrieval-Augmented Generation) memory pipeline, allowing it to naturally recall facts about users and past conversations over time (see a bit lower).

### Autonomous Memory & Prefill Injection (RAG)
Most conversational bots handle memory by simply stuffing past chat logs into the system prompt until they run out of tokens, leading to high latency and context dilution. RokuNana takes a much more deliberate approach by building an internal, semantic knowledge base that it governs itself.

Because RokuNana relies on a dynamic single-pass JSON schema, the model is continuously evaluating the conversation for new information. We built an `unknown_fact` field directly into its thought process. While the bot is generating its response, if it realizes a user just shared a new preference, trait, or context it didn't previously know, it organically extracts that detail into the JSON stream. The parser catches this in real-time and silently commits it to a ChromaDB vector store using Mistral's embedding models. There is no separate background agent summarizing logs—RokuNana decides what is worth remembering exactly when it learns it.

The way this memory is retrieved and applied is equally seamless. When new messages arrive in the chat, `main.py` queries the vector database to pull up to four highly relevant past facts. But rather than pasting these facts into the system prompt where the model might ignore them, we use a technique called **Assistant Prefilling**. 

Inside `core.py`, the retrieved memories are injected *as the assistant's own starting output* (e.g., forcing the generation to begin with `(Temporal memory: User x needs their code in Python 3.10)`). By prefilling the beginning of the model's response sequence with this data, we force the LLM to structurally acknowledge the memory right before it constructs its `MessageSchema`. This guarantees the model factors its past learnings into its current social context and tool selection, resulting in a persistent, hallucination-free memory that scales indefinitely.

## Setup Instructions

1. Clone the repository and navigate to the project directory.
   ```bash
   git clone https://github.com/neoluigi4123/RokuNana-s-Project.git
   cd RokuNana-s-Project
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```bash
    pip install -r requirements.txt
    ```

4. Set up Google Calendar API credentials:

   - Go to the[Google Cloud Console](https://console.cloud.google.com/).
     
    - Create a new project.
      
![bandicam 2026-02-28 16-07-50-247](https://github.com/user-attachments/assets/e7ea54ec-0807-42a4-bc0c-102d6bca3774)
![bandicam 2026-02-28 16-08-16-024](https://github.com/user-attachments/assets/4901f39d-b317-4db0-877f-cbc45b3daf3a)
![bandicam 2026-02-28 16-08-21-926](https://github.com/user-attachments/assets/7e844676-af36-41a8-934b-e1d4b769970e)

   -When your project is created, configure Google Auth Platform.

![bandicam 2026-02-28 16-08-46-175](https://github.com/user-attachments/assets/a0b21674-c9d6-42a7-8216-0ba4d87e77c8)
![bandicam 2026-02-28 16-08-58-436](https://github.com/user-attachments/assets/397f2b54-6750-4dc5-a323-a21c94ca9ba2)
![bandicam 2026-02-28 16-09-01-417](https://github.com/user-attachments/assets/e5c4d3a1-bd33-4197-901c-05a4ea988abb)
![bandicam 2026-02-28 16-09-10-551](https://github.com/user-attachments/assets/6e20cc8a-7c88-4b4a-884c-711984c83aff)
![bandicam 2026-02-28 16-09-12-929](https://github.com/user-attachments/assets/7549c709-4561-4cac-a4e2-4e1e5e434cfa)
![bandicam 2026-02-28 16-09-14-619](https://github.com/user-attachments/assets/068cd856-5a80-474a-98e8-b8486d8601ee)

   -Then go to Credentials under APIs & Services.
   
![bandicam 2026-02-28 16-10-04-119](https://github.com/user-attachments/assets/4132c572-6d8f-423f-9770-3b1587a5755c)

   -Create an OAuth cliend ID.
   
![bandicam 2026-02-28 16-10-13-932](https://github.com/user-attachments/assets/de82c641-9fd2-4d8c-a6bb-895a4b55dd34)
![bandicam 2026-02-28 16-10-25-021](https://github.com/user-attachments/assets/e050647f-fa73-412e-bf23-966b7dec3ec0)

   -Download the JSON file.
   
![bandicam 2026-02-28 16-10-31-094](https://github.com/user-attachments/assets/1ce8a3cb-822f-431b-b7a9-32d2f338090b)

   -Rename the file to `credentials.json`.
   
![bandicam 2026-02-28 16-11-16-285](https://github.com/user-attachments/assets/35d3816a-c3f3-4e15-9bed-8cc2585cda11)

   -Put the `credentials.json` file in the `local_data/` folder in the root of RokuNana-s-Project or create it if not existing.

   -Return to the [Google Cloud Console](https://console.cloud.google.com/).

   -Go to View all products and search for google calendar API in the top search bar.

![bandicam 2026-02-28 16-11-45-470](https://github.com/user-attachments/assets/a66aa001-29d6-427b-bdad-9170667f25f8)
![bandicam 2026-02-28 16-12-38-362](https://github.com/user-attachments/assets/d76a6409-f52e-4ad7-9323-ea35a55e53b8)

   -Enable the Google Calendar API.

![bandicam 2026-02-28 16-12-46-988](https://github.com/user-attachments/assets/ce8cda89-36df-41e6-862d-f0ce89f6c910)

   -Finally, go to OAuth consent screen under APIs & Services.
   
![bandicam 2026-02-28 16-13-21-513](https://github.com/user-attachments/assets/3ca59367-1617-4862-8b65-c10359c71dd4)

   -And add a test user with your e-mail adress.
   
![bandicam 2026-02-28 16-13-35-030](https://github.com/user-attachments/assets/8a2ecdd2-12e3-4b64-94d0-f8d67187284c)
![bandicam 2026-02-28 16-13-46-205](https://github.com/user-attachments/assets/7316d381-4feb-4508-8d9a-4687c9e78393)

6. Discord:

You also require to setup a discord bot in the discord dev portal and get its token.

Once you got it, you can head over the config.py and specify the name of your discord bot in the SYSTEM_PROMPT.

7. Run the main application:
    ```bash
    python main.py
    ```

## Keys and configuration
Create a `.env` file in the root of the project and add the following variables with your own values:
```python
MISTRAL_API_KEY=PUT_YOUR_ACTUAL_MISTRAL_API_KEY_HERE
DISCORD_BOT_TOKEN=PUT_YOUR_ACTUAL_DISCORD_BOT_TOKEN_HERE
ELEVENLABS_API_KEY=PUT_YOUR_ACTUAL_ELEVENLABS_API_KEY_HERE
```

---

Since this project was part of an hackaton, it will not be updated anymore. If you're having any issue with the setup or the script itself, you can contact the devs on discord (neo_luigi). note that this script works best with python 1.12+ and may fails to run at 3.11 or less.

# Made with Love, Passion and LOT of Fun.
