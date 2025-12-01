import datetime as dt
import json
import requests
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types

#プロンプト送受信
def chat(request_prompt):
    client = genai.Client(api_key='AIzaSyD2ImO1QZ6Uau7jGQMyTmpJslQoNaeiw1U')
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

#実行
system_prompt = """
    # 命令
    タグをつけて
    # 制約条件
    できるだけたくさん
    # 出力形式
    文字だけで出力する
"""
content = 'ディストリビューションズの永愛選手が、11日行われたモノリシックス戦にて、驚異的な活躍を披露し、チームを勝利に導きました。'
request_prompt = generate_request_prompt(system_prompt, content, 0.4, 1)
chat_res = chat(request_prompt)
res_str = chat_res['candidates'][0]['text']
print(res_str)