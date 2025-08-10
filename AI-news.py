

######################################################################################################################################
#version 4
# 📦 Built-in libraries
import re
import json
import urllib.parse
from datetime import datetime, timedelta
import os
import sys
from datetime import datetime
import nltk
# 🌐 Third-party libraries
import feedparser
from bs4 import BeautifulSoup
from transformers import pipeline
from newspaper import Article, ArticleException
import torch
import psutil  # תוסיף לייבוא אם עדיין אין
from nltk.tokenize import word_tokenize
import hashlib
import requests
from urllib.parse import urlparse
import html
import time
import urllib.parse


# 🔹 הגדרות קבועות
RSS_FEED_URL = ["https://www.google.com/alerts/feeds/09319502742519693922/9130105644423405796",
                "https://www.google.com/alerts/feeds/09319502742519693922/2709858297864352166",
                "https://www.google.com/alerts/feeds/09319502742519693922/5074408424556604747",
                "https://www.google.com/alerts/feeds/09319502742519693922/17636026846122575117",
                "https://www.google.com/alerts/feeds/09319502742519693922/6560690250207293083",
                "https://www.google.com/alerts/feeds/09319502742519693922/760654435510193703",
                "https://www.google.com/alerts/feeds/09319502742519693922/14847802292678122746",
                "https://www.google.com/alerts/feeds/09319502742519693922/16682802628855175014",
                "https://www.google.com/alerts/feeds/09319502742519693922/11207419750880160977",
                "https://www.google.com/alerts/feeds/09319502742519693922/7167494616409468847",
                "https://www.google.com/alerts/feeds/09319502742519693922/4978653762718633940",
                "https://www.google.com/alerts/feeds/09319502742519693922/14188242328750799264"]

rss_country_map = {
                "https://www.google.com/alerts/feeds/09319502742519693922/9130105644423405796": "United States",
                "https://www.google.com/alerts/feeds/09319502742519693922/2709858297864352166": "United States",
                "https://www.google.com/alerts/feeds/09319502742519693922/5074408424556604747": "United States",
                "https://www.google.com/alerts/feeds/09319502742519693922/17636026846122575117": "United States",
                "https://www.google.com/alerts/feeds/09319502742519693922/6560690250207293083": "United States",
                "https://www.google.com/alerts/feeds/09319502742519693922/760654435510193703": "United States",
                "https://www.google.com/alerts/feeds/09319502742519693922/14847802292678122746": "United States",
                "https://www.google.com/alerts/feeds/09319502742519693922/16682802628855175014": "All World",
                "https://www.google.com/alerts/feeds/09319502742519693922/11207419750880160977": "All World",
}

API_KEY = "AIzaSyCyQzdgM7kLZRgy0HKuZFaoM55IhZwVgTE"
SEARCH_ENGINE_ID = "c55ce9e630f0f4e4e"
TELEGRAM_BOT_TOKEN = "8184679748:AAF8CAYqFgaGcbqffZxhO2eEb0n6eaASKe4"
TELEGRAM_CHAT_ID = "-1002548211860"
POSTED_NEWS_FILE = "ai-news_posted.json"
# 🔗 כתובת ה-Webhook של Microsoft Teams
TEAMS_WEBHOOK_URL = ""



