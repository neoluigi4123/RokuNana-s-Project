# RokuNana-s-Project
Allowing LLMs to do Multi-Party chat (with multiple users)
# Table of Contents
- [Project presentation](#project-presentation)
- [Setup Instructions](#setup-instructions)
- [Gif Token Setup](#gif-token-setup)
# Project presentation

Pipeline chart:

<img width="3219" height="3273" alt="image" src="https://github.com/user-attachments/assets/8d625780-db2a-4f01-950c-97d9bae0df4d" />

# Pipeline description:

1. The user initiates a conversation with the system, which is designed to handle multi-party interactions.
2. The system processes the user's input and generates a response using a language model (LLM), which is capable of understanding and managing conversations with multiple participants.
3. The system then checks if the response contains any actionable items, such as scheduling a meeting or setting a reminder.
4. If actionable items are detected, the system interacts with the Google Calendar API to perform the necessary actions, such as creating events or sending invitations.
5. The system continues the conversation, allowing for further interactions and updates as needed.


# Setup Instructions
1. Clone the repository and navigate to the project directory.
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
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
     
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

   -Then go to Credentials under APIs & Services
   
![bandicam 2026-02-28 16-10-04-119](https://github.com/user-attachments/assets/4132c572-6d8f-423f-9770-3b1587a5755c)

   -Create an OAuth cliend ID
   
![bandicam 2026-02-28 16-10-13-932](https://github.com/user-attachments/assets/de82c641-9fd2-4d8c-a6bb-895a4b55dd34)
![bandicam 2026-02-28 16-10-25-021](https://github.com/user-attachments/assets/e050647f-fa73-412e-bf23-966b7dec3ec0)

   -Download the JSON file
   
![bandicam 2026-02-28 16-10-31-094](https://github.com/user-attachments/assets/1ce8a3cb-822f-431b-b7a9-32d2f338090b)

   -Rename the file to "credentials.json"
   
![bandicam 2026-02-28 16-11-16-285](https://github.com/user-attachments/assets/35d3816a-c3f3-4e15-9bed-8cc2585cda11)

   -Put the credentials.json file in the "local_data" folder in the root of RokuNana-s-Project or create it if not existing

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

# Gif Token Setup
1. Go to the [Giphy Developers](https://developers.giphy.com/) website and sign up for an account if you don't have one.
2. Once you have an account, navigate to the "Create an App" section.
3. Fill in the required information for your application, such as the name and description.
4. After creating the app, you will be provided with an API key (also known as a token). Copy this API key.
5. Create a file named `config.py` in the root directory of the project and add the following line, replacing `YOUR_GIPHY_API_KEY` with the API key you copied:
   ```python   
   GIPHY_API_KEY = 'YOUR_GIPHY_API_KEY'
   ```

6. Run the main application:
    ```bash
    python main.py
    ```
