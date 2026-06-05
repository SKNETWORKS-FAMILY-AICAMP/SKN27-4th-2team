import os
import json
import pandas as pd

from .utils import clean_text, extract_expert_name, safe_parse_literal, get_slug

def process_youtube_csv(file_path):
    """유튜브 자막 CSV를 읽어 영상 단위로 1개의 문서 JSON 목록 반환"""
    df = pd.read_csv(file_path)
    file_name = os.path.basename(file_path)
    structured_docs = []
    
    for idx, row in df.iterrows():
        video_id = row.get('video_id', '')
        video_url = row.get('video_url', '')
        channel = row.get('channel', '')
        title = clean_text(row.get('title', '제목 없음'))
        caption = row.get('new_cleaned_caption', '')
        
        if not isinstance(caption, str) or caption.strip() == "":
            continue
            
        expert = extract_expert_name(channel)
        
        # 1. 캡션 정리: 문단 줄바꿈 정리하되 개행 유지
        paragraphs = [p.strip() for p in caption.split('\n') if p.strip()]
        cleaned_caption = "\n\n".join(paragraphs)
        
        if not cleaned_caption:
            continue
            
        doc_id = f"yt_{video_id}"
        
        # RAG 검색 최적화용 텍스트 (영상 전체 내용 포함)
        rag_full_text = f"Expert: {expert}\nVideo: {title}\n\nContent:\n{cleaned_caption}"
        
        doc = {
            "id": doc_id,
            "content": cleaned_caption,
            "full_text_for_embedding": rag_full_text,
            "metadata": {
                "video_id": video_id,
                "video_url": video_url,
                "channel": channel,
                "expert": expert,
                "title": title,
                "doc_type": "video",
                "source_file": file_name
            }
        }
        structured_docs.append(doc)
        
    return structured_docs

def process_article_csv(file_path):
    page_contents = []
    noise_headers = {'we use cookies', 'privacy preference center', 'manage consent preferences', 'strictly necessary cookies'}
    
    category = os.path.splitext(os.path.basename(file_path))[0]
    df = pd.read_csv(file_path)

    for idx, row in df.iterrows():
        url = row.get('url', '')
        title = clean_text(row.get('title', '제목 없음'))
        updated_date = clean_text(row.get('updated_date', '작성일 정보 없음'))
        author = clean_text(row.get('author', '저자 정보 없음'))
        intro = clean_text(row.get('intro', ''))
        
        # 태그 리스트 복원
        tags = safe_parse_literal(row.get('tag_list'), [])
        tags = [clean_text(t) for t in tags]
        
        # 본문 딕셔너리 복원
        full_content = safe_parse_literal(row.get('full_content'), {})
        
        # FAQ 리스트 복원
        faq_list = safe_parse_literal(row.get('faq'), [])
        
        # 기사 제목 기반 고유 식별자 슬러그 생성
        title_slug = get_slug(title)

        if intro:
            doc_id = f"akc_{category}_{title_slug}_intro"
            
            # RAG 임베딩에 최적화된 통합 텍스트 구성 (기사 제목 + 서론)
            rag_full_text = f"Title: {title}\nContext: Introduction\n\n" + clean_text(intro)
            
            doc = {
                "id": doc_id,
                "content": intro,
                "full_text_for_embedding": rag_full_text,
                "metadata": {
                    "category": category,
                    "url": url,
                    "title": title,
                    "updated_date": updated_date,
                    "author": author,
                    "tags": tags,
                    "section_title": "Introduction",
                    "doc_type": "intro"
                }
            }
            page_contents.append(doc)

        # 1) 본문 소제목(H2) 단위 문서 생성
        for sec_title, sec_content in full_content.items():
            sec_title_cleaned = clean_text(sec_title)
            
            # 쿠키/개인정보 노이즈 섹션 필터링
            if sec_title_cleaned.lower() in noise_headers:
                continue
                
            sec_content_cleaned = clean_text(sec_content)
            if not sec_content_cleaned or len(sec_content_cleaned) < 30:
                continue
            
            # 문서 ID 생성
            doc_id = f"akc_{category}_{title_slug}_section_{sec_title_cleaned}"
            
            # RAG 임베딩에 최적화된 통합 텍스트 구성 (기사 제목 + 소제목 + 문맥 정보)
            # 이 텍스트는 벡터 임베딩(Vector Embedding) 시 높은 검색 정확도를 보장합니다.
            rag_full_text = f"Title: {title}\nSection: {sec_title_cleaned}\nContent:\n{sec_content_cleaned}"
            
            doc = {
                "id": doc_id,
                "content": sec_content_cleaned,
                "full_text_for_embedding": rag_full_text,
                "metadata": {
                    "category": category,
                    "url": url,
                    "title": title,
                    "updated_date": updated_date,
                    "author": author,
                    "tags": tags,
                    "section_title": sec_title_cleaned,
                    "doc_type": "section"
                }
            }
            page_contents.append(doc)

        # 2) FAQ 질의응답 쌍 단위 문서 생성
        for faq in faq_list:
            question = clean_text(faq.get('question', ''))
            answer = clean_text(faq.get('answer', ''))
            
            if not question or not answer:
                continue
            
            # FAQ 문서 ID 생성 (고유성 확보)
            faq_id = f"akc_{category}_{title_slug}_faq_{question[:20]}"
            
            # RAG 임베딩에 최적화된 통합 텍스트 구성
            rag_full_text = f"Title: {title}\nFAQ\nQuestion: {question}\nAnswer: {answer}"
            
            doc = {
                "id": faq_id,
                "content": answer,  # RAG가 실제 답변을 검색하도록 content는 답변으로 저장
                "full_text_for_embedding": rag_full_text,
                "metadata": {
                    "category": category,
                    "url": url,
                    "title": title,
                    "updated_date": updated_date,
                    "author": author,
                    "tags": tags,
                    "question": question,
                    "doc_type": "faq"
                }
            }
            page_contents.append(doc)

    return page_contents

def save_docs(source, csv_path, save):
    """
    CSV 입력받아서 가공 후, JSON으로 저장
    """
    all_docs = []
    
    if os.path.exists(csv_path):
        print(f"[진행] '{os.path.basename(csv_path)}' 가공 시작...")
        if source == 'youtube':
            all_docs.extend(process_youtube_csv(csv_path))
        elif source == 'article':
            all_docs.extend(process_article_csv(csv_path))
    
    with open(save, 'w', encoding='utf-8') as f:
        json.dump(all_docs, f, ensure_ascii=False, indent=2)
    
    print(f"[완료] 총 {len(all_docs)}개의 문서가 '{save}'에 저장되었습니다.")

