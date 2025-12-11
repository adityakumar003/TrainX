from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
import os

# Load API key
load_dotenv()
API_KEY = os.getenv("ELEVEN_API_KEY")

if not API_KEY:
    raise Exception("❌ No ElevenLabs API key found in .env")

# Initialize ElevenLabs client
client = ElevenLabs(api_key=API_KEY)

# Public universal voice (works even if not in your account)
VOICE_ID = "TxGEqnHWrfWFTfGW9XjX"  # Josh

print("\n🔊 Attempting voice test using Josh...\n")

try:
    client.text_to_speech.stream(
        text="Hello champion. This is Josh speaking. If you hear me, everything is working.",
        voice_id=VOICE_ID,
        model_id="eleven_turbo_v2"
    )
    print("\n✔ Voice Test Completed — If you heard Josh, it's working.\n")

except Exception as e:
    print("\n❌ Voice test failed.\n")
    print("Error:", e)
