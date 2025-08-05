# Finstage Market Data

AI 기반 퀀트 분석 시스템으로, 머신러닝을 활용한 주식 패턴 분석과 실시간 투자 신호를 제공하는 백엔드 서비스입니다.

## ✨ 주요 기능

- **K-means 클러스터링**: 과거 10년 데이터 기반 패턴 자동 분류 및 성공률 분석
- **📊 일일 퀀트 리포트**: AI 분석 결과를 일반인이 이해하기 쉽게 텔레그램 자동 전송
- **⚡ 실시간 가격 모니터링**: 빅테크 7종목 + 주요 지수 3분마다 모니터링 및 알림
- **📈 자동 데이터 업데이트**: 일봉 데이터 자동 수집 및 누락 구간 자동 보완
- **🔍 고급 패턴 분석**: 기술적 지표 기반 매매 신호 생성 및 백테스팅
- **📱 텔레그램 통합**: 실시간 알림 및 상세한 분석 리포트 자동 전송

## 🛠 기술 스택

| 카테고리              | 기술                          |
| --------------------- | ----------------------------- |
| **언어 & 프레임워크** | Python 3.12, FastAPI          |
| **데이터베이스**      | MySQL 8.0, SQLAlchemy 2.0 ORM |
| **데이터 분석**       | Pandas, NumPy, yfinance       |
| **머신러닝**          | K-means 클러스터링, 패턴 분류 |
| **스케줄링**          | APScheduler (백그라운드 작업) |
| **알림 시스템**       | Telegram Bot API              |
| **개발 환경**         | macOS (Apple M3), Python venv |

## 🚀 개발 환경 설정

> **개발 환경**: macOS (Apple M3 칩셋)에서 개발 및 테스트되었습니다.

### 사전 요구사항

- **Python 3.12+**
- **MySQL 8.0+**
- **Git**
- **Homebrew** (macOS 패키지 매니저)

### 1. 저장소 클론

```bash
git clone https://github.com/your-username/Finstage-Market-Data.git
cd Finstage-Market-Data
```

### 2. Python 가상환경 설정

```bash
# 가상환경 생성
python3 -m venv .venv

# 가상환경 활성화 (macOS)
source .venv/bin/activate

# 가상환경 비활성화 (필요시)
# deactivate
```

### 3. 의존성 설치

```bash
# 패키지 설치
pip install -r requirements.txt

# pip 업그레이드 (권장)
pip install --upgrade pip
```

### 4. MySQL 설치 및 설정 (macOS)

```bash
# Homebrew로 MySQL 설치
brew install mysql

# MySQL 서비스 시작
brew services start mysql

# MySQL 보안 설정 (선택사항)
mysql_secure_installation

# 데이터베이스 생성
mysql -u root -p
CREATE DATABASE finstage_market_data;
EXIT;
```

### 5. 환경 변수 설정

```bash
# 환경 변수 파일 생성
cp .env.example .env.dev

# .env.dev 파일 편집
nano .env.dev
```

**`.env.dev` 파일 설정 예시**:

```env
# 애플리케이션 설정
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000

# 데이터베이스 설정
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=finstage_market_data

# 텔레그램 봇 설정 (BotFather에서 발급)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Yahoo Finance API 설정
YFINANCE_DELAY=0.5

# 로깅 설정
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 6. 스케줄러 실행

```bash
# 백그라운드 스케줄러 실행 (메인 기능)
python app/scheduler/scheduler_runner.py

