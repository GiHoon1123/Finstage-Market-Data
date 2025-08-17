#!/usr/bin/env python3
"""
수동 뉴스 감정분석 테스트 스크립트

수동으로 뉴스 데이터를 생성하여 감정분석 기능을 테스트합니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone
from app.news_crawler.service.news_processor import NewsProcessor
from app.news_crawler.infra.model.repository.content_sentiment_repository import ContentSentimentRepository
from app.common.infra.database.config.database_config import SessionLocal


def create_test_news():
    """테스트용 뉴스 데이터 생성"""
    test_news = [
        {
            "symbol": "AAPL",
            "title": "Apple Stock Surges 8% After Strong iPhone Sales Report",
            "summary": "Apple Inc. reported exceptional iPhone sales in Q3, beating analyst expectations by 15%. The company's revenue grew significantly.",
            "url": "https://test.com/apple-strong-sales",
            "html": "<html>Test content</html>",
            "source": "test.com",
            "crawled_at": datetime.now(timezone.utc),
            "published_at": datetime.now(timezone.utc),
            "content_hash": "test_hash_apple_strong_sales_001"
        },
        {
            "symbol": "TSLA",
            "title": "Tesla Shares Plunge 12% on Disappointing Delivery Numbers",
            "summary": "Tesla reported lower than expected vehicle deliveries in Q3, causing significant concern among investors.",
            "url": "https://test.com/tesla-disappointing-deliveries",
            "html": "<html>Test content</html>",
            "source": "test.com",
            "crawled_at": datetime.now(timezone.utc),
            "published_at": datetime.now(timezone.utc),
            "content_hash": "test_hash_tesla_disappointing_001"
        },
        {
            "symbol": "MSFT",
            "title": "Microsoft Beats Revenue Expectations with Strong Cloud Growth",
            "summary": "Microsoft's cloud services division showed exceptional growth, driving overall revenue above expectations.",
            "url": "https://test.com/microsoft-cloud-growth",
            "html": "<html>Test content</html>",
            "source": "test.com",
            "crawled_at": datetime.now(timezone.utc),
            "published_at": datetime.now(timezone.utc),
            "content_hash": "test_hash_microsoft_cloud_001"
        },
        {
            "symbol": "GOOGL",
            "title": "Breaking: Google Announces Major AI Breakthrough",
            "summary": "Google has announced a revolutionary AI breakthrough that could transform the technology industry.",
            "url": "https://test.com/google-ai-breakthrough",
            "html": "<html>Test content</html>",
            "source": "test.com",
            "crawled_at": datetime.now(timezone.utc),
            "published_at": datetime.now(timezone.utc),
            "content_hash": "test_hash_google_ai_001"
        },
        {
            "symbol": "AMZN",
            "title": "Amazon Reports Mixed Q3 Results Amid Market Uncertainty",
            "summary": "Amazon's Q3 results showed mixed performance with some segments performing well while others struggled.",
            "url": "https://test.com/amazon-mixed-results",
            "html": "<html>Test content</html>",
            "source": "test.com",
            "crawled_at": datetime.now(timezone.utc),
            "published_at": datetime.now(timezone.utc),
            "content_hash": "test_hash_amazon_mixed_001"
        }
    ]
    
    return test_news


def test_manual_sentiment_analysis():
    """수동 뉴스 감정분석 테스트"""
    print("=== 수동 뉴스 감정분석 테스트 ===")
    
    try:
        # 테스트 뉴스 생성
        test_news = create_test_news()
        print(f"✅ {len(test_news)}개의 테스트 뉴스를 생성했습니다.")
        
        # 뉴스 처리 (감정분석 포함)
        print("뉴스 처리 및 감정분석 중...")
        processor = NewsProcessor(test_news, telegram_enabled=False)
        processor.run()
        
        print("✅ 뉴스 처리 및 감정분석이 완료되었습니다.")
        
        # 결과 확인
        print("\n=== 저장된 감정분석 결과 확인 ===")
        session = SessionLocal()
        sentiment_repo = ContentSentimentRepository(session)
        
        try:
            # 모든 심볼의 감정분석 결과 조회
            all_sentiments = []
            symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
            
            for symbol in symbols:
                sentiments = sentiment_repo.get_by_symbol(symbol, limit=5)
                all_sentiments.extend(sentiments)
            
            if all_sentiments:
                print(f"✅ {len(all_sentiments)}개의 감정분석 결과를 찾았습니다.\n")
                
                for i, sentiment in enumerate(all_sentiments, 1):
                    print(f"{i}. [{sentiment.content.symbol}] {sentiment.content.title}")
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
            
            # 심볼별 통계 (수정된 쿼리)
            from app.news_crawler.infra.model.entity.content import Content
            
            symbol_stats = session.query(
                Content.symbol,
                func.count(ContentSentiment.id)
            ).join(ContentSentiment).group_by(Content.symbol).all()
            
            print(f"\n심볼별 분포:")
            for symbol, count in symbol_stats:
                print(f"  {symbol}: {count}개")
            
    finally:
        session.close()


def main():
    """메인 테스트 함수"""
    print("수동 뉴스 감정분석 테스트를 시작합니다...\n")
    
    # 1. 수동 뉴스 감정분석 테스트
    test_manual_sentiment_analysis()
    
    # 2. 감정분석 통계 확인
    test_sentiment_statistics()
    
    print("수동 테스트가 완료되었습니다!")


if __name__ == "__main__":
    main()
