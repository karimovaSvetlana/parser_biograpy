import requests
import wikipediaapi
from bs4 import BeautifulSoup
from huggingface_hub import login
import openpyxl
from openpyxl import Workbook
from transformers import MBartForConditionalGeneration, MBartTokenizer, pipeline


def load_summarizer(model_name: str = "facebook/mbart-large-50"):
    tokenizer = MBartTokenizer.from_pretrained(model_name)
    model = MBartForConditionalGeneration.from_pretrained(model_name)
    summarizer = pipeline("summarization", model=model, tokenizer=tokenizer)
    return summarizer


def search_wikipedia(full_name):
    """
    Ищет статью в Википедии.
    """
    wiki_wiki = wikipediaapi.Wikipedia(user_agent="MyApp/1.0 (myemail@example.com)", language="ru")
    page = wiki_wiki.page(full_name)

    if page.exists():
        return page.summary, [page.fullurl]
    return None, []

def search_web(full_name):
    """
    Выполняет поиск в DuckDuckGo и берет информацию с топ-5 сайтов.
    """
    search_url = f"https://www.duckduckgo.com/html/?q={full_name} биография"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    links = [a['href'] for a in soup.find_all('a', href=True) if 'http' in a['href']][:5]
    
    bio_texts = []
    for link in links:
        try:
            page_response = requests.get(link, headers=headers, timeout=5)
            page_soup = BeautifulSoup(page_response.text, 'html.parser')
            paragraphs = page_soup.find_all('p')
            text = ' '.join([p.get_text() for p in paragraphs])
            bio_texts.append((text, link))
        except Exception:
            continue
    
    return bio_texts

def summarize_biography(text):
    """
    Суммаризует текст с помощью mBART.
    """
    if len(text) > 1000:
        text = text[:1000]
    summary = summarizer(text, max_length=500, min_length=50, do_sample=False)
    return summary[0]['summary_text']

def save_to_excel(full_name, summary, sources):
    """
    Сохраняет суммаризованные данные и источники в Excel.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Биография"
    
    ws.append(["ФИО", "Суммаризованная информация", "Источники"])
    ws.append([full_name, summary, "\n".join(sources)])
    
    filename = f"{full_name.replace(' ', '_')}.xlsx"
    wb.save(filename)
    print(f"Данные сохранены в {filename}")


if __name__ == "__main__":
    login(token=os.environ["HF_TOKEN"] , add_to_git_credential=True)
    summarizer = load_summarizer()

    full_name = input("Введите ФИО: ")
    
    bio_text, sources = search_wikipedia(full_name)
    
    if not bio_text:
        web_results = search_web(full_name)
        bio_text = " ".join([text for text, _ in web_results])
        sources = [url for _, url in web_results]
    
    if bio_text:
        summarized_info = summarize_biography(bio_text)
        save_to_excel(full_name, summarized_info, sources)
    else:
        print("Информацию не удалось найти.")
