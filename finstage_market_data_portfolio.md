# Finstage Market Data API - 포트폴리오

## 1. 서비스 소개

Finstage Market Data API는 Finstage 통합 금융 플랫폼의 핵심 백엔드 서비스로, "자신이 잘 아는 분야에만 투자하라"는 철학을 기술적으로 구현한 지능형 금융 데이터 분석 시스템입니다.

단순한 시장 데이터 제공을 넘어서, AI 기반 신호 품질 평가, 매매 전략 백테스팅, 고급 패턴 인식을 통해 투자자가 신뢰할 수 있는 투자 판단 근거를 제공합니다. 특히 산업군 중심의 통합적 분석과 실시간 검증된 알림 시스템을 통해 기존 금융 서비스와 차별화된 가치를 제공합니다.

Python과 FastAPI를 기반으로 개발된 이 서비스는 다음과 같은 핵심 기능을 제공합니다:

1. **AI 기반 신호 품질 평가**: 10년 데이터 기반 A~F 등급 신호 신뢰도 검증
2. **매매 전략 백테스팅**: 실제 매매 시뮬레이션을 통한 정확한 수익률 예측
3. **고급 패턴 인식 시스템**: 머신러닝 기반 차트 패턴 자동 발견 및 분석
4. **산업군 중심 뉴스 통합**: 특정 산업에 특화된 시황 정보 수집 및 분석
5. **실시간 검증된 알림**: 성과가 입증된 신호만 선별하여 텔레그램으로 전송
6. **신호 결과 추적 시스템**: 모든 신호의 실제 결과를 추적하여 시스템 자체 학습

## 2. 기술 스택

### 백엔드

| 카테고리         | 기술                                    |
| ---------------- | --------------------------------------- |
| **언어**         | Python 3.12                             |
| **프레임워크**   | FastAPI                                 |
| **데이터베이스** | MySQL 8.0, SQLAlchemy 2.0 ORM           |
| **비동기 처리**  | asyncio, aiohttp                        |
| **병렬 처리**    | concurrent.futures (ThreadPoolExecutor) |
| **스케줄링**     | APScheduler 3.11                        |

### 데이터 처리 및 AI

| 카테고리        | 기술                                  |
| --------------- | ------------------------------------- |
| **데이터 분석** | Pandas 2.2, NumPy 2.2                 |
| **머신러닝**    | K-means 클러스터링, 코사인 유사도 분석 |
| **통계 분석**   | 시계열 분석, 상관관계 분석, 백테스팅   |
| **패턴 인식**   | Dynamic Time Warping, 패턴 매칭       |
| **외부 API**    | Yahoo Finance API (yfinance)          |
| **크롤링**      | BeautifulSoup4, requests              |

### 인프라 및 도구

| 카테고리        | 기술                                    |
| --------------- | --------------------------------------- |
| **알림 시스템** | Telegram Bot API                        |
| **캐싱**        | 메모리 캐시, Redis 지원 추상화 레이어   |
| **모니터링**    | 자체 개발 성능 모니터링 시스템 (psutil) |
| **개발 환경**   | macOS, VSCode, Git                      |
| **배포**        | Docker, AWS EC2                         |

## 3. 주요 기능 상세 설명

### AI 기반 신호 품질 평가 시스템

기존 금융 서비스들이 단순히 기술적 지표만 제공하는 것과 달리, 본 시스템은 10년간의 과거 데이터를 기반으로 각 신호의 신뢰도를 수학적으로 정량화하여 A~F 등급으로 평가합니다.

#### 신호 품질 평가 알고리즘

신호 품질 점수는 다음 5가지 요소를 종합하여 0~100점으로 계산됩니다:

- **승률 (20점)**: 해당 신호의 성공 확률
- **평균 수익률 (20점)**: 신호 발생 후 평균 수익률
- **리스크 지표 (30점)**: 최대 손실률, 변동성, 샤프 비율
- **샘플 크기 (10점)**: 통계적 신뢰도를 위한 충분한 데이터 확보
- **시장 적응성 (20점)**: 다양한 시장 상황에서의 일관된 성과

#### 등급별 분류 기준

- **A등급 (80점 이상)**: 승률 70% 이상, 평균 수익률 3% 이상의 우수한 신호
- **B등급 (70-79점)**: 승률 60% 이상의 안정적인 수익 신호
- **C등급 (60-69점)**: 다른 지표와 함께 사용 권장
- **D등급 이하**: 성과가 검증되지 않아 사용 비권장

#### 다차원 성과 분석

