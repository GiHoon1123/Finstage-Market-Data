[Finstage Market Data] Python 성능 최적화 시리즈 (1/5) - 성능 문제 분석과 해결 방향

## 프로젝트 배경

Finstage Market Data라는 AI 기반 실시간 투자 신호 서비스를 개발하게 되었다. 이 서비스는 24시간 자동으로 시장을 모니터링하여 차트 지표분석, 시장 상황 분석, 뉴스 크롤링, 백테스팅으로 검증된 투자 신호 등을 텔레그램으로 실시간 제공하는 기능을 가진다.

서비스는 여러 개의 도메인으로 구성되어 있었으며, 이 글에서는 그 중 핵심 기능들의 성능 개선 과정을 공유하려 한다.

주요 기능들은 다음과 같다:

- **실시간 데이터 수집**: Yahoo Finance, Investing.com에서 시장 데이터 수집
- **기술적 분석**: 20+ 기술적 분석 전략을 통한 투자 신호 생성
- **뉴스 크롤링**: 경제 뉴스 및 종목별 뉴스 자동 수집
- **백테스팅**: 10년치 과거 데이터 기반 전략 검증
- **실시간 알림**: 텔레그램을 통한 즉시 신호 전송

어느정도 개발하고 다시 돌아보니, 특정 설계와 구현 방식으로 인해 외부 API 의존성, 리소스 관리 측면에서 성능 저하나 장애 발생 가능성이 존재할 수 있다는 점을 인지하게 되었다. 실제 모니터링 결과, 스케줄러 작업이 50초 이상 걸리는 구간이 빈번했고, API 평균 응답시간이 1.2초를 넘는 경우가 전체 요청의 30% 이상을 차지했다.

베타 테스트 중이지만, 이 상태에서 서비스를 오픈한다면 사용자들이 투자 신호를 받기까지 과도한 대기 시간을 경험하게 되고, 실시간성이 생명인 투자 서비스의 신뢰도가 크게 떨어질 것이라는 우려가 컸다.

특히 이 시스템은 단발성 개발이 아니기 때문에,단순 구현을 넘어 성능과 안정성, 사용자 경험을 고려한 개선이 필수적이라고 판단했다.

해당 서비스가 큰 수익을 발생시키지 않기 때문에 인프라를 도입하는 것 보다는 프레임워크 수준에서 적용 가능한 최적화 기법들을 중심으로 개선을 시도했으며, 그만큼 구조적 설계와 리소스 사용 최적화에 집중하게 되었다.

## 잠재적인 문제점 분석

### 1. 스케줄러 작업 순차 처리로 인한 지연

**문제 상황**

기존 스케줄러는 모든 심볼을 순차적으로 처리하고 있었다. 각 심볼마다 5초의 지연을 두고 처리하다 보니 전체 작업 시간이 매우 길어졌다.

```python
# 기존: 순차 처리 방식
def run_news_crawling_job():
    symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]  # 5개 심볼

    for symbol in symbols:
        try:
            crawler = NewsCrawler(symbol)
            result = crawler.process_all()
            print(f"✅ {symbol} 처리 완료")
        except Exception as e:
            print(f"❌ {symbol} 처리 실패: {e}")

        time.sleep(5.0)  # 5초 대기

    # 총 소요 시간: 5개 심볼 × (처리시간 + 5초) = 약 50초
```

**발생 가능성 있는 문제점**

- 전체 작업 시간: 약 50초 (심볼 수 × 처리시간)
- CPU 유휴 시간: 대부분의 시간을 대기로 소모
- 확장성 제약: 심볼이 늘어날수록 선형적으로 시간 증가

**실제 서비스 영향**: 뉴스 크롤링이 50초씩 걸리면 중요한 시장 뉴스가 발생해도 사용자에게 전달되기까지 최대 1분의 지연이 발생한다. 급변하는 시장 상황에서 이런 지연은 투자 기회를 놓치게 만들어 서비스 신뢰도를 크게 떨어뜨린다.

### 2. 데이터베이스 연결 관리 비효율

**문제 상황**

기본적인 SQLAlchemy 설정만 사용하여 연결 풀링이 최적화되지 않았다.

