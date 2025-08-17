# 머신러닝을 활용한 주가 예측 시스템 개발 - 3. 1차 훈련과 예측

## LSTM 모델 훈련 과정

이전 단계에서 구축한 **107개의 특성**을 사용하여 LSTM 모델을 훈련시키고 첫 번째 예측을 수행했다. 이번 글에서는 실제 훈련 과정과 예측 결과를 자세히 살펴보겠습니다.

## 1. 모델 아키텍처 설계

### 1.1 멀티 아웃풋 LSTM 구조

7일, 14일, 30일 후의 가격을 동시에 예측하기 위해 **멀티 아웃풋 LSTM 모델**을 설계했다:

```python
class MultiOutputLSTMPredictor:
    def __init__(self, input_shape: Tuple[int, int], config: Optional[ModelConfig] = None):
        self.input_shape = input_shape  # (60, 107) - 60일간의 107개 특성
        self.target_days = [7, 14, 30]  # 예측 대상 일수
        self.config = config or ml_settings.model
```

### 1.2 모델 구조

```python
def build_multi_output_model(self) -> Model:
    # 입력 레이어
    input_layer = layers.Input(shape=self.input_shape)

    # LSTM 레이어들
    lstm1 = layers.LSTM(50, return_sequences=True, dropout=0.2)(input_layer)
    lstm2 = layers.LSTM(50, dropout=0.2)(lstm1)

    # 각 타임프레임별 출력 레이어
    outputs = []
    for days in self.target_days:
        output = layers.Dense(1, name=f'output_{days}d')(lstm2)
        outputs.append(output)

    # 모델 생성
    model = Model(inputs=input_layer, outputs=outputs)
    return model
```

**모델 구조 요약:**

- **입력**: (60, 107) - 60일간의 107개 특성
- **LSTM 레이어**: 2개 (각각 50개 유닛)
- **드롭아웃**: 0.2 (과적합 방지)
- **출력**: 3개 (7일, 14일, 30일 예측)

## 2. 데이터 준비 과정

### 2.1 시계열 윈도우 생성

```python
def _create_sequences_and_targets(self, feature_data: pd.DataFrame, target_column: str):
    X = []
    y_dict = {f"{days}d": [] for days in self.target_days}

    # 최대 예측 일수만큼 여유를 둠
    max_target_days = max(self.target_days)  # 30일

    for i in range(self.window_size, len(feature_data) - max_target_days):
        # 특성 시퀀스 (과거 60일)
        X.append(feature_data.iloc[i - self.window_size : i].values)

        # 각 타임프레임별 타겟
        for days in self.target_days:
            future_price = feature_data.iloc[i + days][target_column]
            y_dict[f"{days}d"].append(future_price)

    return np.array(X), y_dict
```

### 2.2 데이터 정규화

```python
def normalize_features(self, X: np.ndarray, fit_scaler: bool = True) -> np.ndarray:
    if fit_scaler or self.feature_scaler is None:
        # MinMaxScaler 사용 (0-1 범위로 정규화)
        self.feature_scaler = MinMaxScaler(feature_range=(0, 1))

        # 3D 데이터를 2D로 변환하여 스케일러 학습
        original_shape = X.shape
        X_2d = X.reshape(-1, X.shape[-1])

        # 스케일러 학습 및 변환
        X_normalized_2d = self.feature_scaler.fit_transform(X_2d)

        # 원래 3D 형태로 복원
        X_normalized = X_normalized_2d.reshape(original_shape)

        return X_normalized
```

## 3. 모델 훈련 과정

### 3.1 훈련 설정

```python
def train_model(self, symbol: str, start_date: date, end_date: date):
    # 훈련 설정
    training_config = {
        "epochs": 100,
        "batch_size": 32,
        "validation_split": 0.2,
        "early_stopping_patience": 10,
        "learning_rate": 0.001
    }

    # 손실 함수: 각 타임프레임별 가중치 적용
    loss_weights = {
        'output_7d': 1.0,   # 7일 예측
        'output_14d': 1.0,  # 14일 예측
        'output_30d': 1.0   # 30일 예측
    }

    # 컴파일
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='mse',
        loss_weights=loss_weights,
        metrics=['mae']
    )
```

### 3.2 훈련 실행

```python
# 콜백 함수들
callbacks = [
    EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True
    ),
    ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=5,
        min_lr=1e-6
    ),
    ModelCheckpoint(
        filepath=f'models/{symbol}_best_model.keras',
        monitor='val_loss',
        save_best_only=True
    )
]

# 모델 훈련
history = model.fit(
    X_train, y_train,
    epochs=100,
    batch_size=32,
    validation_split=0.2,
    callbacks=callbacks,
    verbose=1
)
```

## 4. 훈련 결과 분석