#---------------------------------------------------------------------------------------------------------------------------------------------------------
#פונקציות לשליפת חדשות
#---------------------------------------------------------------------------------------------------------------------------------------------------------
#1
def get_google_alerts(time_range=1):
    """
    שולף כתבות מ-RSS שהוגדרו מראש.
    :param time_range: מספר הימים לאחור לשליפת חדשות (ברירת מחדל: 1 - היום הנוכחי)
    :return: רשימת כתבות חדשות עם שדות נוספים
    """
    articles = []
    today = datetime.today().date()
    start_date = today - timedelta(days=time_range)
    invalid_count = 0

    for rss_url in RSS_FEED_URL:
        try:
            response = requests.get(rss_url, timeout=10)
            response.raise_for_status()
            feed = feedparser.parse(response.text)

            if not feed.entries:
                print(f"⚠️No articles found in RSS: {rss_url}")
                continue

            print(f"📡 RSS Source: {rss_url} - {len(feed.entries)} articles found.")
            rss_source = rss_country_map.get(rss_url, "Unknown")  # כאן מוסף שדה המדינה

            for entry in feed.entries:
                try:
                    article_id = entry.id if hasattr(entry, "id") else str(datetime.now().timestamp())
                    title = clean_text(entry.title) if hasattr(entry, "title") else None
                    raw_url = entry.link if hasattr(entry, "link") else None
                    clean_url = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query).get("url", [raw_url])[0] if raw_url else None
                    summary = clean_text(entry.summary) if hasattr(entry, "summary") else ""
                    published_dt = datetime(*entry.published_parsed[:6]) if hasattr(entry, "published_parsed") else datetime.now()
                    published_date_obj = published_dt.date()
                    published_date = published_dt.strftime("%Y-%m-%d")
                    published_time = published_dt.strftime("%H:%M:%S")

                    # סינון לפי טווח תאריכים
                    if start_date <= published_date_obj <= today:
                        if not title or not clean_url:
                            print(f"⚠️ Invalid article (missing title or URL) – skipping.")
                            invalid_count += 1
                            continue

                        # בדיקת אורך התקציר
                        word_count = len(summary.split())
                        if word_count < 10:
                            print(f"⚠️ Summary too short ({word_count} words) – skipping.")
                            invalid_count += 1
                            continue

                        source = extract_source_from_url(clean_url)
                        keywords = extract_keywords(summary)
                        text_hash = compute_text_hash(summary) if summary.strip() else None

                        articles.append({
                            "id": article_id,
                            "title": title,
                            "url": clean_url,
                            "text_hash": text_hash,
                            "published_date": published_date,
                            "published_time": published_time,
                            "summary": summary,
                            "source": source,
                            "keywords": keywords,
                            "rss_source": rss_source  # הוספת המדינה
                        })
                        print(f"✅ Article added: {title}")

                except Exception as e:
                    print(f"⚠️ Error processing article from RSS ({rss_url}): {e}")


        except requests.RequestException as e:
            print(f"❌ Failed to fetch RSS from - {rss_url}: {e}")

    print(f"📡 Total new articles retrieved from all RSS feeds: {len(articles)} (Skipped: {invalid_count})")
    return articles




#2
def fetch_full_text(url, max_words=600):
    """
    שליפת טקסט מלא מכתבה
    :param url: כתובת URL של המאמר
    :param max_words: מספר המילים המקסימלי לשליפה (ברירת מחדל: 600)
    :return: טקסט המאמר או הודעת שגיאה
    """
    try:
        print(f"🌐 Attempting to fetch article from URL: {url}")
        # Create the Article object with a custom User-Agent
        article = Article(url, language='en')
        article.download()
        print(f"⬇️ Article download successful: {url}")
        article.parse()
        print(f"📝 Article parsing successful: {url}")

        text = article.text.strip()
        word_count = len(text.split())
        print(f"📄 Extracted {word_count} words from article: {url}")

        # Check if the article is too short
        if word_count < 10:
            print(f"⚠️ Article text too short (<10 words) – skipping: {url}")
            return "⚠️ Article text too short (<10 words)"

        # Trim the article if it's too long
        if word_count > max_words:
            text = " ".join(text.split()[:max_words])
            print(f"✂️ Trimming article to {max_words} words: {url}")

        print(f"✅ Full article text successfully extracted: {url}")
        return text

    except ArticleException as ae:
        print(f"⚠️ ArticleException while processing article from {url}: {ae}")
        return "⚠️ Article processing error"

    except ConnectionError as ce:
        print(f"⚠️ Connection error while accessing article from {url}: {ce}")
        return "⚠️ Connection error"

    except Exception as e:
        print(f"⚠️ General error while retrieving article from {url}: {e}")
        return "⚠️ General article retrieval error"


