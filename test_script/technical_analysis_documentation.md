# Technical Analysis 패키지 및 Scheduler 시스템 분석

## 📋 개요

Technical Analysis 패키지는 금융 시장의 기술적 지표를 모니터링하고, 신호를 감지하여 알림을 보내며, 신호의 성과를 추적하는 종합적인 시스템입니다. 이 시스템은 나스닥 선물과 지수를 중심으로 실시간 기술적 분석을 수행합니다.

## 🏗️ 시스템 아키텍처

### 데이터베이스 테이블 구조

#### 1. `technical_signals` 테이블
**목적**: 모든 기술적 분석 신호 저장
- **주요 컬럼**:
  - `symbol`: 심볼 (NQ=F, ^IXIC 등)
  - `signal_type`: 신호 타입 (MA200_breakout_up, RSI_overbought 등)
  - `timeframe`: 시간대 (1min, 15min, 1day)
  - `current_price`: 신호 발생 시점 가격
  - `indicator_value`: 관련 지표값 (MA값, RSI값 등)
  - `signal_strength`: 신호 강도 (돌파폭, 과매수 정도)
  - `alert_sent`: 텔레그램 알림 발송 여부

#### 2. `signal_outcomes` 테이블
**목적**: 신호 발생 후 결과 추적
- **주요 컬럼**:
  - `signal_id`: 원본 신호 ID (FK)
  - `price_1h_after`, `price_1d_after`, `price_1w_after`, `price_1m_after`: 시간대별 가격
  - `return_1h`, `return_1d`, `return_1w`, `return_1m`: 시간대별 수익률
  - `max_return`, `max_drawdown`: 최대 수익률, 최대 손실률
  - `is_successful_1h`, `is_successful_1d`, `is_successful_1w`: 성공 여부

#### 3. `signal_patterns` 테이블
**목적**: 여러 신호의 조합 패턴 분석
- **주요 컬럼**:
  - `pattern_name`: 패턴명 (RSI_overbought_then_BB_upper 등)
  - `pattern_type`: 패턴 유형 (sequential, concurrent, leading)
  - `first_signal_id` ~ `fifth_signal_id`: 패턴 구성 신호들
  - `confidence_score`: 패턴 신뢰도 점수 (0~100)

## 🔧 서비스 컴포넌트

### 1. TechnicalMonitorService
**역할**: 실시간 기술적 지표 모니터링 및 신호 감지

#### 주요 기능:
- **나스닥 선물 1분봉 모니터링** (`check_nasdaq_futures_1min`)
  - 20분, 50분 이동평균선 돌파/이탈
  - RSI 과매수/과매도 신호
  - 볼린저 밴드 터치/돌파
  - **용도**: 스캘핑, 초단타 매매

- **나스닥 선물 15분봉 모니터링** (`check_nasdaq_futures_15min`)
  - 20봉, 50봉 이동평균선 분석
  - **용도**: 단타매매, 스윙트레이딩

- **나스닥 지수 일봉 모니터링** (`check_nasdaq_index_daily`)
  - 50일, 200일 이동평균선 분석
  - 골든크로스/데드크로스 감지
  - **용도**: 중장기 투자 (가장 신뢰도 높음)

#### 신호 감지 로직:
1. 야후 파이낸스에서 가격 데이터 수집
2. 기술적 지표 계산 (이동평균, RSI, 볼린저 밴드)
3. 신호 감지 (돌파, 과매수/과매도 등)
4. 중복 알림 방지 체크
5. 데이터베이스에 신호 저장
6. 텔레그램 알림 발송
7. 알림 발송 상태 업데이트

### 2. TechnicalIndicatorService
**역할**: 기술적 지표 계산 엔진

#### 제공 지표:
- **이동평균선** (`calculate_moving_average`)
  - 20일, 50일, 200일 이동평균
  - 돌파 감지 (`detect_ma_breakout`)

- **RSI** (`calculate_rsi`)
  - 14일 기준 상대강도지수
  - 과매수(70 이상), 과매도(30 이하) 감지

- **볼린저 밴드** (`calculate_bollinger_bands`)
  - 20일 이동평균 ± 2 표준편차
  - 상단/하단 터치 및 돌파 감지

- **골든크로스/데드크로스** (`detect_cross_signals`)
  - 50일선과 200일선 교차 감지

### 3. SignalStorageService
**역할**: 신호 데이터베이스 저장 관리

#### 주요 기능:
- **신호 저장** (`save_signal`)
  - 중복 체크 (기본 60분 윈도우)
  - 신호 강도 계산
  - 시장 상황 판단

