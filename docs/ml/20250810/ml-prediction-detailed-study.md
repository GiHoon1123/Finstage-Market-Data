# ML 주가 예측 시스템 - 개인 학습용 상세 코드 해설

## 목차

1. [전체 구조 이해하기](#전체-구조-이해하기)
2. [LSTM 모델 코드 완전 분해](#lstm-모델-코드-완전-분해)
3. [데이터 전처리 코드 완전 분해](#데이터-전처리-코드-완전-분해)
4. [예측 실행 코드 완전 분해](#예측-실행-코드-완전-분해)
5. [서비스 레이어 코드 분석](#서비스-레이어-코드-분석)
6. [API 레이어 코드 분석](#api-레이어-코드-분석)
7. [헷갈렸던 부분들 정리](#헷갈렸던-부분들-정리)
8. [디버깅할 때 유용한 팁들](#디버깅할-때-유용한-팁들)

---

## 전체 구조 이해하기

### 각 파일이 뭘 하는 건지

우리 시스템은 이렇게 구성되어 있어:

```
app/ml_prediction/
├── ml/                          # 실제 머신러닝 로직
│   ├── model/
│   │   ├── lstm_model.py        # LSTM 모델 정의 (뇌)
│   │   ├── trainer.py           # 모델 훈련 (선생님)
│   │   └── predictor.py         # 예측 실행 (점쟁이)
│   ├── data/
│   │   ├── preprocessor.py      # 데이터 전처리 (요리사)
│   │   ├── feature_engineer.py  # 특성 생성 (재료 준비)
│   │   └── source_manager.py    # 데이터 수집 (장보기)
│   └── evaluation/
│       └── evaluator.py         # 성능 평가 (채점)
├── service/
│   └── ml_prediction_service.py # 비즈니스 로직 (매니저)
├── handler/
│   └── ml_prediction_handler.py # API 요청 처리 (접수원)
└── web/route/
    └── ml_prediction_router.py  # API 엔드포인트 (창구)
```

### 데이터가 어떻게 흘러가는지

**훈련 과정:**

```
1. 사용자가 "모델 훈련해줘" 요청
2. Router가 받아서 Handler에게 전달
3. Handler가 Service에게 "훈련 시작" 명령
4. Service가 Trainer에게 "훈련해" 지시
5. Trainer가 Preprocessor에게 "데이터 준비해" 요청
6. Preprocessor가 데이터 수집하고 정리해서 전달
7. Trainer가 LSTM 모델 만들고 훈련
8. 훈련 완료되면 모델 파일로 저장
9. 결과를 거슬러 올라가서 사용자에게 응답
```

**예측 과정:**

```
1. 사용자가 "가격 예측해줘" 요청
2. Router → Handler → Service → Predictor 순서로 전달
3. Predictor가 저장된 모델 로드
4. 최근 60일 데이터 수집하고 전처리
5. 모델에 넣어서 7일, 14일, 30일 후 가격 예측
6. 신뢰도 계산하고 결과 정리해서 응답
```

---

## LSTM 모델 코드 완전 분해

### MultiOutputLSTMPredictor 클래스 전체 구조

이 클래스가 우리 시스템의 핵심 뇌 역할을 해. 한 번에 7일, 14일, 30일 후 가격을 예측하는 똑똑한 뇌야.

```python
class MultiOutputLSTMPredictor:
    def __init__(self, input_shape, config, model_name):
        # input_shape: (60, 152) - 60일치 데이터, 각 날마다 152개 특성
        # config: 모델 설정 (LSTM 유닛 수, 드롭아웃 비율 등)
        # model_name: 모델 이름 (예: "IXIC_lstm")

        self.input_shape = input_shape
        self.config = config
        self.model_name = model_name
        self.target_days = [7, 14, 30]  # 예측할 기간들

        # 아직 모델은 없어, 나중에 build_multi_output_model()에서 만들어
        self.model = None
        self.is_compiled = False  # 컴파일 했는지 체크용
```

### build_multi_output_model() 메서드 한 줄씩 해설

이 메서드가 실제로 신경망을 만드는 곳이야. 차근차근 뜯어보자:

```python
def build_multi_output_model(self) -> Model:
    # 1단계: 입력 레이어 만들기
    inputs = layers.Input(shape=self.input_shape, name="price_sequence_input")
    # → 케라스에서 입력을 받는 문 같은 거야
    # → shape=(60, 152)는 "60일치 데이터, 각 날마다 152개 숫자"라는 뜻
    # → name은 나중에 모델 구조 볼 때 알아보기 쉽게 이름 붙인 거

    # 2단계: LSTM 레이어들 쌓기
    x = inputs  # x는 현재 데이터가 흘러가는 파이프라고 생각해

    # self.config.lstm_units = [50, 50] 이라고 가정하자
    for i, units in enumerate(self.config.lstm_units):
        # i=0일 때: units=50 (첫 번째 LSTM)
        # i=1일 때: units=50 (두 번째 LSTM)

        # 이 부분이 핵심! 마지막 LSTM인지 확인
        return_sequences = i < len(self.config.lstm_units) - 1
        # → i=0일 때: 0 < 2-1 = True (시퀀스 전체 반환)
        # → i=1일 때: 1 < 2-1 = False (마지막 값만 반환)

        x = layers.LSTM(
            units=units,                    # LSTM 뉴런 개수 (50개)
            return_sequences=return_sequences,  # 위에서 계산한 값
            dropout=0.2,                    # 20% 뉴런 랜덤하게 끄기 (과적합 방지)
            recurrent_dropout=0.2,          # LSTM 내부 연결도 20% 끄기
            name=f"lstm_{i+1}",            # "lstm_1", "lstm_2" 이런 식으로 이름
        )(x)

        # 배치 정규화 추가 (훈련 안정화)
        x = layers.BatchNormalization(name=f"batch_norm_lstm_{i+1}")(x)
        # → 각 배치마다 데이터를 정규화해서 훈련이 더 안정적이 되게 해
```

    # 3단계: 공통 Dense 레이어들
    # self.config.dense_units = [25] 라고 가정
    for i, units in enumerate(self.config.dense_units):
        x = layers.Dense(
            units=units,                    # 25개 뉴런
            activation=self.config.activation,  # "relu" 활성화 함수
            name=f"dense_common_{i+1}",    # "dense_common_1"
        )(x)

        x = layers.Dropout(
            self.config.dropout_rate,      # 0.2 (20% 드롭아웃)
            name=f"dropout_common_{i+1}"
        )(x)
        # → 여기까지가 공통 특성 추출 부분이야
        # → 모든 예측 기간이 이 특성을 공유해

    # 4단계: 각 타임프레임별 출력 분기 (핵심!)
    output_layers = []

    for days in self.target_days:  # [7, 14, 30]
        # 각 기간별로 전용 레이어 만들기
        branch = layers.Dense(
            units=16,                       # 16개 뉴런 (각 기간별 특화)
            activation=self.config.activation,  # "relu"
            name=f"dense_{days}d_branch",   # "dense_7d_branch" 이런 식
        )(x)

        branch = layers.Dropout(
            self.config.dropout_rate,
            name=f"dropout_{days}d_branch"
        )(branch)

        # 최종 출력 레이어 (가격 1개 예측)
        output = layers.Dense(
            units=1,                        # 1개 뉴런 (가격 1개)
            activation="linear",            # 선형 활성화 (실제 가격 값)
            name=f"price_prediction_{days}d"  # "price_prediction_7d"
        )(branch)

        output_layers.append(output)
        # → 이렇게 해서 3개 출력이 만들어져: [7일예측, 14일예측, 30일예측]

    # 5단계: 최종 모델 생성
    self.model = Model(
        inputs=inputs,           # 입력: (60, 152) 형태
        outputs=output_layers,   # 출력: 3개 (7d, 14d, 30d)
        name=self.model_name     # 모델 이름
    )

    return self.model

# 🤔 왜 이렇게 복잡하게 만들었을까?

# 1. 공통 LSTM: 시계열 패턴은 모든 기간이 공유

# 2. 분기 Dense: 각 기간별 특성은 따로 학습

# 3. 멀티 아웃풋: 한 번에 3개 기간 예측으로 효율성 UP

```

```

### compile_model() 메서드 상세 분석

모델을 만들었으면 이제 "어떻게 학습할지" 설정해야 해. 이게 컴파일이야.

```python
def compile_model(self, optimizer=None, loss=None, metrics=None, loss_weights=None):
    if self.model is None:
        raise ValueError("Model must be built before compilation")
        # → 모델 먼저 만들고 컴파일하라는 뜻

    # 기본값 설정
    if optimizer is None:
        optimizer = Adam(learning_rate=0.001)
        # → Adam: 가장 많이 쓰는 최적화 알고리즘
        # → learning_rate=0.001: 학습 속도 (너무 크면 발산, 너무 작으면 느림)

    if loss is None:
        loss = "mse"  # Mean Squared Error
        # → 예측값과 실제값 차이의 제곱 평균
        # → 가격 예측에 가장 적합한 손실 함수

    if metrics is None:
        metrics = ["mae"]  # Mean Absolute Error
        # → 예측값과 실제값 차이의 절댓값 평균
        # → 실제 얼마나 틀렸는지 직관적으로 알 수 있어

    if loss_weights is None:
        loss_weights = self.config.loss_weights  # [0.5, 0.3, 0.2]
        # → 7일 예측: 50% 중요도
        # → 14일 예측: 30% 중요도
        # → 30일 예측: 20% 중요도
        # → 단기 예측이 더 정확하고 실용적이라서 가중치 높게

    # 멀티 아웃풋을 위한 손실 함수 설정
    if isinstance(loss, str):
        # 모든 출력에 동일한 손실 함수 적용
        loss_dict = {f"price_prediction_{days}d": loss for days in self.target_days}
        # → {"price_prediction_7d": "mse",
        #    "price_prediction_14d": "mse",
        #    "price_prediction_30d": "mse"}

    if isinstance(metrics, list):
        # 모든 출력에 동일한 지표 적용
        metrics_dict = {f"price_prediction_{days}d": metrics for days in self.target_days}
        # → {"price_prediction_7d": ["mae"],
        #    "price_prediction_14d": ["mae"],
        #    "price_prediction_30d": ["mae"]}

    # 실제 컴파일
    self.model.compile(
        optimizer=optimizer,      # Adam 최적화
        loss=loss_dict,          # 각 출력별 MSE 손실
        metrics=metrics_dict,    # 각 출력별 MAE 지표
        loss_weights=loss_weights # [0.5, 0.3, 0.2] 가중치
    )

    self.is_compiled = True  # 컴파일 완료 표시

# 💡 핵심 포인트:
# - 멀티 아웃풋이라서 손실 함수도 딕셔너리로 설정
# - 가중치로 단기 예측에 더 집중
# - Adam + MSE + MAE 조합은 가격 예측의 황금 조합
```

### train() 메서드 동작 원리

이제 실제로 모델을 훈련시키는 부분이야. 여기가 제일 복잡해.

```python
def train(self, X_train, y_train, X_val=None, y_val=None, epochs=None, batch_size=None):
    if not self.is_compiled:
        raise ValueError("Model must be compiled before training")
        # → 컴파일 먼저 하고 훈련하라는 뜻

    # 기본값 설정
    epochs = epochs or ml_settings.training.epochs  # 100
    batch_size = batch_size or ml_settings.training.batch_size  # 32

    # ⚠️ 여기가 핵심! 멀티 아웃풋 데이터 변환
    # y_train은 딕셔너리: {"7d": [가격들], "14d": [가격들], "30d": [가격들]}
    # 케라스는 리스트를 원해: [7일가격들, 14일가격들, 30일가격들]

    y_train_list = [y_train[f"{days}d"] for days in self.target_days]
    # → [y_train["7d"], y_train["14d"], y_train["30d"]]
    # → 이 순서가 모델 출력 순서와 정확히 일치해야 해!

    validation_data = None
    if X_val is not None and y_val is not None:
        y_val_list = [y_val[f"{days}d"] for days in self.target_days]
        validation_data = (X_val, y_val_list)
        # → 검증 데이터도 같은 방식으로 변환

    # 기본 콜백 설정 (훈련 중 자동 제어)
    callbacks_list = self._create_default_callbacks()
    # → 조기 종료, 학습률 감소 등

    # 실제 훈련 시작!
    history = self.model.fit(
        X_train,              # 입력: (샘플수, 60, 152)
        y_train_list,         # 출력: [7일타겟, 14일타겟, 30일타겟]
        validation_data=validation_data,  # 검증 데이터
        epochs=epochs,        # 최대 100번 반복
        batch_size=batch_size, # 한 번에 32개씩 처리
        callbacks=callbacks_list, # 자동 제어 기능들
        verbose=1,            # 진행상황 출력
        shuffle=True,         # 데이터 섞기 (시계열이지만 윈도우 단위로는 OK)
    )

    self.training_history = history  # 훈련 기록 저장

    return training_metadata  # 훈련 결과 정보 반환

# 🔥 훈련 과정 상세:
# 1. 32개 샘플씩 모델에 넣어
# 2. 예측값과 실제값 비교해서 오차 계산
# 3. 오차를 줄이는 방향으로 가중치 업데이트
# 4. 이걸 전체 데이터에 대해 반복 (1 에포크)
# 5. 에포크를 100번 반복하거나 조기 종료될 때까지 계속
```

---

## 데이터 전처리 코드 완전 분해

### MLDataPreprocessor 클래스 역할

이 클래스는 요리사 같은 역할이야. 날것의 주식 데이터를 모델이 먹을 수 있게 요리해줘.

```python
class MLDataPreprocessor:
    def __init__(self, cache_dir=None, enable_caching=True, strict_validation=False):
        # cache_dir: 처리된 데이터 저장할 폴더
        # enable_caching: 캐싱 사용할지 (True면 빨라져)
        # strict_validation: 엄격한 검증 모드

        self.cache_dir = cache_dir or "models/ml_prediction/cache"
        self.enable_caching = enable_caching
        self.strict_validation = strict_validation

        # 하위 컴포넌트들 초기화
        self.data_source_manager = DataSourceManager()    # 데이터 수집기
        self.feature_engineer = FeatureEngineer()         # 특성 생성기
        self.quality_validator = DataQualityValidator()   # 품질 검사기
        self.fallback_handler = DataSourceFallbackHandler()  # 오류 처리기
```

### prepare_training_data() 메서드 단계별 해설

이 메서드가 전체 데이터 전처리의 핵심이야. 단계별로 뜯어보자:

```python
def prepare_training_data(self, symbol, start_date, end_date, force_refresh=False):
    # symbol: "^IXIC" (나스닥) 또는 "^GSPC" (S&P500)
    # start_date, end_date: 데이터 기간
    # force_refresh: 캐시 무시하고 새로 만들지

    # 1단계: 캐시 확인 (24시간 유효)
    if self.enable_caching and not force_refresh:
        cached_data = self._load_from_cache(symbol, start_date, end_date, "training")
        if cached_data is not None:
            logger.info("training_data_loaded_from_cache")
            return cached_data
            # → 이미 처리된 데이터가 있으면 바로 반환 (시간 절약!)

    # 2단계: 원시 데이터 수집
    raw_data = self._collect_raw_data(symbol, start_date, end_date)
    # → 데이터베이스에서 OHLCV 데이터 + 기술적 지표들 가져와
    # → 결과: DataFrame with columns [open, high, low, close, volume, sma_5, rsi_14, ...]

    # 3단계: 데이터 품질 검증
    validation_passed, validation_results, quality_score = \
        self._validate_data_quality(raw_data, symbol, (start_date, end_date))

    if not validation_passed:
        raise ValueError(f"Data quality validation failed for {symbol}")
        # → 데이터가 이상하면 여기서 멈춰 (쓰레기 넣으면 쓰레기 나와)

    # 4단계: 특성 엔지니어링 (152개 기술적 지표 생성)
    X, y_dict, feature_names = self.feature_engineer.create_multi_target_sequences(
        raw_data, target_column="close"
    )
    # → X: (샘플수, 60, 152) - 60일 윈도우, 152개 특성
    # → y_dict: {"7d": [...], "14d": [...], "30d": [...]} - 각 기간별 타겟
    # → feature_names: ["sma_5", "rsi_14", ...] - 특성 이름들

    # 5단계: 정규화 (0-1 범위로 스케일링)
    X_normalized = self.feature_engineer.normalize_features(X, fit_scaler=True)
    y_normalized_dict = self.feature_engineer.normalize_targets(y_dict, fit_scalers=True)
    # → fit_scaler=True: 스케일러를 새로 만들어 (훈련 시에만)
    # → 예측할 때는 이 스케일러를 재사용해야 해

    # 6단계: 데이터 분할 (시계열 순서 유지!)
    X_splits, y_splits = self.feature_engineer.split_data(X_normalized, y_normalized_dict)
    # → X_splits: {"train": [...], "val": [...], "test": [...]}
    # → y_splits: {"7d": {"train": [...], "val": [...], "test": [...]}, ...}
    # → ⚠️ 시계열이라서 랜덤 셔플 안 해! 시간 순서대로 분할

    # 7단계: 메타데이터 생성
    metadata = self._create_metadata(symbol, start_date, end_date, raw_data,
                                   validation_results, quality_score, feature_names)
    # → 나중에 참고할 정보들 (데이터 크기, 품질 점수, 특성 이름 등)

    # 8단계: 캐시 저장 (다음에 빨리 쓰려고)
    if self.enable_caching:
        self._save_to_cache((X_splits, y_splits, metadata),
                          symbol, start_date, end_date, "training")

    return X_splits, y_splits, metadata

# 💡 전체 과정 요약:
# 날것 데이터 → 품질검사 → 특성생성 → 정규화 → 분할 → 완성!
# 마치 재료 → 씻기 → 썰기 → 양념 → 나누기 → 요리완성 같은 느낌
```

### 캐싱 시스템 동작 원리

캐싱은 한 번 처리한 데이터를 저장해뒀다가 재사용하는 거야. 엄청 시간 절약돼!

```python
def _save_to_cache(self, data, symbol, start_date, end_date, data_type):
    if not self.enable_caching:
        return  # 캐싱 안 쓰면 그냥 리턴

    # 캐시 키 생성 (파일명으로 사용)
    cache_key = self._generate_cache_key(symbol, start_date, end_date, data_type)
    # → "IXIC_2020-01-01_2024-12-31_training_60" 이런 식
    # → 심볼, 날짜, 타입, 윈도우크기로 유니크하게 만들어

    cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
    # → "models/ml_prediction/cache/abc123.pkl" 경로

    cache_data = {
        "data": data,           # 실제 처리된 데이터
        "metadata": {
            "symbol": symbol,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data_type": data_type,
            "created_at": datetime.now().isoformat(),
            "feature_engineer_config": self.feature_engineer.get_feature_info(),
        },
    }

    # pickle로 저장 (파이썬 객체를 파일로 저장하는 방법)
    with open(cache_file, "wb") as f:
        pickle.dump(cache_data, f)
    # → 이제 다음에 같은 요청 오면 이 파일 읽어서 바로 반환

def _load_from_cache(self, symbol, start_date, end_date, data_type):
    cache_key = self._generate_cache_key(symbol, start_date, end_date, data_type)
    cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")

    if not os.path.exists(cache_file):
        return None  # 캐시 파일 없으면 None 반환

    # 파일 나이 확인 (24시간 이상 된 캐시는 무효)
    file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
    if file_age > timedelta(hours=24):
        os.remove(cache_file)  # 오래된 캐시 삭제
        return None

    # 캐시 파일 읽기
    with open(cache_file, "rb") as f:
        cache_data = pickle.load(f)

    # 설정 호환성 확인 (윈도우 크기나 타겟 기간이 바뀌었나?)
    cached_config = cache_data["metadata"].get("feature_engineer_config", {})
    current_config = self.feature_engineer.get_feature_info()

    if cached_config.get("window_size") != current_config.get("window_size"):
        return None  # 설정이 바뀌었으면 캐시 무효

    return cache_data["data"]  # 캐시된 데이터 반환

# 🚀 캐싱의 장점:
# - 첫 번째: 25년 데이터 처리 (30초) → 두 번째: 캐시 로드 (0.1초)
# - 같은 기간 데이터 요청하면 거의 즉시 응답
# - 디스크 용량은 좀 쓰지만 시간은 엄청 절약
```

### 특성 엔지니어링 코드 분석

이 부분이 152개 기술적 지표를 만드는 핵심이야:

```python
def create_multi_target_sequences(self, data, target_column="close"):
    # 1단계: 기술적 지표 생성 (152개 특성)
    feature_data = self._prepare_features(data)
    # → 원본 OHLCV 데이터에서 SMA, RSI, MACD 등등 계산
    # → 결과: DataFrame with 152 columns

    sequences = []  # 입력 시퀀스들 저장할 리스트
    targets = {f"{days}d": [] for days in self.target_days}  # 타겟들

    # 2단계: 60일 윈도우로 시퀀스 생성
    for i in range(self.window_size, len(feature_data)):
        # i=60일 때: 0~59일 데이터로 60일 예측
        # i=61일 때: 1~60일 데이터로 61일 예측
        # ...

        # 입력: 과거 60일 특성 데이터
        sequence = feature_data.iloc[i-self.window_size:i].values
        # → shape: (60, 152) - 60일 × 152개 특성
        sequences.append(sequence)

        # 타겟: 미래 7일, 14일, 30일 후 가격
        for days in self.target_days:
            future_idx = min(i + days, len(data) - 1)  # 범위 벗어나지 않게
            future_price = data[target_column].iloc[future_idx]
            targets[f"{days}d"].append(future_price)

    # 3단계: numpy 배열로 변환
    X = np.array(sequences)  # (샘플수, 60, 152)
    y_dict = {k: np.array(v) for k, v in targets.items()}
    # → {"7d": [가격들], "14d": [가격들], "30d": [가격들]}

    return X, y_dict, feature_names

# 🎯 핵심 아이디어:
# - 과거 60일 데이터로 미래 여러 기간 예측
# - 슬라이딩 윈도우: 하루씩 밀면서 샘플 생성
# - 멀티 타겟: 한 번에 여러 기간 타겟 만들기
```

---

## 예측 실행 코드 완전 분해

### MultiTimeframePredictor 클래스 구조

이 클래스는 점쟁이 역할이야. 훈련된 모델을 가지고 실제로 미래 가격을 예측해.

```python
class MultiTimeframePredictor:
    def __init__(self, preprocessor=None, confidence_method=None):
        self.preprocessor = preprocessor or MLDataPreprocessor()
        self.confidence_method = confidence_method or "ensemble"

        # 로드된 모델들 캐시 (같은 모델 여러 번 로드 안 하려고)
        self.loaded_models = {}  # {"IXIC_active": (model, entity), ...}

        # 예측 세션 정보
        self.current_predictions = {}  # 예측 결과 임시 저장
```

### predict_price() 메서드 단계별 해설

실제 예측을 수행하는 핵심 메서드야:

```python
def predict_price(self, symbol, prediction_date=None, model_version=None):
    prediction_date = prediction_date or date.today()  # 기본값: 오늘
    batch_id = str(uuid.uuid4())  # 고유 ID 생성

    # 1단계: 모델 로드 (캐시 활용)
    model_predictor, model_entity = self._load_model(symbol, model_version)
    # → 저장된 .keras 파일과 스케일러들 로드
    # → 캐시에 있으면 바로 사용, 없으면 새로 로드

    # 2단계: 예측용 데이터 준비 (최근 60일)
    X_pred, data_metadata = self.preprocessor.prepare_prediction_data(
        symbol=symbol, end_date=prediction_date
    )
    # → 최근 60일 데이터 수집하고 152개 특성 계산
    # → 정규화까지 완료된 상태: shape (1, 60, 152)

    # 3단계: 예측 실행
    raw_predictions = model_predictor.predict(X_pred)
    # → LSTM 모델에 넣어서 예측
    # → 결과: [7일예측, 14일예측, 30일예측] (정규화된 값)

    # 4단계: 역정규화 (실제 가격으로 복원)
    denormalized_predictions = \
        self.preprocessor.feature_engineer.denormalize_predictions(raw_predictions)
    # → 0~1 범위 값을 실제 가격으로 변환
    # → 결과: {"7d": [15234.56], "14d": [15456.78], "30d": [15123.45]}

    # 5단계: 신뢰도 계산
    confidence_scores = self._calculate_confidence_scores(
        model_predictor, X_pred, raw_predictions
    )
    # → 앙상블 방법으로 예측 불확실성 계산
    # → 결과: {"7d": 0.75, "14d": 0.68, "30d": 0.62}

    # 6단계: 예측 결과 구성
    current_price = data_metadata.get("last_price", 0.0)  # 현재 가격
    prediction_results = []

    for timeframe, predicted_price in denormalized_predictions.items():
        days = int(timeframe.replace("d", ""))  # "7d" → 7
        target_date = prediction_date + timedelta(days=days)  # 예측 대상 날짜

        # 가격 변화율 계산
        price_change_percent = ((predicted_price[0] - current_price) / current_price) * 100

        # 예측 방향 결정
        if price_change_percent > 0.5:
            predicted_direction = "up"      # 0.5% 이상 상승
        elif price_change_percent < -0.5:
            predicted_direction = "down"    # 0.5% 이상 하락
        else:
            predicted_direction = "neutral" # 그 사이는 중립

        prediction_results.append({
            "timeframe": timeframe,                    # "7d"
            "target_date": target_date,                # 2025-08-16
            "predicted_price": float(predicted_price[0]), # 15234.56
            "predicted_direction": predicted_direction,    # "up"
            "price_change_percent": float(price_change_percent), # 1.56
            "confidence_score": confidence_scores.get(timeframe, 0.5), # 0.75
        })

    # 7단계: 예측 일관성 검증
    consistency_score = self._calculate_consistency_score(prediction_results)
    # → 기간별 예측이 논리적으로 일관성 있는지 체크
    # → 예: 7일은 상승, 14일은 하락, 30일은 상승 → 일관성 낮음

    return {
        "status": "success",
        "symbol": symbol,
        "current_price": current_price,
        "predictions": prediction_results,
        "consistency_score": consistency_score,
        "batch_id": batch_id
    }

# 🎯 전체 과정 요약:
# 모델로드 → 데이터준비 → 예측실행 → 역정규화 → 신뢰도계산 → 결과구성
```

### 신뢰도 계산 알고리즘 상세 분석

이 부분이 정말 똑똑한 부분이야. 예측이 얼마나 믿을 만한지 수치로 계산해:

```python
def _calculate_confidence_scores(self, model_predictor, X_pred, predictions):
    confidence_scores = {}

    if self.confidence_method == "ensemble":
        # 앙상블 방법: 여러 번 예측하여 분산 계산
        confidence_scores = self._calculate_ensemble_confidence(
            model_predictor, X_pred, predictions
        )

    return confidence_scores

def _calculate_ensemble_confidence(self, model_predictor, X_pred, base_predictions):
    confidence_scores = {}
    n_samples = 100  # 100번 예측 수행

    # 핵심 아이디어: 드롭아웃을 활성화한 상태에서 여러 번 예측
    all_predictions = []
    for _ in range(n_samples):
        # verbose=0: 출력 안 함, training=True: 드롭아웃 활성화
        pred = model_predictor.predict(X_pred, verbose=0)
        all_predictions.append(pred)
        # → 드롭아웃 때문에 매번 조금씩 다른 결과 나와

    # 각 타임프레임별 신뢰도 계산
    for timeframe in base_predictions.keys():  # ["7d", "14d", "30d"]
        # 100번 예측 결과 수집
        predictions_array = np.array([pred[timeframe][0] for pred in all_predictions])
        # → [예측1, 예측2, ..., 예측100] 배열

        # 표준편차를 기반으로 신뢰도 계산 (낮은 분산 = 높은 신뢰도)
        std = np.std(predictions_array)      # 표준편차 (얼마나 흩어져 있나)
        mean_pred = np.mean(predictions_array)  # 평균 예측값

        if mean_pred != 0:
            relative_std = std / abs(mean_pred)  # 상대적 표준편차
            # → 예측값 대비 얼마나 흩어져 있는가

            confidence = max(0.1, min(0.9, 1.0 - relative_std))
            # → 흩어짐이 적을수록 신뢰도 높음
            # → 최소 0.1, 최대 0.9로 제한
        else:
            confidence = 0.5  # 예측값이 0이면 중간 신뢰도

        confidence_scores[timeframe] = float(confidence)

    return confidence_scores

# 💡 신뢰도 계산 원리:
# 1. 같은 입력에 대해 100번 예측 (드롭아웃으로 매번 다름)
# 2. 100개 결과가 비슷하면 → 신뢰도 높음
# 3. 100개 결과가 흩어져 있으면 → 신뢰도 낮음
# 4. 이게 Monte Carlo Dropout이라는 기법이야!

# 🤔 왜 이렇게 할까?
# - 모델이 확신 있으면 드롭아웃 있어도 비슷한 결과
# - 모델이 헷갈리면 드롭아웃에 따라 결과가 많이 달라짐
# - 이 차이를 이용해서 불확실성을 측정하는 거야
```

### 모델 로드 및 캐싱 메커니즘

같은 모델을 여러 번 로드하지 않게 캐싱하는 똑똑한 시스템:

```python
def _load_model(self, symbol, model_version=None):
    cache_key = f"{symbol}_{model_version or 'active'}"
    # → "IXIC_active" 또는 "IXIC_v1.0.0_20250809_120032"

    # 캐시에서 확인
    if cache_key in self.loaded_models:
        logger.debug("model_loaded_from_cache", cache_key=cache_key)
        return self.loaded_models[cache_key]
        # → 이미 로드된 모델 있으면 바로 반환

    # 데이터베이스에서 모델 정보 조회
    session = SessionLocal()
    model_repository = MLModelRepository(session)

    try:
        if model_version:
            # 특정 버전 모델 조회
            model_entity = model_repository.find_by_name_and_version(
                f"{symbol.replace('^', '')}_lstm", model_version
            )
        else:
            # 활성 모델 조회 (성능 기반 자동 선택)
            model_entity = model_repository.find_active_model("lstm", symbol)

        if not model_entity:
            raise ValueError(f"No suitable model found for {symbol}")

        # 모델 파일 로드
        model_predictor = MultiOutputLSTMPredictor(
            input_shape=(ml_settings.model.window_size, 0),  # 실제 크기는 로드 시 결정
            config=ml_settings.model,
            model_name=model_entity.model_name,
        )

        # .keras 파일 로드
        model_predictor.load_model(
            filepath=model_entity.model_path,  # "models/.../model.keras"
            load_format=ml_settings.storage.model_format,  # "keras"
        )

        # 스케일러들도 로드 (정규화/역정규화용)
        scaler_dir = os.path.join(os.path.dirname(model_entity.model_path), "scalers")
        if os.path.exists(scaler_dir):
            self.preprocessor.feature_engineer.load_scalers(scaler_dir)
            # → feature_scaler.pkl, target_scaler_7d.pkl 등등 로드

        # 캐시에 저장 (다음에 빨리 쓰려고)
        self.loaded_models[cache_key] = (model_predictor, model_entity)

        return model_predictor, model_entity

    finally:
        session.close()

# 🚀 캐싱의 효과:
# - 첫 번째 예측: 모델 로드 (2초) + 예측 (0.1초) = 2.1초
# - 두 번째 예측: 캐시 사용 (0초) + 예측 (0.1초) = 0.1초
# - 20배 빨라짐!
```

---

## 서비스 레이어 코드 분석

### MLPredictionService 비동기 처리 원리

이 클래스는 매니저 역할이야. 모든 ML 작업을 조율하고 비동기로 처리해:

```python
class MLPredictionService:
    def __init__(self):
        self.trainer = ModelTrainer()           # 모델 훈련 담당
        self.predictor = MultiTimeframePredictor()  # 예측 담당
        self.evaluator = ModelEvaluator()       # 성능 평가 담당

        # CPU 집약적 작업을 위한 스레드 풀
        self.executor = ThreadPoolExecutor(max_workers=3)
        # → 최대 3개 작업을 동시에 처리할 수 있어
        # → ML 작업은 CPU를 많이 써서 너무 많이 하면 오히려 느려져

async def train_model(self, symbol, training_days=1000, force_retrain=False):
    # 기존 모델 확인 (빠른 DB 조회)
    if not force_retrain:
        existing_model = await self._check_existing_model(symbol)
        if existing_model:
            return {"status": "skipped", "existing_model": existing_model}
            # → 이미 모델 있으면 훈련 안 하고 바로 반환

    # CPU 집약적 훈련 작업을 스레드 풀에서 실행
    training_result = await asyncio.get_event_loop().run_in_executor(
        self.executor,           # 스레드 풀
        self._train_model_sync,  # 실행할 함수
        symbol,                  # 함수 인자들
        training_days,
        force_retrain
    )
    # → 이 부분이 핵심! 동기 함수를 비동기로 실행

    return training_result

def _train_model_sync(self, symbol, training_days, force_retrain):
    """동기 모델 훈련 (스레드 풀에서 실행)"""
    end_date = date.today()
    start_date = end_date - timedelta(days=training_days)

    # 실제 훈련 실행 (시간 오래 걸림)
    return self.trainer.train_model(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        force_retrain=force_retrain
    )

# 🤔 왜 이렇게 복잡하게 할까?
# 1. ML 훈련은 시간이 오래 걸려 (몇 분~몇 시간)
# 2. 동기로 하면 API 서버가 멈춰버려
# 3. 비동기로 하면 다른 요청도 처리할 수 있어
# 4. 사용자는 "훈련 시작됨" 응답 받고 나중에 결과 확인
```

### ThreadPoolExecutor 사용법

파이썬의 비동기 처리 방법 중 하나야:

```python
# 일반적인 동기 처리 (나쁜 예)
def bad_api():
    result = heavy_ml_work()  # 10분 걸림
    return result
    # → 10분 동안 서버가 다른 요청 처리 못 함

# 비동기 처리 (좋은 예)
async def good_api():
    result = await asyncio.get_event_loop().run_in_executor(
        executor,      # 스레드 풀
        heavy_ml_work  # 무거운 작업
    )
    return result
    # → 무거운 작업은 별도 스레드에서, 메인 스레드는 다른 요청 처리

# 🎯 핵심 개념:
# - 메인 스레드: API 요청 받고 응답하는 역할
# - 워커 스레드: 실제 ML 작업 수행
# - 비동기: 메인 스레드가 블록되지 않음
```

### 데이터베이스 연동 코드

예측 결과를 DB에 저장하는 부분:

```python
async def _save_prediction_results(self, symbol, prediction_date, prediction_result):
    session = SessionLocal()  # DB 세션 생성
    prediction_repo = MLPredictionRepository(session)

    try:
        # 전체 결과에서 공통 정보 추출
        batch_id = prediction_result.get("batch_id")
        model_version = prediction_result.get("model_version", "unknown")
        current_price = prediction_result.get("current_price", 0.0)

        # 각 예측 기간별로 DB 레코드 생성
        for pred in prediction_result.get("predictions", []):
            prediction_entity = MLPrediction(
                symbol=symbol,                           # "^IXIC"
                prediction_date=prediction_date,         # 2025-08-09
                target_date=pred["target_date"],         # 2025-08-16 (7일 후)
                prediction_timeframe=pred["timeframe"], # "7d"
                predicted_price=pred["predicted_price"], # 15234.56
                predicted_direction=pred["predicted_direction"], # "up"
                confidence_score=pred["confidence_score"], # 0.75
                current_price=current_price,             # 15000.0
                model_version=model_version,             # "v1.0.0_20250809_120032"
                model_type="lstm",                       # "lstm"
                batch_id=batch_id,                       # UUID
                created_at=datetime.now(),               # 현재 시간
            )

            prediction_repo.save(prediction_entity)  # DB에 저장
            # → 이렇게 해서 나중에 예측 이력 조회 가능

        logger.info("prediction_results_saved",
                   symbol=symbol, batch_id=batch_id,
                   predictions_count=len(prediction_result.get("predictions", [])))

    except Exception as e:
        logger.error("prediction_results_save_failed", error=str(e))
        raise
    finally:
        session.close()  # DB 세션 정리

# 💾 DB 저장 이유:
# 1. 예측 이력 추적 (나중에 정확도 계산)
# 2. 사용자별 예측 기록 관리
# 3. 모델 성능 모니터링
# 4. 감사(Audit) 목적
```

---

## API 레이어 코드 분석

### FastAPI 라우터 동작 원리

사용자가 실제로 접근하는 API 엔드포인트들이야:

```python
@router.post("/train", response_model=TrainModelResponse, status_code=status.HTTP_201_CREATED)
async def train_model(
    request: TrainModelRequest,  # 요청 데이터 (자동 검증됨)
    handler: MLPredictionHandler = Depends(get_ml_handler)  # 의존성 주입
) -> TrainModelResponse:
    """모델 훈련 엔드포인트"""

    request_id = str(uuid.uuid4())  # 요청 추적용 ID

    # 로깅 (어떤 요청이 들어왔는지 기록)
    logger.info("train_model_endpoint_called",
               request_id=request_id,
               symbol=request.symbol,
               training_days=request.training_days)

    # 실제 처리는 핸들러에게 위임
    return await handler.train_model(request, request_id)

# 🔍 각 부분 설명:
# - @router.post: POST 요청 받는 엔드포인트
# - response_model: 응답 형태 정의 (자동 문서화)
# - status_code: 성공 시 201 반환
# - Depends: 의존성 주입 (핸들러 자동 생성)
# - async def: 비동기 함수 (다른 요청 블록 안 함)

@router.post("/predict", response_model=PredictionResponse)
async def predict_prices(
    request: PredictionRequest,
    handler: MLPredictionHandler = Depends(get_ml_handler)
) -> PredictionResponse:
    """가격 예측 엔드포인트"""

    request_id = str(uuid.uuid4())

    logger.info("predict_prices_endpoint_called",
               request_id=request_id,
               symbol=request.symbol,
               prediction_date=request.prediction_date)

    return await handler.predict_prices(request, request_id)

# 💡 FastAPI의 장점:
# 1. 자동 입력 검증 (Pydantic 모델 기반)
# 2. 자동 API 문서 생성 (Swagger UI)
# 3. 타입 힌트 기반 개발
# 4. 비동기 처리 내장 지원
```

### 의존성 주입 패턴 이해

코드의 결합도를 낮추는 똑똑한 패턴이야:

```python
# 의존성 주입 함수
def get_ml_handler() -> MLPredictionHandler:
    """ML 예측 핸들러 의존성"""
    return MLPredictionHandler()
    # → 매 요청마다 새로운 핸들러 인스턴스 생성

# 사용하는 곳
async def train_model(
    request: TrainModelRequest,
    handler: MLPredictionHandler = Depends(get_ml_handler)  # 여기서 주입
):
    # handler는 자동으로 생성되어 전달됨
    return await handler.train_model(request, request_id)

# 🤔 왜 이렇게 할까?
# 1. 테스트 용이성: 가짜 핸들러로 쉽게 교체 가능
# 2. 설정 관리: 환경별로 다른 구현체 주입 가능
# 3. 생명주기 관리: FastAPI가 자동으로 인스턴스 관리
# 4. 코드 분리: 라우터는 HTTP만, 핸들러는 비즈니스 로직만

# 나쁜 예 (직접 생성)
async def bad_train_model(request):
    handler = MLPredictionHandler()  # 하드코딩
    return await handler.train_model(request)
    # → 테스트하기 어렵고, 설정 변경 어려움

# 좋은 예 (의존성 주입)
async def good_train_model(request, handler=Depends(get_ml_handler)):
    return await handler.train_model(request)
    # → 유연하고 테스트 가능
```

### 에러 처리 메커니즘

API에서 발생하는 다양한 에러들을 처리하는 방법:

```python
class MLPredictionHandler:
    async def train_model(self, request: TrainModelRequest, request_id: str):
        try:
            # 입력 검증
            if request.training_days < 100 or request.training_days > 5000:
                raise ValueError("Training days must be between 100 and 5000")
                # → 비즈니스 규칙 위반

            # 실제 비즈니스 로직 호출
            result = await self.ml_service.train_model(
                symbol=request.symbol,
                training_days=request.training_days,
                force_retrain=request.force_retrain
            )

            # 성공 응답 생성
            return TrainModelResponse(
                status=result["status"],
                model_name=result.get("model_name"),
                model_version=result.get("model_version"),
                training_metadata=result.get("training_metadata"),
                request_id=request_id
            )

        except ValueError as e:
            # 입력 검증 오류 (400 Bad Request)
            logger.error("validation_error", request_id=request_id, error=str(e))
            raise HTTPException(status_code=400, detail=str(e))

        except FileNotFoundError as e:
            # 모델 파일 없음 (404 Not Found)
            logger.error("model_not_found", request_id=request_id, error=str(e))
            raise HTTPException(status_code=404, detail="Model not found")

        except Exception as e:
            # 기타 모든 오류 (500 Internal Server Error)
            logger.error("unexpected_error", request_id=request_id, error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

# 🎯 에러 처리 전략:
# 1. 구체적인 예외부터 처리 (ValueError → Exception 순서)
# 2. 적절한 HTTP 상태 코드 반환
# 3. 사용자에게는 간단한 메시지, 로그에는 상세 정보
# 4. request_id로 요청 추적 가능

# 📊 HTTP 상태 코드 의미:
# - 200: 성공
# - 201: 생성 성공 (모델 훈련 완료)
# - 400: 잘못된 요청 (입력값 오류)
# - 404: 리소스 없음 (모델 없음)
# - 500: 서버 오류 (예상치 못한 오류)
```

---

## 헷갈렸던 부분들 정리

### 멀티 아웃풋 모델 타겟 데이터 처리

이 부분이 제일 헷갈렸어. 딕셔너리 ↔ 리스트 변환을 계속 해야 해:

```python
# 데이터 준비 단계에서는 딕셔너리 형태
y_dict = {
    "7d": [15100, 15200, 15300, ...],   # 7일 후 가격들
    "14d": [15150, 15250, 15350, ...],  # 14일 후 가격들
    "30d": [15200, 15300, 15400, ...]   # 30일 후 가격들
}

# 모델 훈련할 때는 리스트 형태로 변환
y_train_list = [y_dict["7d"], y_dict["14d"], y_dict["30d"]]
# → [[7일가격들], [14일가격들], [30일가격들]]

# 🤔 왜 이렇게 해야 할까?
# 1. 딕셔너리: 사람이 이해하기 쉬움 (키로 구분)
# 2. 리스트: 케라스가 요구하는 형태 (순서로 구분)
# 3. 변환할 때 순서가 중요! 모델 출력 순서와 일치해야 함

# ⚠️ 주의사항:
# - self.target_days = [7, 14, 30] 순서
# - 모델 출력도 [7일, 14일, 30일] 순서
# - y_train_list도 [7일, 14일, 30일] 순서
# → 이 순서가 하나라도 틀리면 엉뚱한 결과!
```

### 시계열 데이터 분할 방법

일반적인 머신러닝과 다르게 시계열은 셔플하면 안 돼:

```python
# 일반 ML (나쁜 예 - 시계열에서는 절대 금지!)
def bad_split(X, y):
    # 랜덤 셔플 후 분할
    indices = np.random.permutation(len(X))
    X_shuffled = X[indices]
    y_shuffled = y[indices]
    # → 미래 정보로 과거 예측하게 됨 (데이터 누출!)

# 시계열 ML (좋은 예)
def good_split(X, y):
    # 시간 순서 유지하며 분할
    total_samples = len(X)
    train_end = int(total_samples * 0.7)      # 70%
    val_end = int(total_samples * 0.85)       # 15%

    X_train = X[:train_end]          # 과거 데이터
    X_val = X[train_end:val_end]     # 중간 데이터
    X_test = X[val_end:]             # 최신 데이터
    # → 시간 순서 보장!

# 🎯 핵심 원칙:
# - 훈련: 가장 오래된 데이터
# - 검증: 중간 시기 데이터
# - 테스트: 가장 최신 데이터
# → 실제 사용 시나리오와 동일
```

### 비동기 처리와 스레드 풀

파이썬의 비동기 처리가 헷갈릴 수 있어:

```python
# 동기 함수 (CPU 집약적)
def heavy_work():
    # 복잡한 계산 (10초 걸림)
    return result

# 비동기 래퍼
async def async_heavy_work():
    # 스레드 풀에서 동기 함수 실행
    result = await asyncio.get_event_loop().run_in_executor(
        executor,    # ThreadPoolExecutor 인스턴스
        heavy_work   # 실행할 동기 함수
    )
    return result

# 🤔 왜 이렇게 복잡하게?
# 1. heavy_work()는 CPU 집약적 → 비동기로 만들 수 없음
# 2. 하지만 API는 비동기로 처리하고 싶음
# 3. 해결책: 동기 함수를 스레드 풀에서 실행
# 4. 메인 스레드는 다른 요청 처리 가능

# 📊 처리 흐름:
# 1. 사용자 요청 → FastAPI (메인 스레드)
# 2. 무거운 작업 → 워커 스레드
# 3. 메인 스레드는 다른 요청 처리
# 4. 워커 스레드 완료 → 결과 반환
```

### 모델 저장/로드 과정

모델과 스케일러를 함께 관리하는 게 복잡해:

```python
# 저장 과정
def save_model(self, model_path):
    # 1. 모델 파일 저장
    self.model.save("model.keras")

    # 2. 스케일러들 저장 (중요!)
    scaler_dir = os.path.join(model_dir, "scalers")
    os.makedirs(scaler_dir, exist_ok=True)

    # 입력 특성 스케일러
    joblib.dump(self.feature_scaler, f"{scaler_dir}/feature_scaler.pkl")

    # 각 타겟별 스케일러
    for days in [7, 14, 30]:
        scaler = self.target_scalers[f"{days}d"]
        joblib.dump(scaler, f"{scaler_dir}/target_scaler_{days}d.pkl")

    # 3. 메타데이터 저장
    metadata = {"input_shape": self.input_shape, ...}
    with open("model_metadata.json", "w") as f:
        json.dump(metadata, f)

# 로드 과정
def load_model(self, model_path):
    # 1. 모델 파일 로드
    self.model = keras.models.load_model("model.keras")

    # 2. 스케일러들 로드
    scaler_dir = os.path.join(model_dir, "scalers")
    self.feature_scaler = joblib.load(f"{scaler_dir}/feature_scaler.pkl")

    for days in [7, 14, 30]:
        scaler = joblib.load(f"{scaler_dir}/target_scaler_{days}d.pkl")
        self.target_scalers[f"{days}d"] = scaler

    # 3. 메타데이터 로드
    with open("model_metadata.json", "r") as f:
        metadata = json.load(f)

# ⚠️ 주의사항:
# - 모델만 저장하면 안 돼! 스케일러도 함께 저장
# - 예측할 때 훈련 시와 동일한 스케일러 사용해야 함
# - 메타데이터로 호환성 체크 필수
```

---

## 디버깅할 때 유용한 팁들

### 각 단계별 데이터 형태 확인 방법

ML 파이프라인에서 데이터가 어떻게 변하는지 확인하는 게 중요해:

```python
# 1. 원시 데이터 확인
print(f"Raw data shape: {raw_data.shape}")
print(f"Raw data columns: {raw_data.columns.tolist()}")
print(f"Raw data sample:\n{raw_data.head()}")

# 2. 특성 엔지니어링 후 확인
print(f"Feature data shape: {feature_data.shape}")
print(f"Feature columns: {feature_data.columns.tolist()}")

# 3. 시퀀스 생성 후 확인
print(f"X shape: {X.shape}")  # (샘플수, 60, 152)
print(f"y_dict keys: {y_dict.keys()}")  # ['7d', '14d', '30d']
for key, value in y_dict.items():
    print(f"y_{key} shape: {value.shape}")

# 4. 정규화 후 확인
print(f"X_normalized range: {X_normalized.min():.3f} ~ {X_normalized.max():.3f}")
for key, value in y_normalized_dict.items():
    print(f"y_{key}_normalized range: {value.min():.3f} ~ {value.max():.3f}")

# 5. 예측 결과 확인
print(f"Raw predictions: {raw_predictions}")
print(f"Denormalized predictions: {denormalized_predictions}")
```

### 자주 발생하는 에러와 해결법

**1. 형태 불일치 에러**

```python
# 에러: ValueError: Input 0 of layer "lstm_1" is incompatible with the layer
# 원인: 입력 데이터 형태가 모델 기대와 다름
# 해결: 데이터 형태 확인
print(f"Expected: (batch_size, 60, 152)")
print(f"Actual: {X.shape}")

# 수정 방법
if len(X.shape) == 2:
    X = X.reshape(X.shape[0], 60, -1)  # 3차원으로 변환
```

**2. 스케일러 관련 에러**

```python
# 에러: sklearn.exceptions.NotFittedError: This MinMaxScaler instance is not fitted yet
# 원인: 스케일러가 fit되지 않은 상태에서 transform 시도
# 해결: fit 여부 확인
if hasattr(scaler, 'data_min_'):
    print("Scaler is fitted")
else:
    print("Scaler is NOT fitted - need to fit first")
    scaler.fit(data)
```

**3. 메모리 부족 에러**

```python
# 에러: MemoryError: Unable to allocate array
# 원인: 데이터가 너무 커서 메모리 부족
# 해결: 배치 처리
def process_in_batches(data, batch_size=1000):
    results = []
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        result = model.predict(batch)
        results.append(result)
    return np.concatenate(results)
```

### 성능 모니터링 포인트

**1. 훈련 과정 모니터링**

```python
# 훈련 중 손실 변화 확인
history = model.fit(...)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.legend()
plt.show()

# 각 출력별 손실 확인
for key in ['price_prediction_7d_loss', 'price_prediction_14d_loss', 'price_prediction_30d_loss']:
    if key in history.history:
        print(f"{key}: {history.history[key][-1]:.4f}")
```

**2. 예측 성능 모니터링**

```python
# 예측 시간 측정
import time
start_time = time.time()
predictions = model.predict(X_test)
prediction_time = time.time() - start_time
print(f"Prediction time: {prediction_time:.3f} seconds for {len(X_test)} samples")
print(f"Average time per sample: {prediction_time/len(X_test)*1000:.1f} ms")

# 메모리 사용량 확인
import psutil
process = psutil.Process()
memory_mb = process.memory_info().rss / 1024 / 1024
print(f"Memory usage: {memory_mb:.1f} MB")
```

**3. 모델 크기 확인**

```python
# 모델 파라미터 수
total_params = model.count_params()
trainable_params = sum([tf.keras.backend.count_params(w) for w in model.trainable_weights])
print(f"Total parameters: {total_params:,}")
print(f"Trainable parameters: {trainable_params:,}")

# 모델 파일 크기
import os
model_size_mb = os.path.getsize('model.keras') / 1024 / 1024
print(f"Model file size: {model_size_mb:.1f} MB")
```

---

## 마무리

이 문서는 내가 만든 ML 주가 예측 시스템의 모든 코드를 상세하게 분석한 개인 학습용 자료야.

나중에 이 코드를 다시 볼 때, 또는 비슷한 시스템을 만들 때 참고하면 될 것 같아.

특히 헷갈렸던 부분들 (멀티 아웃풋 데이터 처리, 시계열 분할, 비동기 처리 등)은 꼭 기억해두자!

---

_이 문서는 실제 구현한 코드를 바탕으로 작성되었으며, 개인 학습 및 복습 목적으로 만들어졌습니다._