#3
def filter_new_articles(articles):
    try:
        posted_news = load_posted_news()
        print(f"✅ Successfully loaded previously sent articles. ({len(posted_news)} items)")
    except Exception as e:
        print(f"⚠️ Error loading sent articles: {e}")
        posted_news = []

    try:
        skipped_news = load_skipped_news()
        print(f"✅ Successfully loaded previously skipped articles. ({len(skipped_news)} items)")
    except Exception as e:
        print(f"⚠️ Error loading skipped articles: {e}")
        skipped_news = {}

    new_articles = []

    for article in articles:
        title = clean_title_for_matching(article.get("title", ""))
        url = clean_url(article.get("url", ""))
        content = article.get("summary", "")
        content_word_count = len(content.split())

        print(f"[DEBUG] Checking article: title='{title}' | url='{url}' | summary word count={content_word_count}")

        if not title or not url:
            print(f"⚠️ Article missing title or URL: {article}")
            continue

        # תמיד מחשבים hash (אם יש תוכן)
        text_hash = compute_text_hash(content) if content.strip() else None
        article["text_hash"] = text_hash

        new_articles.append(article)

    print(f"✅ Found {len(new_articles)} articles to process (duplicates will be filtered later).")
    return new_articles





#---------------------------------------------------------------------------------------------------------------------------------------------------------
# פונקציות לניקוי ועיבוד טקסט
#---------------------------------------------------------------------------------------------------------------------------------------------------------

#1
def clean_url(url):
    # Remove query parameters from the URL
    parsed_url = urlparse(url)
    clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    print(f"[CLEAN_URL] Cleaned: {clean_url}")
    return clean_url


#2
def clean_title(title):
    """Performs basic title cleaning for display purposes only."""
    return BeautifulSoup(title, "html.parser").get_text().strip()
#3
def clean_title_for_matching(title):
    """
    Cleans the title for matching purposes only:
    - Removes HTML tags
    - Converts to lowercase
    - Removes suffixes like ' - Source' or ' | Website'
    """
    title = BeautifulSoup(title, "html.parser").get_text()
    title = title.strip().lower()
    title = re.sub(r' - [\w\s]+$| \| [\w\s]+$', '', title)
    return title


#4
# 🔹 Clean text from HTML tags
def clean_text(raw_text):
    soup = BeautifulSoup(raw_text, "html.parser")
    text = soup.get_text()
    return re.sub(r'\s+', ' ', text).strip()

#5
def safe_text_cut(text, max_words=500):
    words = text.split()
    if len(words) > max_words:
        print(f"⚠️ Text exceeds {max_words} words – trimming.")
        return " ".join(words[:max_words])
    return text

#6
def is_summary_relevant(summary, title, threshold=2):
    """Checks if the summary contains at least `n` words from the title."""
    return extract_text_relevance(summary, title.split()) >= threshold

#7
def is_youtube_link(url):
    """Checks whether the given URL is a YouTube link."""
    parsed_url = urllib.parse.urlparse(url)
    return "youtube.com" in parsed_url.netloc or "youtu.be" in parsed_url.netloc

#8
def extract_text_relevance(text, keywords):
    if not text:
        return 0

    try:
        text_tokens = set(word_tokenize(text.lower()))
        keyword_tokens = set(word.lower() for word in keywords)
        return len(text_tokens & keyword_tokens)  # Intersection between tokens
    except Exception as e:
        print(f"⚠️ Error during tokenization: {e}")
        return 0


#9
def compute_text_hash(text):
    """
    Generates a hash from the content after removing HTML and extra whitespace.
    Used to identify duplicate articles even if the URL or title is different.
    """
    if not text or not isinstance(text, str):
        return None  # Prevents crashes on invalid input

    cleaned = clean_text(text).strip().lower()
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

from urllib.parse import urlparse

def extract_source_from_url(url):
    try:
        return urlparse(url).netloc
    except:
        return ""

from nltk.tokenize import word_tokenize
from collections import Counter

def extract_keywords(text, num_keywords=5):
    try:
        tokens = word_tokenize(text.lower())
        tokens = [t for t in tokens if t.isalpha() and len(t) > 4]
        most_common = Counter(tokens).most_common(num_keywords)
        return [kw for kw, _ in most_common]
    except Exception:
        return []


#---------------------------------------------------------------------------------------------------------------------------------------------------------
#פונקציות ליצירת תקציר
#---------------------------------------------------------------------------------------------------------------------------------------------------------

