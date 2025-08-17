#!/usr/bin/env python3
"""
뉴스 크롤링 + 감정분석 통합 테스트 스크립트

실제 뉴스를 크롤링하고 감정분석을 수행하여 데이터베이스에 저장합니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler
from app.news_crawler.service.news_processor import NewsProcessor
from app.news_crawler.infra.model.repository.content_sentiment_repository import ContentSentimentRepository
from app.common.infra.database.config.database_config import SessionLocal


def test_news_crawling_with_sentiment():
    """뉴스 크롤링과 감정분석 통합 테스트"""
    print("=== 뉴스 크롤링 + 감정분석 통합 테스트 ===")
    
    try:
        # TSLA 뉴스 크롤링 (최소한의 뉴스만)
        print("TSLA 뉴스 크롤링 중...")
        crawler = YahooNewsCrawler("TSLA")
        news_items = crawler.crawl()
        
        if not news_items:
            print("❌ 크롤링된 뉴스가 없습니다.")
            return
        
        print(f"✅ {len(news_items)}개의 뉴스를 크롤링했습니다.")
        
        # 뉴스 처리 (감정분석 포함)
        print("뉴스 처리 및 감정분석 중...")
        processor = NewsProcessor(news_items, telegram_enabled=False)
        processor.run()
        
        print("✅ 뉴스 처리 및 감정분석이 완료되었습니다.")
        
        # 결과 확인
        print("\n=== 저장된 감정분석 결과 확인 ===")
        session = SessionLocal()
        sentiment_repo = ContentSentimentRepository(session)
        
        try:
            # TSLA 관련 감정분석 결과 조회
            sentiments = sentiment_repo.get_by_symbol("TSLA", limit=10)
            
            if sentiments:
                print(f"✅ {len(sentiments)}개의 감정분석 결과를 찾았습니다.\n")
                
                for i, sentiment in enumerate(sentiments, 1):
                    print(f"{i}. {sentiment.content.title[:60]}...")
                    print(f"   감정: {sentiment.sentiment_label} ({sentiment.sentiment_score:.3f})")
                    print(f"   신뢰도: {sentiment.confidence:.3f}")
                    print(f"   시장 영향도: {sentiment.market_impact_score:.3f}")
                    print(f"   시장 민감: {'예' if sentiment.is_market_sensitive else '아니오'}")
                    print()
            else:
                print("❌ 저장된 감정분석 결과가 없습니다.")
                
        finally:
            session.close()
        
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()


def test_sentiment_statistics():
    """감정분석 통계 확인"""
    print("=== 감정분석 통계 확인 ===")
    
    session = SessionLocal()
    sentiment_repo = ContentSentimentRepository(session)
    
    try:
        # 전체 감정분석 결과 수 확인
        from sqlalchemy import func
        from app.news_crawler.infra.model.entity.content_sentiments import ContentSentiment
        
        total_count = session.query(func.count(ContentSentiment.id)).scalar()
        print(f"전체 감정분석 결과 수: {total_count}")
        
        if total_count > 0:
            # 감정별 통계
            sentiment_stats = session.query(
                ContentSentiment.sentiment_label,
                func.count(ContentSentiment.id)
            ).group_by(ContentSentiment.sentiment_label).all()
            
            print("\n감정별 분포:")
            for label, count in sentiment_stats:
                percentage = (count / total_count) * 100
                print(f"  {label}: {count}개 ({percentage:.1f}%)")
            
            # 시장 민감 뉴스 통계
            market_sensitive_count = session.query(func.count(ContentSentiment.id)).filter(
                ContentSentiment.is_market_sensitive == True
            ).scalar()
            
            print(f"\n시장 민감 뉴스: {market_sensitive_count}개 ({market_sensitive_count/total_count*100:.1f}%)")
            
    finally:
        session.close()


def main():
    """메인 테스트 함수"""
    print("뉴스 크롤링 + 감정분석 통합 테스트를 시작합니다...\n")
    
    # 1. 뉴스 크롤링 + 감정분석 테스트
    test_news_crawling_with_sentiment()
    
    # 2. 감정분석 통계 확인
    test_sentiment_statistics()
    
    print("통합 테스트가 완료되었습니다!")


if __name__ == "__main__":
    main()
