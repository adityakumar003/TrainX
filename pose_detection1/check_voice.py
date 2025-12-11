from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
import os

load_dotenv()
client = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

voices = client.voices.get_all()
print("\n--- Voice Capability Check ---")
for v in voices.voices:
    print(f"{v.name} | can_tts: {v.settings.can_be_used_for_tts}")
