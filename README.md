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
      <img width="412" height="138" alt="image" src="https://github.com/user-attachments/assets/4b4a764d-502c-45ba-ae28-ba3739625726" />

    - Create OAuth 2.0 credentials and download the `credentials.json` file.
      <img width="464" height="915" alt="image" src="https://github.com/user-attachments/assets/dd86d097-e75d-43b8-b649-20e12698738a" />
      <img width="934" height="404" alt="image" src="https://github.com/user-attachments/assets/93f90f57-5ab3-4c86-8c7f-f86b2882c877" />
      <img width="892" height="331" alt="image" src="https://github.com/user-attachments/assets/dcb640d2-8921-4fcc-856f-1044c85479a8" />
      <img width="801" height="531" alt="image" src="https://github.com/user-attachments/assets/89642eaf-c98b-4369-a79b-3340e1180cf3" />
      <img width="487" height="584" alt="image" src="https://github.com/user-attachments/assets/5917da76-19f8-4f14-a075-2097752d6cd3" />

    - Place the `credentials.json` file in the `local_data/` directory (create it if not existing yet).
5. Run the main application:
    ```bash
    python main.py
    ```
