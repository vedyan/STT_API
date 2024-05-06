from flask import Flask, request, jsonify, render_template
import boto3
from datetime import datetime
import os
import threading
import requests
from dotenv import load_dotenv
import logging

app = Flask(__name__)

# Configure logging
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

...

# Load environment variables from .env file
load_dotenv()

# Get the port from the environment variable or use 4000 as default
port = int(os.environ.get("PORT", 4000))
...

# Replace with your AWS access key and secret access key
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

# Replace with your AWS region and S3 bucket name
REGION = 'us-east-1'
BUCKET_NAME = 'aiml-stt-inputs'

# Initialize boto3 clients
s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                         aws_secret_access_key=SECRET_KEY, region_name=REGION)
transcribe_client = boto3.client('transcribe', aws_access_key_id=ACCESS_KEY,
                                 aws_secret_access_key=SECRET_KEY, region_name=REGION)

@app.route('/')
def index():
    # logging.info('Received request: GET /')
    return render_template('frontend4.html')

def record_audio(filename, duration):
    os.system(f"arecord -d {duration} -f cd -t wav {filename}")

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    # logging.info('Received request: POST /transcribe')
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

            threading.Thread(target=record_audio, args=(file_path, 5)).start()

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
                transcript_text = requests.get(transcript_uri).json()['results']['transcripts'][0]['transcript']
                return jsonify({"transcription": transcript_text})
            else:
                return jsonify({"error": "Transcription failed."}), 500
    except Exception as e:
        # logging.error(f'Error processing request: {str(e)}')
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)