- **시간대별 성과 추적**: 신호 발생 후 1시간, 1일, 1주일, 1개월 후의 실제 결과를 자동으로 추적하여 시간대별 효과성 분석
- **시장 상황별 분석**: 상승장, 하락장, 횡보장 등 다양한 시장 환경에서의 신호 성과 비교 분석
- **계절성 패턴 분석**: 월별, 요일별, 시간대별 신호 발생 빈도 및 성공률 패턴 식별

#### 실제 활용 사례

```
MA200_breakout_up (200일선 상향 돌파) 신호 분석:
- 등급: A (85점)
- 승률: 73.2% (158건 중 116건 성공)
- 평균 수익률: +3.8%
- 최대 손실: -2.1%
- 권장사항: 적극 활용 권장
```

### 매매 전략 백테스팅 엔진

투자자의 핵심 질문인 "이 전략으로 실제 매매했다면 얼마나 벌었을까?"에 대한 정확한 답을 제공하는 시뮬레이션 시스템입니다.

#### 실전 매매 시뮬레이션

- **다중 신호 조합 전략**: 여러 기술적 지표를 조합한 복합 전략의 효과성 검증
- **리스크 관리 시스템**: 손절매(-5%), 익절매(+10%) 등 리스크 관리 규칙 적용
- **포지션 관리**: 자본금 대비 투자 비율 조절을 통한 안전한 자금 관리
- **거래 비용 반영**: 수수료, 슬리피지 등 실제 거래 비용을 고려한 정확한 수익률 계산

#### 정교한 성과 지표 분석

```
백테스팅 결과 예시:
총 거래 수: 47건
승률: 68.1%
총 수익률: +23.7%
최대 손실(MDD): -8.3%
샤프 비율: 1.84
수익 팩터: 2.31
평균 보유 기간: 3.2일
```

#### 전략 최적화 기능

- **파라미터 최적화**: 그리드 서치를 통한 최적의 손절매/익절매 비율 탐색
- **신호 조합 분석**: 다양한 신호 조합의 시너지 효과 검증
- **시기별 성과 분석**: 특정 시장 상황이나 기간에서 유효한 전략 식별
- **리스크 조정 수익률**: 변동성을 고려한 위험 조정 성과 측정

### 고급 패턴 인식 시스템

머신러닝과 통계 기법을 활용하여 사람이 놓치기 쉬운 숨겨진 차트 패턴을 자동으로 발견하고 분석하는 시스템입니다.

#### 패턴 유사도 분석

- **코사인 유사도 분석**: 차트 패턴 간의 수학적 유사성을 정량적으로 계산
- **유클리드 거리 측정**: 패턴의 구조적 차이점을 기하학적으로 분석
- **Dynamic Time Warping**: 시간축 변형을 고려한 정교한 패턴 매칭 알고리즘

#### K-means 클러스터링 기반 패턴 그룹화

```
패턴 클러스터링 분석 결과:
클러스터 1: "상승 돌파형" (23개 패턴, 평균 수익률 +4.2%)
클러스터 2: "횡보 이탈형" (18개 패턴, 평균 수익률 +1.8%)
클러스터 3: "반등형" (31개 패턴, 평균 수익률 +2.9%)
```

#### 시계열 패턴 분석

- **시간대별 패턴 발견**: 특정 시간대에 집중적으로 발생하는 패턴 식별 (예: 화요일 오전 10시 골든크로스 패턴 다발 발생)
- **계절성 분석**: 월별, 분기별 패턴 성공률 변화 추적 (예: 12월 200일선 돌파 신호 성공률 85%)
- **주기성 발견**: 특정 패턴의 반복 주기 및 재현 가능성 분석

### 산업군 중심 뉴스 통합 시스템

개별 종목이 아닌 산업 전체의 맥락에서 투자 기회를 발견하는 차별화된 접근 방식을 제공합니다.

#### 지능형 뉴스 수집 및 분류

- **다중 소스 크롤링**: Yahoo Finance, Investing.com 등 다양한 소스에서 뉴스 자동 수집
- **산업군 자동 분류**: 반도체, 블록체인, 바이오 등 사용자 관심 분야별 카테고리 정리
- **관련성 점수 분석**: AI 기반 뉴스-종목 연관도 분석으로 중요도 순 정렬
- **자동 번역 및 요약**: 영문 뉴스의 한글 번역 및 핵심 내용 추출

#### 맥락적 분석 및 인사이트 제공

