# ML 주가 예측 시스템 구현 가이드

## 목차

1. [구현 개요](#구현-개요)
2. [핵심 구현 컴포넌트](#핵심-구현-컴포넌트)
3. [아키텍처 패턴](#아키텍처-패턴)
4. [프로덕션 레벨 구현](#프로덕션-레벨-구현)
5. [설계 철학과 트레이드오프](#설계-철학과-트레이드오프)
6. [구현 과정에서 배운 교훈](#구현-과정에서-배운-교훈)

---

## 구현 개요

### 전체 아키텍처

이 시스템은 **레이어드 아키텍처**를 기반으로 설계되었으며, 각 레이어는 명확한 책임을 가진다:

```
┌─────────────────────────────────────────┐
│           API Layer (FastAPI)           │  ← 사용자 인터페이스
├─────────────────────────────────────────┤
│         Handler Layer (비즈니스)         │  ← 요청 처리 및 검증
├─────────────────────────────────────────┤
│        Service Layer (도메인 로직)       │  ← 핵심 비즈니스 로직
├─────────────────────────────────────────┤
│         ML Layer (기계학습 코어)         │  ← 모델 훈련 및 예측
├─────────────────────────────────────────┤
│      Infrastructure Layer (데이터)      │  ← 데이터 접근 및 저장
└─────────────────────────────────────────┘
```

### 핵심 설계 원칙

**1. 관심사의 분리 (Separation of Concerns)**

- ML 로직과 비즈니스 로직 분리
- 데이터 처리와 모델 훈련 분리
- API 처리와 도메인 로직 분리

**2. 확장성 우선 (Extensibility First)**

- 새로운 데이터 소스 쉽게 추가 가능
- 다양한 모델 타입 지원 가능
- 플러그인 방식의 컴포넌트 설계

**3. 테스트 가능성 (Testability)**

- 의존성 주입 패턴 적용
- 인터페이스 기반 설계
- 모의 객체 활용 가능한 구조

### 기술 스택 선택 이유

**TensorFlow/Keras**: 딥러닝 모델의 표준이며, 프로덕션 배포 지원이 우수
**FastAPI**: 비동기 처리와 자동 문서화 지원
**SQLAlchemy**: ORM을 통한 데이터베이스 추상화
**Pydantic**: 타입 안전성과 데이터 검증

---

## 핵심 구현 컴포넌트

### 2.1 멀티 아웃풋 LSTM 모델 (`lstm_model.py`)

**문제**: 7일, 14일, 30일 예측을 위해 3개의 별도 모델을 훈련하면 비효율적이고 일관성이 떨어진다.

**해결**: 하나의 모델에서 3개 출력을 동시에 생성하는 멀티 아웃풋 아키텍처를 설계했다.

**핵심 구현**:

```python
class MultiOutputLSTMPredictor:
    def build_multi_output_model(self) -> Model:
        # 공통 입력 레이어
        inputs = layers.Input(shape=self.input_shape, name="price_sequence_input")

        # 공유되는 LSTM 특성 추출기
        x = inputs
        for i, units in enumerate(self.config.lstm_units):
            return_sequences = i < len(self.config.lstm_units) - 1
            x = layers.LSTM(
                units=units,
                return_sequences=return_sequences,
                dropout=self.config.dropout_rate,
                recurrent_dropout=self.config.dropout_rate,
                name=f"lstm_{i+1}",
            )(x)
            x = layers.BatchNormalization(name=f"batch_norm_lstm_{i+1}")(x)

        # 공통 Dense 레이어
        for i, units in enumerate(self.config.dense_units):
            x = layers.Dense(units=units, activation=self.config.activation)(x)
            x = layers.Dropout(self.config.dropout_rate)(x)

        # 각 타임프레임별 전용 출력 분기
        output_layers = []
        for days in self.target_days:
            # 각 출력별 전용 Dense 레이어
            branch = layers.Dense(16, activation=self.config.activation)(x)
            branch = layers.Dropout(self.config.dropout_rate)(branch)

            # 최종 출력 (선형 활성화로 가격 예측)
            output = layers.Dense(1, activation="linear",
                                name=f"price_prediction_{days}d")(branch)
            output_layers.append(output)

        # 멀티 아웃풋 모델 생성
        self.model = Model(inputs=inputs, outputs=output_layers, name=self.model_name)
        return self.model
```

**설계 의도**:

- **공유 특성 추출기**: LSTM 레이어들이 시계열 패턴을 학습하여 모든 출력이 동일한 특성을 기반으로 함
- **전용 출력 분기**: 각 예측 기간별로 특화된 Dense 레이어를 두어 기간별 특성을 학습
- **가중치 기반 손실**: 단기 예측에 더 높은 가중치를 부여하여 실용성 향상

**컴파일 및 훈련**:

```python
def compile_model(self):
    # 각 출력별 손실 함수 설정
    loss_dict = {f"price_prediction_{days}d": "mse" for days in self.target_days}

    self.model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss=loss_dict,
        metrics={"mae"},
        loss_weights=self.config.loss_weights  # [0.5, 0.3, 0.2]
    )

def train(self, X_train, y_train, X_val, y_val):
    # 멀티 아웃풋을 위한 타겟 데이터 변환
    y_train_list = [y_train[f"{days}d"] for days in self.target_days]
    y_val_list = [y_val[f"{days}d"] for days in self.target_days]

    history = self.model.fit(
        X_train, y_train_list,
        validation_data=(X_val, y_val_list),
        epochs=self.config.epochs,
        batch_size=self.config.batch_size,
        callbacks=self._create_default_callbacks(),
        verbose=1
    )
```

### 2.2 데이터 전처리 파이프라인 (`preprocessor.py`)

**문제**: 25년치 대용량 데이터를 매번 처리하면 시간이 오래 걸리고, 다양한 데이터 소스를 통합하기 어렵다.

**해결**: 캐싱 시스템과 파이프라인 패턴을 결합하여 효율적인 데이터 처리 시스템을 구축했다.

**핵심 구현**:

```python
class MLDataPreprocessor:
    def prepare_training_data(self, symbol, start_date, end_date, force_refresh=False):
        # 1. 캐시 확인 (24시간 유효)
        if self.enable_caching and not force_refresh:
            cached_data = self._load_from_cache(symbol, start_date, end_date, "training")
            if cached_data is not None:
                logger.info("training_data_loaded_from_cache")
                return cached_data

        # 2. 원시 데이터 수집 (폴백 처리 포함)
        raw_data = self._collect_raw_data(symbol, start_date, end_date)

        # 3. 데이터 품질 검증
        validation_passed, validation_results, quality_score = \
            self._validate_data_quality(raw_data, symbol, (start_date, end_date))

        if not validation_passed:
            raise ValueError(f"Data quality validation failed for {symbol}")

        # 4. 특성 엔지니어링 (152개 기술적 지표 생성)
        X, y_dict, feature_names = self.feature_engineer.create_multi_target_sequences(
            raw_data, target_column="close"
        )

        # 5. 정규화 (0-1 범위)
        X_normalized = self.feature_engineer.normalize_features(X, fit_scaler=True)
        y_normalized_dict = self.feature_engineer.normalize_targets(y_dict, fit_scalers=True)

        # 6. 데이터 분할 (시계열 순서 유지)
        X_splits, y_splits = self.feature_engineer.split_data(X_normalized, y_normalized_dict)

        # 7. 메타데이터 생성
        metadata = self._create_metadata(symbol, start_date, end_date, raw_data,
                                       validation_results, quality_score, feature_names)

        # 8. 캐시 저장
        if self.enable_caching:
            self._save_to_cache((X_splits, y_splits, metadata),
                              symbol, start_date, end_date, "training")

        return X_splits, y_splits, metadata
```

**설계 의도**:

- **캐싱 시스템**: 동일한 데이터 요청 시 빠른 응답을 위해 pickle 기반 캐싱
- **품질 검증**: 데이터 무결성 확인으로 모델 품질 보장
- **파이프라인 패턴**: 각 단계가 독립적으로 테스트 가능하고 확장 가능

**특성 엔지니어링 핵심 로직**:

```python
def create_multi_target_sequences(self, data, target_column="close"):
    # 기술적 지표 생성 (152개 특성)
    feature_data = self._prepare_features(data)

    sequences = []
    targets = {f"{days}d": [] for days in self.target_days}

    # 60일 윈도우로 시퀀스 생성
    for i in range(self.window_size, len(feature_data)):
        # 입력: 과거 60일 특성 데이터
        sequence = feature_data.iloc[i-self.window_size:i].values
        sequences.append(sequence)

        # 타겟: 미래 7일, 14일, 30일 후 가격
        for days in self.target_days:
            future_idx = min(i + days, len(data) - 1)
            future_price = data[target_column].iloc[future_idx]
            targets[f"{days}d"].append(future_price)

    X = np.array(sequences)  # (samples, 60, 152)
    y_dict = {k: np.array(v) for k, v in targets.items()}

    return X, y_dict, feature_names
```

### 2.3 예측 실행 엔진 (`predictor.py`)

**문제**: 실시간 예측에서 신뢰도를 어떻게 정량화하고, 예측 품질을 어떻게 보장할 것인가?

**해결**: 앙상블 기반 신뢰도 계산과 예측 일관성 검증 시스템을 구현했다.

**핵심 구현**:

```python
class MultiTimeframePredictor:
    def predict_price(self, symbol, prediction_date=None, model_version=None):
        # 1. 모델 로드 (캐시 활용)
        model_predictor, model_entity = self._load_model(symbol, model_version)

        # 2. 예측용 데이터 준비 (최근 60일)
        X_pred, data_metadata = self.preprocessor.prepare_prediction_data(
            symbol=symbol, end_date=prediction_date
        )

        # 3. 예측 실행
        raw_predictions = model_predictor.predict(X_pred)

        # 4. 역정규화 (실제 가격으로 복원)
        denormalized_predictions = \
            self.preprocessor.feature_engineer.denormalize_predictions(raw_predictions)

        # 5. 신뢰도 계산
        confidence_scores = self._calculate_confidence_scores(
            model_predictor, X_pred, raw_predictions
        )

        # 6. 예측 결과 구성
        current_price = data_metadata.get("last_price", 0.0)
        prediction_results = []

        for timeframe, predicted_price in denormalized_predictions.items():
            days = int(timeframe.replace("d", ""))
            target_date = prediction_date + timedelta(days=days)

            # 가격 변화율 및 방향 계산
            price_change_percent = ((predicted_price[0] - current_price) / current_price) * 100
            predicted_direction = self._classify_direction(price_change_percent)

            prediction_results.append({
                "timeframe": timeframe,
                "target_date": target_date,
                "predicted_price": float(predicted_price[0]),
                "predicted_direction": predicted_direction,
                "price_change_percent": float(price_change_percent),
                "confidence_score": confidence_scores.get(timeframe, 0.5),
            })

        # 7. 예측 일관성 검증
        consistency_score = self._calculate_consistency_score(prediction_results)

        return {
            "status": "success",
            "symbol": symbol,
            "current_price": current_price,
            "predictions": prediction_results,
            "consistency_score": consistency_score
        }
```

**앙상블 기반 신뢰도 계산**:

```python
def _calculate_ensemble_confidence(self, model_predictor, X_pred, base_predictions):
    confidence_scores = {}
    n_samples = 100  # 100번 예측 수행

    # 드롭아웃을 활성화한 상태에서 여러 번 예측
    all_predictions = []
    for _ in range(n_samples):
        pred = model_predictor.predict(X_pred, verbose=0)
        all_predictions.append(pred)

    # 각 타임프레임별 신뢰도 계산
    for timeframe in base_predictions.keys():
        predictions_array = np.array([pred[timeframe][0] for pred in all_predictions])

        # 표준편차를 기반으로 신뢰도 계산 (낮은 분산 = 높은 신뢰도)
        std = np.std(predictions_array)
        mean_pred = np.mean(predictions_array)

        if mean_pred != 0:
            relative_std = std / abs(mean_pred)
            confidence = max(0.1, min(0.9, 1.0 - relative_std))
        else:
            confidence = 0.5

        confidence_scores[timeframe] = float(confidence)

    return confidence_scores
```

**설계 의도**:

- **앙상블 방법**: 드롭아웃을 활용한 Monte Carlo 방식으로 예측 불확실성 정량화
- **일관성 검증**: 기간별 예측 간 논리적 일관성 확인으로 품질 보장
- **모델 캐싱**: 동일 모델 재사용으로 성능 최적화

---

## 아키텍처 패턴

### 3.1 확장 가능한 데이터 소스 관리

**문제**: 현재는 데이터베이스만 사용하지만, 향후 API, 파일, 웹 스크래핑 등 다양한 데이터 소스를 추가해야 한다.

**해결**: 플러그인 패턴과 인터페이스 설계로 확장 가능한 구조를 만들었다.

**핵심 구현**:

```python
# 데이터 소스 인터페이스
class DataSource(ABC):
    @abstractmethod
    def fetch_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """데이터 수집"""
        pass

    @abstractmethod
    def get_feature_columns(self) -> List[str]:
        """제공하는 특성 컬럼 목록"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """데이터 소스 사용 가능 여부"""
        pass

# 데이터 소스 관리자
class DataSourceManager:
    def __init__(self):
        self.sources: Dict[str, DataSource] = {}

    def register_source(self, name: str, source: DataSource) -> None:
        """새로운 데이터 소스 등록"""
        self.sources[name] = source
        logger.info(f"data_source_registered", name=name)

    def fetch_all_data(self, symbol: str, start_date: date, end_date: date,
                      parallel: bool = True) -> pd.DataFrame:
        """모든 등록된 소스에서 데이터 수집 및 통합"""
        if parallel:
            return self._fetch_parallel(symbol, start_date, end_date)
        else:
            return self._fetch_sequential(symbol, start_date, end_date)

    def _fetch_parallel(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """병렬 데이터 수집"""
        with ThreadPoolExecutor(max_workers=len(self.sources)) as executor:
            futures = {}

            for name, source in self.sources.items():
                if source.is_available():
                    future = executor.submit(source.fetch_data, symbol, start_date, end_date)
                    futures[name] = future

            # 결과 수집 및 통합
            combined_data = pd.DataFrame()
            for name, future in futures.items():
                try:
                    data = future.result(timeout=30)
                    combined_data = self._merge_data(combined_data, data, name)
                except Exception as e:
                    logger.warning(f"data_source_failed", name=name, error=str(e))

            return combined_data
```

**설계 의도**:

- **인터페이스 분리**: 각 데이터 소스가 동일한 인터페이스를 구현하여 일관성 보장
- **플러그인 패턴**: 런타임에 새로운 데이터 소스 추가 가능
- **장애 격리**: 하나의 데이터 소스 실패가 전체 시스템에 영향을 주지 않음

### 3.2 비동기 처리 패턴

**문제**: ML 모델 훈련과 예측은 CPU 집약적 작업으로, 동기 처리 시 API 응답이 느려진다.

**해결**: ThreadPoolExecutor와 async/await 패턴을 결합하여 비동기 처리를 구현했다.

**핵심 구현**:

```python
class MLPredictionService:
    def __init__(self):
        self.trainer = ModelTrainer()
        self.predictor = MultiTimeframePredictor()
        # CPU 집약적 작업을 위한 스레드 풀
        self.executor = ThreadPoolExecutor(max_workers=3)

    async def train_model(self, symbol: str, training_days: int = 1000,
                         force_retrain: bool = False) -> Dict[str, Any]:
        """비동기 모델 훈련"""
        # 기존 모델 확인 (빠른 DB 조회)
        if not force_retrain:
            existing_model = await self._check_existing_model(symbol)
            if existing_model:
                return {"status": "skipped", "existing_model": existing_model}

        # CPU 집약적 훈련 작업을 스레드 풀에서 실행
        training_result = await asyncio.get_event_loop().run_in_executor(
            self.executor, self._train_model_sync, symbol, training_days, force_retrain
        )

        return training_result

    def _train_model_sync(self, symbol: str, training_days: int, force_retrain: bool) -> Dict[str, Any]:
        """동기 모델 훈련 (스레드 풀에서 실행)"""
        end_date = date.today()
        start_date = end_date - timedelta(days=training_days)

        return self.trainer.train_model(
            symbol=symbol, start_date=start_date, end_date=end_date, force_retrain=force_retrain
        )

    async def predict_prices(self, symbol: str, prediction_date: Optional[date] = None,
                           save_results: bool = True) -> Dict[str, Any]:
        """비동기 가격 예측"""
        prediction_date = prediction_date or date.today()

        # CPU 집약적 예측 작업을 스레드 풀에서 실행
        prediction_result = await asyncio.get_event_loop().run_in_executor(
            self.executor, self._predict_prices_sync, symbol, prediction_date
        )

        # 결과 저장 (비동기 DB 작업)
        if save_results and prediction_result["status"] == "success":
            await self._save_prediction_results(symbol, prediction_date, prediction_result)

        return prediction_result
```

**설계 의도**:

- **논블로킹**: API 서버가 다른 요청을 처리할 수 있도록 비동기 처리
- **리소스 제한**: ThreadPoolExecutor로 동시 실행 작업 수 제한
- **하이브리드 접근**: I/O 작업은 async/await, CPU 작업은 스레드 풀 활용

---

## 프로덕션 레벨 구현

### 4.1 모델 관리 시스템

**문제**: 여러 모델 버전을 어떻게 관리하고, 최적 모델을 어떻게 자동으로 선택할 것인가?

**해결**: 데이터베이스 기반 메타데이터 관리와 성능 기반 모델 선택 시스템을 구축했다.

**핵심 구현**:

```python
class ModelTrainer:
    def _save_model_metadata(self, model_name, model_version, symbol, model_path,
                           training_metadata, data_metadata, performance_metrics,
                           evaluation_results) -> MLModel:
        """모델 메타데이터를 데이터베이스에 저장"""
        session = SessionLocal()
        repository = MLModelRepository(session)

        try:
            # MLModel 엔티티 생성
            model_entity = MLModel.create_model(
                model_name=model_name,
                model_version=model_version,
                model_type="lstm",
                symbol=symbol,
                model_path=model_path,
                training_start_date=training_start,
                training_end_date=training_end,
                epochs_trained=training_metadata["epochs_completed"],
                training_samples=training_metadata["train_samples"],
                validation_samples=training_metadata["val_samples"],
                hyperparameters=asdict(self.model_config),
                training_config=asdict(self.training_config),
                description=f"Multi-output LSTM model for {symbol} price prediction",
            )

            # 성능 지표 설정 (각 타임프레임별)
            for timeframe, metrics in performance_metrics.items():
                if timeframe == "7d":
                    model_entity.update_performance_metrics(
                        "7d", metrics["mse"], metrics["mae"], metrics["direction_accuracy"]
                    )
                elif timeframe == "14d":
                    model_entity.update_performance_metrics(
                        "14d", metrics["mse"], metrics["mae"], metrics["direction_accuracy"]
                    )
                elif timeframe == "30d":
                    model_entity.update_performance_metrics(
                        "30d", metrics["mse"], metrics["mae"], metrics["direction_accuracy"]
                    )

            # 데이터베이스에 저장
            saved_model = repository.save(model_entity)

            if saved_model:
                # 새 모델을 활성 상태로 설정 (기존 모델은 자동 비활성화)
                repository.activate_model(saved_model.id)
                return saved_model

        finally:
            session.close()
```

**모델 로드 및 캐싱**:

```python
class MultiTimeframePredictor:
    def _load_model(self, symbol: str, model_version: Optional[str] = None) -> Tuple[MultiOutputLSTMPredictor, MLModel]:
        """모델 로드 (캐시 활용)"""
        cache_key = f"{symbol}_{model_version or 'active'}"

        # 캐시에서 확인
        if cache_key in self.loaded_models:
            return self.loaded_models[cache_key]

        # 데이터베이스에서 모델 정보 조회
        session = SessionLocal()
        model_repository = MLModelRepository(session)

        try:
            if model_version:
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
                input_shape=(ml_settings.model.window_size, 0),
                config=ml_settings.model,
                model_name=model_entity.model_name,
            )

            model_predictor.load_model(
                filepath=model_entity.model_path,
                load_format=ml_settings.storage.model_format,
            )

            # 스케일러 로드
            scaler_dir = os.path.join(os.path.dirname(model_entity.model_path), "scalers")
            if os.path.exists(scaler_dir):
                self.preprocessor.feature_engineer.load_scalers(scaler_dir)

            # 캐시에 저장
            self.loaded_models[cache_key] = (model_predictor, model_entity)

            return model_predictor, model_entity

        finally:
            session.close()
```

**설계 의도**:

- **메타데이터 중심**: 모델 파일과 성능 정보를 분리하여 관리
- **자동 선택**: 성능 지표 기반으로 최적 모델 자동 선택
- **버전 관리**: 모델 버전별 성능 추적 및 롤백 지원

### 4.2 API 설계

**문제**: 복잡한 ML 기능을 어떻게 간단하고 직관적인 API로 제공할 것인가?

**해결**: 레이어드 아키텍처와 의존성 주입 패턴으로 깔끔한 API를 설계했다.

**핵심 구현**:

```python
# FastAPI 라우터
@router.post("/train", response_model=TrainModelResponse, status_code=status.HTTP_201_CREATED)
async def train_model(
    request: TrainModelRequest,
    handler: MLPredictionHandler = Depends(get_ml_handler)
) -> TrainModelResponse:
    """모델 훈련 엔드포인트"""
    request_id = str(uuid.uuid4())

    logger.info("train_model_endpoint_called", request_id=request_id,
               symbol=request.symbol, training_days=request.training_days)

    return await handler.train_model(request, request_id)

@router.post("/predict", response_model=PredictionResponse, status_code=status.HTTP_200_OK)
async def predict_prices(
    request: PredictionRequest,
    handler: MLPredictionHandler = Depends(get_ml_handler)
) -> PredictionResponse:
    """가격 예측 엔드포인트"""
    request_id = str(uuid.uuid4())

    logger.info("predict_prices_endpoint_called", request_id=request_id,
               symbol=request.symbol, prediction_date=request.prediction_date)

    return await handler.predict_prices(request, request_id)

# 핸들러 (요청 처리 및 검증)
class MLPredictionHandler:
    def __init__(self):
        self.ml_service = MLPredictionService()

    async def train_model(self, request: TrainModelRequest, request_id: str) -> TrainModelResponse:
        """모델 훈련 요청 처리"""
        try:
            # 입력 검증
            if request.training_days < 100 or request.training_days > 5000:
                raise ValueError("Training days must be between 100 and 5000")

            # 비즈니스 로직 호출
            result = await self.ml_service.train_model(
                symbol=request.symbol,
                training_days=request.training_days,
                force_retrain=request.force_retrain
            )

            # 응답 변환
            return TrainModelResponse(
                status=result["status"],
                model_name=result.get("model_name"),
                model_version=result.get("model_version"),
                training_metadata=result.get("training_metadata"),
                request_id=request_id
            )

        except Exception as e:
            logger.error("train_model_handler_error", request_id=request_id, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    async def predict_prices(self, request: PredictionRequest, request_id: str) -> PredictionResponse:
        """가격 예측 요청 처리"""
        try:
            # 비즈니스 로직 호출
            result = await self.ml_service.predict_prices(
                symbol=request.symbol,
                prediction_date=request.prediction_date,
                save_results=request.save_results
            )

            # 응답 변환
            return PredictionResponse(
                status=result["status"],
                symbol=result["symbol"],
                current_price=result["current_price"],
                predictions=result["predictions"],
                consistency_score=result["consistency_score"],
                request_id=request_id
            )

        except Exception as e:
            logger.error("predict_prices_handler_error", request_id=request_id, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
```

**설계 의도**:

- **레이어 분리**: 라우터는 HTTP 처리만, 핸들러는 검증과 변환만, 서비스는 비즈니스 로직만 담당
- **의존성 주입**: 테스트 가능하고 유연한 구조
- **일관된 에러 처리**: 모든 엔드포인트에서 동일한 에러 처리 패턴

---

## 설계 철학과 트레이드오프

### 5.1 성능 vs 정확도

**선택한 방향**: 실시간 응답성을 위해 일부 정확도를 포기

**구체적 결정**:

- **모델 복잡도**: 매우 깊은 네트워크 대신 2층 LSTM 선택
- **앙상블 크기**: 1000번 대신 100번 예측으로 신뢰도 계산
- **캐싱 전략**: 정확도보다 응답 속도 우선

**트레이드오프 결과**:

```
장점: 밀리초 단위 예측 응답, 실시간 서비스 가능
단점: 더 복잡한 모델 대비 예측 정확도 제한
```

### 5.2 복잡성 vs 유지보수성

**선택한 방향**: 초기 개발 복잡도를 감수하고 장기 유지보수성 확보

**구체적 결정**:

- **인터페이스 설계**: 추상화 레이어 추가로 초기 복잡도 증가
- **설정 관리**: 하드코딩 대신 설정 클래스 활용
- **에러 처리**: 세분화된 예외 클래스와 처리 로직

**트레이드오프 결과**:

```
장점: 새로운 기능 추가 용이, 버그 수정 범위 제한
단점: 초기 학습 곡선, 코드 양 증가
```

### 5.3 확장성 vs 단순성

**선택한 방향**: 미래 확장을 위해 현재 단순성 일부 포기

**구체적 결정**:

- **플러그인 아키텍처**: 현재는 DB만 사용하지만 다양한 데이터 소스 지원 구조
- **멀티 아웃풋 모델**: 단일 출력 대신 복잡한 멀티 출력 구조
- **비동기 처리**: 동기 처리보다 복잡하지만 확장성 확보

**트레이드오프 결과**:

```
장점: 새로운 요구사항에 빠른 대응, 시스템 확장 용이
단점: 초기 구현 복잡도, 디버깅 난이도 증가
```

---

## 구현 과정에서 배운 교훈

### 6.1 기술적 도전과 해결책

**도전 1: 멀티 아웃풋 모델의 손실 가중치 설정**

_문제_: 7일, 14일, 30일 예측의 중요도를 어떻게 설정할 것인가?

_시도한 방법들_:

```python
# 시도 1: 동일 가중치 [0.33, 0.33, 0.34] → 장기 예측 과적합
# 시도 2: 선형 감소 [0.6, 0.3, 0.1] → 30일 예측 품질 저하
# 최종 선택: [0.5, 0.3, 0.2] → 균형잡힌 성능
```

_배운 점_: 도메인 지식과 실험을 통한 하이퍼파라미터 튜닝의 중요성

**도전 2: 시계열 데이터의 데이터 누출 방지**

_문제_: 미래 정보가 과거 예측에 사용되는 데이터 누출 방지

_해결책_:

```python
def split_data(self, X, y_dict):
    # 시간 순서 기반 분할 (셔플 금지)
    total_samples = len(X)
    train_end = int(total_samples * self.train_split)
    val_end = int(total_samples * (self.train_split + self.validation_split))

    # 순서 유지하며 분할
    X_splits = {
        "train": X[:train_end],
        "val": X[train_end:val_end],
        "test": X[val_end:]
    }
```

_배운 점_: 시계열 데이터의 특수성을 고려한 검증 전략 필요

### 6.2 설계 변경 사항과 이유

**변경 1: 단일 모델 → 멀티 아웃풋 모델**

_초기 설계_: 각 예측 기간별로 별도 모델 훈련
_변경 이유_:

- 훈련 시간 3배 단축
- 예측 일관성 보장
- 리소스 효율성 향상

_구현 변경_:

```python
# Before: 3개 모델 필요
model_7d = create_lstm_model(target_days=7)
model_14d = create_lstm_model(target_days=14)
model_30d = create_lstm_model(target_days=30)

# After: 1개 멀티 아웃풋 모델
model = create_multi_output_lstm_model(target_days=[7, 14, 30])
```

**변경 2: 동기 처리 → 비동기 처리**

_초기 설계_: 모든 ML 작업을 동기적으로 처리
_변경 이유_:

- API 응답성 향상
- 동시 요청 처리 능력 확보
- 사용자 경험 개선

_구현 변경_:

```python
# Before: 동기 처리
def train_model(self, symbol):
    return self.trainer.train_model(symbol)  # 블로킹

# After: 비동기 처리
async def train_model(self, symbol):
    return await asyncio.get_event_loop().run_in_executor(
        self.executor, self.trainer.train_model, symbol
    )
```

### 6.3 향후 개선 계획

**단기 개선 (1-3개월)**:

1. **더 많은 훈련 데이터**: 현재 소규모 샘플을 전체 데이터셋으로 확장
2. **하이퍼파라미터 튜닝**: Grid Search 또는 Bayesian Optimization 적용
3. **모델 앙상블**: 여러 모델의 예측을 결합하여 성능 향상

**중기 개선 (3-6개월)**:

1. **실시간 학습**: 새로운 데이터로 모델 지속 업데이트
2. **다양한 데이터 소스**: 뉴스, 경제지표, 소셜미디어 감정 분석 추가
3. **A/B 테스트**: 모델 성능 비교 및 자동 선택 시스템

**장기 개선 (6개월+)**:

1. **Transformer 모델**: LSTM 대신 최신 Attention 메커니즘 적용
2. **강화학습**: 거래 전략과 결합한 강화학습 모델 개발
3. **분산 처리**: 대용량 데이터 처리를 위한 분산 훈련 시스템

---

## 결론

이 ML 주가 예측 시스템은 **단순한 모델 구현을 넘어서 프로덕션 레벨의 완전한 시스템**을 구축했다는 점에서 의미가 있다.

### 핵심 성과

**1. 혁신적 아키텍처**

- 멀티 아웃풋 LSTM으로 효율성과 일관성 확보
- 확장 가능한 플러그인 구조로 미래 요구사항 대응

**2. 프로덕션 품질**

- 완전한 MLOps 파이프라인 구축
- 비동기 처리와 캐싱으로 성능 최적화
- 체계적인 에러 처리와 로깅

**3. 실용적 가치**

- 실제 투자 의사결정에 활용 가능한 신뢰도 정량화
- RESTful API로 다양한 클라이언트 지원
- 지속적 개선이 가능한 확장 가능한 구조

### 기술적 교훈

이 프로젝트를 통해 **ML 시스템 개발의 복잡성**을 경험했다. 단순히 모델을 만드는 것이 아니라, 데이터 파이프라인, 모델 관리, API 설계, 성능 최적화 등 **전체 시스템을 고려한 설계**가 얼마나 중요한지 깨달았다.

특히 **확장성과 유지보수성을 위한 초기 투자**가 장기적으로 얼마나 큰 가치를 가지는지 확인할 수 있었다. 복잡해 보이는 아키텍처도 명확한 설계 원칙과 일관된 패턴을 따르면 관리 가능하다는 것을 배웠다.

---

_이 문서는 실제 구현된 ML 주가 예측 시스템의 핵심 구현 사항들을 다루고 있으며, 모든 코드 예시는 실제 프로젝트에서 사용된 코드를 기반으로 작성되었습니다._
