from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
import os
import io
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract
import requests
import csv
import openpyxl

app = Flask(__name__)
CORS(app)
app.secret_key = 'your_secret_key'  # Change this!

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Placeholder for Gemini API key
GEMINI_API_KEY = 'AIzaSyAIE8d3BV_adTDP87GscCDZRljrR0bOOQs'
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=' + GEMINI_API_KEY

# Helper to extract text from PDF
def extract_text_from_pdf(file_stream):
    reader = PdfReader(file_stream)
    text = ''
    for page in reader.pages:
        text += page.extract_text() or ''
    return text

# Helper to extract text from image
def extract_text_from_image(file_stream):
    image = Image.open(file_stream)
    text = pytesseract.image_to_string(image)
    return text

# Helper to extract text from text file
def extract_text_from_txt(file_stream):
    return file_stream.read().decode('utf-8')

# Helper to extract text from CSV
def extract_text_from_csv(file_stream):
    file_stream.seek(0)
    reader = csv.reader(io.StringIO(file_stream.read().decode('utf-8')))
    rows = list(reader)
    text = '\n'.join([', '.join(row) for row in rows])
    return text

# Helper to extract text from XLSX
def extract_text_from_xlsx(file_stream):
    file_stream.seek(0)
    wb = openpyxl.load_workbook(file_stream, read_only=True, data_only=True)
    text = ''
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(values_only=True):
            text += ', '.join([str(cell) if cell is not None else '' for cell in row]) + '\n'
    return text

# Store uploaded content in session
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower()
    content = ''
    if ext == 'pdf':
        content = extract_text_from_pdf(file)
    elif ext in ['png', 'jpg', 'jpeg']:
        content = extract_text_from_image(file)
    elif ext in ['txt', 'md']:
        content = extract_text_from_txt(file)
    elif ext == 'csv':
        content = extract_text_from_csv(file)
    elif ext == 'xlsx':
        content = extract_text_from_xlsx(file)
    else:
        return jsonify({'error': 'Unsupported file type'}), 400
    session['uploaded_content'] = content
    return jsonify({'message': 'File uploaded and content extracted.'})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '')
    uploaded_content = session.get('uploaded_content', '')
    prompt = f"User message: {user_message}\n\nUploaded file content (if any): {uploaded_content}"
    # Call Gemini API
    headers = {'Content-Type': 'application/json'}
    payload = {
        'contents': [{
            'parts': [{
                'text': prompt
            }]
        }]
    }
    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        gemini_reply = response.json()['candidates'][0]['content']['parts'][0]['text']
        return jsonify({'reply': gemini_reply})
    else:
        print('Gemini API error:', response.text)
        return jsonify({'error': 'Gemini API error', 'details': response.text}), 500

if __name__ == '__main__':
    app.run(debug=True) 