import requests
import openai
import os
import pdfplumber
from fpdf import FPDF
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
import re

# Supported models/providers
MODEL_OPTIONS = [
    ("OpenAI GPT-4", "openai-gpt-4"),
    ("OpenAI GPT-3.5", "openai-gpt-3.5"),
    ("Google Gemini Pro", "google-gemini-pro")
]

# Store API keys per provider
api_keys = {
    "openai": os.getenv('OPENAI_API_KEY', ''),
    "google": os.getenv('GOOGLE_API_KEY', '')
}

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

def generate_cv(job_description, fact_table_text=None, model_id="openai-gpt-4", api_key=None):
    """Send job description and optional fact table to selected AI model and get a tailored CV."""
    prompt = f"""
    На основе этого описания вакансии:
    {job_description}
    """
    if fact_table_text:
        prompt += f"\nФакт-таблица кандидата (PDF):\n{fact_table_text}\n"
    prompt += "Сгенерируй CV кандидата, максимально подходящего под требования вакансии. Формат: ФИО, контакты, опыт, навыки, образование, достижения."

    if model_id.startswith("openai"):
        if not api_key:
            raise ValueError("Не указан API ключ OpenAI.")
        import openai
        client = openai.OpenAI(api_key=api_key)
        model = "gpt-4" if model_id == "openai-gpt-4" else "gpt-3.5-turbo"
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        return response.choices[0].message.content
    elif model_id == "google-gemini-pro":
        # Placeholder for Google Gemini API integration
        raise NotImplementedError("Google Gemini API integration is not implemented yet.")
    else:
        raise ValueError("Неизвестная модель/провайдер.")

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
    def on_model_change(event=None):
        sel = model_var.get()
        if sel.startswith("OpenAI"):
            api_key_entry.delete(0, tk.END)
            api_key_entry.insert(0, api_keys.get("openai", ""))
        elif sel.startswith("Google"):
            api_key_entry.delete(0, tk.END)
            api_key_entry.insert(0, api_keys.get("google", ""))

    def on_api_key_change(event=None):
        sel = model_var.get()
        key = api_key_entry.get().strip()
        if sel.startswith("OpenAI"):
            api_keys["openai"] = key
        elif sel.startswith("Google"):
            api_keys["google"] = key

    def on_generate():
        result_text.delete(1.0, tk.END)
        error_label.config(text='')
        url = url_entry.get().strip()
        direct_text = direct_text_field.get(1.0, tk.END).strip()
        file_paths = file_list.copy()
        model_label, model_id = next((l, v) for l, v in MODEL_OPTIONS if l == model_var.get())
        api_key = api_key_entry.get().strip()
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
                cv = generate_cv(job_desc, files_text, model_id=model_id, api_key=api_key)
                result_text.insert(tk.END, cv)
                try:
                    save_cv_to_pdf(cv, "generated_cv.pdf")
                except Exception as e:
                    error_label.config(text=f"Ошибка сохранения PDF: {e}")
            except NotImplementedError as e:
                error_label.config(text=f"{e}")
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
    root.geometry("800x750")

    # Top frame for API key and model selection
    top_frame = tk.Frame(root)
    top_frame.pack(fill='x', padx=5, pady=5)
    tk.Label(top_frame, text="API ключ:").pack(side='left')
    api_key_entry = tk.Entry(top_frame, width=40)
    api_key_entry.pack(side='left', padx=5)
    tk.Label(top_frame, text="Модель:").pack(side='left', padx=(10,0))
    model_var = tk.StringVar(value=MODEL_OPTIONS[0][0])
    model_menu = tk.OptionMenu(top_frame, model_var, *(l for l, v in MODEL_OPTIONS), command=on_model_change)
    model_menu.pack(side='left', padx=5)
    api_key_entry.bind('<FocusOut>', on_api_key_change)
    api_key_entry.bind('<Return>', on_api_key_change)

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

    on_model_change()  # Set initial API key
    root.mainloop()

if __name__ == "__main__":
    gui_main()