```python
# 기존: 기본 설정
from sqlalchemy import create_engine

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# 매 요청마다 새로운 연결 생성/해제 반복
def get_data():
    session = SessionLocal()
    try:
        result = session.query(Model).all()
        return result
    finally:
        session.close()
```

**발생 가능성 있는 문제점**

- 연결 생성/해제 오버헤드
- 동시 요청 시 연결 부족
- 연결 끊김 시 자동 복구 기능 없음
- QueuePool limit 오류 발생 가능성

**실제 서비스 영향**: 사용자가 많아지면 "Database connection pool exhausted" 오류가 발생하여 서비스가 완전히 중단된다. 특히 시장 개장 시간대처럼 동시 접속이 몰리는 상황에서는 아예 데이터를 조회할 수 없게 되어 서비스 장애로 이어진다.

### 3. 세션 관리 일관성 부족

**문제 상황**

각 서비스마다 세션을 직접 생성하고 관리하는 방식이 달랐다.

```python
# 기존: 일관성 없는 세션 관리
class PriceService:
    def get_price(self, symbol):
        session = SessionLocal()  # 직접 생성
        try:
            # 작업 수행
            return result
        except Exception as e:
            # 에러 처리 방식이 제각각
            session.rollback()
            raise e
        finally:
            session.close()

class NewsService:
    def get_news(self, symbol):
        session = SessionLocal()  # 또 다른 방식
        # 세션 정리 로직이 다름
        result = session.query(...).all()
        session.close()
        return result
```

**발생 가능성 있는 문제점**

- 세션 누수 가능성
- 트랜잭션 관리 불일치
- 에러 처리 방식 상이

**실제 서비스 영향**: 세션 누수가 발생하면 시간이 지날수록 메모리 사용량이 계속 증가하여 결국 서버가 다운된다. 또한 트랜잭션 관리가 일관되지 않으면 데이터 정합성 문제가 발생하여 잘못된 투자 신호가 전송될 수 있다.

### 4. 캐시 시스템 부재로 인한 중복 계산

**문제 상황**

기술적 분석 서비스에서 동일한 계산을 반복 수행하고 있었다.

```python
# 기존: 매번 새로 계산
class TechnicalIndicatorService:
    def calculate_moving_average(self, symbol, period):
        # 매번 전체 데이터를 다시 계산
        prices = self.get_price_data(symbol)
        ma = prices.rolling(window=period).mean()
        return ma

    def calculate_rsi(self, symbol, period=14):
        # 또 다시 전체 계산
        prices = self.get_price_data(symbol)
        # RSI 계산 로직...
        return rsi
```

**발생 가능성 있는 문제점**

- 동일한 데이터에 대한 반복 계산
- CPU 자원 낭비
- 응답 시간 지연

**실제 서비스 영향**: 같은 기술적 지표를 여러 번 계산하느라 API 응답이 3-5초씩 걸리게 된다. 사용자가 차트를 확인하거나 신호를 조회할 때마다 답답한 로딩 시간을 경험하게 되어 서비스 이탈률이 높아진다.

### 5. API 호출 최적화 부재

**문제 상황**

외부 API 호출 시 고정된 지연시간과 재시도 로직 부재로 비효율이 발생했다.

```python
# 기존: 고정 지연 및 단순 에러 처리
def get_current_price(symbol):
    try:
        response = requests.get(f"https://api.example.com/price/{symbol}")
        time.sleep(0.5)  # 고정 지연
        return response.json()
    except Exception as e:
        print(f"API 호출 실패: {e}")
        return None
```

**발생 가능성 있는 문제점**

- API 응답 시간: 평균 1.2초
- 실패 시 재시도 없음
- 고정 지연으로 인한 비효율

**실제 서비스 영향**: 외부 API 호출이 실패하면 해당 종목의 데이터가 아예 업데이트되지 않아 사용자가 오래된 정보를 보게 된다. 특히 변동성이 큰 시장에서는 잘못된 투자 판단으로 이어질 수 있어 서비스 신뢰성에 치명적이다.

### 6. 메모리 관리 시스템 부재

**문제 상황**

메모리 사용량 모니터링이나 최적화 시스템이 구축되어 있지 않았다.

