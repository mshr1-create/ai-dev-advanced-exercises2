import datetime as dt
import json
import os
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
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('API_KEY')
#ニュース取得
def get_topics(rss_url):
    topics = []
    res = requests.get(rss_url)
    root = ET.fromstring(res.text)
    for item in root[0].findall('item'):
        title = '' if item.find('title') is None else item.find('title').text
        link = '' if item.find('link') is None else item.find('link').text
        description = '' if item.find('description') is None else item.find('description').text
        pub_date = '' if item.find('pubDate') is None else item.find('pubDate').text
        if '+' in pub_date:
            pub_date = dt.datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z')
        else:
            pub_date = dt.datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
        topic = {
            'title': title,
            'link': link,
            'description': description,
            'pub_date': pub_date.isoformat(),
        }
        topics.append(topic)
    return topics

#プロンプト送受信
def chat(request_prompt):
    GEMINI_API_KEY = API_KEY
    client = genai.Client(api_key=GEMINI_API_KEY)
    content_string = request_prompt['messages'][0]['content']
    config = types.GenerateContentConfig(
        system_instruction=request_prompt['context'],
        max_output_tokens=request_prompt['maxOutputTokens'],
        temperature=request_prompt['temperature'],
        top_p=request_prompt['topP'],
    )
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=content_string,
            config=config,
        )
        return {'candidates': [{'text': response.text}]}
    except Exception as e:
        print(f"API呼び出し中にエラーが発生しました: {e}")
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
    res_str = chat_res['candidates'][0]['text']
    res_dict = json.loads(res_str)
    return res_dict

#実行
news_links = [
    'https://news.yahoo.co.jp/rss/categories/sports.xml',
    'https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml',
    'https://rss.itmedia.co.jp/rss/2.0/business.xml'
]
all_topics = []
for news_link in news_links:
    topics = get_topics(news_link)[:2]
    all_topics += topics
for topic in all_topics:
    content = topic['title'] + ' ' + topic['description']
    topic['tags'] = tag_topic(content)
with open('all_topics.json', 'w', encoding='utf-8') as f:
    json.dump(all_topics, f, indent=4, ensure_ascii=False)