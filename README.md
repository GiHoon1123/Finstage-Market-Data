# Finstage Market Data API

Finstage 통합 금융 플랫폼의 핵심 백엔드 서비스로, AI 기반 신호 품질 평가, 매매 전략 백테스팅, 실시간 알림을 통해 투자자에게 신뢰할 수 있는 투자 판단 근거를 제공합니다.

## 주요 기능

- **AI 기반 신호 품질 평가**: 10년 데이터 기반 A~F 등급 신호 신뢰도 검증
- **매매 전략 백테스팅**: 실제 매매 시뮬레이션을 통한 정확한 수익률 예측
- **고급 패턴 인식**: 머신러닝 기반 차트 패턴 자동 발견 및 분석
- **실시간 검증된 알림**: 텔레그램을 통한 성과 입증 신호 선별 전송
- **산업군 중심 뉴스 수집**: 특정 산업에 특화된 시황 정보 자동 수집
- **신호 결과 추적**: 모든 신호의 실제 결과 추적 및 시스템 자체 학습

## 기술 스택

| 카테고리 | 기술 |
|---------|------|
| **언어 & 프레임워크** | Python 3.12, FastAPI |
| **데이터베이스** | MySQL 8.0, SQLAlchemy 2.0 ORM |
| **데이터 분석** | Pandas 2.2, NumPy 2.2 |
| **머신러닝** | K-means 클러스터링, 코사인 유사도 분석 |
| **비동기 처리** | asyncio, aiohttp, concurrent.futures |
| **스케줄링** | APScheduler 3.11 |
| **외부 API** | Yahoo Finance API (yfinance) |
| **알림 시스템** | Telegram Bot API |
| **배포** | Docker, AWS EC2 |

## 설치 및 실행 (macOS 환경)

### 사전 요구사항

- Python 3.12+
- MySQL 8.0+
- Git

### 1. 저장소 클론

```bash
git clone https://github.com/your-username/Finstage-Market-Data.git
cd Finstage-Market-Data
```

### 2. Python 가상환경 설정

```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 가상환경 비활성화 (필요시)
# deactivate
```

### 3. 의존성 설치

```bash
# 패키지 설치
pip install -r requirements.txt

# 개발 의존성 설치 (선택사항)
pip install -r requirements-dev.txt
```

### 4. 환경 변수 설정

```bash
# 환경 변수 파일 복사
cp .env.example .env

# .env 파일 편집
nano .env
```

`.env` 파일 설정 예시:
```env
# 데이터베이스 설정
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=finstage_market_data

# 텔레그램 봇 설정
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Yahoo Finance API 설정
YFINANCE_DELAY=0.5
```

### 5. 데이터베이스 설정

```bash
# MySQL 서버 시작 (Homebrew 설치 시)
brew services start mysql

# 데이터베이스 생성
mysql -u root -p
CREATE DATABASE finstage_market_data;
```

### 6. 서버 실행

```bash
# 개발 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 또는 스크립트 실행
python -m app.main
```

### 7. API 문서 확인

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 프로젝트 구조

```
app/
├── main.py                     # FastAPI 애플리케이션 진입점
├── config.py                   # 설정 파일
├── technical_analysis/         # 기술적 분석 모듈
│   ├── service/               # 비즈니스 로직
│   │   ├── backtesting_service.py          # 백테스팅 엔진
│   │   ├── advanced_pattern_service.py     # 고급 패턴 인식
│   │   └── signal_storage_service.py       # 신호 저장 관리
│   ├── web/route/             # API 라우터
│   └── infra/                 # 데이터 접근 계층
├── news_crawler/              # 뉴스 수집 모듈
│   ├── service/               # 뉴스 크롤링 서비스
│   └── infra/                 # 뉴스 데이터 저장
├── market_price/              # 시장 데이터 모듈
├── message_notification/      # 알림 시스템
├── scheduler/                 # 스케줄러
├── common/                    # 공통 유틸리티
│   ├── utils/                 # 유틸리티 함수
│   └── infra/                 # 인프라 공통 코드
└── archive/                   # 아카이브
```

## 주요 API 엔드포인트

### 신호 분석 API
```bash
# 전체 신호 성과 분석
GET /api/technical-analysis/signals/performance/all

# 특정 신호 타입 성과 분석
GET /api/technical-analysis/signals/performance/{signal_type}

# 매매 전략 백테스팅
POST /api/technical-analysis/signals/backtest/strategy
```

### 패턴 분석 API
```bash
# 패턴 유사도 분석
GET /api/technical-analysis/patterns/similarity/{symbol}

# 패턴 클러스터링
GET /api/technical-analysis/patterns/clustering/{symbol}
```

### 시장 데이터 API
```bash
# 현재 가격 조회
GET /api/market/price/{symbol}

# 기술적 지표 계산
GET /api/market/indicators/{symbol}
```

## 스케줄러 작업

시스템은 다음과 같은 정기 작업을 자동으로 실행합니다:

```bash
# 스케줄러 실행
python -m app.scheduler.scheduler_runner

# 개별 작업 테스트
python -c "from app.scheduler.jobs import *; run_high_price_update_job()"
```

주요 스케줄 작업:
- **실시간 가격 모니터링**: 2분마다 실행
- **기술적 신호 감지**: 1시간마다 실행
- **뉴스 수집**: 30분마다 실행
- **신호 결과 추적**: 1일마다 실행

## 개발 도구

### 테스트 실행
```bash
# 전체 테스트
pytest

# 특정 모듈 테스트
pytest app/technical_analysis/tests/

# 커버리지 포함 테스트
pytest --cov=app
```

### 코드 포맷팅
```bash
# Black 포맷터
black app/

# isort import 정렬
isort app/

# flake8 린터
flake8 app/
```

### 로그 확인
```bash
# 애플리케이션 로그
tail -f uvicorn.log

# 스케줄러 로그
tail -f scheduler.log
```

## 성능 최적화

시스템은 다음과 같은 성능 최적화를 적용했습니다:

- **병렬 처리**: ThreadPoolExecutor를 활용한 다중 심볼 동시 처리
- **지능형 캐싱**: 반복 계산 95% 감소로 CPU 사용량 절약
- **비동기 API**: aiohttp 기반 비동기 처리로 I/O 대기 시간 최소화
- **데이터베이스 최적화**: 연결 풀링 및 배치 처리로 DB 부하 감소

주요 성능 지표:
- API 응답 시간: 75% 단축 (1.2초 → 0.3초)
- 동시 처리량: 300% 증가 (50 req/s → 200 req/s)
- 스케줄러 처리: 80% 단축 (50초 → 10초)

## 문제 해결

### 일반적인 문제

1. **MySQL 연결 오류**
   ```bash
   # MySQL 서비스 상태 확인
   brew services list | grep mysql
   
   # MySQL 재시작
   brew services restart mysql
   ```

2. **가상환경 활성화 문제**
   ```bash
   # 가상환경 경로 확인
   which python
   
   # 가상환경 재생성
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **패키지 설치 오류**
   ```bash
   # pip 업그레이드
   pip install --upgrade pip
   
   # 캐시 클리어 후 재설치
   pip cache purge
   pip install -r requirements.txt
   ```

### 로그 레벨 조정

개발 시 더 자세한 로그를 보려면 `.env` 파일에서:
```env
LOG_LEVEL=DEBUG
```

## 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 연락처

프로젝트에 대한 질문이나 제안사항이 있으시면 이슈를 생성해 주세요.
