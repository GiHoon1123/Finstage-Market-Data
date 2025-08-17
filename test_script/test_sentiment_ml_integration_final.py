#!/usr/bin/env python3
"""
감정 특성 ML 모델 통합 최종 테스트

감정 특성이 기존 ML 모델에 제대로 통합되는지 확인합니다.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ml_prediction.ml.data.feature_engineer import FeatureEngineer
from app.ml_prediction.ml.data.sentiment_feature_engineer import SentimentFeatureEngineer
from app.ml_prediction.config.ml_config import ml_settings


def create_sample_price_data():
    """샘플 가격 데이터 생성"""
    print("=== 샘플 가격 데이터 생성 ===")
    
    # 100일간의 샘플 데이터 생성
    end_date = datetime.now()
    start_date = end_date - timedelta(days=100)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # 랜덤 가격 데이터 생성
    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, len(date_range))  # 일일 수익률
    
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # OHLCV 데이터 생성
    data = []
    for i, (date, price) in enumerate(zip(date_range, prices)):
        # 고가, 저가, 시가, 종가 생성
        high = price * (1 + abs(np.random.normal(0, 0.01)))
        low = price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = price * (1 + np.random.normal(0, 0.005))
        close_price = price
        
        # 거래량 생성
        volume = np.random.randint(1000000, 10000000)
        
        data.append({
            'date': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df = df.set_index('date')
    
    print(f"✅ {len(df)}일간의 샘플 가격 데이터 생성 완료")
    print(f"📊 데이터 형태: {df.shape}")
    print(f"📅 날짜 범위: {df.index.min()} ~ {df.index.max()}")
    
    return df


def test_sentiment_feature_engineer():
    """감정 특성 엔지니어 테스트"""
    print("\n=== 감정 특성 엔지니어 테스트 ===")
    
    try:
        # 감정 특성 엔지니어 초기화
        sentiment_engineer = SentimentFeatureEngineer()
        
        # 샘플 가격 데이터 생성
        price_data = create_sample_price_data()
        
        # 감정 특성 생성
        start_date = price_data.index.min()
        end_date = price_data.index.max()
        
        sentiment_features = sentiment_engineer.get_sentiment_features(
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"✅ 감정 특성 생성 완료")
        print(f"📊 감정 특성 형태: {sentiment_features.shape}")
        print(f"📋 감정 특성 컬럼: {list(sentiment_features.columns)}")
        
        # 가격 데이터와 병합
        merged_data = sentiment_engineer.merge_with_price_data(
            price_df=price_data,
            sentiment_df=sentiment_features
        )
        
        print(f"✅ 데이터 병합 완료")
        print(f"📊 병합된 데이터 형태: {merged_data.shape}")
        
        return merged_data
        
    except Exception as e:
        print(f"❌ 감정 특성 엔지니어 테스트 실패: {str(e)}")
        return None


def test_feature_engineer_with_sentiment():
    """감정 특성이 포함된 특성 엔지니어 테스트"""
    print("\n=== 감정 특성이 포함된 특성 엔지니어 테스트 ===")
    
    try:
        # 특성 엔지니어 초기화
        feature_engineer = FeatureEngineer()
        
        # 샘플 가격 데이터 생성
        price_data = create_sample_price_data()
        
        print(f"🔧 특성 엔지니어 설정:")
        print(f"  - 윈도우 크기: {feature_engineer.window_size}")
        print(f"  - 타겟 일수: {feature_engineer.target_days}")
        print(f"  - 감정 특성 사용: {feature_engineer.use_sentiment_features}")
        
        # 멀티 타겟 시퀀스 생성 (감정 특성 포함)
        X, y_dict, feature_names = feature_engineer.create_multi_target_sequences(
            data=price_data,
            target_column="close",
            include_features=True
        )
        
        print(f"✅ 멀티 타겟 시퀀스 생성 완료")
        print(f"📊 특성 데이터 형태: {X.shape}")
        print(f"📊 타겟 데이터 형태:")
        for key, value in y_dict.items():
            print(f"  - {key}: {value.shape}")
        
        print(f"📋 총 특성 수: {len(feature_names)}")
        print(f"📋 특성 목록:")
        for i, feature in enumerate(feature_names):
            print(f"  {i+1:2d}. {feature}")
        
        # 감정 특성 개수 확인
        sentiment_features = [f for f in feature_names if any(keyword in f.lower() for keyword in 
                                                             ['sentiment', 'market_impact', 'news_count', 'positive', 'negative', 'neutral', 'compound'])]
        
        print(f"\n🎯 감정 관련 특성: {len(sentiment_features)}개")
        for feature in sentiment_features:
            print(f"  - {feature}")
        
        return X, y_dict, feature_names
        
    except Exception as e:
        print(f"❌ 특성 엔지니어 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None


def test_ml_model_ready():
    """ML 모델 통합 준비 상태 확인"""
    print("\n=== ML 모델 통합 준비 상태 확인 ===")
    
    try:
        # ML 모델 관련 모듈 임포트 테스트
        from app.ml_prediction.ml.model.trainer import ModelTrainer
        from app.ml_prediction.ml.model.lstm_model import MultiOutputLSTMPredictor
        
        print("✅ ML 모델 모듈 임포트 성공")
        
        # 설정 확인
        print(f"🔧 ML 설정:")
        print(f"  - 윈도우 크기: {ml_settings.model.window_size}")
        print(f"  - 타겟 일수: {ml_settings.model.target_days}")
        print(f"  - LSTM 유닛: {ml_settings.model.lstm_units}")
        print(f"  - 드롭아웃: {ml_settings.model.dropout_rate}")
        
        return True
        
    except Exception as e:
        print(f"❌ ML 모델 준비 실패: {str(e)}")
        return False


def main():
    """메인 테스트 함수"""
    print("감정 특성 ML 모델 통합 최종 테스트를 시작합니다...\n")
    
    # 1. 감정 특성 엔지니어 테스트
    merged_data = test_sentiment_feature_engineer()
    
    # 2. 감정 특성이 포함된 특성 엔지니어 테스트
    X, y_dict, feature_names = test_feature_engineer_with_sentiment()
    
    # 3. ML 모델 준비 상태 확인
    ml_ready = test_ml_model_ready()
    
    # 4. 최종 결과 요약
    print("\n=== 최종 결과 요약 ===")
    
    if merged_data is not None and X is not None and ml_ready:
        print("✅ 모든 테스트가 성공했습니다!")
        
        print(f"\n📊 데이터 요약:")
        print(f"  - 병합된 데이터: {merged_data.shape}")
        print(f"  - 특성 데이터: {X.shape}")
        print(f"  - 총 특성 수: {len(feature_names)}")
        
        # 감정 특성 비율 계산
        sentiment_features = [f for f in feature_names if any(keyword in f.lower() for keyword in 
                                                             ['sentiment', 'market_impact', 'news_count', 'positive', 'negative', 'neutral', 'compound'])]
        sentiment_ratio = len(sentiment_features) / len(feature_names) * 100
        
        print(f"  - 감정 특성 비율: {sentiment_ratio:.1f}% ({len(sentiment_features)}/{len(feature_names)})")
        
        print(f"\n🚀 다음 단계:")
        print(f"1. 나스닥(IXIC) 모델에 감정 특성 통합")
        print(f"2. S&P 500(GSPC) 모델에 감정 특성 통합")
        print(f"3. 모델 재훈련 및 성능 비교")
        print(f"4. 백테스팅으로 효과 검증")
        
    else:
        print("⚠️ 일부 테스트가 실패했습니다.")
        if merged_data is None:
            print("  - 감정 특성 엔지니어 테스트 실패")
        if X is None:
            print("  - 특성 엔지니어 테스트 실패")
        if not ml_ready:
            print("  - ML 모델 준비 실패")
    
    print("\n테스트가 완료되었습니다!")


if __name__ == "__main__":
    main()
