from flask import Flask, request, jsonify, render_template
import boto3
from datetime import datetime
import json
import pyaudio
import wave
import os
import threading
import urllib.request
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Replace with your AWS access key and secret access key
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

# Replace with your AWS region and S3 bucket name
REGION = 'us-east-1'
BUCKET_NAME = 'aiml-stt-inputs'

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Audio parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

# Initialize boto3 clients
s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                         aws_secret_access_key=SECRET_KEY, region_name=REGION)
transcribe_client = boto3.client('transcribe', aws_access_key_id=ACCESS_KEY,
                                 aws_secret_access_key=SECRET_KEY, region_name=REGION)

@app.route('/')
def index():
    return render_template('index2.html')

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    try:
        audio_file = request.files['audio']
        if audio_file:
            file_name = f"audio_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
            file_path = os.path.join(app.root_path, file_name)
            audio_file.save(file_path)

            # Upload the audio file to S3
            s3_key = f"recordings/{file_name}"
            s3_client.upload_file(file_path, BUCKET_NAME, s3_key)

            # Delete the audio file from the local system
            os.remove(file_path)

            # Start transcription job
            job_name = f"transcription_job_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': f's3://{BUCKET_NAME}/{s3_key}'},
                MediaFormat='wav',
                LanguageCode='en-US'
            )

            # Wait for transcription job to complete
            while True:
                response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
                if response['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                    break

            if response['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
                transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                transcript_text = json.load(urllib.request.urlopen(transcript_uri))['results']['transcripts'][0]['transcript']
                return jsonify({"transcription": transcript_text})
            else:
                return jsonify({"error": "Transcription failed."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5000)