import os
from dotenv import load_dotenv
import openai
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
from urllib.parse import urlparse

chromedriver_autoinstaller.install()


load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

prompt_template = """
    너는 주식 시세 예측 전문가야. 아래는 삼성전자에 대한 최근 뉴스들과 주가 정보야.
    이걸 바탕으로 내일 삼성전자의 종가를 예측해줘.

    최근 뉴스:
    {news_summary}

    최근 종가 (마지막 5일):
    {price_data}

    예측 조건:
    - 내일(영업일 기준) 종가를 예측해줘.
    - 오직 숫자 하나만 예측해줘.
    - 추가 설명은 하지마.
"""

def get_price_data(ticker="005930.KS", days=5):
    df = yf.download(ticker, period="7d", interval="1d")
    close_prices = df["Close"].dropna().tail(days).tolist()
    return [round(p) for p in close_prices]  # 정수 변환

def predict_price_gpt(news_summary, price_data):
    prompt = prompt_template.format(
        news_summary=news_summary,
        price_data=price_data
    )

def get_news_urls(keyword="삼성전자", max_count=8):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(options=options)
        print("✅ driver 생성 성공")
    except Exception as e:
        print("❌ driver 생성 실패:", e)

    driver.get(f"https://search.naver.com/search.naver?where=news&query={keyword}")
    #driver.get("https://www.naver.com")
    print("🔍 현재 URL:", driver.current_url)
    print("🔍 페이지 제목:", driver.title)

    with open("naver_test.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    print("📄 HTML 길이:", len(driver.page_source))

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[target="_blank"]'))
        )
    except Exception as e:
        print("❌ 대기 중 에러 발생:", e)
    finally:
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("✅ debug.html 저장 완료")

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    links = []
    seen_domains = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not any(domain in href for domain in [
            "www.newsis.com",           # 뉴시스
            "www.yna.co.kr",            # 연합뉴스
            "www.hankyung.com",         # 한국경제    
            "www.mk.co.kr",             # 매일경제
            "www.hani.co.kr",           # 한겨레
            "www.khan.co.kr",           # 경향신문
            "www.donga.com",            # 동아일보
            "www.ohmynews.com",         # 오마이뉴스
        ]):
            continue

        # 언론사 도메인만 추출
        netloc = urlparse(href).netloc
        domain = ".".join(netloc.split(".")[-2:])  # 예: newsis.com

        if domain not in seen_domains:
            seen_domains.add(domain)
            links.append(href)

        if len(links) >= max_count:
            break

    return links

def extract_news_body(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    body = soup.select_one("#dic_area")
    return body.text.strip() if body else ""


def summarize_articles_with_gpt(article_texts):
    full_text = "\n\n".join(article_texts)[:6000]  # 길이 제한
    prompt = """
        너는 금융 뉴스 분석가야. 아래는 삼성전자 관련 기사들이야.
        이걸 바탕으로 최근 이슈를 4줄 정도로 요약해줘.

        {full_text}
        """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()

def get_samsung_news_summary():
    urls = get_news_urls()
    articles = [extract_news_body(url) for url in urls]
    #summary = summarize_articles_with_gpt(articles)
    #return summary

print(get_news_urls())
#print(get_samsung_news_summary())