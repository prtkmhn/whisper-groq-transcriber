import json
import os
import queue
import threading
import time
import keyboard
import pyperclip
from audioplayer import AudioPlayer
from pynput.keyboard import Controller
from transcription import create_local_model, record_and_transcribe
from status_window import StatusWindow
from groq_integration import get_groq_response, send_latest_text_to_groq, update_json, set_model, setup_embedding
import gradio as gr

# Global variables for chat history, selected model, and dynamic URLs
chat_history = []
selected_model = "llama3-8b-8192"
dynamic_urls = []
folder_path = os.path.join('src', 'upload')  # Define folder_path globally

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

def clear_status_queue():
    while not status_queue.empty():
        try:
            status_queue.get_nowait()
        except queue.Empty:
            break

def stop_recording():
    global recording_thread
    if recording_thread and recording_thread.is_alive():
        recording_thread.stop()
        recording_thread.join()
        print("Recording stopped.")

def on_shortcut():
    global status_queue, local_model, recording_thread, status_window
    clear_status_queue()

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
        typewrite(groq_response, interval=config['writing_key_press_delay'])

    if config['noise_on_completion']:
        AudioPlayer(os.path.join('assets', 'beep.wav')).play(block=True)

    # Ensure the recording stops and re-enable the shortcut after Groq response
    keyboard.remove_hotkey(config['activation_key'])
    keyboard.add_hotkey(config['activation_key'], on_shortcut)

def typewrite(text, interval):
    global recording_thread
    for letter in text:
        if recording_thread and recording_thread.stop_transcription:  # Check if the transcription was stopped
            break
        pyinput_keyboard.press(letter)
        pyinput_keyboard.release(letter)
        time.sleep(interval)

def format_keystrokes(key_string):
    return '+'.join(word.capitalize() for word in key_string.split('+'))

def on_groq_shortcut():
    response = send_latest_text_to_groq()
    typewrite(response, interval=config['writing_key_press_delay'])

def handle_hotkey_action(hotkey_name, dynamic_hotkeys):
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
def create_hotkey(hotkey_name, hotkey_combination, post_processing, action_type):
    if 'dynamic_hotkeys' not in globals():
        global dynamic_hotkeys
        dynamic_hotkeys = {}
    dynamic_hotkeys[hotkey_name] = {
        'combination': hotkey_combination,
        'post_processing': post_processing,
        'action_type': action_type
    }
    keyboard.add_hotkey(hotkey_combination, lambda name=hotkey_name: handle_hotkey_action(name, dynamic_hotkeys))
    return f"Hotkey '{hotkey_combination}' for '{hotkey_name}' set up successfully."

def chat_with_bot(query):
    global chat_history
    response = generate_answer(query)
    chat_history.append((query, response))
    return chat_history, f"Model: {selected_model}\nURLs: {', '.join(dynamic_urls)}"

def add_url(url):
    global dynamic_urls, retriever
    dynamic_urls.append(url)
    retriever = setup_embedding(dynamic_urls, folder_path)
    return f"URL '{url}' added successfully."

def set_model_and_retriever(model_name):
    global selected_model, retriever
    selected_model = model_name
    set_model(model_name)
    retriever = setup_embedding(dynamic_urls, folder_path)
    return f"Model set to {model_name} and retriever updated."

# New function to update JSON file
def update_json_file(key, value):
    file_path = os.path.join('src', 'data.json')
    update_json(file_path, key, value)
    return f"Updated {key} in data.json with value: {value}"
