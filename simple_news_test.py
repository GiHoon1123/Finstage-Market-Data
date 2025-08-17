#!/usr/bin/env python3
"""
간단한 뉴스 크롤링 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.news_crawler.infra.model.repository.content_repository import ContentRepository
from app.news_crawler.infra.model.entity.content import Content
from app.common.infra.database.config.database_config import SessionLocal
from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler
from sqlalchemy import func

def simple_test():
    """간단한 뉴스 테스트"""
    print("🔧 간단한 뉴스 크롤링 테스트...")
    
    # 1. 현재 상태 확인
    session = SessionLocal()
    repo = ContentRepository(session)
    
    try:
        current_count = session.query(func.count(Content.id)).scalar()
        print(f"📊 현재 뉴스 개수: {current_count}개")
        
        # 2. 단일 심볼 테스트
        print(f"\n📡 Investing 경제 뉴스 크롤링 테스트...")
        from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler
        try:
            crawler = InvestingNewsCrawler("INVESTING:ECONOMY")
            result = crawler.process_all(telegram_enabled=True)  # 텔레그램 활성화
            print(f"✅ 결과: {result}")
        except Exception as e:
            print(f"❌ 예외 발생: {e}")
            import traceback
            traceback.print_exc()
        
        # 3. 크롤링 후 상태 확인
        new_count = session.query(func.count(Content.id)).scalar()
        print(f"📊 크롤링 후 뉴스 개수: {new_count}개")
        print(f"📈 새로 추가된 뉴스: {new_count - current_count}개")
        
        # 4. 최신 뉴스 확인
        latest = session.query(Content).order_by(Content.crawled_at.desc()).limit(3).all()
        print(f"📰 최신 뉴스 3개:")
        for news in latest:
            print(f"  - {news.title[:50]}... ({news.symbol}) - {news.crawled_at}")
            
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    simple_test()
