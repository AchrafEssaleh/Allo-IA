import os
import requests

BASE_URL = "https://llm.ilaas.fr/v1"
API_KEY = os.environ["ILAAS_API_KEY"]

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# Retrieve the model list
models_response = requests.get(
    f"{BASE_URL}/models",
    headers=headers,
    timeout=30,
)
models_response.raise_for_status()

models = models_response.json()["data"]

print("Available models:")
for model in models:
    print(f" - {model['id']}")

# Use a chosen model returned by ILaaS
model_id = "qwen-3.6-35b-instruct"
print("Testing model:", model_id)

# Send a basic chat-completion request
response = requests.post(
    f"{BASE_URL}/chat/completions",
    headers=headers,
    json={
        "model": model_id,
        "messages": [
            {"role": "user", "content": "Bonjour ! Réponds en une phrase."}
        ],
        "stream": False,
        "max_tokens": 100,
    },
    timeout=60,
)

print("HTTP status:", response.status_code)
print("Response:", response.text)