#1
def load_summarizer():
    try:
        if torch.cuda.is_available():
            print("🚀 Using GPU for summarization")
            return pipeline("summarization", model="facebook/bart-large-cnn", device=0)
        else:
            print("⚠️ GPU not available, falling back to CPU")
            return pipeline("summarization", model="facebook/bart-large-cnn", device=-1)
    except Exception as e:
        print(f"⚠️ GPU failed – switching to CPU: {e}")
        torch.cuda.empty_cache()  # ניקוי זיכרון GPU
        return pipeline("summarization", model="facebook/bart-large-cnn", device=-1)


#2
def is_rss_summary_sufficient(text):
    """
    בודק אם התקציר מ-RSS מספק:
    - מכיל לפחות 15 מילים.
    - אינו ריק או קצר מדי.
    """
    word_count = len(text.split())
    return word_count >= 15


summarizer_loaded = False  # משתנה גלובלי לבדיקת טעינת המודל
#3
def summarize_text(text, title=""):
    global summarizer, summarizer_loaded

    try:
        # Check if the model is already loaded
        if not summarizer_loaded or summarizer is None:
            print("⚠️ Summarization model not loaded – reloading...")
            summarizer = load_summarizer()
            summarizer_loaded = True

        if not text.strip():
            print("⚠️ Input text is empty.")
            return ""

        # Return short texts (under 30 words) as-is
        original_word_count = len(text.split())
        if original_word_count < 30:
            print(f"✅ Short text detected ({original_word_count} words) – skipping summarization.")
            return text

        # Optionally prepend the title as hidden context
        if title:
            text = f"{title}. {text}"

        # Trim to 500 words max
        if original_word_count > 500:
            text = " ".join(text.split()[:500])

        max_length = min(200, original_word_count * 2)
        min_length = max(20, max_length // 2)

        print(f"🤖 Summarizing {len(text.split())} words with max_length={max_length}, min_length={min_length}...")
        summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)

        if summary and summary[0]['summary_text'].strip():
            summarized_text = summary[0]['summary_text'].strip()
            word_count = len(summarized_text.split())
            print(f"✅ Summary generated – {word_count} words.")
            return summarized_text
        else:
            print("⚠️ Empty summary returned – using fallback.")
            return ""

    except NameError as ne:
        print(f"⚠️ Model error (not found): {ne}")
        summarizer_loaded = False
        return summarize_text(text, title)  # Retry after reloading

    except Exception as e:
        print(f"🔥 Error during summarization: {e}")
        torch.cuda.empty_cache()
        summarizer_loaded = False
        return ""





#---------------------------------------------------------------------------------------------------------------------------------------------------------
#פונקציות לשליחה לטלגרם וטימס
#---------------------------------------------------------------------------------------------------------------------------------------------------------

#1
def send_telegram_message(message, retries=3, delay=5):
    print(f"➡️ Sending Telegram message: {message[:40]}...")
    print(f"[BOT] {TELEGRAM_BOT_TOKEN[:10]}... | [CHAT_ID] {TELEGRAM_CHAT_ID}")

    """ שולח הודעה לטלגרם עם טיפול רק בשגיאת 429 והשהיה במקרה הצורך """

    clean_message = message.strip()
    clean_message_text = BeautifulSoup(clean_message, "html.parser").get_text().strip()

    if not clean_message_text:
        print("⚠️ Message is empty after cleaning. Skipping Telegram send.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": clean_message, "parse_mode": "HTML"}

    for attempt in range(retries):
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            print("✅ Message sent successfully.")
            return  # Exit after successful sendציאה מהפונקציה לאחר הצלחה

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", delay))
                print(f"⏳ Received 429 Too Many Requests – retrying in {retry_after} seconds...")
                time.sleep(retry_after)  # השהיה לפי זמן שנשלח בהודעה
            else:
                print(f"❌ Error sending message: {e} – Status code: {response.status_code}")
                break  # במקרה של שגיאה שאינה 429, לא ננסה שוב

        except requests.exceptions.RequestException as e:
            print(f"❌ Telegram communication error: {e}")
            break  # במקרה של בעיות חיבור כלליות לא ננסה שוב

    print("⚠️ Failed to send the message after multiple attempts.")