- **편의 함수들**:
  - `save_ma_breakout_signal`: 이동평균 돌파 신호
  - `save_rsi_signal`: RSI 신호
  - `save_bollinger_signal`: 볼린저 밴드 신호
  - `save_cross_signal`: 크로스 신호

### 4. OutcomeTrackingService
**역할**: 신호 발생 후 결과 추적 (Phase 2 핵심 기능)

#### 추적 프로세스:
1. **초기화** (`initialize_outcome_tracking`)
   - 신호 발생 시 빈 결과 레코드 생성

2. **업데이트** (`update_outcomes`)
   - 스케줄러가 1시간마다 실행
   - 경과 시간에 따라 해당 시간대 가격 수집
   - 수익률 계산 및 성공 여부 판정

3. **완료**
   - 1개월 후 모든 데이터 수집 완료

#### 수집 데이터:
- **시간대별 가격**: 1시간, 4시간, 1일, 1주일, 1개월 후
- **수익률**: 각 시간대별 수익률 (%)
- **극값**: 최대 수익률, 최대 손실률
- **성공 판정**: 신호 방향에 따른 성공/실패

### 5. PatternAnalysisService
**역할**: 신호 조합 패턴 발견 및 분석

#### 패턴 유형:
- **순차적 패턴**: A 신호 → B 신호 → C 신호
- **동시 패턴**: A 신호 + B 신호 (같은 시점)
- **선행 패턴**: A 신호 → (시간 간격) → B 신호

#### 주요 기능:
- `discover_patterns`: 자동 패턴 발견
- `analyze_pattern_performance`: 패턴 성과 분석
- `find_successful_patterns`: 성공적인 패턴 탐색

### 6. BacktestingService
**역할**: 과거 신호 성과 분석 및 매매 전략 검증

#### 분석 항목:
- **수익률 분석**: 평균, 최대, 최소 수익률
- **승률 분석**: 성공한 신호 비율
- **리스크 분석**: 최대 손실폭, 변동성
- **시장 상황별 분석**: 상승장/하락장 성과 차이

#### 주요 기능:
- `analyze_all_signals_performance`: 전체 신호 성과 분석
- `simulate_trading_strategy`: 매매 전략 시뮬레이션
- `evaluate_signal_quality`: 신호 품질 평가 (A~F 등급)

## ⚙️ Scheduler 시스템

### scheduler_runner.py 주요 작업들

#### 현재 활성화된 작업:
```python
# 🆕 Phase 2: 결과 추적 스케줄러 작업들
# 신호 결과 추적 업데이트 (1시간마다)
scheduler.add_job(run_outcome_tracking_update, "interval", hours=1)

# 최근 신호들 결과 추적 초기화 (6시간마다)
scheduler.add_job(initialize_recent_signals_tracking, "interval", hours=6)
```

#### 주석 처리된 작업들 (필요시 활성화 가능):
- **뉴스 크롤링**: Investing, Yahoo 뉴스 수집
- **가격 모니터링**: 실시간 가격 변화 감지
- **기술적 지표 모니터링**: 1분봉, 15분봉, 일봉 분석

#### 서버 시작시 즉시 실행:
1. **알림 테스트** (`test_technical_alerts`)
2. **결과 추적 초기화** (`initialize_recent_signals_tracking`)
3. **결과 추적 테스트** (`test_outcome_tracking`)

## 🔄 프로세스 흐름

### 1. 신호 감지 → 저장 → 알림 프로세스
```
1. TechnicalMonitorService가 주기적으로 실행
2. 야후 파이낸스에서 가격 데이터 수집
3. TechnicalIndicatorService로 지표 계산
4. 신호 감지 시:
   - SignalStorageService로 DB 저장
   - 텔레그램 알림 발송
   - 알림 상태 업데이트
```

### 2. 결과 추적 프로세스 (Phase 2)
```
1. 신호 저장 시 OutcomeTrackingService.initialize_outcome_tracking 호출
2. 빈 결과 레코드 생성 (signal_outcomes 테이블)
3. 스케줄러가 1시간마다 run_outcome_tracking_update 실행
4. 경과 시간에 따라 해당 시간대 가격 수집
5. 수익률 계산 및 성공 여부 판정
6. 1개월 후 추적 완료
```

### 3. 패턴 분석 프로세스
```
1. PatternAnalysisService.discover_patterns 실행
2. 기존 신호들에서 반복되는 조합 패턴 탐색
3. 패턴 저장 (signal_patterns 테이블)
4. 패턴별 성과 분석
5. 성공적인 패턴 식별
```

## 📊 데이터 활용 방안

### 1. 백테스팅
- 과거 신호들의 실제 성과 분석
- 신호별 승률, 평균 수익률 계산
- 최적 매매 타이밍 발견

