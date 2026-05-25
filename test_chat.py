#!/usr/bin/env python3
import requests
import json

url = "http://localhost:8004/api/chat"
data = {"message": "你好，做个自我介绍"}
headers = {"Content-Type": "application/json"}

try:
    response = requests.post(url, json=data, headers=headers, timeout=15)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
