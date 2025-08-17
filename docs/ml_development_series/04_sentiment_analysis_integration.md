# 머신러닝을 활용한 주가 예측 시스템 개발 - 4. 감정분석 데이터 통합

## 뉴스 크롤링과 감정분석 시스템

1차 예측에서 **107개의 차트 특성**만으로 모델을 훈련했지만, 예측 정확도에 한계가 있었다. 이번 단계에서는 **뉴스 감정분석 데이터**를 추가하여 모델의 성능을 향상시키는 과정을 다루겠습니다.

## 1. 기존 뉴스 크롤링 서비스 활용

**기존에 구축된 뉴스 크롤링 서비스**를 활용하여 감정분석 데이터를 생성한다. 이 서비스는 Investing.com과 Yahoo Finance에서 뉴스를 수집하여 데이터베이스에 저장하는 기능을 제공한다.

### 1.1 뉴스 크롤링 서비스 구조

**3분마다 자동으로 실행**되는 스케줄러를 통해 뉴스 데이터를 지속적으로 수집한다:

```python
def run_investing_economic_news():
    """경제 뉴스 크롤링 작업"""
    for symbol in INVESTING_ECONOMIC_SYMBOLS:
        InvestingNewsCrawler(symbol).process_all()

def run_yahoo_index_news():
    """지수 뉴스 크롤링 작업"""
    for symbol in INDEX_SYMBOLS:
        YahooNewsCrawler(symbol).process_all()
```

**수집되는 뉴스 데이터:**

- **제목 (title)**: 뉴스 제목
- **요약 (description)**: 뉴스 내용 요약
- **링크 (link)**: 원본 뉴스 URL
- **발행일 (pub_date)**: 뉴스 발행 시간
- **소스 (source)**: 뉴스 출처 (investing, yahoo)
- **심볼 (symbol)**: 관련 주식/지수 심볼

## 2. 감정분석 시스템

### 2.1 VADER 감정분석기

**금융 뉴스에 특화된 감정분석**을 수행하는 시스템:

```python
class SentimentAnalyzer:
    def __init__(self):
        """감정분석기 초기화"""
        self.analyzer = SentimentIntensityAnalyzer()
        self._setup_financial_lexicon()

    def _setup_financial_lexicon(self):
        """금융 뉴스에 특화된 Lexicon 설정"""
        # 긍정적 금융 키워드
        positive_financial_words = {
            'surge': 1.5, 'rally': 1.3, 'jump': 1.2, 'soar': 1.4,
            'gain': 1.1, 'rise': 1.0, 'climb': 1.1, 'advance': 1.0,
            'profit': 1.2, 'earnings': 1.1, 'growth': 1.0, 'revenue': 0.8,
            'beat': 1.3, 'exceed': 1.2, 'outperform': 1.1, 'upgrade': 1.2,
            'bullish': 1.3, 'positive': 1.0, 'strong': 0.9, 'robust': 0.9
        }

        # 부정적 금융 키워드
        negative_financial_words = {
            'plunge': -1.5, 'crash': -1.6, 'drop': -1.1, 'fall': -1.0,
            'decline': -1.0, 'slump': -1.2, 'tumble': -1.3, 'dive': -1.4,
            'loss': -1.2, 'deficit': -1.1, 'weak': -0.9, 'miss': -1.3,
            'disappoint': -1.2, 'underperform': -1.1, 'downgrade': -1.2,
            'bearish': -1.3, 'negative': -1.0, 'poor': -1.0
        }

        # Lexicon 업데이트
        self.analyzer.lexicon.update(positive_financial_words)
        self.analyzer.lexicon.update(negative_financial_words)
```

### 2.2 감정분석 수행

**뉴스 텍스트의 감정을 분석**하여 점수화:

```python
def analyze_sentiment(self, text: str) -> Dict[str, Any]:
    """텍스트의 감정분석 수행"""
    if not text or not text.strip():
        return self._get_neutral_result()

    try:
        # VADER 감정분석 수행
        scores = self.analyzer.polarity_scores(text)

        # 감정 라벨 결정
        sentiment_label = self._determine_sentiment_label(scores['compound'])

        # 시장 영향도 계산
        market_impact_score = self._calculate_market_impact(text, scores)

        # 신뢰도 계산
        confidence = self._calculate_confidence(scores)

        result = {
            'sentiment_score': scores['compound'],
            'sentiment_label': sentiment_label,
            'confidence': confidence,
            'positive_score': scores['pos'],
            'negative_score': scores['neg'],
            'neutral_score': scores['neu'],
            'compound_score': scores['compound'],
            'market_impact_score': market_impact_score,
            'is_market_sensitive': abs(market_impact_score) > 0.5
        }

        return result

    except Exception as e:
        logger.error("sentiment_analysis_failed", error=str(e))
        return self._get_neutral_result()
```

### 2.3 뉴스 처리 파이프라인

**크롤링 → 번역 → 감정분석 → 저장**의 전체 파이프라인:

