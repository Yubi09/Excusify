import requests

try:
    response = requests.get("https://api-inference.huggingface.co/status")
    print(f"Status from HF: {response.status_code}")
    print(f"Response text: {response.text}")
except requests.exceptions.ConnectionError as e:
    print(f"Connection error: Could not connect to Hugging Face API. This might be a network, firewall, or proxy issue. Error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")