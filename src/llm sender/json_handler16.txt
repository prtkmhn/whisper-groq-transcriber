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
    

def load_json_as_list(file_path):
    data = load_json(file_path)
    return [data] if isinstance(data, dict) else data

# Function to save list of dictionaries back to JSON
def save_list_to_json(file_path, data_list):
    data = data_list[0] if len(data_list) == 1 else data_list
    save_json(file_path, data)