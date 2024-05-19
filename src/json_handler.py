import os
import json

# Load JSON file
def load_json(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save JSON file
def save_json(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)

# Update JSON data with a key-value pair
def update_json(file_path, key, value):
    data = load_json(file_path)
    data[key] = value
    save_json(file_path, data)

# Load resume content from resume.json (read-only)
def load_resume_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)