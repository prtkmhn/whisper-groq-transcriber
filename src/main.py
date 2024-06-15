# main.py

import os
import json
import queue
import threading
import time
import keyboard
import pyperclip
from pynput import keyboard as pynput_keyboard
from audioplayer import AudioPlayer
from transcription import create_local_model, record_and_transcribe
from groq_integration import get_groq_response, send_latest_text_to_groq, update_json, set_model, setup_embedding  # Import the new Groq integration
import gradio as gr
from pynput.keyboard import Controller
from helpers import (
    ResultThread, load_config_with_defaults, clear_status_queue, stop_recording, on_shortcut, on_hands_free_shortcut,
    typewrite, format_keystrokes, on_groq_shortcut, chat_with_bot, add_url, upload_pdf, set_model_and_retriever
)
from hotkey import setup_dynamic_hotkeys, update_hotkey, get_current_hotkeys, create_hotkey

# Global variables for chat history, selected model, and dynamic URLs
chat_history = []
selected_model = "llama3-8b-8192"
dynamic_urls = []
folder_path = os.path.join('src', 'upload')  # Define folder_path globally
# Clear hotkeys.json on app start
hotkeys_path = os.path.join('src', 'hotkeys.json')
with open(hotkeys_path, 'w') as file:
    json.dump({}, file)

# Main script
config = load_config_with_defaults()

model_method = 'OpenAI\'s API' if config['use_api'] else 'a local model'
print(f'Script activated. Whisper is set to run using {model_method}. To change this, modify the "use_api" value in the src\\config.json file.')

# Set up local model if needed
local_model = None
if not config['use_api']:
    print('Creating local model...')
    local_model = create_local_model(config)
    print('Local model created.')

print(f'WhisperWriter is set to record using {config["recording_mode"]}. To change this, modify the "recording_mode" value in the src\\config.json file.')
print(f'The activation key combo is set to {format_keystrokes(config["activation_key"])}.', end='')
if config['recording_mode'] == 'voice_activity_detection':
    print(' When it is pressed, recording will start, and will stop when you stop speaking.')
elif config['recording_mode'] == 'press_to_toggle':
    print(' When it is pressed, recording will start, and will stop when you press the key combo again.')
# elif config['recording_mode'] == 'hold_to_record':
#     print(' When it is pressed, recording will start, and will stop when you release the key combo.')
print('Press alt+C on the terminal window to quit.')

# Set up status queue and keyboard listener
status_queue = queue.Queue()
pyinput_keyboard = Controller()
recording_thread = None  # Initialize recording_thread

keyboard.add_hotkey(config['activation_key'], lambda: on_shortcut(config, status_queue, local_model, recording_thread))
keyboard.add_hotkey('ctrl+alt+space', lambda: on_shortcut(config, status_queue, local_model, recording_thread))  # Add new hotkey for Groq integration
keyboard.add_hotkey('alt+c', lambda: stop_recording(recording_thread))  # Add hotkey to stop recording
keyboard.add_hotkey('ctrl+alt+v', lambda: on_groq_shortcut(config))  # Add hotkey to paste clipboard content
keyboard.add_hotkey('ctrl+alt+f', lambda: on_hands_free_shortcut(config, status_queue, local_model, recording_thread))
keyboard.add_hotkey('ctrl+alt+i', lambda: stop_recording(recording_thread))
# Set up dynamic hotkeys
dynamic_hotkeys = setup_dynamic_hotkeys(config)

# Function to add URL or PDF
def add_url_or_pdf(url, pdf, config):
    if url:
        return add_url(url, config)
    elif pdf:
        return upload_pdf(pdf, config)
    else:
        return "Please provide a URL or PDF."

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("# WhisperWriter with Gradio UI")
    
    with gr.Tab("Chat with Bot"):
        model_selector = gr.Dropdown(["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768"], label="Select Model", value="llama3-8b-8192")
        model_selector.change(lambda model_name: set_model_and_retriever(model_name, config), inputs=model_selector, outputs=None)
        
        chat_output = gr.Chatbot(label="Chat History")
        query = gr.Textbox(label="Your Query", placeholder="Type your message here...")
        chat_button = gr.Button("Chat")
        
        chat_button.click(lambda query: chat_with_bot(query, config), inputs=[query], outputs=[chat_output, gr.Textbox(label="Details")])
    
    with gr.Tab("Manage Hotkeys"):
        
        with gr.Row():
            with gr.Column():
                hotkeys_list = gr.Textbox(label="Current Hotkeys", value=get_current_hotkeys(), interactive=False)         
            with gr.Column():
                gr.Markdown("### Create/Update Hotkey")
                hotkey_name = gr.Textbox(label="Hotkey Name")
                ctrl_button = gr.Checkbox(label="Ctrl")
                alt_button = gr.Checkbox(label="Alt")
                shift_button = gr.Checkbox(label="Shift")
                key_input = gr.Textbox(label="Key")
                post_processing = gr.Textbox(label="Post-Processing Command")
                action_type = gr.Radio(["json", "print"], label="Action Type")
                create_button = gr.Button("Create Hotkey")
                create_output = gr.Textbox(label="Output")
                
                def create_hotkey_ui(hotkey_name, key_input, ctrl, alt, shift, post_processing, action_type):
                    combination = '+'.join([key for key, selected in zip(['ctrl', 'alt', 'shift'], [ctrl, alt, shift]) if selected])
                    if key_input:
                        combination += f"+{key_input}"
                    result = create_hotkey(hotkey_name, combination, post_processing, action_type, dynamic_hotkeys, config)
                    updated_hotkeys = get_current_hotkeys()
                    return result, updated_hotkeys
                
                create_button.click(create_hotkey_ui, inputs=[hotkey_name, key_input, ctrl_button, alt_button, shift_button, post_processing, action_type], outputs=[create_output, hotkeys_list])
            

        
    with gr.Tab("Add URL or PDF"):
        url_input = gr.Textbox(label="Enter URL")
        pdf_input = gr.File(label="Upload PDF", file_types=[".pdf"])
        add_url_button = gr.Button("Add URL or PDF")
        add_url_output = gr.Textbox(label="Output")
        
        add_url_button.click(lambda url, pdf: add_url_or_pdf(url, pdf, config), inputs=[url_input, pdf_input], outputs=add_url_output)

demo.launch()

try:
    keyboard.wait()  # Keep the script running to listen for the shortcut
except KeyboardInterrupt:
    print('\nExiting the script...')
    os.system('exit')
