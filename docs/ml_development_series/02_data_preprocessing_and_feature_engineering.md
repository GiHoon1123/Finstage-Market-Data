# 머신러닝을 활용한 주가 예측 시스템 개발 - 2. 차트 데이터 분석과 특성 엔지니어링

## 데이터 수집과 전처리 과정

머신러닝 모델의 성능은 **데이터의 품질**에 크게 좌우된다. 이번 글에서는 나스닥(^IXIC)과 S&P500(^GSPC) 지수의 일봉 데이터를 수집하고, 이를 ML 모델이 학습할 수 있는 형태로 가공하는 과정을 자세히 살펴보겠습니다.

## 1. 원시 데이터 수집

### 1.1 일봉 데이터 구조

먼저 수집하는 데이터의 기본 구조를 정의했다:

```python
class DailyPrice(Base):
    __tablename__ = "daily_prices"

    # 기본 식별 정보
    symbol = Column(String(10), nullable=False)  # ^IXIC, ^GSPC
    date = Column(Date, nullable=False)          # 거래일

    # OHLCV 데이터
    open_price = Column(DECIMAL(12, 4))   # 시가
    high_price = Column(DECIMAL(12, 4))   # 고가
    low_price = Column(DECIMAL(12, 4))    # 저가
    close_price = Column(DECIMAL(12, 4))  # 종가 (가장 중요!)
    volume = Column(BigInteger)           # 거래량

    # 추가 계산 필드
    price_change = Column(DECIMAL(12, 4))        # 가격 변화량
    price_change_percent = Column(DECIMAL(8, 4)) # 가격 변화율
```

### 1.2 데이터 수집 전략

**초기 수집**: 10년치 과거 데이터 일괄 수집 (2015~2025)

- Yahoo Finance API를 통한 과거 데이터 수집
- 중복 방지를 위한 symbol + date 유니크 제약
- 최소 200일 이상의 데이터 확보 (기술적 지표 계산용)

**일일 업데이트**: 매일 장 마감 후 최신 1일봉 추가

- 자동화된 스케줄러를 통한 정기 업데이트
- 누락 데이터 자동 보완 시스템

## 2. 특성 엔지니어링

### 2.1 가격 기반 특성

기본 OHLCV 데이터에서 추가적인 가격 특성을 생성했다:

```python
def _add_price_features(self, data: pd.DataFrame) -> pd.DataFrame:
    # 일일 수익률
    data["daily_return"] = data["close"].pct_change()

    # 가격 범위 (고가-저가)
    data["price_range"] = data["high"] - data["low"]
    data["price_range_pct"] = data["price_range"] / data["close"]

    # 캔들 몸통 크기
    data["candle_body"] = abs(data["close"] - data["open"])
    data["candle_body_pct"] = data["candle_body"] / data["close"]

    # 위꼬리, 아래꼬리
    data["upper_shadow"] = data["high"] - np.maximum(data["open"], data["close"])
    data["lower_shadow"] = np.minimum(data["open"], data["close"]) - data["low"]

    # 캔들 타입 (양봉/음봉)
    data["is_green_candle"] = (data["close"] > data["open"]).astype(float)

    # 갭 (전일 종가 대비 시가)
    data["gap"] = data["open"] - data["close"].shift(1)
    data["gap_pct"] = data["gap"] / data["close"].shift(1)

    return data
```

### 2.2 거래량 기반 특성

거래량과 가격의 관계를 분석하는 특성을 추가했다:

```python
def _add_volume_features(self, data: pd.DataFrame) -> pd.DataFrame:
    # 거래량 변화율
    data["volume_change"] = data["volume"].pct_change()

    # 가격-거래량 관계
    data["price_volume"] = data["close"] * data["volume"]

    # 거래량 가중 평균 가격 (VWAP 근사)
    data["vwap_approx"] = (data["high"] + data["low"] + data["close"]) / 3

    return data
```

### 2.3 시간 기반 특성

시장의 계절성과 주기성을 반영하는 시간 특성을 추가했다:

```python
def _add_time_features(self, data: pd.DataFrame) -> pd.DataFrame:
    # 요일 (0=월요일, 6=일요일)
    data["day_of_week"] = data.index.weekday

    # 월
    data["month"] = data.index.month

    # 분기
    data["quarter"] = data.index.quarter

    # 월 시작/끝 여부
    data["is_month_start"] = data.index.is_month_start.astype(float)
    data["is_month_end"] = data.index.is_month_end.astype(float)

    # 분기 시작/끝 여부
    data["is_quarter_start"] = data.index.is_quarter_start.astype(float)
    data["is_quarter_end"] = data.index.is_quarter_end.astype(float)

    # 요일별 원-핫 인코딩
    for i in range(7):
        data[f"is_weekday_{i}"] = (data.index.weekday == i).astype(float)

    return data
```

### 2.4 래그 특성과 롤링 통계

과거 데이터의 패턴을 학습하기 위한 래그 특성과 롤링 통계를 추가했다:

