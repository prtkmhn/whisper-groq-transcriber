
# Whisper-Groq-Transcriber

## Version

Whisper-Groq-Transcriber is a speech-to-text application that uses [OpenAI's Whisper model](https://openai.com/research/whisper) for transcription and integrates Groq for enhanced functionality.

## Features

- **Speech-to-Text Transcription**: Utilizes OpenAI's Whisper model to transcribe audio from the microphone.
- **Groq Integration**: Adds functionality to handle JSON data and respond to queries using Groq's API.
- **Flexible Recording Options**: Supports various recording modes and customizable activation keys.
- **Dynamic Hotkeys**: Allows users to set up custom hotkeys for specific actions.
- **Gradio UI**: Provides a user-friendly interface for interacting with the application.

## Usage

1. **Start Recording**: Use the default keyboard shortcut (`ctrl+shift+space`) to start recording.
2. **Stop Recording**: Choose from voice activity detection, press-to-toggle, or hold-to-record modes.
3. **Transcription**: The transcribed text will be automatically written to the active window.
4. **Send Text from Clipboard**: Pressing `Ctrl+Alt+V` sends the last item from the clipboard history as a prompt to the Groq Agent.
5. **Update Context**: When the user says "Update" followed by `<Keywords>`, Groq creates a JSON file with the keyword as the JSON key and the clipboard content as its value, which can be used to provide context to Groq.
6. **Dynamic Hotkeys**: Set up custom hotkeys for specific actions using the Gradio UI.
7. **Gradio UI**: Interact with the application through a web-based interface.

## Installation

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/prtkmhn/whisper-groq-transcriber.git
    cd Whisper-Groq-Transcriber
    ```

2. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Set Up Environment Variables**:
    Create a `.env` file in the root directory and add your API keys. You can skip OpenAi Api for locally run whisper model:
    ```plaintext
    OPENAI_API_KEY=your_openai_api_key
    GROQ_API_KEY=your_groq_api_key
    ```

## Configuration

The application uses a configuration file (`src/config.json`) to set various options. Here are the default settings:

```json
{
    "use_api": false,
    "api_options": {
        "model": "whisper-1",
        "language": null,
        "temperature": 0.0,
        "initial_prompt": null
    },
    "local_model_options": {
        "model": "base",
        "device": "auto",
        "compute_type": "auto",
        "language": null,
        "temperature": 0.0,
        "initial_prompt": null,
        "condition_on_previous_text": true,
        "vad_filter": false
    },
    "activation_key": "ctrl+shift+space",
    "recording_mode": "voice_activity_detection",
    "sound_device": null,
    "sample_rate": 16000,
    "silence_duration": 900,
    "writing_key_press_delay": 0.008,
    "noise_on_completion": false,
    "remove_trailing_period": true,
    "add_trailing_space": false,
    "remove_capitalization": false,
    "print_to_terminal": true,
    "hide_status_window": false
}
```

## Running the Application

1. **Start the Application**:
    ```bash
    python .\run.py   
    ```

2. **Gradio UI**:
    The Gradio UI will launch automatically. You can interact with the application through the web interface.

## Additional Functionality

### Groq Integration

The integration with Groq allows for advanced handling of JSON data and responding to user queries. The `groq_integration.py` file contains functions for setting the model, loading and saving JSON data, updating JSON data, and getting responses from the Groq API.

### Embedding and Retriever Setup

The `embedding_utils.py` file handles the setup of embeddings and retrievers for document processing. It includes functions for loading local documents, processing documents from URLs, chunking documents, and loading documents into a vector store.

### Transcription

The `transcription.py` file contains functions for recording audio, transcribing audio using either a local model or the OpenAI API, and post-processing the transcription.

### Main Script

The `main.py` file is the entry point of the application. It sets up the configuration, initializes the local model if needed, and handles the recording and transcription process. It also includes functions for setting up dynamic hotkeys and interacting with the Gradio UI.

## Screenshots and Videos

![Gradio Interface](https://github.com/prtkmhn/whisper-groq-transcriber/blob/main/images/gradio_interface.png)
*Gradio Interface*

![Hotkey Creation](https://github.com/prtkmhn/whisper-groq-transcriber/blob/main/images/hotkeycreation.png)
*Hotkey Creation*

![Changing Recording Mode](https://github.com/prtkmhn/whisper-groq-transcriber/blob/main/images/ChangeRecordingMode.png)
*Changing Recording Mode*

![Hotkey in Action](https://github.com/prtkmhn/whisper-groq-transcriber/blob/main/images/HotKeyInAction.mp4)
*Hotkey in Action*

![Recording Output](https://github.com/prtkmhn/whisper-groq-transcriber/blob/main/images/ctrl%2Balt%2Bspace_output.mp4)
*Recording Output*

## Credits

- Original project by [savbell](https://github.com/savbell/whisper-writer).
- Utilizes [OpenAI's Whisper model](https://openai.com/research/whisper) and [Groq](https://groq.com/).

## License

This project is licensed under the GNU General Public License. See the [LICENSE](LICENSE) file for details.
```