```python
# 기존: 메모리 관리 없음
def process_large_dataset():
    # 대용량 DataFrame 처리
    df = pd.read_csv("large_file.csv")  # 100MB+

    # 메모리 사용량 체크 없음
    result = df.groupby('symbol').apply(complex_calculation)

    # 메모리 정리 없음
    return result
```

**발생 가능성 있는 문제점**

- 시스템 메모리 사용률: 85% 이상
- 가비지 컬렉션 빈발
- 메모리 누수 위험

**실제 서비스 영향**: 메모리 사용률이 85%를 넘으면 시스템 전체가 느려지고, 최악의 경우 OOM(Out of Memory) 오류로 서버가 강제 종료된다. 이는 모든 사용자가 동시에 서비스를 이용할 수 없게 되는 전면 장애 상황을 초래한다.

### 7. 동기 처리로 인한 병목

**문제 상황**

모든 작업이 동기식으로 처리되어 I/O 대기 시간이 길었다.

```python
# 기존: 동기 처리
def analyze_multiple_symbols(symbols):
    results = []
    for symbol in symbols:
        # 각 심볼을 순차적으로 처리
        data = fetch_data(symbol)      # I/O 대기
        analysis = analyze_data(data)   # CPU 작업
        results.append(analysis)
    return results
```

**발생 가능성 있는 문제점**

- I/O 대기로 인한 CPU 유휴
- 전체 처리 시간 증가
- 동시성 활용 부족

**실제 서비스 영향**: 여러 종목을 동시에 분석해야 하는 상황에서 순차 처리로 인해 전체 분석 시간이 10분 이상 걸린다. 사용자가 포트폴리오 분석을 요청했을 때 결과를 받기까지 너무 오래 기다려야 해서 서비스 만족도가 크게 떨어진다.

### 8. 모니터링 시스템 부재

**문제 상황**

성능 지표나 시스템 상태를 실시간으로 추적할 수 있는 시스템이 없었다.

```python
# 기존: 모니터링 없음
def critical_task():
    # 중요한 작업이지만 성능 측정 없음
    start_time = time.time()

    # 작업 수행
    result = perform_task()

    # 단순 print로만 확인
    print(f"작업 완료: {time.time() - start_time}초")
    return result
```

**발생 가능성 있는 문제점**

- 성능 병목 지점 파악 어려움
- 시스템 상태 가시성 부족
- 사후 대응 위주 운영

**실제 서비스 영향**: 시스템에 문제가 발생해도 어디서 병목이 생겼는지 알 수 없어 복구 시간이 길어진다. 사용자들은 서비스가 느려지거나 중단되는 이유를 모른 채 불편을 겪게 되고, 운영진은 문제 원인을 찾느라 골든타임을 놓치게 된다.

## 문제점 종합 분석

이러한 문제들을 종합해보면, 단순히 기능 구현에만 집중하다 보니 시스템의 안정성과 확장성을 간과했다는 것을 알 수 있다. 특히 다음과 같은 구조적인 한계가 드러났다:

### 외부 의존성 과다

- API 호출 시 병목 가능성
- 네트워크 지연에 따른 성능 변동

### 시스템 리소스 관리 부재

- 메모리, CPU 사용에 대한 제어 부족
- 리소스 고갈 시 대응 방안 없음

### 확장성 고려 부족

- 사용자 증가에 따른 선형적 병목
- 동시성 처리 능력 제한

### 사용자 경험 간과

- 응답 지연과 불안정성으로 인한 만족도 저하
- 실시간성 요구사항 미충족

## 해결 방향 설정

이러한 문제점들이 실제 서비스 장애로 이어지기 전에 선제적으로 해결하기 위해, 체계적인 성능 최적화 전략을 수립했다. 단계별로 접근하여 안정성을 확보하면서도 성능을 극대화하는 것이 목표였다:

### Phase 1: 기반 시스템 최적화

- **데이터베이스 연결 풀링 최적화**: 안정적인 DB 연결 확보
- **스케줄러 작업 병렬화**: ThreadPoolExecutor를 활용한 동시 처리
- **세션 관리 개선**: 컨텍스트 매니저 기반 일관된 세션 관리