### 2. 알림 최적화
- 성과가 좋은 신호만 알림 발송
- 신호 품질 기반 필터링
- 중복 알림 방지

### 3. 매매 전략 개발
- 효과적인 신호 조합 발견
- 리스크 관리 규칙 수립
- 자동 매매 알고리즘 개발

### 4. 성과 모니터링
- 실시간 신호 품질 추적
- 시장 상황별 성과 분석
- 전략 성과 대시보드

## 🔧 선행 요구사항

### 1. 데이터베이스
- PostgreSQL 또는 MySQL
- 테이블 생성: `technical_signals`, `signal_outcomes`, `signal_patterns`
- 인덱스 설정 (성능 최적화)

### 2. 외부 API
- **야후 파이낸스**: 가격 데이터 수집
- **텔레그램 봇**: 알림 발송

### 3. 환경 설정
- 데이터베이스 연결 정보
- 텔레그램 봇 토큰
- 심볼 및 지표 설정값

### 4. 의존성 패키지
```python
pandas  # 데이터 분석
numpy   # 수치 계산
sqlalchemy  # ORM
yfinance    # 야후 파이낸스 API
apscheduler # 스케줄러
```

## 🚀 실행 순서

### 1. 초기 설정
```bash
# 데이터베이스 테이블 생성
# 환경 변수 설정
# 의존성 패키지 설치
```

### 2. 스케줄러 시작
```python
# scheduler_runner.py 실행
python app/scheduler/scheduler_runner.py
```

### 3. 모니터링 활성화
```python
# 필요한 모니터링 작업 주석 해제
scheduler.add_job(run_technical_analysis_1min, "interval", minutes=1)
scheduler.add_job(run_technical_analysis_15min, "interval", minutes=15)
scheduler.add_job(run_technical_analysis_daily, "interval", hours=1)
```

### 4. 결과 확인
- 데이터베이스에서 신호 및 결과 확인
- 텔레그램 알림 수신 확인
- 백테스팅 결과 분석

## 📈 주요 신호 타입들

### 이동평균선 신호
- `MA20_breakout_up`: 20일선 상향 돌파
- `MA50_breakout_down`: 50일선 하향 이탈
- `MA200_breakout_up`: 200일선 상향 돌파 (매우 중요)

### RSI 신호
- `RSI_overbought`: RSI 70 이상 (과매수)
- `RSI_oversold`: RSI 30 이하 (과매도)
- `RSI_bullish`: RSI 50 상향 돌파
- `RSI_bearish`: RSI 50 하향 이탈

### 볼린저 밴드 신호
- `BB_touch_upper`: 상단 밴드 터치
- `BB_touch_lower`: 하단 밴드 터치
- `BB_break_upper`: 상단 밴드 돌파
- `BB_break_lower`: 하단 밴드 이탈

### 크로스 신호
- `golden_cross`: 골든크로스 (50일선이 200일선 상향 돌파)
- `dead_cross`: 데드크로스 (50일선이 200일선 하향 이탈)

## 🎯 성과 측정 지표

### 수익률 지표
- **시간대별 수익률**: 1시간, 1일, 1주일, 1개월 후
- **최대 수익률**: 추적 기간 중 최고점
- **최대 손실률**: 추적 기간 중 최저점

### 성공률 지표
- **1일 기준 성공률**: 신호 방향과 일치하는 비율
- **1주일 기준 성공률**: 중기 관점 성공률
- **1개월 기준 성공률**: 장기 관점 성공률

### 리스크 지표
- **변동성**: 가격 변동의 표준편차
- **최대 손실폭**: 최악의 시나리오 손실률
- **샤프 비율**: 위험 대비 수익률

## 💡 시스템 특징

### 장점
1. **완전 자동화**: 신호 감지부터 결과 추적까지 자동
2. **실시간 모니터링**: 1분봉부터 일봉까지 다양한 시간대
3. **성과 추적**: Phase 2를 통한 신호 품질 검증
4. **패턴 분석**: 복합 신호 조합의 효과 측정
5. **백테스팅**: 과거 데이터 기반 전략 검증

### 주의사항
1. **데이터 의존성**: 야후 파이낸스 API 장애 시 영향
2. **시장 변화**: 시장 상황 변화에 따른 신호 효과 변동
3. **과최적화**: 과거 데이터에만 맞춘 전략의 위험
4. **지연 시간**: 실시간 데이터와 약간의 지연 가능성

이 시스템은 완전한 기술적 분석 파이프라인을 제공하며, 신호 감지부터 성과 추적까지 전 과정을 자동화합니다. Phase 2의 결과 추적 기능을 통해 신호의 실제 효과를 측정하고, 이를 바탕으로 지속적인 개선이 가능합니다.