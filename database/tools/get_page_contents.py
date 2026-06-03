import re
import os
import logging
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import async_playwright

from utils import scrap_article

# 로그 및 데이터 디렉토리 생성
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# 로그 파일 설정
log_filename = os.path.join(log_dir, f"crawler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# 로거 구성
logger = logging.getLogger("akc_crawler")
logger.setLevel(logging.INFO)

# 로그 포맷
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# 파일 핸들러 (UTF-8 인코딩 적용)
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# 콘솔 핸들러
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# 핸들러 등록
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Playwright를 사용하여 웹페이지에서 데이터를 수집하는 함수
async def run(browser, url):
    context = await browser.new_context()
    page = await context.new_page()
    try:
        logger.info(f'[시작] 페이지 로딩 중: {url}')
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(1500) # 동적 자바스크립트 및 본문 렌더링 안정화를 위한 1.5초 대기

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        page_content = scrap_article(soup, url)

        logger.info(f"[성공] 수집 완료 - {page_content.get('title')}...")

        return page_content
    
    except Exception as e:
        logger.error(f"[실패] {url} 크롤링 중 오류 발생: {e}")
        return {"url": url, "error": str(e)}
    
    finally:
        # 생성된 페이지 컨텍스트 닫기
        await context.close()

# 목록 페이지에서 기사 카드를 발견하는 족족 즉시 상세 페이지로 접속하여 실시간 수집을 수행하는 스트리밍식 크롤러 함수
async def collect_and_scrape(browser, list_url, max_clicks, user_agent, viewport):
    context = await browser.new_context(
        user_agent=user_agent,
        viewport=viewport
    )
    list_page = await context.new_page()
    scraped_results = []
    visited_urls = set() # 중복 수집 방지용 세트
    click_count = 0
    
    try:
        logger.info(f"[시작] 기사 목록 페이지 로딩 중: {list_url}")
        await list_page.goto(list_url, wait_until="domcontentloaded", timeout=30000)
        
        # 목록을 확장해가며 실시간 크롤링을 처리하는 루프 (무한 루프 또는 지정 횟수 반복)
        while True:
            limit_str = str(max_clicks) if max_clicks is not None else "무제한"
            logger.info(f"[진행] 현재 목록에서 새로운 기사 카드 검색 중... (클릭 진행: {click_count}/{limit_str})")
            
            # 현재 로딩된 목록의 HTML 소스 분석
            html = await list_page.content()
            soup = BeautifulSoup(html, "html.parser")
            
            # list_url에서 현재 수집 대상인 카테고리 식별자 추출 (예: 'home-living')
            category_match = re.search(r'/expert-advice/([^/]+)', list_url)
            current_category = category_match.group(1) if category_match else None

            # 기사 카드 내부의 상세 링크 수집
            current_urls = []
            for a_tag in soup.find_all('a', href=True, class_="content-card__title"):
                href = a_tag['href']
                full_url = href if href.startswith('http') else f"https://www.akc.org{href}"
                if not full_url.endswith('/'):
                    full_url += '/'
                
                # 카테고리 일치성 필터링: 중복 수집 방지를 위해 현재 카테고리 주소를 정확히 포함하는지 검증
                if current_category and f"/expert-advice/{current_category}/" not in full_url:
                    continue
                
                # 미방문 URL만 수집 큐에 추가
                if full_url not in visited_urls:
                    current_urls.append(full_url)
                    visited_urls.add(full_url)
            
            # 새로 발견된 기사들에 대해 즉시 상세 수집 가동 (실시간 스크래핑 구조)
            if current_urls:
                logger.info(f"[알림] {len(current_urls)}개의 신규 기사를 발견했습니다. 즉시 파싱을 실행합니다.")
                for idx, url in enumerate(current_urls):
                    logger.info(f"       -> [{idx+1}/{len(current_urls)}] 상세 기사 수집 중: {url}")
                    # 목록 세션을 훼손하지 않기 위해 동일 브라우저상에서 run 함수 호출
                    data = await run(browser, url)
                    scraped_results.append(data)
                    await asyncio.sleep(1) # 사이트 차단 방지를 위한 정중한 지연
            else:
                logger.info("[알림] 새로 감지된 기사 카드가 없습니다.")
                
            # 'Load More' 클릭 조건 판단 및 실행
            if max_clicks is None or click_count < max_clicks:
                # 1. 페이지 최하단으로 부드럽게 스크롤
                await list_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await list_page.wait_for_timeout(1500)
                
                # 2. 'LOAD MORE' 버튼 클릭
                load_more_btn = list_page.locator("a:has-text('LOAD MORE'), button:has-text('LOAD MORE'), .load-more, .btn-load-more")
                
                if await load_more_btn.is_visible(timeout=5000):
                    await load_more_btn.click()
                    click_count += 1
                    logger.info(f"[성공] 'Load More' {click_count}번째 클릭 완료")
                    await list_page.wait_for_timeout(3000) # 새 카드들의 로딩을 보장하는 3초 대기
                else:
                    logger.info("[안내] 'Load More' 버튼이 더 이상 노출되지 않아 목록 확장을 중단합니다.")
                    break
            else:
                logger.info(f"[안내] 지정된 최대 클릭 제한({max_clicks}회)에 도달하여 목록 확장을 중단합니다.")
                break
                
        logger.info(f"[완료] {list_url} 목록에서 총 {len(scraped_results)}개의 기사 수집을 성공적으로 완수했습니다.")
        return scraped_results
        
    except Exception as e:
        logger.error(f"[실패] 스트리밍 수집 도중 오류 발생: {e}")
        return scraped_results
    finally:
        await list_page.close()
        await context.close()

# 메인 실행 함수
async def main(list_url, max_clicks=2):
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    viewport = {'width': 1920, 'height': 1080}

    # Playwright 컨텍스트 매니저를 사용하여 안전하게 실행
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 목록에서 발견하는 즉시 상세 페이지로 이동해 실시간 수집
        results = await collect_and_scrape(browser, list_url, max_clicks=max_clicks, user_agent=user_agent, viewport=viewport)
        
        await browser.close()
        return results

# 비동기 메인 함수 실행
if __name__ == "__main__":
    # 기사 카테고리
    categories = [
        'dog-breeds', 
        'health', 
        'travel', 
        'nutrition', 
        'training', 
        'sports', 
        'puppy-information', 
        'lifestyle', 
        'home-living', 
        'news', 
        'family-dog', 
        'gazette', 
        'vets-corner'
    ]

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'contents')
    os.makedirs(output_dir, exist_ok=True)

    for category in categories:
        target_list_url = f"https://www.akc.org/expert-advice/{category}/"
        logger.info(f"[시작] {category} 카테고리 수집 시작")
        scraped_data = asyncio.run(main(list_url=target_list_url, max_clicks=None))
        df = pd.DataFrame(scraped_data)
        df.to_csv(f'{output_dir}/{category}.csv', index=False, encoding='utf-8-sig')
        logger.info(f"[완료] {category} 카테고리 수집 완료. 총 {len(df)}개의 기사가 '{output_dir}/{category}.csv'로 완벽하게 내보내졌습니다.")