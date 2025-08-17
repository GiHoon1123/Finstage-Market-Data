#!/usr/bin/env python3
"""
감정분석 기능 테스트 스크립트

뉴스 크롤링과 감정분석이 정상적으로 작동하는지 확인합니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.news_crawler.service.sentiment_analyzer import SentimentAnalyzer
from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler
from app.news_crawler.service.news_processor import NewsProcessor


def test_sentiment_analyzer():
    """감정분석기 단위 테스트"""
    print("=== 감정분석기 테스트 ===")
    
    analyzer = SentimentAnalyzer()
    
    # 테스트 케이스들
    test_cases = [
        {
            "text": "Apple stock surges after strong earnings report",
            "expected": "positive"
        },
        {
            "text": "Tesla shares plunge on disappointing delivery numbers",
            "expected": "negative"
        },
        {
            "text": "Market remains stable with minimal changes",
            "expected": "neutral"
        },
        {
            "text": "Breaking: Fed announces emergency rate cut",
            "expected": "negative"
        },
        {
            "text": "Exclusive: Major tech company beats revenue expectations",
            "expected": "positive"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        result = analyzer.analyze_sentiment(case["text"])
        print(f"테스트 {i}: {case['text']}")
        print(f"  예상: {case['expected']}, 실제: {result['sentiment_label']}")
        print(f"  점수: {result['sentiment_score']:.3f}, 신뢰도: {result['confidence']:.3f}")
        print(f"  시장 영향도: {result['market_impact_score']:.3f}")
        print()


def test_news_crawling_with_sentiment():
    """뉴스 크롤링과 감정분석 통합 테스트"""
    print("=== 뉴스 크롤링 + 감정분석 통합 테스트 ===")
    
    try:
        # AAPL 뉴스 크롤링
        crawler = YahooNewsCrawler("AAPL")
        news_items = crawler.crawl()
        
        if not news_items:
            print("❌ 크롤링된 뉴스가 없습니다.")
            return
        
        print(f"✅ {len(news_items)}개의 뉴스를 크롤링했습니다.")
        
        # 뉴스 처리 (감정분석 포함)
        processor = NewsProcessor(news_items, telegram_enabled=False)
        processor.run()
        
        print("✅ 뉴스 처리 및 감정분석이 완료되었습니다.")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")


def main():
    """메인 테스트 함수"""
    print("감정분석 기능 테스트를 시작합니다...\n")
    
    # 1. 감정분석기 단위 테스트
    test_sentiment_analyzer()
    
    # 2. 통합 테스트 (선택적)
    user_input = input("뉴스 크롤링 + 감정분석 통합 테스트를 실행하시겠습니까? (y/n): ")
    if user_input.lower() == 'y':
        test_news_crawling_with_sentiment()
    
    print("테스트가 완료되었습니다.")


if __name__ == "__main__":
    main()
