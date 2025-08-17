#!/usr/bin/env python3
"""
예측 문제 해결 테스트 스크립트

감정분석 특성이 포함된 모델로 예측이 제대로 작동하는지 확인합니다.
"""

import sys
import os
from datetime import date, datetime
import pickle

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from app.ml_prediction.ml.model.predictor import MultiTimeframePredictor
from app.ml_prediction.ml.data.preprocessor import MLDataPreprocessor
from app.ml_prediction.config.ml_config import ml_settings

def test_prediction_with_sentiment():
    """감정분석 특성이 포함된 예측 테스트"""
    print("=== 감정분석 특성 예측 테스트 ===")
    
    try:
        # 1. 예측기 초기화
        predictor = MultiTimeframePredictor()
        
        # 2. 예측 실행 (감정분석 특성 활성화)
        result = predictor.predict_price(
            symbol="^GSPC",
            prediction_date=date.today(),
            model_version=None,  # 최신 활성 모델 사용
            save_prediction=False,
            use_sentiment=True  # 감정분석 특성 활성화
        )
        
        print("✅ 예측 성공!")
        print(f"상태: {result.get('status')}")
        print(f"예측 결과 수: {len(result.get('predictions', []))}")
        
        for pred in result.get('predictions', []):
            print(f"  - {pred['timeframe']}: {pred['predicted_price']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 예측 실패: {str(e)}")
        return False

def test_feature_count():
    """특성 수 확인"""
    print("\n=== 특성 수 확인 ===")
    
    try:
        # 1. 전처리기 초기화
        preprocessor = MLDataPreprocessor()
        
        # 2. 예측 데이터 준비 (감정분석 특성 활성화)
        X, metadata = preprocessor.prepare_prediction_data(
            symbol="^GSPC",
            end_date=date.today(),
            use_sentiment=True
        )
        
        print(f"✅ 특성 수: {X.shape[-1]}")
        print(f"감정 특성 활성화: {metadata.get('sentiment_features_enabled', False)}")
        
        return X.shape[-1]
        
    except Exception as e:
        print(f"❌ 특성 수 확인 실패: {str(e)}")
        return None

def test_model_scaler():
    """모델 스케일러 확인"""
    print("\n=== 모델 스케일러 확인 ===")
    
    try:
        # 최신 모델 경로 확인
        model_dir = "models/ml_prediction/GSPC_lstm"
        if not os.path.exists(model_dir):
            print("❌ 모델 디렉토리가 없습니다.")
            return None
            
        # 최신 버전 찾기
        versions = [d for d in os.listdir(model_dir) if d.startswith('v')]
        if not versions:
            print("❌ 모델 버전이 없습니다.")
            return None
            
        latest_version = sorted(versions)[-1]
        scaler_path = f"{model_dir}/{latest_version}/scalers/feature_scaler.pkl"
        
        if not os.path.exists(scaler_path):
            print(f"❌ 스케일러 파일이 없습니다: {scaler_path}")
            return None
            
        # 스케일러 로드
        with open(scaler_path, 'rb') as f:
            scaler = pickle.load(f)
            
        print(f"✅ 스케일러 로드 성공")
        print(f"스케일러 타입: {type(scaler).__name__}")
        print(f"예상 특성 수: {scaler.n_features_in_}")
        
        return scaler.n_features_in_
        
    except Exception as e:
        print(f"❌ 스케일러 확인 실패: {str(e)}")
        return None

if __name__ == "__main__":
    print("감정분석 특성 예측 테스트 시작...\n")
    
    # 1. 특성 수 확인
    feature_count = test_feature_count()
    
    # 2. 스케일러 확인
    expected_features = test_model_scaler()
    
    # 3. 예측 테스트
    if feature_count and expected_features:
        if feature_count == expected_features:
            print(f"\n✅ 특성 수 일치: {feature_count}")
            test_prediction_with_sentiment()
        else:
            print(f"\n❌ 특성 수 불일치: 예측={feature_count}, 스케일러={expected_features}")
    else:
        print("\n❌ 기본 정보 확인 실패")
