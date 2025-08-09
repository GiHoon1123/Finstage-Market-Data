models/ml_prediction/
├── cache/ # 캐시 파일들
├── GSPC_lstm/ # S&P 500 모델들
└── IXIC_lstm/ # 나스닥 모델들
├── v1.0.0_20250809_115750/ # 각 훈련 버전별 디렉토리
├── v1.0.0_20250809_123502/ # 최신 활성 모델 (ID: 7)
│ ├── model.keras # 실제 딥러닝 모델 파일
│ ├── model.keras_metadata.json # 모델 메타데이터
│ └── scalers/ # 데이터 정규화 스케일러들
│ ├── feature_scaler.pkl # 입력 특성 스케일러
│ ├── target_scaler_7d.pkl # 7일 예측 타겟 스케일러
│ ├── target_scaler_14d.pkl # 14일 예측 타겟 스케일러
│ └── target_scaler_30d.pkl # 30일 예측 타겟 스케일러
