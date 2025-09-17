import requests
import openai
import os
import pdfplumber
from fpdf import FPDF

# Set your OpenAI API key here or via environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your-api-key-here')
openai.api_key = OPENAI_API_KEY

def fetch_job_description(url):
    """Download job description from the given URL."""
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def extract_pdf_text(pdf_path):
    """Extract text from a PDF file."""
    if not pdf_path:
        return ""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def generate_cv(job_description, fact_table_text=None):
    """Send job description and optional fact table to ChatGPT and get a tailored CV."""
    prompt = f"""
    На основе этого описания вакансии:
    {job_description}
    """
    if fact_table_text:
        prompt += f"\nФакт-таблица кандидата (PDF):\n{fact_table_text}\n"
    prompt += "Сгенерируй CV кандидата, максимально подходящего под требования вакансии. Формат: ФИО, контакты, опыт, навыки, образование, достижения."

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )
    return response.choices[0].message.content

def save_cv_to_pdf(cv_text, output_path):
    """Save the generated CV to a PDF file."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in cv_text.split('\n'):
        pdf.multi_cell(0, 10, line)
    pdf.output(output_path)

def get_job_description_from_input(user_input):
    """Detect if input is a URL or plain text and return the job description."""
    if user_input.strip().lower().startswith(('http://', 'https://')):
        return fetch_job_description(user_input.strip())
    else:
        return user_input.strip()

def get_job_description_from_multiline_input():
    print("Вставьте описание вакансии (или ссылку на него). Введите @@@@ на новой строке для завершения ввода:")
    lines = []
    while True:
        line = input()
        if line.strip() == "@@@@":
            break
        lines.append(line)
    # Remove empty lines at start/end
    lines = [l for l in lines if l.strip()]
    if len(lines) == 1 and lines[0].strip().lower().startswith(('http://', 'https://')):
        return fetch_job_description(lines[0].strip())
    return "\n".join(lines)

def main():
    job_description = get_job_description_from_multiline_input()
    pdf_path = input("Введите путь к PDF-файлу с факт-таблицей (или оставьте пустым): ").strip()
    fact_table_text = extract_pdf_text(pdf_path) if pdf_path else None
    cv = generate_cv(job_description, fact_table_text)
    print("\nСгенерированное CV:\n")
    print(cv)
    output_pdf = "generated_cv.pdf"
    save_cv_to_pdf(cv, output_pdf)
    print(f"\nCV сохранено в PDF: {output_pdf}")

if __name__ == "__main__":
    main()
