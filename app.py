import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from pydub import AudioSegment
import speech_recognition as sr
from googletrans import Translator

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
TRANSLATED_FOLDER = 'translated_files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TRANSLATED_FOLDER'] = TRANSLATED_FOLDER

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSLATED_FOLDER, exist_ok=True)

def prepare_voice_file(path: str) -> str:
    """Converts the uploaded audio file to WAV format with required properties."""
    try:
        audio_file = AudioSegment.from_file(path)
        wav_file = os.path.splitext(path)[0] + '_converted.wav'
        audio_file = audio_file.set_frame_rate(16000).set_channels(1)
        audio_file.export(wav_file, format='wav')
        return wav_file
    except Exception as e:
        raise RuntimeError(f"Error in converting audio file: {e}")

def transcribe_audio(audio_file_path, language) -> str:
    """Converts audio speech to text using Google Speech Recognition."""
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file_path) as source:
        audio_data = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio_data, language=language)
        return text
    except sr.UnknownValueError:
        raise RuntimeError("Speech Recognition could not understand the audio")
    except sr.RequestError:
        raise RuntimeError("Error connecting to the Google Speech Recognition API")

def translate_to_english(text: str, source_lang: str) -> str:
    """Translates the transcribed text to English using Google Translate."""
    translator = Translator()
    try:
        translation = translator.translate(text, src=source_lang, dest='en')
        return translation.text
    except Exception as e:
        raise RuntimeError(f"Translation error: {e}")

def save_translation_to_file(translated_text: str, filename: str) -> str:
    """Saves the translated text into a file."""
    file_path = os.path.join(app.config['TRANSLATED_FOLDER'], filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(translated_text)
    return file_path

@app.route('/')
def home():
    """Home page route."""
    return render_template('home.html')

@app.route('/translate')
def translate_page():
    """Translation page route."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles audio file uploads, transcription, and translation."""
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    file = request.files['audio']
    language = request.form.get('language')

    if not file.filename or not language:
        return jsonify({'error': 'File or language not provided'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    try:
        wav_file = prepare_voice_file(filepath)
        transcription = transcribe_audio(wav_file, language)

        # Ensure the language is supported for translation
        supported_languages = ['hi', 'en', 'ur', 'bn', 'pa', 'ta', 'te', 'kn', 'ml']
        if language[:2] not in supported_languages:
            return jsonify({'error': 'Language not supported for translation'}), 400

        translation = translate_to_english(transcription, language[:2])
        translated_file_path = save_translation_to_file(
            translation, file.filename.split('.')[0] + '_translated.txt'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({
        'transcription': transcription,
        'translation': translation,
        'download_link': f"/download/{os.path.basename(translated_file_path)}"
    })

@app.route('/download/<filename>')
def download_file(filename):
    """Handles the downloading of translated text files."""
    return send_from_directory(app.config['TRANSLATED_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