### 4.1 훈련 성능 지표

**S&P 500 (^GSPC) 모델 훈련 결과:**

```
훈련 데이터: 2,500개 시퀀스
검증 데이터: 625개 시퀀스
훈련 시간: 약 15분
최종 에포크: 45 (조기 종료)

손실 함수:
- 훈련 손실: 0.0023
- 검증 손실: 0.0028

평균 절대 오차 (MAE):
- 7일 예측: 2.1%
- 14일 예측: 3.2%
- 30일 예측: 4.8%
```

**나스닥 (^IXIC) 모델 훈련 결과:**

```
훈련 데이터: 2,500개 시퀀스
검증 데이터: 625개 시퀀스
훈련 시간: 약 15분
최종 에포크: 52 (조기 종료)

손실 함수:
- 훈련 손실: 0.0031
- 검증 손실: 0.0035

평균 절대 오차 (MAE):
- 7일 예측: 2.8%
- 14일 예측: 4.1%
- 30일 예측: 5.9%
```

### 4.2 과적합 방지

**드롭아웃과 조기 종료**를 통해 과적합을 방지했다:

```python
# LSTM 레이어에 드롭아웃 적용
lstm1 = layers.LSTM(50, return_sequences=True, dropout=0.2)(input_layer)
lstm2 = layers.LSTM(50, dropout=0.2)(lstm1)

# 조기 종료 콜백
EarlyStopping(
    monitor='val_loss',
    patience=10,
    restore_best_weights=True
)
```

## 5. 첫 번째 예측 결과

### 5.1 S&P 500 (^GSPC) 예측

**예측 날짜**: 2025-08-09  
**현재 가격**: 6,340.00

```
예측 결과:
7일 후 (2025-08-16): 6,236.59 (-1.63% 하락)
14일 후 (2025-08-23): 6,212.96 (-2.00% 하락)
30일 후 (2025-09-08): 6,231.97 (-1.70% 하락)

예측 방향: 모두 "down" (하락)
```

### 5.2 나스닥 (^IXIC) 예측

**예측 날짜**: 2025-08-09  
**현재 가격**: 21,242.70

```
예측 결과:
7일 후 (2025-08-16): 20,409.62 (-3.92% 하락)
14일 후 (2025-08-23): 20,665.47 (-2.72% 하락)
30일 후 (2025-09-08): 20,703.51 (-2.54% 하락)

예측 방향: 모두 "down" (하락)
```

## 6. 예측 결과 분석

### 6.1 모델의 특징

**일관된 하락 예측:**

- 두 지수 모두 단기/중기/장기 예측에서 하락 방향
- 이는 모델이 **현재 시장 상황의 약세 신호**를 포착했음을 의미

**예측 신뢰도:**

- S&P 500: 1.6-2.0% 범위의 하락 예측
- 나스닥: 2.5-3.9% 범위의 하락 예측
- 나스닥이 더 큰 변동성을 예측 (실제 시장 특성 반영)

### 6.2 현재 한계점

**오차가 큰 이유:**

1. **데이터 부족**: 10년 데이터는 ML 모델 기준으로 부족
2. **특성 제한**: 기술적 지표와 감정분석이 아직 포함되지 않음
3. **시장 복잡성**: 주가 예측의 본질적 어려움

**개선 방향:**

- 더 많은 데이터 수집
- 기술적 지표 특성 추가
- 감정분석 데이터 통합
- 앙상블 모델 도입

## 7. 모델 저장 및 배포

### 7.1 모델 저장

```python
def save_model(self, model_path: str, scaler_path: str):
    # 모델 저장
    self.model.save(model_path)

    # 스케일러 저장
    with open(scaler_path, 'wb') as f:
        joblib.dump(self.feature_scaler, f)

    # 메타데이터 저장
    metadata = {
        "model_version": self.model_version,
        "input_shape": self.input_shape,
        "target_days": self.target_days,
        "training_date": datetime.now().isoformat(),
        "feature_count": 107,
        "symbol": symbol
    }

    with open(f"{model_path}_metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
```

### 7.2 API 엔드포인트

```python
@router.post("/predict")
async def predict_prices(request: PredictionRequest):
    result = await ml_service.predict_prices(
        symbol=request.symbol,
        prediction_date=request.prediction_date,
        model_version=request.model_version,
        save_results=request.save_results,
        use_sentiment=False  # 1차 예측에서는 감정분석 제외
    )
    return result
```

## 결론

**107개의 특성**으로 구성된 LSTM 모델을 성공적으로 훈련하고 첫 번째 예측을 수행했다. 시간이 지나봐야 알겠지만 7일 후 예측 결과는 아주 엉망인 수준이였다.
꾸준히 하다보면 좋아질 것이라는 믿을을 가지고 노력 해야겠다.
