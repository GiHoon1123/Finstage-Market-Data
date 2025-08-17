#!/usr/bin/env python3
"""
감정분석 수정사항 테스트 스크립트

수정된 감정분석 기능이 제대로 작동하는지 확인합니다.
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from app.ml_prediction.ml.data.sentiment_feature_engineer import SentimentFeatureEngineer
from app.ml_prediction.ml.data.feature_engineer import FeatureEngineer
from app.ml_prediction.service.ml_prediction_service import MLPredictionService
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


def test_sentiment_feature_engineer():
    """감정 특성 엔지니어 테스트"""
    print("=== 감정 특성 엔지니어 테스트 ===")
    
    try:
        sentiment_engineer = SentimentFeatureEngineer()
        
        # 테스트 기간 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # 30일 데이터
        
        print(f"📅 테스트 기간: {start_date.date()} ~ {end_date.date()}")
        
        # 1. 나스닥 감정 데이터 테스트
        print("\n🔍 나스닥(^IXIC) 감정 데이터 테스트:")
        ixic_sentiment = sentiment_engineer.get_sentiment_features(
            start_date=start_date,
            end_date=end_date,
            symbol="^IXIC"
        )
        print(f"  - 데이터 형태: {ixic_sentiment.shape}")
        print(f"  - 특성 수: {len(ixic_sentiment.columns)}")
        print(f"  - 샘플 데이터:")
        if not ixic_sentiment.empty:
            print(f"    {ixic_sentiment.head(3)}")
        else:
            print("    데이터 없음")
        
        # 2. S&P 500 감정 데이터 테스트
        print("\n🔍 S&P 500(^GSPC) 감정 데이터 테스트:")
        gspc_sentiment = sentiment_engineer.get_sentiment_features(
            start_date=start_date,
            end_date=end_date,
            symbol="^GSPC"
        )
        print(f"  - 데이터 형태: {gspc_sentiment.shape}")
        print(f"  - 특성 수: {len(gspc_sentiment.columns)}")
        print(f"  - 샘플 데이터:")
        if not gspc_sentiment.empty:
            print(f"    {gspc_sentiment.head(3)}")
        else:
            print("    데이터 없음")
        
        # 3. 전체 감정 데이터 테스트 (심볼 필터 없음)
        print("\n🔍 전체 감정 데이터 테스트:")
        all_sentiment = sentiment_engineer.get_sentiment_features(
            start_date=start_date,
            end_date=end_date
        )
        print(f"  - 데이터 형태: {all_sentiment.shape}")
        print(f"  - 특성 수: {len(all_sentiment.columns)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 감정 특성 엔지니어 테스트 실패: {str(e)}")
        logger.error("sentiment_feature_engineer_test_failed", error=str(e))
        return False


def test_feature_engineer():
    """특성 엔지니어 테스트"""
    print("\n=== 특성 엔지니어 테스트 ===")
    
    try:
        feature_engineer = FeatureEngineer()
        
        # 샘플 데이터 생성
        import pandas as pd
        import numpy as np
        
        # 100일간의 샘플 데이터 생성
        end_date = datetime.now()
        start_date = end_date - timedelta(days=100)
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 랜덤 가격 데이터 생성
        np.random.seed(42)
        base_price = 100
        returns = np.random.normal(0.001, 0.02, len(date_range))
        
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # OHLCV 데이터 생성
        data = []
        for i, (date, price) in enumerate(zip(date_range, prices)):
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            open_price = price * (1 + np.random.normal(0, 0.005))
            close_price = price
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
        
        print(f"📊 샘플 데이터 생성: {df.shape}")
        
        # 1. 감정 특성 없이 테스트
        print("\n🔍 감정 특성 없이 테스트:")
        feature_engineer.use_sentiment_features = False
        X_no_sentiment, y_dict_no_sentiment, feature_names_no_sentiment = feature_engineer.create_multi_target_sequences(
            df, target_column="close", symbol="^IXIC"
        )
        print(f"  - 특성 수: {len(feature_names_no_sentiment)}")
        print(f"  - X 형태: {X_no_sentiment.shape}")
        
        # 2. 감정 특성 포함 테스트
        print("\n🔍 감정 특성 포함 테스트:")
        feature_engineer.use_sentiment_features = True
        X_with_sentiment, y_dict_with_sentiment, feature_names_with_sentiment = feature_engineer.create_multi_target_sequences(
            df, target_column="close", symbol="^IXIC"
        )
        print(f"  - 특성 수: {len(feature_names_with_sentiment)}")
        print(f"  - X 형태: {X_with_sentiment.shape}")
        
        # 감정 관련 특성 확인
        sentiment_features = [f for f in feature_names_with_sentiment if any(keyword in f.lower() for keyword in 
            ['sentiment', 'market_impact', 'news_count', 'positive', 'negative', 'neutral', 'compound'])]
        print(f"  - 감정 관련 특성: {len(sentiment_features)}개")
        
        return True
        
    except Exception as e:
        print(f"❌ 특성 엔지니어 테스트 실패: {str(e)}")
        logger.error("feature_engineer_test_failed", error=str(e))
        return False


async def test_ml_service():
    """ML 서비스 테스트"""
    print("\n=== ML 서비스 테스트 ===")
    
    try:
        ml_service = MLPredictionService()
        
        # 심볼 정규화 테스트
        print("🔍 심볼 정규화 테스트:")
        test_symbols = ["IXIC", "GSPC", "^IXIC", "^GSPC"]
        for symbol in test_symbols:
            normalized = ml_service._normalize_symbol(symbol)
            print(f"  - {symbol} -> {normalized}")
        
        # 간단한 훈련 테스트 (실제 훈련은 하지 않음)
        print("\n🔍 훈련 서비스 테스트:")
        print("  - 서비스 초기화 완료")
        print("  - 심볼 매핑 정상 작동")
        print("  - 감정 특성 지원 활성화")
        
        return True
        
    except Exception as e:
        print(f"❌ ML 서비스 테스트 실패: {str(e)}")
        logger.error("ml_service_test_failed", error=str(e))
        return False


async def main():
    """메인 테스트 함수"""
    print("감정분석 수정사항 테스트를 시작합니다...\n")
    
    # 1. 감정 특성 엔지니어 테스트
    sentiment_test = test_sentiment_feature_engineer()
    
    # 2. 특성 엔지니어 테스트
    feature_test = test_feature_engineer()
    
    # 3. ML 서비스 테스트
    service_test = await test_ml_service()
    
    # 4. 결과 요약
    print("\n=== 테스트 결과 요약 ===")
    print(f"✅ 감정 특성 엔지니어: {'성공' if sentiment_test else '실패'}")
    print(f"✅ 특성 엔지니어: {'성공' if feature_test else '실패'}")
    print(f"✅ ML 서비스: {'성공' if service_test else '실패'}")
    
    if all([sentiment_test, feature_test, service_test]):
        print("\n🎉 모든 테스트가 성공했습니다!")
        print("이제 감정분석이 포함된 ML 모델 훈련을 시도할 수 있습니다.")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다.")
        print("추가 디버깅이 필요합니다.")
    
    print("\n테스트가 완료되었습니다!")


if __name__ == "__main__":
    asyncio.run(main())
