import json
import os
import queue
import threading
import time
import keyboard
from audioplayer import AudioPlayer
import pyperclip
from pynput.keyboard import Controller
from transcription import create_local_model, record_and_transcribe
from status_window import StatusWindow
from groq_integration import get_groq_response, send_latest_text_to_groq, update_json  # Import the new Groq integration

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
            'model': 'whisper-1',
            'language': None,
            'temperature': 0.0,
            'initial_prompt': None
        },
        'local_model_options': {
            'model': 'base',
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
        if recording_thread.stop_transcription:  # Check if the transcription was stopped
            break
        pyinput_keyboard.press(letter)
        pyinput_keyboard.release(letter)
        time.sleep(interval)

def format_keystrokes(key_string):
    return '+'.join(word.capitalize() for word in key_string.split('+'))

def on_groq_shortcut():
    response = send_latest_text_to_groq()
    typewrite(response, interval=config['writing_key_press_delay'])

def setup_dynamic_hotkeys():
    dynamic_hotkeys = {}
    while True:
        hotkey_name = input("Enter the name for the new hotkey (or press Enter to finish): ")
        if not hotkey_name:
            break
        hotkey_combination = input(f"Enter the hotkey combination for '{hotkey_name}' (or press Enter to skip): ")
        if not hotkey_combination:
            print(f"Skipping '{hotkey_name}'")
            continue
        dynamic_hotkeys[hotkey_name] = hotkey_combination
        keyboard.add_hotkey(hotkey_combination, lambda name=hotkey_name: save_clipboard_to_json(name))
        print(f"Hotkey '{hotkey_combination}' for '{hotkey_name}' set up successfully.")
    return dynamic_hotkeys

def save_clipboard_to_json(hotkey_name):
    clipboard_content = pyperclip.paste()
    update_json(os.path.join('src', 'data.json'), hotkey_name, clipboard_content)
    print(f"Saved clipboard content to '{hotkey_name}' in data.json")

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
keyboard.add_hotkey(config['activation_key'], on_shortcut)
keyboard.add_hotkey('ctrl+alt+space', on_shortcut)  # Add new hotkey for Groq integration
keyboard.add_hotkey('alt+c', stop_recording)  # Add hotkey to stop recording
keyboard.add_hotkey('ctrl+alt+v', on_groq_shortcut)  # Add hotkey to paste clipboard content

# Set up dynamic hotkeys
dynamic_hotkeys = setup_dynamic_hotkeys()

try:
    keyboard.wait()  # Keep the script running to listen for the shortcut
except KeyboardInterrupt:
    print('\nExiting the script...')
    os.system('exit')