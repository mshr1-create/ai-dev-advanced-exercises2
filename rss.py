import datetime as dt
import json
import os
import re
import time
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load API credentials from .env once at import time
load_dotenv()
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    raise RuntimeError('環境変数 GEMINI_API_KEY が設定されていません (.env を確認してください)')
#ニュース取得
def get_topics(rss_url, retries=3, timeout=10):
    topics = []
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            res = requests.get(rss_url, timeout=timeout)
            res.raise_for_status()
            root = ET.fromstring(res.text)
            for item in root[0].findall('item'):
                title = '' if item.find('title') is None else item.find('title').text
                link = '' if item.find('link') is None else item.find('link').text
                description = '' if item.find('description') is None else item.find('description').text
                content_node = item.find('{http://purl.org/rss/1.0/modules/content/}encoded')
                body = description if content_node is None else (content_node.text or '')
                pub_date = '' if item.find('pubDate') is None else item.find('pubDate').text
                if '+' in pub_date:
                    pub_date = dt.datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z')
                else:
                    pub_date = dt.datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
                topic = {
                    'title': title,
                    'link': link,
                    'description': description,
                    'body': body,
                    'pub_date': pub_date.isoformat(),
                }
                topics.append(topic)
            return topics
        except Exception as e:
            last_error = e
            print(f"[WARN] RSS fetch failed (attempt {attempt}/{retries}) for {rss_url}: {e}")
    print(f"[ERROR] RSS fetch exhausted retries for {rss_url}: {last_error}")
    return topics

#プロンプト送受信（簡易リトライ付き）
def chat(request_prompt, retries=1, backoff_seconds=5):
    client = genai.Client(api_key=API_KEY)
    content_string = request_prompt['messages'][0]['content']
    config = types.GenerateContentConfig(
        system_instruction=request_prompt['context'],
        max_output_tokens=request_prompt['maxOutputTokens'],
        temperature=request_prompt['temperature'],
        top_p=request_prompt['topP'],
    )
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=content_string,
                config=config,
            )
            return {'candidates': [{'text': response.text}]}
        except Exception as e:
            last_error = e
            print(f"[WARN] API呼び出し中にエラーが発生しました (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                retry_after = backoff_seconds * attempt
                match = re.search(r"Please retry in ([0-9.]+)s", str(e))
                if match:
                    retry_after = float(match.group(1))
                time.sleep(retry_after)
    print(f"[ERROR] API呼び出しが失敗しました: {last_error}")
    return None

#リクエスト作成
def generate_request_prompt(prompt, content, tmp, p):
    request_prompt = {
        'context': prompt,
        'maxOutputTokens': 1024,
        'messages': [
            {
                'author': 'user',
                'content': content,
            }
        ],
        'temperature': tmp,
        'topP': p,
    }
    return request_prompt

#タグ付け
def tag_topic(content):
    system_prompt = """
        # 命令
        入力されるニュース記事の文章に関連するタグを、出力形式に合わせて出力する。
        # 制約条件
        出力にデータ以外の情報は含めない。
        # 出力形式
        ["政治", "経済"]
    """
    request_prompt = generate_request_prompt(system_prompt, content, 0, 1)
    chat_res = chat(request_prompt)
    if not chat_res or 'candidates' not in chat_res:
        print("[WARN] タグ生成に失敗しました: 応答なし")
        return []
    try:
        res_str = chat_res['candidates'][0].get('text', '[]')
        res_dict = json.loads(res_str)
        return res_dict
    except Exception as e:
        print(f"[WARN] タグ生成結果のパースに失敗しました: {e}")
        return []

#実行
news_links = [
    'https://news.yahoo.co.jp/rss/categories/sports.xml',
    'https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml',
    'https://rss.itmedia.co.jp/rss/2.0/business.xml'
]
limit_per_feed = 2  # Reduced to minimize token usage
RATE_LIMIT_SLEEP_SECONDS = 15  # Increased to stay safely within free tier
MIN_EXPECTED_TOPICS = 6  # current max items = 3 feeds * 2 items each
all_topics = []
for news_link in news_links:
    topics = get_topics(news_link)[:limit_per_feed]
    all_topics += topics
if len(all_topics) < MIN_EXPECTED_TOPICS:
    print(f"[WARN] collected topics are below expected count: {len(all_topics)} < {MIN_EXPECTED_TOPICS}")
for topic in all_topics:
    content = topic['title'] + ' ' + topic['description']
    topic['tags'] = tag_topic(content)
    time.sleep(RATE_LIMIT_SLEEP_SECONDS)
with open('all_topics.json', 'w', encoding='utf-8') as f:
    json.dump(all_topics, f, indent=4, ensure_ascii=False)