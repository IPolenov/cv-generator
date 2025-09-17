import requests
import openai
import os
import pdfplumber
from fpdf import FPDF
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
import re

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

def correct_url(url):
    url = url.strip()
    if not url:
        return ''
    # Add http if missing
    if not re.match(r'^https?://', url):
        url = 'http://' + url
    # Remove spaces
    url = url.replace(' ', '')
    return url

def extract_text_from_files(file_paths):
    texts = []
    for path in file_paths:
        try:
            if path.lower().endswith('.pdf'):
                texts.append(extract_pdf_text(path))
            elif path.lower().endswith(('.txt', '.md', '.csv')):
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    texts.append(f.read())
            else:
                texts.append(f"[Файл {os.path.basename(path)}: не поддерживается для извлечения текста]")
        except Exception as e:
            texts.append(f"[Ошибка при чтении {os.path.basename(path)}: {e}]")
    return '\n'.join(texts)

def gui_main():
    def on_generate():
        result_text.delete(1.0, tk.END)
        error_label.config(text='')
        url = url_entry.get().strip()
        direct_text = direct_text_field.get(1.0, tk.END).strip()
        file_paths = file_list.copy()
        # Try to fetch job description
        job_desc = ''
        if url:
            try:
                url_corr = correct_url(url)
                job_desc = fetch_job_description(url_corr)
            except Exception as e:
                error_label.config(text=f"Ошибка загрузки вакансии: {e}")
                job_desc = ''
        if not job_desc and direct_text:
            job_desc = direct_text
        if not job_desc:
            error_label.config(text="Не указано описание вакансии или текст для AI.")
            return
        # Extract text from files
        files_text = extract_text_from_files(file_paths) if file_paths else None
        # Compose prompt and call AI in a thread
        def ai_thread():
            try:
                cv = generate_cv(job_desc, files_text)
                result_text.insert(tk.END, cv)
                try:
                    save_cv_to_pdf(cv, "generated_cv.pdf")
                except Exception as e:
                    error_label.config(text=f"Ошибка сохранения PDF: {e}")
            except Exception as e:
                error_label.config(text=f"Ошибка генерации CV: {e}")
        threading.Thread(target=ai_thread).start()

    def on_add_files():
        paths = filedialog.askopenfilenames(title="Выберите файлы кандидата", filetypes=[
            ("Документы", "*.pdf *.txt *.md *.csv"),
            ("Все файлы", "*.*")
        ])
        for p in paths:
            if p not in file_list:
                file_list.append(p)
                files_box.insert(tk.END, os.path.basename(p))

    def on_clear_files():
        file_list.clear()
        files_box.delete(0, tk.END)

    root = tk.Tk()
    root.title("AI CV Generator")
    root.geometry("800x700")

    tk.Label(root, text="URL вакансии (с автоисправлением):").pack(anchor='w')
    url_entry = tk.Entry(root, width=100)
    url_entry.pack(fill='x', padx=5)

    tk.Label(root, text="Или введите/вставьте текст для AI (многострочно):").pack(anchor='w')
    direct_text_field = scrolledtext.ScrolledText(root, height=6)
    direct_text_field.pack(fill='x', padx=5)

    tk.Label(root, text="Файлы кандидата (PDF, TXT, MD, CSV):").pack(anchor='w')
    files_frame = tk.Frame(root)
    files_frame.pack(fill='x', padx=5)
    files_box = tk.Listbox(files_frame, height=4, width=60)
    files_box.pack(side='left', fill='y')
    file_list = []
    btn_add = tk.Button(files_frame, text="Добавить файлы", command=on_add_files)
    btn_add.pack(side='left', padx=5)
    btn_clear = tk.Button(files_frame, text="Очистить", command=on_clear_files)
    btn_clear.pack(side='left', padx=5)

    tk.Label(root, text="Результат (CV):").pack(anchor='w')
    result_text = scrolledtext.ScrolledText(root, height=16)
    result_text.pack(fill='both', expand=True, padx=5)

    error_label = tk.Label(root, text="", fg="red")
    error_label.pack(anchor='w', padx=5)

    btn_generate = tk.Button(root, text="Сгенерировать CV", command=on_generate)
    btn_generate.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    gui_main()
