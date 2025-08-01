import os
import google.generativeai as genai
from flask import Flask, request, render_template, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from utils.pdf_utils import extract_text_from_pdf
from utils.mcq_utils import remove_duplicate_mcqs
from fpdf import FPDF

# Load environment variables and configure Gemini API
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise Exception("GOOGLE_API_KEY not found in .env file")

genai.configure(api_key=api_key)

# Flask setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'temp'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# MCQ Generation
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
    
    try:
        response = model.generate_content(prompt)
        raw_mcqs = response.text.strip()
        unique_mcqs = remove_duplicate_mcqs(raw_mcqs)
        return unique_mcqs
    except Exception as e:
        return f"Error generating MCQs: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html', mcqs=None)

@app.route('/upload', methods=['POST'])
def upload_pdf():
    try:
        file = request.files['pdf']
        num_questions = int(request.form['num_questions'])

        if not file or file.filename == '':
            return "No file uploaded!", 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Extract text
        text = extract_text_from_pdf(filepath)
        if not text.strip():
            return "PDF text extraction failed or returned empty content", 400

        # Generate MCQs
        mcqs = generate_mcqs_with_gemini(text, num_questions)
        return render_template('index.html', mcqs=mcqs)
    
    except Exception as e:
        return f"Server Error: {str(e)}", 500

@app.route('/download_mcqs')
def download_mcqs():
    mcqs_text = request.args.get('mcqs', '')
    if not mcqs_text:
        return "No MCQs to download", 400

    try:
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
        return f"PDF Generation Error: {str(e)}", 500


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
