import os

import json
import queue
import threading
import time
import pyperclip
from pynput import keyboard as pynput_keyboard
from audioplayer import AudioPlayer
from transcription import create_local_model, record_and_transcribe
from status_window import StatusWindow
from groq_integration import get_groq_response, send_latest_text_to_groq, update_json, set_model, setup_embedding
import gradio as gr
from pynput.keyboard import Controller
import keyboard  # Ensure keyboard is imported
from langchain_community.document_loaders import WebBaseLoader, PyMuPDFLoader, TextLoader

# Global variables for chat history, selected model, and dynamic URLs
chat_history = []
selected_model = "llama3-8b-8192"
dynamic_urls = []
folder_path = os.path.join('src', 'upload')  # Define folder_path globally

# Path to save hotkeys
hotkeys_path = os.path.join('src', 'hotkeys.json')

class ResultThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(ResultThread, self).__init__(*args, **kwargs)
        self.result = None
        self.stop_transcription = False

    def run(self):
        self.result = self._target(*self._args, cancel_flag=lambda: self.stop_transcription, **self._kwargs)

    def stop(self):
        self.stop_transcription = True

def load_config_with_defaults():
    default_config = {
        'use_api': False,
        'api_options': {
            'model': 'whisper',
            'language': None,
            'temperature': 0.0,
            'initial_prompt': None
        },
        'local_model_options': {
            'model': 'small',
            'device': 'auto',
            'compute_type': 'auto',
            'language': None,
            'temperature': 0.0,
            'initial_prompt': None,
            'condition_on_previous_text': True,
            'vad_filter': False,
        },
        'activation_key': 'ctrl+shift+space',
        'recording_mode': 'voice_activity_detection', # 'voice_activity_detection', 'press_to_toggle', or 'hold_to_record'
        'sound_device': None,
        'sample_rate': 16000,
        'silence_duration': 900,
        'writing_key_press_delay': 0.008,
        'noise_on_completion': False,
        'remove_trailing_period': True,
        'add_trailing_space': False,
        'remove_capitalization': False,
        'print_to_terminal': True,
        'hide_status_window': False
    }

    config_path = os.path.join('src', 'config.json')
    if os.path.isfile(config_path):
        with open(config_path, 'r') as config_file:
            user_config = json.load(config_file)
            for key, value in user_config.items():
                if key in default_config and value is not None:
                    default_config[key] = value

    return default_config

def clear_status_queue(status_queue):
    while not status_queue.empty():
        try:
            status_queue.get_nowait()
        except queue.Empty:
            break

def stop_recording(recording_thread):
    if recording_thread and recording_thread.is_alive():
        recording_thread.stop()
        recording_thread.join()
        print("Recording stopped.")

def on_shortcut(config, status_queue, local_model, recording_thread, status_window):
    clear_status_queue(status_queue)

    status_queue.put(('recording', 'Recording...'))
    recording_thread = ResultThread(target=record_and_transcribe, 
                                    args=(status_queue,),
                                    kwargs={'config': config,
                                            'local_model': local_model if local_model and not config['use_api'] else None},)
    
    if not config['hide_status_window']:
        status_window = StatusWindow(status_queue)
        status_window.recording_thread = recording_thread
        status_window.start()
    
    recording_thread.start()
    recording_thread.join()
    
    if not config['hide_status_window']:
        if status_window.is_alive():
            status_queue.put(('cancel', ''))

    transcribed_text = recording_thread.result

    if transcribed_text:
        # Check if the transcribed text contains 'clipboard' or 'clip board'
        if 'clipboard' in transcribed_text.lower() or 'clip board' in transcribed_text.lower():
            clipboard_content = pyperclip.paste()
            transcribed_text = transcribed_text.replace('clipboard', clipboard_content).replace('clip board', clipboard_content)
        
        groq_response = get_groq_response(transcribed_text)  # Get response from Groq API
        typewrite(groq_response, interval=config['writing_key_press_delay'], recording_thread=recording_thread)

    if config['noise_on_completion']:
        AudioPlayer(os.path.join('assets', 'beep.wav')).play(block=True)

    # Ensure the recording stops and re-enable the shortcut after Groq response
    keyboard.remove_hotkey(config['activation_key'])
    keyboard.add_hotkey(config['activation_key'], lambda: on_shortcut(config, status_queue, local_model, recording_thread, status_window))

# Function to capture selected text
def get_selected_text():
    with pynput_keyboard.Controller() as controller:
        controller.press(pynput_keyboard.Key.ctrl)
        controller.press('c')
        controller.release('c')
        controller.release(pynput_keyboard.Key.ctrl)
    time.sleep(0.1)  # Wait for clipboard to update
    return pyperclip.paste()

def typewrite(text, interval, recording_thread=None):
    pyinput_keyboard = Controller()  # Define pyinput_keyboard here
    for letter in text:
        if recording_thread and recording_thread.stop_transcription:  # Check if the transcription was stopped
            break
        pyinput_keyboard.press(letter)
        pyinput_keyboard.release(letter)
        time.sleep(interval)

def format_keystrokes(key_string):
    return '+'.join(word.capitalize() for word in key_string.split('+'))

def on_groq_shortcut(config):
    response = send_latest_text_to_groq()
    typewrite(response, interval=config['writing_key_press_delay'])

