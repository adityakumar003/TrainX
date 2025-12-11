from elevenlabs import ElevenLabs
from dotenv import load_dotenv
import os

load_dotenv()

client = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

voices = client.voices.get_all()

print("\n=== AVAILABLE VOICES ===\n")

for v in voices.voices:
    print(f"Name: {v.name} | ID: {v.voice_id}")
