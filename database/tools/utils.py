import os
import json
import re
import ast
import pandas as pd

from dotenv import load_dotenv

def scrap_article(soup, url):
    # 1) 제목
    h1_tag = soup.find('h1')
    title = h1_tag.text.strip() if h1_tag else "제목 없음"

    # 2) 작성일
    date_class = soup.find(class_=lambda x: x and 'publish-meta' in x.lower())
    updated_date = "작성일 정보 없음"
    if date_class:
        date_text = date_class.text.strip()
        date_match = re.search(r':\s*(.*?)\s*\|', date_text)
        if date_match:
            updated_date = date_match.group(1)
        else:
            updated_date = date_text

    # 3) 저자
    author_tag = soup.find('a', rel='author')
    author = author_tag.text.strip() if author_tag else "저자 정보 없음"

    # 4) 태그
    tag_tags = soup.find_all('li', class_='tag-set__item')
    tag_list = []
    for tag in tag_tags:
        tag_list.append(tag.text.strip())

    # 5) 서론
    intro = ""
    first_h2 = soup.find('h2')
    if first_h2:
        # h2 이전의 모든 형제 태그 가져오기
        pre_h2_elements = first_h2.find_previous_siblings()
        
        # 순서가 뒤집혀서 반환되므로 reverse() 사용 (선택사항)
        pre_h2_elements.reverse()
        
        for element in pre_h2_elements:
            if element.name == 'p':
                p_text = element.text.strip()
                # 제휴 마케팅 면책 및 구독 유도 필터링
                if "originally appeared in the award-winning" in p_text and "Subscribe now" in p_text:
                    continue
                if "affiliate advertising programs" in p_text or "purchase a product through this article" in p_text:
                    continue
                p_text = p_text.replace('\xa0', ' ').strip()
                if p_text:
                    intro += p_text + '\n\n'

    # 6) 본문 및 FAQ 분리 수집
    full_content = {}
    faq_content = []
    faq_section_found = False
    
    # h2 태그들을 순회
    for h2 in soup.find_all('h2'):
        h2_title = h2.text.strip()
        
        # 'We use cookies', 'Privacy Preference Center' 등 쿠키/개인정보 관련 노이즈 H2 섹션 차단
        if any(noise in h2_title.lower() for noise in ['cookie', 'privacy preference', 'consent preference', 'necessary cookies']):
            continue
            
        section_text = ""
        
        # h2 태그의 다음 형제(sibling) 태그들을 순회
        for sibling in h2.find_next_siblings():
            # 다음 h2를 만나면 멈춤
            if sibling.name == 'h2':
                break
                
            # 만약 클래스명에 'content-accordion'이 포함되어 있으면 본문 수집 중단하고 FAQ 파서로 유도
            if sibling.get('class') and any('content-accordion' in c for c in sibling.get('class')):
                faq_section_found = True
                break
            
            # p 태그인 경우 내용에 추가
            if sibling.name == 'p':
                p_text = sibling.text.strip()
                # 제휴 마케팅 면책 및 정기구독 광고 노이즈 필터링
                if "affiliate advertising programs" in p_text or "purchase a product through this article" in p_text:
                    continue
                if "originally appeared in the award-winning" in p_text and "Subscribe now" in p_text:
                    continue
                
                # 공백 특수문자 정리
                p_text = p_text.replace('\xa0', ' ').strip()
                if p_text:
                    section_text += p_text + '\n\n'
        
        if faq_section_found:
            break  # FAQ 영역에 도달하여 전체 본문 H2 순회 루프 종료
            
        cleaned_text = section_text.strip()
        if cleaned_text:
            full_content[h2_title] = cleaned_text

    # class가 'content-accordion'인 요소를 정교하게 수집하여 FAQ 구조화
    faq_elements = soup.find_all(class_=re.compile("content-accordion"))
    if faq_elements:
        for faq_el in faq_elements:
            # 0단계: 제공해주신 1:1 정밀 클래스명(trigger & content) 매칭 우선 적용
            triggers = faq_el.find_all(class_=re.compile("content-accordion__trigger"))
            contents = faq_el.find_all(class_=re.compile("content-accordion__content"))
            
            if len(triggers) == len(contents) and len(triggers) > 0:
                for t, c in zip(triggers, contents):
                    faq_content.append({
                        "question": t.text.replace('+', '').strip(),
                        "answer": c.text.replace('+', '').strip()
                    })

    return {
        "url": url,
        "title": title,
        "updated_date": updated_date,
        "tag_list": tag_list,
        "author": author,
        "intro": intro.strip(),
        "full_content": full_content,
        "faq": faq_content
    }

def clean_text(text):
    """텍스트 내 잔여 특수문자 및 공백 문자 제거"""
    if not isinstance(text, str):
        return ""
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_expert_name(channel):
    """채널명을 기준으로 대표 전문가 이름 추출"""
    if not isinstance(channel, str):
        return "전문가"
    if "강형욱" in channel:
        return "강형욱 훈련사"
    elif "설채현" in channel:
        return "설채현 수의사"
    return channel.strip()

def safe_parse_literal(val, default):
    """문자열로 저장된 딕셔너리/리스트를 안전하게 Python 객체로 복원"""
    if pd.isna(val) or not isinstance(val, str) or val.strip() == "":
        return default
    try:
        return ast.literal_eval(val)
    except Exception:
        try:
            return json.loads(val)
        except Exception:
            return default

def get_slug(text):
    """텍스트에서 슬러그 생성"""
    if not isinstance(text, str):
        return ""
    text = text.strip().lower()
    text = re.sub(r'[^a-zA-Z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text)
    return text

def get_db_connection_string() -> str:
    """LangChain PGVector가 사용할 PostgreSQL 연결 문자열을 만든다.

    - docker-compose.yml 기본값과 맞춘다.
    - 팀 Docker 설정 기본값:
      - DB: pet_dog
      - USER: admin
      - PASSWORD: admin1234
    """
    load_dotenv()
    
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "pet_dog")
    user = os.getenv("POSTGRES_USER", "admin")
    password = os.getenv("POSTGRES_PASSWORD", "admin1234")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