def setup_dynamic_hotkeys(config):
    dynamic_hotkeys = load_hotkeys()
    while True:
        hotkey_name = input("Enter the name for the new hotkey (or press Enter to finish): ")
        if not hotkey_name:
            break
        hotkey_combination = input(f"Enter the hotkey combination for '{hotkey_name}' (or press Enter to skip): ")
        if not hotkey_combination:
            print(f"Skipping '{hotkey_name}'")
            continue
        post_processing = input(f"Enter the post-processing command for '{hotkey_name}' (or press Enter to skip): ")
        action_type = input(f"Do you want to save the output to JSON or print it directly? (Enter 'json' or 'print'): ").strip().lower()
        
        dynamic_hotkeys[hotkey_name] = {
            'combination': hotkey_combination,
            'post_processing': post_processing,
            'action_type': action_type
        }
        
        keyboard.add_hotkey(hotkey_combination, lambda name=hotkey_name: handle_hotkey_action(name, dynamic_hotkeys, config))
        print(f"Hotkey '{hotkey_combination}' for '{hotkey_name}' set up successfully.")
    save_hotkeys(dynamic_hotkeys)
    return dynamic_hotkeys

def handle_hotkey_action(hotkey_name, dynamic_hotkeys, config):
    clipboard_content = pyperclip.paste()
    post_processing_command = dynamic_hotkeys[hotkey_name]['post_processing']
    action_type = dynamic_hotkeys[hotkey_name]['action_type']
    
    if post_processing_command:
        query = f"{post_processing_command} {clipboard_content}"
    else:
        query = clipboard_content
    
    response = generate_answer(query)
    
    if action_type == 'json':
        update_json(os.path.join('src', 'data.json'), hotkey_name, response)
        print(f"Saved response to '{hotkey_name}' in data.json")
    else:
        typewrite(response, interval=config['writing_key_press_delay'])

def generate_answer(query):
    return get_groq_response(query)

# Gradio UI functions
def create_hotkey(hotkey_name, hotkey_combination, post_processing, action_type, dynamic_hotkeys, config):
    dynamic_hotkeys[hotkey_name] = {
        'combination': hotkey_combination,
        'post_processing': post_processing,
        'action_type': action_type
    }
    keyboard.add_hotkey(hotkey_combination, lambda name=hotkey_name: handle_hotkey_action(name, dynamic_hotkeys, config))
    save_hotkeys(dynamic_hotkeys)
    return f"Hotkey '{hotkey_combination}' for '{hotkey_name}' set up successfully."

def chat_with_bot(query, config):
    global chat_history
    response = generate_answer(query)
    chat_history.append((query, response))
    return chat_history, f"Model: {selected_model}\nURLs: {', '.join(dynamic_urls)}"

def add_url(url, config):
    global dynamic_urls, retriever
    dynamic_urls.append(url)
    retriever = setup_embedding(dynamic_urls, folder_path)
    return f"URL '{url}' added successfully."

def upload_pdf(pdf, config):
    if pdf is None:
        return "No PDF file uploaded."

    try:
        # Load the PDF using PyMuPDFLoader directly from the uploaded file object
        loader = PyMuPDFLoader(pdf)
        docs = loader.load()

        # Add the loaded documents to the retriever
        global retriever
        retriever = setup_embedding(dynamic_urls, folder_path)

        return f"PDF '{pdf.name}' uploaded and processed successfully."
    except Exception as e:
        return f"Error uploading PDF: {str(e)}"

def set_model_and_retriever(model_name, config):
    global selected_model, retriever
    selected_model = model_name
    set_model(model_name)
    retriever = setup_embedding(dynamic_urls, folder_path)
    return f"Model set to {model_name} and retriever updated."

def add_url_or_pdf(url, pdf, config):
    if url:
        return add_url(url, config)
    elif pdf:
        return upload_pdf(pdf, config)
    else:
        return "Please provide a URL or PDF."

# New function to update JSON file
def update_json_file(key, value):
    file_path = os.path.join('src', 'data.json')
    update_json(file_path, key, value)
    return f"Updated {key} in data.json with value: {value}"

# Functions to save and load hotkeys
def save_hotkeys(hotkeys):
    with open(hotkeys_path, 'w') as file:
        json.dump(hotkeys, file, indent=2)

def load_hotkeys():
    if os.path.exists(hotkeys_path):
        with open(hotkeys_path, 'r') as file:
            return json.load(file)
    return {}

# Function to update hotkeys
def update_hotkey(hotkey_name, new_combination, new_post_processing, new_action_type):
    dynamic_hotkeys = load_hotkeys()
    if hotkey_name in dynamic_hotkeys:
        if new_combination:
            dynamic_hotkeys[hotkey_name]['combination'] = new_combination
            keyboard.add_hotkey(new_combination, lambda name=hotkey_name: handle_hotkey_action(name, dynamic_hotkeys, config))
        if new_post_processing:
            dynamic_hotkeys[hotkey_name]['post_processing'] = new_post_processing
        if new_action_type:
            dynamic_hotkeys[hotkey_name]['action_type'] = new_action_type
        save_hotkeys(dynamic_hotkeys)  # Save the updated hotkeys
        return f"Hotkey '{hotkey_name}' updated successfully."
    return f"Hotkey '{hotkey_name}' not found."


# Function to create or update hotkeys
def create_hotkey(hotkey_name, hotkey_combination, post_processing, action_type, dynamic_hotkeys, config):
    dynamic_hotkeys[hotkey_name] = {
        'combination': hotkey_combination,
        'post_processing': post_processing,
        'action_type': action_type
    }
    keyboard.add_hotkey(hotkey_combination, lambda name=hotkey_name: handle_hotkey_action(name, dynamic_hotkeys, config))
    save_hotkeys(dynamic_hotkeys)
    return f"Hotkey '{hotkey_combination}' for '{hotkey_name}' set up successfully."

# Function to display current hotkeys
def get_current_hotkeys():
    return json.dumps(load_hotkeys(), indent=2)
