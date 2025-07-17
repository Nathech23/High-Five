import requests

print("=== TEST DE TON API ===")
print("Analyse du feedback: 'Long wait.'")

response = requests.post("http://localhost:8001/analyze", 
                        json={"text": "Long wait."})

result = response.json()
print(f"Sentiment: {result['sentiment']}")
print(f"Rating: {result['predicted_rating']}/5")
print(f"Thèmes: {result['themes']}")
print(f"Urgent: {result['is_urgent']}")
print(f"Temps: {result['processing_time_ms']}ms")