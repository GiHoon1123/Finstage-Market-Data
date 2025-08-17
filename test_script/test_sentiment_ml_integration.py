#!/usr/bin/env python3
"""
감정분석 데이터를 ML 모델에 통합하는 테스트 스크립트

기존 감정분석 데이터를 확인하고 ML 훈련 데이터에 추가하는 방법을 테스트합니다.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.common.infra.database.config.database_config import SessionLocal
from app.news_crawler.infra.model.entity.content_sentiments import ContentSentiment
from app.news_crawler.infra.model.entity.content import Content
from sqlalchemy import func, and_


def analyze_sentiment_data():
    """현재 감정분석 데이터 분석"""
    print("=== 현재 감정분석 데이터 분석 ===")
    
    session = SessionLocal()
    try:
        # 전체 감정분석 데이터 통계
        total_sentiments = session.query(func.count(ContentSentiment.id)).scalar()
        print(f"📊 전체 감정분석 데이터 수: {total_sentiments}")
        
        if total_sentiments == 0:
            print("❌ 감정분석 데이터가 없습니다.")
            return None
        
        # 일별 감정 통계
        daily_stats = session.query(
            func.date(ContentSentiment.analyzed_at).label('date'),
            func.count(ContentSentiment.id).label('count'),
            func.avg(ContentSentiment.sentiment_score).label('avg_sentiment'),
            func.avg(ContentSentiment.market_impact_score).label('avg_market_impact')
        ).group_by(
            func.date(ContentSentiment.analyzed_at)
        ).order_by(
            func.date(ContentSentiment.analyzed_at).desc()
        ).limit(10).all()
        
        print(f"\n📅 최근 10일간 감정 통계:")
        for stat in daily_stats:
            print(f"  {stat.date}: {stat.count}개 뉴스, 평균 감정 {stat.avg_sentiment:.3f}, 시장 영향도 {stat.avg_market_impact:.3f}")
        
        # 감정 분포
        sentiment_dist = session.query(
            ContentSentiment.sentiment_label,
            func.count(ContentSentiment.id)
        ).group_by(ContentSentiment.sentiment_label).all()
        
        print(f"\n😊 감정 분포:")
        for label, count in sentiment_dist:
            percentage = (count / total_sentiments) * 100
            print(f"  {label}: {count}개 ({percentage:.1f}%)")
        
        return daily_stats
        
    except Exception as e:
        print(f"❌ 데이터 분석 실패: {str(e)}")
        return None
    finally:
        session.close()


def create_sentiment_features(daily_stats):
    """감정 데이터를 ML 특성으로 변환"""
    print("\n=== 감정 데이터를 ML 특성으로 변환 ===")
    
    if not daily_stats:
        print("❌ 감정 데이터가 없습니다.")
        return None
    
            # DataFrame으로 변환
    df = pd.DataFrame([
        {
            'date': stat.date,
            'news_count': stat.count,
            'avg_sentiment': stat.avg_sentiment,
            'avg_market_impact': stat.avg_market_impact,
            'sensitive_news_count': 0  # 임시로 0으로 설정
        }
        for stat in daily_stats
    ])
    
    # 날짜를 인덱스로 설정
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    
    # 추가 특성 생성
    df['sentiment_change'] = df['avg_sentiment'].diff()  # 전일 대비 감정 변화
    df['sentiment_volatility'] = df['avg_sentiment'].rolling(3).std()  # 3일 감정 변동성
    df['sentiment_ma_3d'] = df['avg_sentiment'].rolling(3).mean()  # 3일 감정 이동평균
    df['sentiment_ma_7d'] = df['avg_sentiment'].rolling(7).mean()  # 7일 감정 이동평균
    
    # 긍정/부정 비율 (가정)
    df['positive_ratio'] = 0.5 + (df['avg_sentiment'] * 0.3)  # 감정 점수 기반 긍정 비율 추정
    df['negative_ratio'] = 0.5 - (df['avg_sentiment'] * 0.3)  # 감정 점수 기반 부정 비율 추정
    
    print(f"✅ {len(df)}일간의 감정 특성 생성 완료")
    print(f"📋 생성된 특성들:")
    for col in df.columns:
        print(f"  - {col}")
    
    return df


def test_ml_integration():
    """ML 모델 통합 테스트"""
    print("\n=== ML 모델 통합 테스트 ===")
    
    # 1. 감정 데이터 분석
    daily_stats = analyze_sentiment_data()
    
    # 2. 감정 특성 생성
    sentiment_features = create_sentiment_features(daily_stats)
    
    if sentiment_features is None:
        print("❌ 감정 특성 생성 실패")
        return
    
    # 3. 샘플 데이터 출력
    print(f"\n📊 샘플 감정 특성 데이터:")
    print(sentiment_features.head())
    
    # 4. 특성 상관관계 분석
    print(f"\n🔗 특성 상관관계:")
    correlation_matrix = sentiment_features.corr()
    print(correlation_matrix['avg_sentiment'].sort_values(ascending=False))
    
    # 5. ML 모델 통합 시뮬레이션
    print(f"\n🤖 ML 모델 통합 시뮬레이션:")
    print("기존 특성: [OHLCV, 기술지표들]")
    print("추가 특성: [감정 점수, 감정 변화율, 시장 영향도, 민감 뉴스 수]")
    print("예상 효과: 시장 감정을 반영한 더 정확한 예측")
    
    return sentiment_features


def check_ml_model_ready():
    """ML 모델 통합 준비 상태 확인"""
    print("\n=== ML 모델 통합 준비 상태 확인 ===")
    
    try:
        # ML 모델 관련 모듈 임포트 테스트
        from app.ml_prediction.ml.data.feature_engineer import FeatureEngineer
        from app.ml_prediction.ml.model.trainer import ModelTrainer
        from app.ml_prediction.config.ml_config import ml_settings
        
        print("✅ ML 모델 모듈 임포트 성공")
        
        # 설정 확인
        print(f"🔧 ML 설정:")
        print(f"  - 윈도우 크기: {ml_settings.model.window_size}")
        print(f"  - 타겟 일수: {ml_settings.model.target_days}")
        print(f"  - LSTM 유닛: {ml_settings.model.lstm_units}")
        
        # 특성 엔지니어 확인
        feature_engineer = FeatureEngineer()
        print(f"✅ 특성 엔지니어 초기화 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ ML 모델 준비 실패: {str(e)}")
        return False


def main():
    """메인 테스트 함수"""
    print("감정분석 데이터를 ML 모델에 통합하는 테스트를 시작합니다...\n")
    
    # 1. 감정 데이터 분석 및 특성 생성
    sentiment_features = test_ml_integration()
    
    # 2. ML 모델 준비 상태 확인
    ml_ready = check_ml_model_ready()
    
    # 3. 통합 계획 제시
    print("\n=== 통합 계획 ===")
    if sentiment_features is not None and ml_ready:
        print("✅ 모든 준비가 완료되었습니다!")
        print("\n📋 다음 단계:")
        print("1. 기존 특성 엔지니어에 감정 특성 추가")
        print("2. 나스닥(IXIC) 모델에 감정 특성 통합")
        print("3. S&P 500(GSPC) 모델에 감정 특성 통합")
        print("4. 모델 재훈련 및 성능 비교")
        print("5. 백테스팅으로 효과 검증")
    else:
        print("⚠️ 일부 준비가 필요합니다.")
    
    print("\n테스트가 완료되었습니다!")


if __name__ == "__main__":
    main()
