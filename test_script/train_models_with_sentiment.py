#!/usr/bin/env python3
"""
감정 특성이 포함된 ML 모델 훈련 스크립트

나스닥(IXIC)과 S&P 500(GSPC) 모델에 감정 특성을 추가하여 훈련합니다.
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ml_prediction.service.ml_prediction_service import MLPredictionService
from app.ml_prediction.ml.model.trainer import ModelTrainer
from app.ml_prediction.config.ml_config import ml_settings
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


async def train_ixic_with_sentiment():
    """나스닥(IXIC) 모델에 감정 특성 추가하여 훈련"""
    print("=== 나스닥(IXIC) 모델 감정 특성 훈련 ===")
    
    try:
        # ML 예측 서비스 초기화
        ml_service = MLPredictionService()
        
        # 훈련 설정
        symbol = "IXIC"
        start_date = datetime.now() - timedelta(days=365)  # 1년 데이터
        end_date = datetime.now()
        
        print(f"🔧 훈련 설정:")
        print(f"  - 심볼: {symbol}")
        print(f"  - 기간: {start_date.date()} ~ {end_date.date()}")
        print(f"  - 감정 특성: 활성화")
        
        # 모델 훈련
        result = await ml_service.train_model(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            use_sentiment=True  # 감정 특성 사용
        )
        
        if result['success']:
            print(f"✅ 나스닥 모델 훈련 성공!")
            print(f"📊 모델 정보:")
            print(f"  - 모델 경로: {result.get('model_path', 'N/A')}")
            print(f"  - 특성 수: {result.get('feature_count', 'N/A')}")
            print(f"  - 훈련 샘플: {result.get('train_samples', 'N/A')}")
            print(f"  - 검증 샘플: {result.get('val_samples', 'N/A')}")
            print(f"  - 훈련 시간: {result.get('training_time', 'N/A')}")
            
            # 성능 메트릭 출력
            if 'metrics' in result:
                metrics = result['metrics']
                print(f"📈 성능 메트릭:")
                for target, target_metrics in metrics.items():
                    print(f"  - {target}:")
                    print(f"    MAE: {target_metrics.get('mae', 'N/A'):.4f}")
                    print(f"    RMSE: {target_metrics.get('rmse', 'N/A'):.4f}")
                    print(f"    R²: {target_metrics.get('r2', 'N/A'):.4f}")
            
            return result
        else:
            print(f"❌ 나스닥 모델 훈련 실패: {result.get('error', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"❌ 나스닥 모델 훈련 중 오류: {str(e)}")
        logger.error("ixic_training_failed", error=str(e))
        return None


async def train_gspc_with_sentiment():
    """S&P 500(GSPC) 모델에 감정 특성 추가하여 훈련"""
    print("\n=== S&P 500(GSPC) 모델 감정 특성 훈련 ===")
    
    try:
        # ML 예측 서비스 초기화
        ml_service = MLPredictionService()
        
        # 훈련 설정
        symbol = "GSPC"
        start_date = datetime.now() - timedelta(days=365)  # 1년 데이터
        end_date = datetime.now()
        
        print(f"🔧 훈련 설정:")
        print(f"  - 심볼: {symbol}")
        print(f"  - 기간: {start_date.date()} ~ {end_date.date()}")
        print(f"  - 감정 특성: 활성화")
        
        # 모델 훈련
        result = await ml_service.train_model(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            use_sentiment=True  # 감정 특성 사용
        )
        
        if result['success']:
            print(f"✅ S&P 500 모델 훈련 성공!")
            print(f"📊 모델 정보:")
            print(f"  - 모델 경로: {result.get('model_path', 'N/A')}")
            print(f"  - 특성 수: {result.get('feature_count', 'N/A')}")
            print(f"  - 훈련 샘플: {result.get('train_samples', 'N/A')}")
            print(f"  - 검증 샘플: {result.get('val_samples', 'N/A')}")
            print(f"  - 훈련 시간: {result.get('training_time', 'N/A')}")
            
            # 성능 메트릭 출력
            if 'metrics' in result:
                metrics = result['metrics']
                print(f"📈 성능 메트릭:")
                for target, target_metrics in metrics.items():
                    print(f"  - {target}:")
                    print(f"    MAE: {target_metrics.get('mae', 'N/A'):.4f}")
                    print(f"    RMSE: {target_metrics.get('rmse', 'N/A'):.4f}")
                    print(f"    R²: {target_metrics.get('r2', 'N/A'):.4f}")
            
            return result
        else:
            print(f"❌ S&P 500 모델 훈련 실패: {result.get('error', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"❌ S&P 500 모델 훈련 중 오류: {str(e)}")
        logger.error("gspc_training_failed", error=str(e))
        return None


async def compare_models():
    """기존 모델과 감정 특성 모델 비교"""
    print("\n=== 모델 성능 비교 ===")
    
    try:
        # 기존 모델과 감정 특성 모델의 성능 비교
        # (실제로는 기존 모델 결과와 비교해야 함)
        
        print("📊 성능 비교:")
        print("  - 기존 모델: 차트 데이터만 사용")
        print("  - 감정 모델: 차트 데이터 + 감정 특성 사용")
        print("  - 예상 개선: 감정 특성으로 인한 예측 정확도 향상")
        
        # 향후 실제 비교 로직 추가 예정
        
    except Exception as e:
        print(f"❌ 모델 비교 중 오류: {str(e)}")


async def main():
    """메인 훈련 함수"""
    print("감정 특성이 포함된 ML 모델 훈련을 시작합니다...\n")
    
    # 1. 나스닥 모델 훈련
    ixic_result = await train_ixic_with_sentiment()
    
    # 2. S&P 500 모델 훈련
    gspc_result = await train_gspc_with_sentiment()
    
    # 3. 모델 비교
    await compare_models()
    
    # 4. 최종 결과 요약
    print("\n=== 최종 결과 요약 ===")
    
    if ixic_result and gspc_result:
        print("✅ 모든 모델 훈련이 성공했습니다!")
        print(f"\n📊 훈련 결과:")
        print(f"  - 나스닥(IXIC): {'성공' if ixic_result['success'] else '실패'}")
        print(f"  - S&P 500(GSPC): {'성공' if gspc_result['success'] else '실패'}")
        
        print(f"\n🚀 다음 단계:")
        print(f"1. 모델 성능 평가 및 백테스팅")
        print(f"2. 실시간 예측 서비스 시작")
        print(f"3. 감정 특성 효과 분석")
        print(f"4. 모델 지속적 개선")
        
    else:
        print("⚠️ 일부 모델 훈련이 실패했습니다.")
        if not ixic_result:
            print("  - 나스닥 모델 훈련 실패")
        if not gspc_result:
            print("  - S&P 500 모델 훈련 실패")
    
    print("\n훈련이 완료되었습니다!")


if __name__ == "__main__":
    asyncio.run(main())