### Phase 2: 성능 향상

- **API 호출 최적화**: 적응형 재시도 로직 및 연결 풀링
- **기술적 지표 계산 최적화**: 결과 캐싱 및 알고리즘 개선
- **배치 처리 도입**: 대량 데이터 효율적 처리
- **캐시 레이어 추상화**: 통합 캐시 매니저 구축

### Phase 3: 고급 시스템 구축

- **비동기 처리 시스템**: AsyncIO 기반 동시성 향상
- **WebSocket 실시간 스트리밍**: 실시간 데이터 전송
- **분산 작업 큐 시스템**: 백그라운드 작업 처리
- **성능 모니터링 시스템**: 실시간 성능 추적 및 자동 튜닝

### 추가 개선 영역

- **메모리 관리 시스템**: LRU 캐시 및 자동 최적화
- **데이터베이스 최적화**: 쿼리 성능 및 인덱스 최적화
- **모니터링 및 관찰성**: Prometheus 메트릭 및 알림 시스템
- **개발 생산성**: 로깅, 에러 처리, 환경 설정 표준화

## 예상 성과 목표

이러한 최적화를 통해 다음과 같은 성과를 목표로 설정했다:

| 항목               | 현재 상태 | 목표      | 개선율     | 측정 근거                         |
| ------------------ | --------- | --------- | ---------- | --------------------------------- |
| 스케줄러 처리 시간 | 50초      | 10초      | 80% 단축   | 실제 로그 기준 5개 심볼 처리 시간 |
| API 응답 시간      | 1.2초     | 0.3초     | 75% 단축   | FastAPI 응답 시간 메트릭 평균값   |
| CPU 사용률         | 85%       | 40%       | 53% 감소   | htop 모니터링 피크 시간대 기준    |
| 메모리 사용량      | 1.2GB     | 0.8GB     | 33% 감소   | 프로세스 RSS 메모리 사용량        |
| 동시 요청 처리     | 50 req/s  | 200 req/s | 300% 증가  | 부하 테스트 도구 측정 결과        |
| 시스템 가용성      | 95.2%     | 99.9%     | 4.7%p 향상 | 월간 다운타임 기준 계산           |

_현재 상태는 1주일간 모니터링한 실제 데이터를 기반으로 하며, 목표치는 업계 표준과 서비스 요구사항을 고려하여 설정했다._

## 다음 단계

이제 문제점 분석이 완료되었으니, 다음 포스트에서는 실제 해결 과정을 단계별로 살펴보겠다. Phase 1에서는 가장 기본이 되는 데이터베이스 연결 풀링 최적화, 스케줄러 병렬화, 세션 관리 개선을 통해 어떻게 처리 시간을 80% 단축시켰는지 구체적인 구현 방법과 실제 코드를 공유할 예정이다.

## 시리즈 목록

- [1편: 성능 문제 분석과 해결 방향](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-15-%EC%84%B1%EB%8A%A5-%EB%AC%B8%EC%A0%9C-%EB%B6%84%EC%84%9D%EA%B3%BC-%ED%95%B4%EA%B2%B0-%EB%B0%A9%ED%96%A5) ← 현재 글
- [2편: 기반 시스템 최적화 (Phase 1)](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-25-%EA%B8%B0%EB%B0%98-%EC%8B%9C%EC%8A%A4%ED%85%9C-%EC%B5%9C%EC%A0%81%ED%99%94-Phase-1)
- [3편: 성능 향상 (Phase 2)](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-35-%EC%84%B1%EB%8A%A5-%ED%8F%AD%EB%B0%9C%EC%A0%81-%ED%96%A5%EC%83%81-Phase-2)
- [4편: 고급 시스템 구축 (Phase 3)](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-45-%EA%B3%A0%EA%B8%89-%EC%8B%9C%EC%8A%A4%ED%85%9C-%EA%B5%AC%EC%B6%95-Phase-3)
- [5편: 메모리 관리 및 최종 성과](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-55-%EB%A9%94%EB%AA%A8%EB%A6%AC-%EA%B4%80%EB%A6%AC-%EB%B0%8F-%EC%B5%9C%EC%A2%85-%EC%84%B1%EA%B3%BC)