# 또는 개별 테스트 실행
python test_script/test_daily_report_with_ml.py
```

## 📁 프로젝트 구조

```
Finstage-Market-Data/
├── app/                                    # 메인 애플리케이션
│   ├── scheduler/                          # 스케줄러 (핵심 기능)
│   │   ├── scheduler_runner.py             # 메인 스케줄러 실행기
│   │   └── parallel_scheduler.py           # 병렬 처리 스케줄러
│   ├── technical_analysis/                 # 기술적 분석 모듈
│   │   ├── service/                        # 비즈니스 로직
│   │   │   ├── daily_comprehensive_report_service.py  # 일일 리포트
│   │   │   ├── advanced_pattern_service.py            # K-means 클러스터링
│   │   │   ├── pattern_analysis_service.py            # 패턴 분석
│   │   │   └── signal_generator_service.py            # 신호 생성
│   │   └── infra/model/                    # 데이터 모델
│   │       ├── entity/                     # 엔티티
│   │       │   ├── pattern_clusters.py    # 클러스터링 결과
│   │       │   ├── daily_prices.py        # 일봉 데이터
│   │       │   └── technical_signals.py   # 기술적 신호
│   │       └── repository/                 # 리포지토리
│   ├── market_price/                       # 시장 데이터 모듈
│   │   └── service/
│   │       ├── daily_price_auto_updater.py # 일봉 데이터 자동 업데이트
│   │       └── price_monitor_service.py    # 실시간 가격 모니터링
│   ├── news_crawler/                       # 뉴스 수집 모듈
│   └── common/                             # 공통 유틸리티
│       ├── constants/                      # 상수 정의
│       │   ├── symbol_names.py             # 종목 심볼 매핑
│       │   └── thresholds.py               # 알림 임계치
│       └── utils/                          # 유틸리티
│           └── telegram_notifier.py        # 텔레그램 알림
├── test_script/                            # 테스트 스크립트
│   ├── test_kmeans_clustering_simple.py    # K-means 클러스터링 테스트
│   ├── test_daily_report_with_ml.py        # 일일 리포트 테스트
│   ├── test_daily_price_auto_updater.py    # 데이터 업데이트 테스트
│   └── README.md                           # 테스트 가이드
├── .env.dev                                # 개발 환경 변수
├── requirements.txt                        # Python 의존성
└── README.md                               # 이 파일
```

## 🔧 환경 변수 설정

시스템 운영에 필요한 주요 환경 변수들:

### 필수 설정

```env
# 데이터베이스 연결
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=finstage_market_data

# 텔레그램 봇 (알림 전송용)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### 선택적 설정

```env
# 애플리케이션
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# API 제한
YFINANCE_DELAY=0.5

# 보안
SECURITY_SECRET_KEY=your-secret-key
SECURITY_ALLOWED_HOSTS=*
```

## 🎯 주요 기능 실행

### 1. K-means 클러스터링 테스트

```bash
# 간단한 클러스터링 테스트
python test_script/test_kmeans_clustering_simple.py

# 전체 파이프라인 테스트
python test_script/test_kmeans_clustering_full.py
```

### 2. 일일 리포트 생성 및 전송

```bash
# ML 기반 일일 리포트 테스트
python test_script/test_daily_report_with_ml.py

# 텔레그램 메시지 미리보기
python test_script/test_telegram_message_preview.py
```

### 3. 실시간 가격 모니터링

```bash
# 가격 모니터링 설정 확인
python test_script/test_stock_monitoring_schedule.py

# 가격 알림 설정 확인
python test_script/test_price_alert_settings.py
```

### 4. 데이터 관리

```bash
# 일봉 데이터 현황 확인
python test_script/test_daily_price_status_only.py

# 데이터 자동 업데이트 테스트
python test_script/test_daily_price_auto_updater.py
```

## 📊 모니터링 대상 종목

### 빅테크 종목 (7개)

- **AAPL**: 애플
- **AMZN**: 아마존
- **GOOGL**: 구글
- **TSLA**: 테슬라
- **MSFT**: 마이크로소프트
- **META**: 메타
- **NVDA**: 엔비디아

### 주요 지수 (2개)

- **^IXIC**: 나스닥 지수
- **^GSPC**: S&P 500 지수

**모니터링 주기**: 3분마다 실시간 가격 체크 및 알림

## 🤖 AI 분석 기능

### K-means 클러스터링

- **데이터**: 과거 10년간 일봉 데이터 (나스닥 2,650개, S&P500 2,650개)
- **특성 벡터**: 11차원 (지속시간, 신호타입, 방향성, 시간적특성)
- **클러스터**: 6개 그룹으로 자동 분류
- **성공률**: 각 클러스터별 과거 성공률 계산

### 일일 리포트

- **생성 시간**: 매일 오전 8시 (현재 테스트용 3분마다)
- **내용**: AI 분석 결과, 투자 인사이트, 리스크 분석
- **전송**: 텔레그램 자동 전송 (일반인 친화적 설명 포함)

## 🔧 문제 해결

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
   rm -rf .venv
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **텔레그램 봇 설정**
   ```bash
   # BotFather에서 봇 생성
   # 1. 텔레그램에서 @BotFather 검색
   # 2. /newbot 명령어로 봇 생성
   # 3. 발급받은 토큰을 .env.dev에 설정
   ```

### 로그 확인

```bash
# 스케줄러 로그 실시간 확인
tail -f scheduler.log

# 애플리케이션 로그 확인
tail -f logs/app.log
```
