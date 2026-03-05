import requests

url = "http://127.0.0.1:8000/math"
payload = {
    "num1": 25,
    "num2": 5,
    "operation": "multiply"
}

response = requests.post(url, json=payload)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")