import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# List all available models with full details
print("=" * 60)
print("AVAILABLE MODELS FOR generateContent:")
print("=" * 60)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"\nModel Name: {model.name}")
        print(f"Display Name: {model.display_name}")
        
# Now test which exact name works
print("\n" + "=" * 60)
print("TESTING MODEL NAMES:")
print("=" * 60)

test_models = []
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        test_models.append(model.name)

for model_name in test_models:
    try:
        test_model = genai.GenerativeModel(model_name)
        response = test_model.generate_content("Say 'Hello'")
        print(f"\n✅ {model_name} - WORKS!")
        print(f"   Response: {response.text[:50]}...")
        break  # Use the first one that works
    except Exception as e:
        print(f"\n❌ {model_name} - FAILED: {str(e)[:100]}")
