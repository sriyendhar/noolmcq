import os
from flask import Flask, request, render_template, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from utils.pdf_utils import extract_text_from_pdf
from utils.mcq_utils import remove_duplicate_mcqs
from fpdf import FPDF
import google.generativeai as genai
import sys

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'temp'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def generate_mcqs_with_gemini(text, num_questions):
    model = genai.GenerativeModel(model_name="models/gemini-2.0-flash")
    prompt = f"""
You are an exam question generator.

From the following text, generate exactly {num_questions} completely unique and non-redundant multiple-choice questions (MCQs). Each question should:
- Cover a different concept or fact.
- Not repeat wording or meaning of other questions.
- Include 4 options labeled A, B, C, D.
- End with the correct answer in the format: Answer: <option>

TEXT:
{text[:3000]}

Format:
Q1. ...
A) ...
B) ...
C) ...
D) ...
Answer: ...
"""
    response = model.generate_content(prompt)
    raw_mcqs = response.text.strip()
    unique_mcqs = remove_duplicate_mcqs(raw_mcqs)
    return unique_mcqs

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_pdf():
    try:
        file = request.files.get('pdf')
        num_questions = int(request.form.get('num_questions', 5))

        if not file:
            return "No file uploaded", 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        text = extract_text_from_pdf(filepath)
        mcqs = generate_mcqs_with_gemini(text, num_questions)

        return render_template('index.html', mcqs=mcqs)
    except Exception as e:
        print("Upload error:", e, file=sys.stderr)
        return "Error processing the PDF", 500

@app.route('/download_mcqs')
def download_mcqs():
    try:
        mcqs_text = request.args.get('mcqs', '')
        if not mcqs_text:
            return "No MCQs to download", 400

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)

        for line in mcqs_text.split('\n'):
            pdf.multi_cell(0, 10, line)

        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'generated_mcqs.pdf')
        pdf.output(output_path)

        return send_file(output_path, as_attachment=True)
    except Exception as e:
        print("PDF download error:", e, file=sys.stderr)
        return "Error generating PDF", 500

# Global error handler
@app.errorhandler(Exception)
def handle_exception(e):
    print("Global error:", e, file=sys.stderr)
    return "Something went wrong", 500
