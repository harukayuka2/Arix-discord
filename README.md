# Example Discord Bot (Python)

Quick example showing a minimal bot using `discord.py` and `python-dotenv`.

Files added:
- `bot.py` - main bot implementation
- `requirements.txt` - dependencies
- `.env.example` - example environment file

Setup:
1. Create a Python virtual environment (recommended).
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   source .venv/bin/activate  # macOS / Linux
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Or install the official Google GenAI SDK directly:
    ```bash
    pip install -q -U google-genai
    ```
3. Copy `.env.example` to `.env` and set `DISCORD_TOKEN` with your bot token.
4. Run the bot:
   ```bash
   python bot.py
   ```

Commands:
- `!ping` - responds with Pong and latency.
- `!hello` - greets the invoking user.

Notes:
- Ensure `Message Content Intent` is enabled for your bot in the Discord Developer Portal.
- Keep your token secret.

- For Gemini: set `GEMINI_API_KEY` in your `.env` (see `.env.example`). The example code uses the official `google-genai` SDK which will read `GEMINI_API_KEY` from the environment.

API key and quickstart
- Create a Gemini API key in Google AI Studio: https://aistudio.google.com/app/apikey
- You can either set the `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) environment variable, or pass the key explicitly to the client.

Windows (quick):
1. Open System Settings → Environment Variables
2. Add `GEMINI_API_KEY` with your key value under User variables
3. Open a new terminal to pick up the change

Python examples
- Environment-based (recommended for server apps):

```py
from google import genai

client = genai.Client()
response = client.models.generate_content(
      model="gemini-3-flash-preview",
      contents="Explain how AI works in a few words",
)
print(response.text)
```

- Explicit API key (useful for quick tests):

```py
from google import genai

client = genai.Client(api_key="YOUR_API_KEY")
response = client.models.generate_content(
      model="gemini-3-flash-preview",
      contents="Explain how AI works in a few words",
)
print(response.text)
```

REST example (curl):

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
   -H "x-goog-api-key: $GEMINI_API_KEY" \
   -H 'Content-Type: application/json' \
   -X POST \
   -d '{
      "contents": [
         {"parts": [{"text": "Explain how AI works in a few words"}]}
      ]
   }'
```

Security
- Never commit API keys to source control. Use server-side environment variables or secret managers for production.
