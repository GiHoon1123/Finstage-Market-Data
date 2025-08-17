#!/usr/bin/env python3
"""
여러 지표의 특성 수 확인 테스트
"""

import sys
import os
from datetime import date

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.ml_prediction.ml.data.preprocessor import MLDataPreprocessor
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)

def test_multiple_symbols():
    """여러 지표의 특성 수를 확인"""
    
    symbols = ["^IXIC", "^GSPC", "^DJI", "AAPL", "GOOGL", "MSFT"]
    
    print("=== 여러 지표 특성 수 확인 ===\n")
    
    for symbol in symbols:
        try:
            print(f"🔍 {symbol} 지표 테스트 중...")
            
            # 전처리기 초기화
            preprocessor = MLDataPreprocessor()
            preprocessor.feature_engineer.use_sentiment_features = True
            
            # 예측 데이터 준비
            prediction_data = preprocessor.prepare_prediction_data(
                symbol=symbol,
                end_date=date(2025, 8, 17),
                lookback_days=90,
                use_sentiment=True
            )
            
            if prediction_data:
                feature_count = prediction_data['X'].shape[1]
                print(f"✅ {symbol}: {feature_count}개 특성")
            else:
                print(f"❌ {symbol}: 데이터 준비 실패")
                
        except Exception as e:
            print(f"❌ {symbol}: 오류 발생 - {str(e)}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_multiple_symbols()
