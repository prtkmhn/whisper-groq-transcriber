import os
import json
from groq import Groq
from dotenv import load_dotenv
import pyperclip

load_dotenv()

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

# Load resume content
def load_resume(file_path):
    with open(file_path, 'r') as file:
        return file.read()

resume_content = load_resume(os.path.join('src', 'resume.txt'))

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

# JSON file path
json_file_path = os.path.join('src', 'data.json')

if not os.path.exists(json_file_path):
    save_json(json_file_path, {})

# Load JSON data
json_data = load_json(json_file_path)

# Update JSON data with resume content
json_data['resume'] = resume_content

# Save updated JSON data
save_json(json_file_path, json_data)

def summarize_context(context):
    if len(context.split()) > 200:
        messages = [
            {
                "role": "system",
                "content": "You are an AI assistant that summarizes long text into a concise summary.",
            },
            {
                "role": "user",
                "content": f"Please summarize the following text:\n\n{context}",
            }
        ]
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            max_tokens=100
        )
        return response.choices[0].message.content
    else:
        return context

def update_json(key, value):
    json_data = load_json(json_file_path)
    json_data[key] = value
    save_json(json_file_path, json_data)

def get_groq_response(query):
    # Check if the query contains 'clipboard' or 'clip board'
    if 'clipboard' in query.lower() or 'clip board' in query.lower():
        clipboard_content = pyperclip.paste()
        query = query.replace('clipboard', clipboard_content).replace('clip board', clipboard_content)
    
    # Check if the query contains 'check my clipboard history'
    if 'check my clipboard history' in query.lower():
        clipboard_content = pyperclip.paste()
        summarized_content = summarize_context(clipboard_content)
        update_json(summarized_content)
        update_json('Clipboard Details', summarized_content)

    if 'job description' in query.lower() or 'history' in query.lower():
        clipboard_content = pyperclip.paste()
        summarized_content = summarize_context(clipboard_content)
        update_json('job_description', summarized_content)
    
    
    # Load JSON data
    json_data = load_json(json_file_path)
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant that helps with job applications. Keep the answer short and under 20 words and write like the user himself. Please make sure to not sound like an AI. Here is the user's data: " + json.dumps(json_data),
            },
            {
                "role": "user",
                "content": query,
            }
        ],
        model="llama3-8b-8192",
        max_tokens=100  # Limit the response to a maximum of 100 tokens
    )
    return chat_completion.choices[0].message.content