```
반도체 산업 종합 분석 예시:
긍정 뉴스: 67% (AI 칩 수요 증가, 정부 지원책)
부정 뉴스: 23% (중국 규제, 공급망 이슈)  
중립 뉴스: 10%
핫 키워드: "AI 반도체", "파운드리", "메모리"
```

### 실시간 검증된 알림 시스템

성과가 입증된 신호만 선별하여 전송하는 지능형 알림 시스템으로, 투자자가 중요한 시장 기회를 놓치지 않도록 지원합니다.

#### 선별적 알림 전송

- **품질 필터링**: A~B 등급 신호만 알림 발송하여 노이즈 최소화
- **성공률 기반 선별**: 승률 60% 이상 검증된 신호만 선택적 전송
- **사용자 맞춤화**: 관심 산업군 및 투자 성향별 개인화된 알림 설정

#### 다양한 알림 타입 지원

```
MA200 상향 돌파 알림 예시:
종목: NVDA (엔비디아)
현재가: $892.50 (+2.3%)
200일선: $875.20
신호 등급: A (승률 78%)
예상 목표가: $950 (+6.4%)
```

#### 시간대 최적화 및 스케줄링

- **한국 시간 자동 변환**: UTC 시간을 KST로 자동 변환하여 사용자 편의성 향상
- **시장 시간 고려**: 개장/폐장 시간에 맞춘 알림 스케줄링으로 적절한 타이밍 보장
- **중요도별 분류**: 긴급/일반/참고용 알림을 구분하여 우선순위 관리

### 신호 결과 추적 및 학습 시스템

모든 신호의 실제 결과를 추적하여 시스템이 스스로 성능을 개선하는 자기 학습 메커니즘을 구현했습니다.

#### 자동 결과 추적

- **실시간 모니터링**: 신호 발생 후 1시간, 1일, 1주일 후 결과를 자동으로 수집
- **성공률 실시간 업데이트**: 신호별 성공률 통계를 실시간으로 갱신
- **패턴 학습**: 성공한 신호들의 공통점을 자동으로 분석하여 패턴 발견

#### 지속적 시스템 개선

```
신호 학습 및 개선 결과:
- RSI_oversold 신호: 성공률 65% → 71% (필터링 조건 개선)
- MA_golden_cross: 거래량 조건 추가로 성공률 +8% 향상
- 볼린저 밴드: 변동성 높은 구간에서 성능 저하 확인 및 조건 수정
```

---

## 🏛️ 시스템 아키텍처

```
📊 외부 데이터 소스 (Yahoo Finance, Investing.com)
        ↓
🔄 데이터 수집 & 전처리 레이어
        ↓
🧠 AI 분석 엔진 (패턴 인식, 신호 생성)
        ↓
⚖️ 신호 품질 평가 시스템 (A~F 등급)
        ↓
🎯 백테스팅 & 검증 엔진
        ↓
📱 실시간 알림 시스템     📊 API 서비스
        ↓                    ↓
👥 사용자 알림          🖥️ 프론트엔드
```

### 핵심 모듈 구조

#### 🧠 AI 분석 모듈
- **패턴 인식 엔진**: 차트 패턴 자동 탐지
- **신호 생성기**: 기술적 지표 기반 매매 신호 생성
- **품질 평가기**: 신호 신뢰도 A~F 등급 평가

#### 🔍 백테스팅 모듈
- **전략 시뮬레이터**: 과거 데이터 기반 매매 시뮬레이션
- **성과 분석기**: 수익률, 리스크, 승률 등 정교한 분석
- **최적화 엔진**: 파라미터 튜닝 및 전략 개선

#### 📡 실시간 처리 모듈
- **데이터 스트리밍**: 실시간 시장 데이터 수집
- **신호 필터링**: 품질 기준 통과 신호만 선별
- **알림 전송**: 텔레그램 기반 즉시 알림

---

## 📈 비즈니스 임팩트

### 🎯 사용자 가치 제공

#### 투자 의사결정 지원
- **신뢰도 높은 신호**: A등급 신호 평균 승률 75% 이상
- **리스크 관리**: 최대 손실 예측으로 안전한 투자
- **시간 절약**: 수동 분석 시간 90% 단축

#### 투자 성과 개선
```
백테스팅 검증 결과:
- 기존 무작위 투자 대비 +18.3% 초과 수익
- 최대 손실 -15.2% → -8.7%로 위험 46% 감소
- 승률 52% → 68%로 16%p 향상
```

### 🏢 Finstage 플랫폼 내 역할

