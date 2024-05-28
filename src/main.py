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
from groq_integration import get_groq_response, send_latest_text_to_groq, update_json, set_model, setup_embedding  # Import the new Groq integration
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
        post_processing = input(f"Enter the post-processing command for '{hotkey_name}' (or press Enter to skip): ")
        action_type = input(f"Do you want to save the output to JSON or print it directly? (Enter 'json' or 'print'): ").strip().lower()
        
        dynamic_hotkeys[hotkey_name] = {
            'combination': hotkey_combination,
            'post_processing': post_processing,
            'action_type': action_type
        }
        
        keyboard.add_hotkey(hotkey_combination, lambda name=hotkey_name: handle_hotkey_action(name, dynamic_hotkeys))
        print(f"Hotkey '{hotkey_combination}' for '{hotkey_name}' set up successfully.")
    return dynamic_hotkeys

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

def upload_pdf(pdf):
    global retriever
    pdf_path = os.path.join(folder_path, pdf.name)
    with open(pdf_path, "wb") as f:
        f.write(pdf.read())
    retriever = setup_embedding(dynamic_urls, folder_path)
    return f"PDF '{pdf.name}' uploaded successfully."

def set_model_and_retriever(model_name):
    global selected_model, retriever
    selected_model = model_name
    set_model(model_name)
    retriever = setup_embedding(dynamic_urls, folder_path)
    return f"Model set to {model_name} and retriever updated."

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

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("# WhisperWriter with Gradio UI")
    
    with gr.Tab("Chat with Bot"):
        model_selector = gr.Dropdown(["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768"], label="Select Model", value="llama3-8b-8192")
        model_selector.change(set_model_and_retriever, inputs=model_selector, outputs=None)
        
        initial_prompt = gr.Textbox(label="Initial Prompt", placeholder="Enter initial prompt for the chatbot...")
        chat_output = gr.Chatbot(label="Chat History")
        query = gr.Textbox(label="Your Query", placeholder="Type your message here...")
        chat_button = gr.Button("Chat")
        
        chat_button.click(chat_with_bot, inputs=[query], outputs=[chat_output, gr.Textbox(label="Details")])
    
    with gr.Tab("Create Hotkey"):
        hotkey_name = gr.Textbox(label="Hotkey Name")
        hotkey_combination = gr.Textbox(label="Hotkey Combination")
        post_processing = gr.Textbox(label="Post-Processing Command")
        action_type = gr.Radio(["json", "print"], label="Action Type")
        create_button = gr.Button("Create Hotkey")
        create_output = gr.Textbox(label="Output")
        
        create_button.click(create_hotkey, inputs=[hotkey_name, hotkey_combination, post_processing, action_type], outputs=create_output)
    
    with gr.Tab("Add URL"):
        url_input = gr.Textbox(label="Enter URL")
        add_url_button = gr.Button("Add URL")
        add_url_output = gr.Textbox(label="Output")
        
        add_url_button.click(add_url, inputs=url_input, outputs=add_url_output)
        
        pdf_input = gr.File(label="Upload PDF")
        upload_pdf_button = gr.Button("Upload PDF")
        upload_pdf_output = gr.Textbox(label="Output")
        
        upload_pdf_button.click(upload_pdf, inputs=pdf_input, outputs=upload_pdf_output)

demo.launch()

try:
    keyboard.wait()  # Keep the script running to listen for the shortcut
except KeyboardInterrupt:
    print('\nExiting the script...')
    os.system('exit')
