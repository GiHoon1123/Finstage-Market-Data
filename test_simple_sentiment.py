#!/usr/bin/env python3
"""
간단한 감정분석 테스트 스크립트

데이터베이스 연결 없이 감정분석 기능만 테스트합니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.news_crawler.service.sentiment_analyzer import SentimentAnalyzer


def test_financial_news_sentiment():
    """금융 뉴스 감정분석 테스트"""
    print("=== 금융 뉴스 감정분석 테스트 ===")
    
    analyzer = SentimentAnalyzer()
    
    # 실제 금융 뉴스 헤드라인들
    financial_news = [
        "Apple Inc. (AAPL) Stock Surges 5% After Strong Q3 Earnings Beat",
        "Tesla (TSLA) Shares Plunge 8% on Disappointing Delivery Numbers",
        "Breaking: Federal Reserve Announces Emergency Interest Rate Cut",
        "Exclusive: Microsoft (MSFT) Beats Revenue Expectations by 15%",
        "Market Update: S&P 500 Rises Modestly in Quiet Trading Session",
        "Crisis Alert: Major Bank Reports Significant Losses in Q4",
        "Positive Outlook: Tech Sector Shows Strong Growth Potential",
        "Warning: Economic Indicators Suggest Potential Market Correction",
        "Bullish Signal: Institutional Investors Increase Stock Holdings",
        "Bearish Trend: Oil Prices Continue Decline Amid Supply Concerns"
    ]
    
    print("금융 뉴스 헤드라인 감정분석 결과:\n")
    
    for i, headline in enumerate(financial_news, 1):
        result = analyzer.analyze_sentiment(headline)
        
        # 감정 이모지
        sentiment_emoji = {
            'positive': '📈',
            'negative': '📉', 
            'neutral': '➡️'
        }
        
        emoji = sentiment_emoji.get(result['sentiment_label'], '❓')
        
        print(f"{i:2d}. {emoji} {headline}")
        print(f"    감정: {result['sentiment_label']} ({result['sentiment_score']:.3f})")
        print(f"    신뢰도: {result['confidence']:.3f}")
        print(f"    시장 영향도: {result['market_impact_score']:.3f}")
        print(f"    시장 민감: {'예' if result['is_market_sensitive'] else '아니오'}")
        print()


def test_sentiment_thresholds():
    """감정 임계값 테스트"""
    print("=== 감정 임계값 테스트 ===")
    
    analyzer = SentimentAnalyzer()
    
    # 다양한 강도의 감정 표현
    test_texts = [
        ("매우 긍정적", "Apple stock skyrockets 20% after revolutionary product launch"),
        ("긍정적", "Apple stock rises 5% after good earnings report"),
        ("약간 긍정적", "Apple stock slightly up after stable performance"),
        ("중립", "Apple stock unchanged in quiet trading"),
        ("약간 부정적", "Apple stock slightly down on market concerns"),
        ("부정적", "Apple stock falls 5% on disappointing results"),
        ("매우 부정적", "Apple stock crashes 20% after major scandal")
    ]
    
    print("감정 강도별 분석 결과:\n")
    
    for label, text in test_texts:
        result = analyzer.analyze_sentiment(text)
        print(f"{label:>10}: {text}")
        print(f"{'':>10}  점수: {result['sentiment_score']:.3f} ({result['sentiment_label']})")
        print()


def main():
    """메인 테스트 함수"""
    print("간단한 감정분석 테스트를 시작합니다...\n")
    
    # 1. 금융 뉴스 감정분석 테스트
    test_financial_news_sentiment()
    
    # 2. 감정 임계값 테스트
    test_sentiment_thresholds()
    
    print("테스트가 완료되었습니다!")


if __name__ == "__main__":
    main()
