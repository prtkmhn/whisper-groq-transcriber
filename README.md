
# Whisper-Groq-Transcriber

version


Whisper-Groq-Transcriber is a speech-to-text application that uses [OpenAI's Whisper model](https://openai.com/research/whisper) for transcription and integrates Groq for enhanced functionality.

## Features

- **Speech-to-Text Transcription**: Utilizes OpenAI's Whisper model to transcribe audio from the microphone.
- **Groq Integration**: Adds functionality to handle JSON data and respond to queries using Groq's API.
- **Flexible Recording Options**: Supports various recording modes and customizable activation keys.

## Usage

1. **Start Recording**: Use the default keyboard shortcut (`ctrl+shift+space`) to start recording.
2. **Stop Recording**: Choose from voice activity detection, press-to-toggle, or hold-to-record modes.
3. **Transcription**: The transcribed text will be automatically written to the active window.
4. **Send Text from Clipboard** : Press Ctrl+alt+v sends the last clipboard history as a Prompt to the Groq Agent
5. **Update Context** : When the user says Update <Keywords>, groq creates a json file with the keyword as json key and the clipboard content as it's value, this can be use to provide context to the Groq

## Additional Functionality

The integration with Groq allows for advanced handling of JSON data and responding to user queries.

## Getting Started

For detailed setup instructions, please refer to the original [Whisper-Readme.md](https://github.com/savbell/whisper-writer).

## Credits

- Original project by [savbell](https://github.com/savbell/whisper-writer).
- Utilizes [OpenAI's Whisper model](https://openai.com/research/whisper) and [Groq](https://groq.com/).

## License

This project is licensed under the GNU General Public License. See the [LICENSE](LICENSE) file for details.

---


