import requests
import openai
import os

# Set your OpenAI API key here or via environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your-api-key-here')
openai.api_key = OPENAI_API_KEY

def fetch_job_description(url):
    """Download job description from the given URL."""
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def generate_cv(job_description):
    """Send job description to ChatGPT and get a tailored CV."""
    prompt = f"""
    На основе этого описания вакансии:
    {job_description}
    Сгенерируй CV кандидата, максимально подходящего под требования вакансии. Формат: ФИО, контакты, опыт, навыки, образование, достижения.
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )
    return response['choices'][0]['message']['content']

def main():
    url = input("Введите ссылку на описание вакансии: ")
    job_description = fetch_job_description(url)
    cv = generate_cv(job_description)
    print("\nСгенерированное CV:\n")
    print(cv)

if __name__ == "__main__":
    main()