#### 핵심 데이터 허브
- **프론트엔드 지원**: 차트, 지표, 뉴스 데이터 실시간 제공
- **AI 모델 지원**: 주가 예측 모델용 전처리된 데이터 공급
- **모의투자 연동**: 실시간 시장 데이터 및 신호 제공

#### 사용자 경험 향상
- **개인화 서비스**: 사용자별 관심 산업군 맞춤 정보
- **학습 지원**: 투자 교육용 백테스팅 도구 제공
- **커뮤니티 기능**: 신호 공유 및 토론 플랫폼 지원

---

## 🔧 기술적 혁신 포인트

### 1. 🎯 신호 품질 정량화
기존 금융 서비스들이 단순히 기술적 지표만 제공하는 것과 달리, **수학적 모델로 신호의 신뢰도를 정량화**하여 투자자가 객관적으로 판단할 수 있도록 지원

### 2. 🔄 자기 학습 시스템
모든 신호의 실제 결과를 추적하여 **시스템이 스스로 성능을 개선**하는 피드백 루프 구현

### 3. 🧠 산업군 통합 분석
개별 종목 분석을 넘어서 **산업 전체의 맥락에서 투자 기회를 발견**하는 차별화된 접근

### 4. ⚡ 실시간 검증 시스템
신호 발생과 동시에 **과거 유사 상황의 성과를 즉시 제시**하여 투자 확신도 제고

---

## 🚀 성능 최적화 핵심 성과

대용량 금융 데이터 처리와 실시간 서비스 제공을 위한 **3단계 성능 최적화**를 통해 안정적이고 빠른 서비스 구현

### 📊 주요 개선 결과
| 항목 | 개선 전 | 개선 후 | 개선율 |
|------|---------|---------|--------|
| **API 응답 시간** | 1.2초 | 0.3초 | **75% 단축** |
| **동시 처리량** | 50 req/s | 200 req/s | **300% 증가** |
| **스케줄러 처리** | 50초 | 10초 | **80% 단축** |
| **메모리 사용량** | 1.2GB | 0.8GB | **33% 감소** |

### 🔧 핵심 최적화 기법
- **병렬 처리**: ThreadPoolExecutor 활용한 다중 심볼 동시 처리
- **지능형 캐싱**: 반복 계산 95% 감소로 CPU 사용량 대폭 절약
- **비동기 API**: aiohttp 기반 비동기 처리로 I/O 대기 시간 최소화
- **데이터베이스 최적화**: 연결 풀링 및 배치 처리로 DB 부하 60% 감소

---

## 🎯 프로젝트 특징 및 차별점

### 💡 기술적 혁신
1. **AI 기반 신호 검증**: 머신러닝으로 신호 품질 자동 평가
2. **실전 백테스팅**: 실제 매매와 동일한 조건의 정확한 시뮬레이션  
3. **패턴 자동 발견**: 사람이 놓치는 숨겨진 차트 패턴 AI 탐지
4. **자기 학습 시스템**: 결과 추적을 통한 지속적 성능 개선

### 🎯 비즈니스 가치
1. **투자 성공률 향상**: 검증된 신호로 승률 68% 달성
2. **리스크 관리**: 최대 손실 예측으로 안전한 투자 지원
3. **시간 효율성**: 수동 분석 시간 90% 단축
4. **개인화 서비스**: 사용자별 맞춤 투자 정보 제공

### 🚀 확장성
1. **모듈식 설계**: 새로운 지표, 데이터 소스 쉽게 추가 가능
2. **마이크로서비스 준비**: 기능별 독립적 확장 가능한 구조
3. **다중 시장 지원**: 국내외 다양한 금융 시장 확장 가능
4. **AI 모델 통합**: 딥러닝 예측 모델 쉽게 연동 가능

---

## 🏆 결론

**Finstage Market Data API**는 단순한 데이터 제공 서비스를 넘어서, **AI 기반 신호 검증**, **실전 백테스팅**, **지능형 패턴 인식**을 통해 투자자에게 **신뢰할 수 있는 투자 판단 근거**를 제공하는 혁신적인 금융 기술 플랫폼입니다.

특히 **"신호 품질 A~F 등급 평가"**와 **"매매 전략 백테스팅"** 기능을 통해 투자자가 객관적이고 과학적인 근거를 바탕으로 투자 결정을 내릴 수 있도록 지원하며, 이는 기존 금융 서비스와의 명확한 차별점을 제공합니다.

Python과 FastAPI 기반의 **고성능 아키텍처**와 **지속적인 성능 최적화**를 통해 실제 프로덕션 환경에서 안정적으로 운영되는 **실전형 금융 기술 솔루션**입니다.