#2
def post_articles_to_telegram(articles):
    start_time = datetime.now()
    print(f"\n🚀 Starting to send articles: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    sent_articles = []
    skipped_articles = []
    skipped_news = load_skipped_news()
    current_posted = load_posted_news()

    posted_titles = set(clean_title_for_matching(item["title"]) for item in current_posted)
    posted_urls = set(clean_url(item["url"]) for item in current_posted)
    posted_hashes = set(item.get("text_hash") for item in current_posted if "text_hash" in item)

    processed_titles = set()
    processed_urls = set()
    processed_hashes = set()

    for index, article in enumerate(articles):
        article_id = article["id"]
        original_title = clean_title(article["title"]) or "🔹 Untitled Article"
        match_title = clean_title_for_matching(article["title"])
        clean_link = clean_url(article["url"])
        summary = article.get("summary", "")
        rss_source = article.get("rss_source", "Unknown")
        text_hash = article.get("text_hash")

        print(f"[CHECK] Title: {original_title} | URL: {clean_link}")

        # בדיקת כפילות לפי hash של תקציר
        if text_hash and (text_hash in posted_hashes or text_hash in processed_hashes):
            print(f"[DUPLICATE_HASH] Skipping by summary hash.")
            skipped_articles.append({
                "id": article_id,
                "title": original_title,
                "url": clean_link,
                "reason": "Duplicate by summary hash",
                "summary": summary,
                "text_hash": text_hash,
                "source": article.get("source", extract_source_from_url(clean_link)),
                "published_date": article.get("published_date", datetime.today().strftime("%Y-%m-%d")),
                "published_time": article.get("published_time", datetime.today().strftime("%H:%M:%S")),
                "rss_source": rss_source
            })
            continue

        # בדיקת כפילות לפי כותרת
        if match_title in posted_titles or match_title in processed_titles:
            print(f"[DUPLICATE_TITLE] Skipping by title.")
            skipped_articles.append({
                "id": article_id,
                "title": original_title,
                "url": clean_link,
                "reason": "Duplicate by title",
                "summary": summary,
                "text_hash": text_hash or "",
                "source": article.get("source", extract_source_from_url(clean_link)),
                "published_date": article.get("published_date", datetime.today().strftime("%Y-%m-%d")),
                "published_time": article.get("published_time", datetime.today().strftime("%H:%M:%S")),
                "rss_source": rss_source
            })
            continue

        # בדיקת כפילות לפי URL
        if clean_link in posted_urls or clean_link in processed_urls:
            print(f"[DUPLICATE_URL] Skipping by url.")
            skipped_articles.append({
                "id": article_id,
                "title": original_title,
                "url": clean_link,
                "reason": "Duplicate by url",
                "summary": summary,
                "text_hash": text_hash or "",
                "source": article.get("source", extract_source_from_url(clean_link)),
                "published_date": article.get("published_date", datetime.today().strftime("%Y-%m-%d")),
                "published_time": article.get("published_time", datetime.today().strftime("%H:%M:%S")),
                "rss_source": rss_source
            })
            continue

        if article_id in skipped_news:
            fail_count = skipped_news[article_id].get("fail_count", 0)
            if fail_count >= 3:
                print(f"❌ The article '{original_title}' has failed too many times ({fail_count}) – skipping it.")
                continue

        if not text_hash and summary.strip():
            text_hash = compute_text_hash(summary)
            article["text_hash"] = text_hash
            print(f"[HASH] Recomputing hash from summary: {text_hash}")

        try:
            full_text = fetch_full_text(clean_link)
        except Exception as e:
            reason = f"Error while fetching article: {str(e)}"
            print(f"❌ {reason}")
            skipped_articles.append({
                "id": article_id,
                "title": original_title,
                "url": clean_link,
                "reason": reason,
                "summary": summary,
                "text_hash": text_hash or "",
                "source": article.get("source", extract_source_from_url(clean_link)),
                "published_date": article.get("published_date", datetime.today().strftime("%Y-%m-%d")),
                "published_time": article.get("published_time", datetime.today().strftime("%H:%M:%S")),
                "rss_source": rss_source
            })
            continue

        if not full_text or len(full_text.split()) < 10:
            reason = "Article text is empty or too short"
            print(f"🚫 {reason} – skipped.")
            skipped_articles.append({
                "id": article_id,
                "title": original_title,
                "url": clean_link,
                "reason": reason,
                "summary": summary,
                "text_hash": text_hash or "",
                "source": article.get("source", extract_source_from_url(clean_link)),
                "published_date": article.get("published_date", datetime.today().strftime("%Y-%m-%d")),
                "published_time": article.get("published_time", datetime.today().strftime("%H:%M:%S")),
                "rss_source": rss_source
            })
            continue

        processed_titles.add(match_title)
        processed_urls.add(clean_link)
        if text_hash:
            processed_hashes.add(text_hash)

        print(f"\n📨 Article {index + 1}/{len(articles)}: {original_title}")

        try:
            summarized_content = summarize_text(full_text, title=original_title)
        except Exception as e:
            reason = f"Error during summarization: {str(e)}"
            print(f"⚠️ {reason}")
            skipped_articles.append({
                "id": article_id,
                "title": original_title,
                "url": clean_link,
                "reason": reason,
                "summary": summary,
                "text_hash": text_hash or "",
                "source": article.get("source", extract_source_from_url(clean_link)),
                "published_date": article.get("published_date", datetime.today().strftime("%Y-%m-%d")),
                "published_time": article.get("published_time", datetime.today().strftime("%H:%M:%S")),
                "rss_source": rss_source
            })
            continue

        if not summarized_content.strip() or len(summarized_content.split()) < 20:
            reason = "Final summary is too short or empty"
            print(f"🚫 {reason} – marking as failed.")
            skipped_articles.append({
                "id": article_id,
                "title": original_title,
                "url": clean_link,
                "reason": reason,
                "summary": summary,
                "text_hash": text_hash or "",
                "source": article.get("source", extract_source_from_url(clean_link)),
                "published_date": article.get("published_date", datetime.today().strftime("%Y-%m-%d")),
                "published_time": article.get("published_time", datetime.today().strftime("%H:%M:%S")),
                "rss_source": rss_source
            })
            continue

        escaped_summary = html.escape(summarized_content.strip())
        message = f"""
📰 <b>{original_title}</b>
📅 <b>Date:</b> {article['published_date']} {article.get('published_time', '')}
🔗 <a href='{clean_link}'>For Additional Reading</a>

✍️ <b>Summary:</b>
{escaped_summary}
"""
        teams_message = {
            "title": original_title,
            "date": article['published_date'],
            "url": clean_link,
            "summary": escaped_summary
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                send_telegram_message(message)
                send_to_teams(teams_message, TEAMS_WEBHOOK_URL)

                enriched = {
                    "title": original_title,
                    "url": clean_link,
                    "text_hash": text_hash or "",
                    "summary": summarized_content.strip(),
                    "source": article.get("source", extract_source_from_url(clean_link)),
                    "keywords": article.get("keywords", []),
                    "published_date": article.get("published_date", datetime.today().strftime("%Y-%m-%d")),
                    "published_time": article.get("published_time", datetime.today().strftime("%H:%M:%S")),
                    "rss_source": rss_source
                }

                sent_articles.append(enriched)
                current_posted.append(enriched)
                save_posted_news(current_posted)

                print(f"✅ Sent and saved: {original_title}")
                break
            except requests.exceptions.RequestException as e:
                reason = f"Error sending to Telegram or Teams: {str(e)}"
                print(f"❌ {reason}")
                skipped_articles.append({
                    "id": article_id,
                    "title": original_title,
                    "url": clean_link,
                    "reason": reason,
                    "summary": summary,
                    "text_hash": text_hash or "",
                    "source": article.get("source", extract_source_from_url(clean_link)),
                    "published_date": article.get("published_date", datetime.today().strftime("%Y-%m-%d")),
                    "published_time": article.get("published_time", datetime.today().strftime("%H:%M:%S")),
                    "rss_source": rss_source
                })
                break

    if skipped_articles:
        save_skipped_news(skipped_articles)

    print("\n📋 Finished sending articles:")
    print(f"✅ Successfully sent: {len(sent_articles)}")
    print(f"⚠️ Skipped or failed: {len(skipped_articles)}")
    print(f"📊 Total summaries processed: {len(articles)}")
    print(f"⏱️ Duration: {datetime.now() - start_time}")



#3
def send_to_teams(message, webhook_url, retries=3, delay=5):
    """ שולח הודעה ל-Microsoft Teams עם טיפול רק בשגיאת 429 """
    try:
        headers = {"Content-Type": "application/json"}

        # יצירת כרטיס אדפטיבי במבנה נכון עם כפתור
        adaptive_card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": "New Update",
                                "weight": "Bolder",
                                "size": "Medium",
                                "color": "Accent"
                            },
                            {
                                "type": "TextBlock",
                                "text": message['title'],
                                "wrap": True,
                                "weight": "Bolder",
                                "size": "Large"
                            },
                            {
                                "type": "TextBlock",
                                "text": f"📅 Date: {message['date']}",
                                "wrap": True
                            },
                            {
                                "type": "TextBlock",
                                "text": f" {message['summary']}",
                                "wrap": True,
                                "separator": True
                            },
                            {
                                "type": "ActionSet",
                                "actions": [
                                    {
                                        "type": "Action.OpenUrl",
                                        "title": "🔗 Further reading",
                                        "url": message['url']
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }

        for attempt in range(retries):
            try:
                response = requests.post(webhook_url, headers=headers, json=adaptive_card)
                response.raise_for_status()
                print(f"✅ Message successfully sent to Teams!")
                return
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", delay))
                    print(f"⏳ Received HTTP 429 – retrying in {retry_after} seconds...")
                    time.sleep(retry_after)
                else:
                    print(f"❌ Failed to send message to Teams: {e} - status: {response.status_code}")
                    break
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Communication error with Teams: {e}")
                break

        print("❌ Failed to send message to Teams after multiple attempts.")
    except Exception as e:
        print(f"⚠️ General error while sending to Teams: {e} {e}")

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#  ניהול JSON (JSON Handling)
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#1
def safe_load_json(filepath, default):

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

#2
def load_posted_news():
    try:
        with open(POSTED_NEWS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

#3
def save_posted_news(posted_news):
    temp_file = POSTED_NEWS_FILE + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(posted_news, f, ensure_ascii=False, indent=4)
        os.replace(temp_file, POSTED_NEWS_FILE)
        print(f"📂 {len(posted_news)} posted articles saved successfully.")
    except Exception as e:
        print(f"⚠️ Error while saving posted_news: {e}")


#4
def load_skipped_news():
    skipped_articles = safe_load_json("ai-news_skipped.json", {})

    if isinstance(skipped_articles, list):
        skipped_articles = {article["id"]: article for article in skipped_articles}

    # ניקוי ישנים/כושלים
    cutoff_date = datetime.today() - timedelta(days=14)
    filtered = {}

    for article_id, article in skipped_articles.items():
        try:
            article_date = datetime.strptime(article.get("date", ""), "%Y-%m-%d")
            if article.get("fail_count", 0) < 3 and article_date >= cutoff_date:
                filtered[article_id] = {
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "fail_count": article.get("fail_count", 1),
                    "date": article.get("date", ""),
                    "reason": article.get("reason", ""),
                    "text_hash": article.get("text_hash", ""),
                    "summary": article.get("summary", ""),
                    "source": article.get("source", ""),
                    "published_date": article.get("published_date", ""),
                    "published_time": article.get("published_time", ""),
                    "rss_source": article.get("rss_source", "")
                }

        except ValueError:
            continue

    with open("ai-news_skipped.json", "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=4)

    return filtered

#5
def save_skipped_news(skipped_articles):
    skipped_file = "ai-news_skipped.json"
    try:
        with open(skipped_file, "r", encoding="utf-8") as f:
            existing_skipped = json.load(f)
            if isinstance(existing_skipped, list):
                existing_skipped = {article["id"]: article for article in existing_skipped}
    except (FileNotFoundError, json.JSONDecodeError):
        existing_skipped = {}

    today_date = datetime.today().strftime("%Y-%m-%d")
    current_time = datetime.today().strftime("%H:%M:%S")

    for article in skipped_articles:
        article_id = article["id"]
        reason = article.get("reason", "Unknown")
        title = article.get("title", "")
        url = article.get("url", "")
        summary = article.get("summary", "")
        source = article.get("source", extract_source_from_url(url))
        published_date = article.get("published_date", today_date)
        published_time = article.get("published_time", current_time)
        rss_source = article.get("rss_source", "Unknown")  # קריאה לשדה המדינה אם קיים

        # חישוב hash אם חסר
        text_hash = article.get("text_hash") or compute_text_hash(summary)

        if article_id in existing_skipped:
            existing = existing_skipped[article_id]
            existing["fail_count"] = existing.get("fail_count", 1) + 1
            existing["date"] = today_date
            existing["reason"] = reason
            existing["text_hash"] = text_hash
            existing["summary"] = summary or existing.get("summary", "")
            existing["source"] = source or existing.get("source", "")
            existing["published_date"] = published_date
            existing["published_time"] = published_time
            existing["rss_source"] = rss_source
        else:
            existing_skipped[article_id] = {
                "title": title,
                "url": url,
                "fail_count": 1,
                "date": today_date,
                "reason": reason,
                "text_hash": text_hash,
                "summary": summary,
                "source": source,
                "published_date": published_date,
                "published_time": published_time,
                "rss_source": rss_source
            }

    with open(skipped_file, "w", encoding="utf-8") as f:
        json.dump(existing_skipped, f, ensure_ascii=False, indent=4)

    print(f"[INFO] Skipped list updated: {len(skipped_articles)} new, {len(existing_skipped)} total.")




#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#  ניהול קובץ נעילה
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

#1
def create_lock():
    with open(LOCK_FILE, "w") as f:
        pid = os.getpid()
        f.write(str(pid))
    print(f"🔒 Lock file created with PID: {pid}")

#2
def remove_lock():
    """מוחק את קובץ הנעילה כשמסיימים את הריצה"""
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

#3
def is_script_running():
    if not os.path.exists(LOCK_FILE):
        return False

    try:
        with open(LOCK_FILE, "r") as f:
            pid = int(f.read().strip())
            if is_process_running(pid):
                print("⚠️ Script is already running (PID: {})".format(pid))
                return True
            else:
                print("🧹 Stale process detected – cleaning up old lock file.")
                remove_lock()
                return False
    except Exception as e:
        print(f"⚠️ Error reading lock file: {e}")
        remove_lock()
        return False

#4
def is_process_running(pid):
    try:
        p = psutil.Process(pid)
        return p.is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#  תהליכים ראשיים
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#1
# 🔹 הפעלת התהליך
def process_and_send_articles():
    print("📬 Entered process_and_send_articles()")
    articles = get_google_alerts()
    new_articles = filter_new_articles(articles)

    if new_articles:
        post_articles_to_telegram(new_articles)
    else:
        print("📭 No new articles for today.")

LOCK_FILE = "script_running.lock"

#2
if __name__ == "__main__":
    now = datetime.now()
    os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

    print("[INFO] Main execution started.")

    try:
        nltk.data.find("tokenizers/punkt")
        print("NLTK resource 'punkt' is available.")
    except LookupError:
        nltk.download("punkt")
        print("NLTK resource 'punkt' has been downloaded.")

    try:
        nltk.data.find("tokenizers/punkt_tab")
        print("NLTK resource 'punkt_tab' is available.")
    except LookupError:
        nltk.download("punkt_tab")
        print("NLTK resource 'punkt_tab' has been downloaded.")

    try:
        with open("run_times.txt", "a", encoding="utf-8") as f:
            f.write(f"Execution started at {now.strftime('%Y-%m-%d %H:%M:%S')}\n")

        with open("log.txt", "a", encoding="utf-8") as f:
            f.write(f"\n=== New run started at {now.strftime('%Y-%m-%d %H:%M:%S')} ===\n")

        # print("Attempting to send startup message via Telegram...")
        # #send_telegram_message(f"Execution started at {now.strftime('%Y-%m-%d %H:%M:%S')}")
        # print("Telegram message sent.")

        print("Checking if script is already running...")
        if is_script_running():
            print("Script is already running. Exiting.")
            sys.exit(0)

        print("Creating lock file...")
        create_lock()

        try:
            print("Starting to process and send articles...")
            process_and_send_articles()
            print("✅ process_and_send_articles() completed successfully.")
        except Exception as e:
            print(f"❌ General error during execution: {e}")
            send_telegram_message(f"❌ General error during execution: {e}")

    finally:
        print("Cleaning up lock file...")
        remove_lock()
        print("Final cleanup complete. Exiting now.")
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)