```python
class NewsProcessor:
    def __init__(self, news_items: list[dict], telegram_enabled: bool = False):
        self.news_items = news_items
        self.sentiment_analyzer = SentimentAnalyzer()

    def run(self):
        """뉴스 데이터베이스 저장 및 감정분석 수행"""
        try:
            session, content_repo, translation_repo, sentiment_repo = self._get_session_and_repos()

            for item in self.news_items:
                try:
                    if self._is_duplicate(item):
                        continue

                    # 1. 뉴스 내용 저장
                    content = self._save_content(item)

                    # 2. 한국어 번역 저장
                    title_ko, summary_ko, symbol = self._save_translation(content)

                    # 3. 감정분석 수행 및 저장
                    self._save_sentiment(content)

                except Exception as item_error:
                    logger.error("individual_news_processing_failed", error=str(item_error))
                    continue

            session.commit()

        except Exception as e:
            if self.session:
                self.session.rollback()
            logger.error("news_processing_failed", error=str(e))
```

## 3. 감정분석 데이터 저장

### 3.1 데이터베이스 스키마

**감정분석 결과를 저장하는 테이블 구조**:

```python
class ContentSentiment(Base):
    __tablename__ = "content_sentiments"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("contents.id"))
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # 감정 점수들
    sentiment_score = Column(Float)  # 전체 감정 점수 (-1 ~ 1)
    positive_score = Column(Float)   # 긍정 점수 (0 ~ 1)
    negative_score = Column(Float)   # 부정 점수 (0 ~ 1)
    neutral_score = Column(Float)    # 중립 점수 (0 ~ 1)
    compound_score = Column(Float)   # 복합 점수 (-1 ~ 1)

    # 추가 메타데이터
    market_impact_score = Column(Float)  # 시장 영향도
    confidence = Column(Float)           # 분석 신뢰도
    sentiment_label = Column(String)     # 감정 라벨 (positive, negative, neutral)
    is_market_sensitive = Column(Boolean) # 시장 민감도 여부
```

### 3.2 감정분석 결과 저장

**뉴스 처리 파이프라인에서 감정분석 결과를 데이터베이스에 저장**:

```python
def _save_sentiment(self, content: Content):
    """감정분석 수행 및 결과 저장"""
    try:
        # 뉴스 텍스트 준비 (제목 + 요약)
        text = f"{content.title} {content.summary}"

        # 감정분석 수행
        sentiment_result = self.sentiment_analyzer.analyze_sentiment(text)

        # 감정분석 결과 저장
        sentiment = ContentSentiment(
            content_id=content.id,
            sentiment_score=sentiment_result['sentiment_score'],
            positive_score=sentiment_result['positive_score'],
            negative_score=sentiment_result['negative_score'],
            neutral_score=sentiment_result['neutral_score'],
            compound_score=sentiment_result['compound_score'],
            market_impact_score=sentiment_result['market_impact_score'],
            confidence=sentiment_result['confidence'],
            sentiment_label=sentiment_result['sentiment_label'],
            is_market_sensitive=sentiment_result['is_market_sensitive']
        )

        self.sentiment_repo.create(sentiment)

        logger.info(
            "sentiment_analysis_saved",
            content_id=content.id,
            sentiment_score=sentiment_result['sentiment_score'],
            sentiment_label=sentiment_result['sentiment_label']
        )

    except Exception as e:
        logger.error("sentiment_analysis_save_failed", content_id=content.id, error=str(e))
```

### 3.3 저장된 데이터 예시

**실제 데이터베이스에 저장되는 감정분석 결과**:

```sql
-- content_sentiments 테이블 예시 데이터
SELECT
    cs.id,
    c.title,
    cs.sentiment_score,
    cs.sentiment_label,
    cs.market_impact_score,
    cs.confidence,
    cs.analyzed_at
FROM content_sentiments cs
JOIN contents c ON cs.content_id = c.id
WHERE c.symbol = 'GSPC'
ORDER BY cs.analyzed_at DESC
LIMIT 5;
```

**결과 예시:**

```
| id | title                                    | sentiment_score | sentiment_label | market_impact_score | confidence | analyzed_at           |
|----|------------------------------------------|----------------|-----------------|-------------------|------------|----------------------|
| 1  | "S&P 500 Surges to New Record High"     | 0.85           | positive        | 0.72              | 0.89       | 2025-08-17 10:30:00  |
| 2  | "Market Concerns Over Fed Policy"       | -0.32          | negative        | 0.65              | 0.78       | 2025-08-17 10:25:00  |
| 3  | "Tech Stocks Show Mixed Performance"    | 0.12           | neutral         | 0.45              | 0.82       | 2025-08-17 10:20:00  |
| 4  | "Earnings Beat Expectations"            | 0.68           | positive        | 0.58              | 0.91       | 2025-08-17 10:15:00  |
| 5  | "Economic Data Disappoints"             | -0.45          | negative        | 0.71              | 0.85       | 2025-08-17 10:10:00  |
```

## 결론

**뉴스 크롤링 서비스를 활용하여 감정분석 데이터를 성공적으로 생성하고 저장**했다.

**저장된 데이터:**

- **감정 점수**: 긍정/부정/중립/복합 점수
- **시장 영향도**: 뉴스의 시장 영향력 평가
- **신뢰도**: 감정분석 결과의 신뢰 수준
- **메타데이터**: 분석 시간, 라벨 등

**다음 단계:**

- 감정분석 데이터를 활용한 모델 훈련
- 특성 엔지니어링 및 통합
- 예측 성능 향상 검증

이제 **감정분석 데이터가 준비**되어 ML 모델에 통합할 수 있는 상태가 되었다.
