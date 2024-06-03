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
from status_window import StatusWindow
from groq_integration import get_groq_response, send_latest_text_to_groq, update_json, set_model, setup_embedding  # Import the new Groq integration
import gradio as gr
from pynput.keyboard import Controller
from helpers import (
    ResultThread, load_config_with_defaults, clear_status_queue, stop_recording, on_shortcut, get_selected_text,
    typewrite, format_keystrokes, on_groq_shortcut, setup_dynamic_hotkeys, handle_hotkey_action, generate_answer,
    create_hotkey, chat_with_bot, add_url, upload_pdf, set_model_and_retriever, update_json_file
)

# Global variables for chat history, selected model, and dynamic URLs
chat_history = []
selected_model = "llama3-8b-8192"
dynamic_urls = []
folder_path = os.path.join('src', 'upload')  # Define folder_path globally

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
elif config['recording_mode'] == 'hold_to_record':
    print(' When it is pressed, recording will start, and will stop when you release the key combo.')
print('Press alt+C on the terminal window to quit.')

# Set up status window and keyboard listener
status_queue = queue.Queue()
pyinput_keyboard = Controller()
recording_thread = None  # Initialize recording_thread
status_window = None  # Initialize status_window

keyboard.add_hotkey(config['activation_key'], lambda: on_shortcut(config, status_queue, local_model, recording_thread, status_window))
keyboard.add_hotkey('ctrl+alt+space', lambda: on_shortcut(config, status_queue, local_model, recording_thread, status_window))  # Add new hotkey for Groq integration
keyboard.add_hotkey('alt+c', lambda: stop_recording(recording_thread))  # Add hotkey to stop recording
keyboard.add_hotkey('ctrl+alt+v', lambda: on_groq_shortcut(config))  # Add hotkey to paste clipboard content

# Set up dynamic hotkeys
dynamic_hotkeys = setup_dynamic_hotkeys(config)

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
    
    with gr.Tab("Create Hotkey"):
        hotkey_name = gr.Textbox(label="Hotkey Name")
        hotkey_combination = gr.Textbox(label="Hotkey Combination")
        post_processing = gr.Textbox(label="Post-Processing Command")
        action_type = gr.Radio(["json", "print"], label="Action Type")
        create_button = gr.Button("Create Hotkey")
        create_output = gr.Textbox(label="Output")
        
        create_button.click(lambda hotkey_name, hotkey_combination, post_processing, action_type: create_hotkey(hotkey_name, hotkey_combination, post_processing, action_type, dynamic_hotkeys, config), inputs=[hotkey_name, hotkey_combination, post_processing, action_type], outputs=create_output)
    
    with gr.Tab("Add URL"):
        url_input = gr.Textbox(label="Enter URL")
        add_url_button = gr.Button("Add URL")
        add_url_output = gr.Textbox(label="Output")
        
        add_url_button.click(lambda url: add_url(url, config), inputs=url_input, outputs=add_url_output)
    
    # New tab to update JSON file
    with gr.Tab("Update JSON"):
        json_key = gr.Textbox(label="Key", placeholder="Enter the key to update...")
        json_value = gr.Textbox(label="Value", placeholder="Enter the value to update...")
        update_button = gr.Button("Update JSON")
        update_output = gr.Textbox(label="Output")
        
        update_button.click(update_json_file, inputs=[json_key, json_value], outputs=update_output)

demo.launch()

try:
    keyboard.wait()  # Keep the script running to listen for the shortcut
except KeyboardInterrupt:
    print('\nExiting the script...')
    os.system('exit')