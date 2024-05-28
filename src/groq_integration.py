import os
import json
from groq import Groq
from dotenv import load_dotenv
import pyperclip
from embedding_utils import setup_embedding

load_dotenv()

# Global variable for selected model
selected_model = "llama3-8b-8192"

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

# Function to set the model
def set_model(model_name):
    global selected_model
    selected_model = model_name

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

resume_json = load_resume_json(os.path.join('src', 'resume.json'))

# JSON file paths
data_path = os.path.join('src', 'data.json')

# Clear data.json at the start of the code
save_json(data_path, {})

# Load JSON data
data = load_json(data_path)

# URLs for documents
urls = [
    "https://prateekmohan.vercel.app/",
    "https://github.com/prtkmhn",
    "https://prateekmohan.vercel.app/about",
]

# Path to the folder containing PDFs and text files
folder_path = os.path.join('src', 'upload')

# Setup embedding and retriever
retriever = setup_embedding(urls, folder_path)
if not retriever:
    print("Failed to setup embedding and retriever.")
    exit(1)

def get_groq_response(query):
    # Check if the query contains 'update <KEYWORD>'
    if 'update' in query.lower():
        keyword = query.lower().split('update')[1].strip()
        clipboard_content = pyperclip.paste()
        update_json(data_path, keyword, clipboard_content)
        return f"Updated {keyword} in data.json with the content from the clipboard."
    
    # Load JSON data
    json_data = load_json(data_path)
    
    # Retrieve documents
    docs = retriever.invoke(query)
    context = "\n\n".join(doc.page_content for doc in docs)
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant that hel:ps with job applications. YOU will answer any question as If I was answering it myself. Make sure that none of your response have any buffer text and shouldn't sound AI generated. Answer directly and to the point, as if you were the user. Here is the user's data " + json.dumps(json_data) + "Here is the context: " + context,
            },
            {
                "role": "user",
                "content": query,
            }
        ],
        model=selected_model,
        max_tokens=100  # Limit the response to a maximum of 100 tokens
    )
    return chat_completion.choices[0].message.content

def send_latest_text_to_groq():
    clipboard_content = pyperclip.paste()
    response = get_groq_response(clipboard_content)
    print(response)
    return response

# Main function to run the bot
def main():
    query = "Your query here"
    response = get_groq_response(query)
    print(response)

# Run the main function
if __name__ == "__main__":
    main()