```python
def _add_lag_features(self, data: pd.DataFrame) -> pd.DataFrame:
    # 주요 컬럼들의 래그 특성
    lag_columns = ["close", "volume", "daily_return"]
    lag_periods = [1, 2, 3, 5, 10]

    for col in lag_columns:
        if col in data.columns:
            for lag in lag_periods:
                data[f"{col}_lag_{lag}"] = data[col].shift(lag)

    return data

def _add_rolling_features(self, data: pd.DataFrame) -> pd.DataFrame:
    # 롤링 윈도우 크기들
    windows = [5, 10, 20]

    for window in windows:
        # 가격 롤링 통계
        data[f"close_mean_{window}"] = data["close"].rolling(window=window).mean()
        data[f"close_std_{window}"] = data["close"].rolling(window=window).std()
        data[f"close_min_{window}"] = data["close"].rolling(window=window).min()
        data[f"close_max_{window}"] = data["close"].rolling(window=window).max()

        # 거래량 롤링 통계
        if "volume" in data.columns:
            data[f"volume_mean_{window}"] = data["volume"].rolling(window=window).mean()
            data[f"volume_std_{window}"] = data["volume"].rolling(window=window).std()

        # 수익률 롤링 통계
        if "daily_return" in data.columns:
            data[f"return_mean_{window}"] = data["daily_return"].rolling(window=window).mean()
            data[f"return_std_{window}"] = data["daily_return"].rolling(window=window).std()

    return data
```

## 3. 데이터 품질 관리

### 3.1 결측치 처리

```python
# Forward fill: 이전 값으로 채우기
data = data.fillna(method='ffill')

# Backward fill: 다음 값으로 채우기
data = data.fillna(method='bfill')

# 여전히 남은 결측치는 0으로 채우기
data = data.fillna(0)
```

### 3.2 이상치 탐지 및 처리

```python
def detect_outliers(data: pd.DataFrame, column: str, threshold: float = 3.0) -> pd.DataFrame:
    """Z-score 기반 이상치 탐지"""
    z_scores = np.abs(stats.zscore(data[column].dropna()))
    outlier_indices = np.where(z_scores > threshold)[0]

    # 이상치를 중앙값으로 대체
    median_value = data[column].median()
    data.loc[outlier_indices, column] = median_value

    return data
```

### 3.3 정규화

모든 특성을 0-1 범위로 정규화하여 스케일 차이를 해결했다:

```python
def normalize_features(self, data: pd.DataFrame) -> pd.DataFrame:
    """MinMaxScaler를 사용한 특성 정규화"""
    scaler = MinMaxScaler()
    normalized_data = scaler.fit_transform(data)

    # 스케일러 저장 (예측 시 사용)
    self.feature_scaler = scaler

    return pd.DataFrame(normalized_data, columns=data.columns, index=data.index)
```

## 4. 최종 특성 구성

### 4.1 특성 개수 분석

최종적으로 생성된 특성의 구성은 다음과 같다:

- **기본 가격 특성**: 7개 (OHLCV + 변화율)
- **시간 특성**: 32개 (요일, 월, 분기, 휴일 등)
- **엔지니어링 특성**: 68개 (지연 특성, 롤링 통계 등)

**총 특성 수**: 107개

## 5. 데이터 검증

### 5.1 데이터 품질 검증

```python
def validate_data_quality(self, data: pd.DataFrame) -> Dict[str, Any]:
    """데이터 품질 검증"""
    validation_results = {
        "total_rows": len(data),
        "missing_values": data.isnull().sum().to_dict(),
        "duplicate_rows": data.duplicated().sum(),
        "feature_count": len(data.columns),
        "date_range": {
            "start": data.index.min(),
            "end": data.index.max(),
            "days": (data.index.max() - data.index.min()).days
        }
    }

    return validation_results
```

### 5.2 특성 상관관계 분석

중복되거나 불필요한 특성을 제거하기 위해 상관관계를 분석했다:

```python
def analyze_feature_correlation(self, data: pd.DataFrame, threshold: float = 0.95) -> List[Tuple[str, str]]:
    """높은 상관관계를 가진 특성 쌍 찾기"""
    correlation_matrix = data.corr()
    high_correlation_pairs = []

    for i in range(len(correlation_matrix.columns)):
        for j in range(i+1, len(correlation_matrix.columns)):
            if abs(correlation_matrix.iloc[i, j]) > threshold:
                high_correlation_pairs.append(
                    (correlation_matrix.columns[i], correlation_matrix.columns[j])
                )

    return high_correlation_pairs
```

## 결론

이번 과정을 통해 **107개의 특성**을 가진 학습 데이터를 구축했다. 훈련시키기에 데이터가 매우 적지만 나쁘지 않은 출발인 것 같다.

핵심은 **다양한 관점에서 데이터를 바라보는 것**이었다:

- **가격 관점**: OHLCV, 캔들 패턴, 갭
- **시간 관점**: 요일, 월, 분기, 계절성
- **통계적 관점**: 래그, 롤링 통계, 변동성

이제 이렇게 가공된 차트 데이터를 사용하여 LSTM 모델을 훈련시키고 1차 예측을 수행할 수 있다. 다음 단계에서는 1차 예측 결과를 분석하고, 기술적 지표와 감정분석 데이터를 추가하여 2차 예측을 진행하는 과정을 다루게 될 것이다.
