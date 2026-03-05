import requests

url = "https://api.hitstatistics.com/math"
payload = {
    "num1": 25,
    "num2": 20,
    "operation": "add"
}

response = requests.post(url, json=payload)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")