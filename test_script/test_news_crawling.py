#!/usr/bin/env python3
"""
뉴스 크롤링 테스트 스크립트
실제 뉴스가 크롤링되고 contents 테이블에 저장되는지 확인
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.news_crawler.infra.model.repository.content_repository import ContentRepository
from app.news_crawler.infra.model.entity.content import Content
from app.common.infra.database.config.database_config import SessionLocal
from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler
from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler
from sqlalchemy import func
from datetime import datetime
import time

def test_news_crawling():
    """뉴스 크롤링 테스트"""
    print("🔧 뉴스 크롤링 테스트 시작...")
    
    # 1. 현재 contents 테이블 상태 확인
    session = SessionLocal()
    repo = ContentRepository(session)
    
    try:
        # 현재 뉴스 개수 확인
        current_count = session.query(func.count(Content.id)).scalar()
        print(f"📊 현재 contents 테이블 뉴스 개수: {current_count}개")
        
        # 최근 뉴스 5개 확인
        recent_news = session.query(Content).order_by(Content.crawled_at.desc()).limit(5).all()
        print(f"📰 최근 뉴스 5개:")
        for news in recent_news:
            print(f"  - {news.title[:50]}... ({news.symbol}) - {news.crawled_at}")
        
        # 2. Yahoo 뉴스 크롤링 테스트
        print(f"\n🔍 Yahoo 뉴스 크롤링 테스트...")
        test_symbols = ['^TNX', '^VIX', 'XLF']
        
        for symbol in test_symbols:
            print(f"  📡 {symbol} 뉴스 크롤링 중...")
            crawler = YahooNewsCrawler(symbol)
            result = crawler.process_all()
            print(f"    ✅ {symbol} 처리 완료: {result}")
            time.sleep(1)  # API 제한 방지
        
        # 3. Investing 뉴스 크롤링 테스트
        print(f"\n🔍 Investing 뉴스 크롤링 테스트...")
        investing_crawler = InvestingNewsCrawler("INVESTING:ECONOMY")
        investing_result = investing_crawler.process_all()
        print(f"  ✅ Investing 경제 뉴스 처리 완료: {investing_result}")
        
        # 4. 크롤링 후 contents 테이블 상태 확인
        print(f"\n📊 크롤링 후 contents 테이블 상태...")
        time.sleep(2)  # 저장 완료 대기
        
        new_count = session.query(func.count(Content.id)).scalar()
        print(f"📊 크롤링 후 뉴스 개수: {new_count}개")
        print(f"📈 새로 추가된 뉴스: {new_count - current_count}개")
        
        # 최신 뉴스 5개 확인
        latest_news = session.query(Content).order_by(Content.crawled_at.desc()).limit(5).all()
        print(f"📰 크롤링 후 최신 뉴스 5개:")
        for news in latest_news:
            print(f"  - {news.title[:50]}... ({news.symbol}) - {news.crawled_at}")
        
        # 5. 거시경제 심볼 뉴스 확인
        print(f"\n📰 거시경제 심볼 뉴스 현황:")
        macro_symbols = ['^TNX', '^VIX', 'XLF', 'XLK', '^TYX']
        for symbol in macro_symbols:
            symbol_news = repo.get_by_symbol(symbol, 3)
            print(f"  {symbol}: {len(symbol_news)}개 뉴스")
            for news in symbol_news[:2]:  # 최근 2개만 표시
                print(f"    - {news.title[:40]}... ({news.crawled_at})")
        
        if new_count > current_count:
            print(f"\n✅ 성공! {new_count - current_count}개의 새로운 뉴스가 저장되었습니다!")
        else:
            print(f"\n⚠️ 경고: 새로운 뉴스가 저장되지 않았습니다.")
            
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_news_crawling()
