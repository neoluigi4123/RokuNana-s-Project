# RokuNana-s-Project
Allowing LLMs to do Multi-Party chat (with multiple users)

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
    - Create a new project and enable the Google Calendar API.
    - Create OAuth 2.0 credentials and download the `credentials.json` file.
    - Place the `credentials.json` file in the `local_data/` directory.
5. Run the main application:
    ```bash
    python main.py
    ```

