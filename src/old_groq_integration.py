import os
import json
from groq import Groq
from dotenv import load_dotenv
import pyperclip

load_dotenv()

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

# Load resume content from resume.json (read-only)
def load_resume_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

resume_json = load_resume_json(os.path.join('src', 'resume.json'))

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

# JSON file paths
data_path = os.path.join('src', 'data.json')

# Clear data.json at the start of the code
save_json(data_path, {})

# Load JSON data
data = load_json(data_path)

# Update JSON data with a key-value pair
def update_json(file_path, key, value):
    data = load_json(file_path)
    data[key] = value
    save_json(file_path, data)

def get_groq_response(query):
    # Check if the query contains 'update <KEYWORD>'
    if 'update' in query.lower():
        keyword = query.lower().split('update')[1].strip()
        clipboard_content = pyperclip.paste()
        update_json(data_path, keyword, clipboard_content)
        return f"Updated {keyword} in data.json with the content from the clipboard."
    
    # Load JSON data
    json_data = load_json(data_path)
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant that helps with job applications.  YOU will answer any question as If I was answering it myself. Make sure that none of your response have any buffer text and shouldnt sounud AI generated. Answer directly and to the point, as if you were the user. Here is the user resume content: " + json.dumps(resume_json) + "Here is the user's data: " + json.dumps(json_data),
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

# Main function to run the bot
def main():
    query = "Your query here"
    response = get_groq_response(query)
    print(response)

# Run the main function
if __name__ == "__main__":
    main()