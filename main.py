from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from groq import Groq
from PyPDF2 import PdfReader

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Initialize Groq client with the provided API key
groq_client = Groq(api_key='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')

# Ensure uploads directory exists
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Load knowledge base
KNOWLEDGE_BASE_FILE = 'knowledge_base.txt'
knowledge_base = ''
if os.path.exists(KNOWLEDGE_BASE_FILE):
    with open(KNOWLEDGE_BASE_FILE, 'r', encoding='utf-8') as f:
        knowledge_base = f.read()

# Function to read PDF files
def read_pdf(file_path):
    text = ''
    try:
        with open(file_path, 'rb') as file:
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ''
    except Exception as e:
        print(f'Error reading PDF: {e}')
    return text

# Function to update knowledge base with uploaded files
def update_knowledge_base():
    global knowledge_base
    knowledge_base = ''
    # Include the initial knowledge base
    if os.path.exists(KNOWLEDGE_BASE_FILE):
        with open(KNOWLEDGE_BASE_FILE, 'r', encoding='utf-8') as f:
            knowledge_base += f.read() + '\n\n'

    # Include uploaded files
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if filename.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                knowledge_base += f.read() + '\n\n'
        elif filename.endswith('.pdf'):
            knowledge_base += read_pdf(file_path) + '\n\n'

# Route for the student interface
@app.route('/')
def index():
    return app.send_static_file('index.html')

# Route for the admin interface
@app.route('/admin')
def admin():
    return app.send_static_file('admin.html')

# Route to handle student questions
@app.route('/ask', methods=['POST'])
def ask():
    query = request.form.get('query')
    if not query:
        print("Error: No query provided in the request")
        return jsonify({'error': 'No query provided'}), 400

    print(f"Received query: {query}")

    # Update knowledge base with the latest uploaded files
    update_knowledge_base()
    print(f"Knowledge base content: {knowledge_base[:500]}...")  # Print first 500 chars for debugging

    # Query Groq with the knowledge base as context
    try:
        prompt = f"Based on the following knowledge base, answer the query in a concise, student-friendly manner using bullet points where appropriate:\n\n{knowledge_base}\n\nQuery: {query}"
        print("Sending request to Groq API...")
        response = groq_client.chat.completions.create(
            messages=[
                {'role': 'system', 'content': 'You are a helpful QA bot for students learning medical coding and RCM. Provide concise, accurate answers using bullet points where appropriate.'},
                {'role': 'user', 'content': prompt}
            ],
            model='llama3-8b-8192',  # Updated model
            temperature=0.5,
            max_tokens=500
        )
        print("Received response from Groq API")
        answer = response.choices[0].message.content
        print(f"Answer: {answer}")
        return jsonify({'answer': answer})
    except Exception as e:
        print(f"Error during Groq API call: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Route to handle file uploads from admin
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        print("Error: No file part in the request")
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        print("Error: No selected file")
        return jsonify({'error': 'No selected file'}), 400

    if file and (file.filename.endswith('.pdf') or file.filename.endswith('.txt')):
        filename = file.filename
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        print(f"File uploaded: {filename}")
        return jsonify({'message': 'File uploaded successfully'})
    else:
        print("Error: Invalid file type")
        return jsonify({'error': 'Invalid file type. Only PDF and TXT are allowed.'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))
