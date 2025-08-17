#!/usr/bin/env python3
"""
예측 시 특성 수 디버깅 스크립트

예측 시 실제로 몇 개의 특성이 생성되는지 확인합니다.
"""

import sys
import os
from datetime import date, datetime
import pickle

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from app.ml_prediction.ml.data.preprocessor import MLDataPreprocessor
from app.ml_prediction.ml.model.predictor import MultiTimeframePredictor
from app.ml_prediction.config.ml_config import ml_settings

def debug_prediction_features():
    """예측 시 특성 수 디버깅"""
    print("=== 예측 시 특성 수 디버깅 ===")
    
    try:
        # 1. Preprocessor 초기화
        preprocessor = MLDataPreprocessor()
        
        # 2. 감정분석 특성 활성화
        preprocessor.feature_engineer.use_sentiment_features = True
        print(f"감정분석 특성 활성화: {preprocessor.feature_engineer.use_sentiment_features}")
        
        # 3. 예측 데이터 준비 (감정분석 특성 활성화)
        X_pred, metadata = preprocessor.prepare_prediction_data(
            symbol="^GSPC", 
            end_date=date.today(), 
            use_sentiment=True
        )
        
        print(f"예측 특성 수: {X_pred.shape[-1]}")
        print(f"메타데이터: {metadata}")
        
        # 4. 스케일러 정보 확인
        if preprocessor.feature_engineer.feature_scaler:
            print(f"스케일러 특성 수: {preprocessor.feature_engineer.feature_scaler.n_features_in_}")
        else:
            print("스케일러가 로드되지 않음")
            
        # 5. Predictor로 테스트
        predictor = MultiTimeframePredictor()
        
        # 6. 모델 로드 (스케일러 로드 포함)
        model_predictor, model_entity = predictor._load_model("^GSPC")
        print(f"모델 로드 완료: {model_entity.model_name}")
        
        # 7. 감정분석 특성 활성화
        predictor.preprocessor.feature_engineer.use_sentiment_features = True
        print(f"Predictor 감정분석 특성 활성화: {predictor.preprocessor.feature_engineer.use_sentiment_features}")
        
        # 8. 예측 데이터 준비
        X_pred2, metadata2 = predictor.preprocessor.prepare_prediction_data(
            symbol="^GSPC", 
            end_date=date.today(), 
            use_sentiment=True
        )
        
        print(f"Predictor 예측 특성 수: {X_pred2.shape[-1]}")
        print(f"Predictor 스케일러 특성 수: {predictor.preprocessor.feature_engineer.feature_scaler.n_features_in_}")
        
        # 9. 특성 수 비교
        if X_pred2.shape[-1] == predictor.preprocessor.feature_engineer.feature_scaler.n_features_in_:
            print("✅ 특성 수 일치!")
        else:
            print(f"❌ 특성 수 불일치: 예측={X_pred2.shape[-1]}, 스케일러={predictor.preprocessor.feature_engineer.feature_scaler.n_features_in_}")
            
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_prediction_features()
