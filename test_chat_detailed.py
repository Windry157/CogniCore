#!/usr/bin/env python3
import requests
import json

url = "http://localhost:8004/api/chat"
data = {"message": "你好"}
headers = {"Content-Type": "application/json"}

try:
    response = requests.post(url, json=data, headers=headers, timeout=30)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {result.get('response', 'No response')[:300]}")
    
    if response.status_code == 200:
        print("\n✅ Chat API working!")
    else:
        print(f"\n❌ Error: {result}")
except Exception as e:
    print(f"❌ Request failed: {e}")
    import traceback
    traceback.print_exc()
