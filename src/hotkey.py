# hotkey.py

import os
import json
import keyboard
import pyperclip
from pynput.keyboard import Controller
from helpers import typewrite, get_groq_response, update_json, generate_answer, setup_embedding

# Path to save hotkeys
hotkeys_path = os.path.join('src', 'hotkeys.json')

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

def create_hotkey(hotkey_name, hotkey_combination, post_processing, action_type, dynamic_hotkeys, config):
    dynamic_hotkeys[hotkey_name] = {
        'combination': hotkey_combination,
        'post_processing': post_processing,
        'action_type': action_type
    }
    keyboard.add_hotkey(hotkey_combination, lambda name=hotkey_name: handle_hotkey_action(name, dynamic_hotkeys, config))
    save_hotkeys(dynamic_hotkeys)
    return f"Hotkey '{hotkey_combination}' for '{hotkey_name}' set up successfully."

def update_hotkey(hotkey_name, new_combination, new_post_processing, new_action_type, config):
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

def save_hotkeys(hotkeys):
    with open(hotkeys_path, 'w') as file:
        json.dump(hotkeys, file, indent=2)

def load_hotkeys():
    if os.path.exists(hotkeys_path):
        with open(hotkeys_path, 'r') as file:
            return json.load(file)
    return {}

def get_current_hotkeys():
    return json.dumps(load_hotkeys(), indent=2)