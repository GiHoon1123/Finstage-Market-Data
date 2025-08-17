"""
감정 특성 엔지니어링 모듈

뉴스 감정분석 데이터를 ML 모델에 사용할 수 있는 특성으로 변환합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.common.infra.database.config.database_config import SessionLocal
from app.news_crawler.infra.model.entity.content_sentiments import ContentSentiment
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class SentimentFeatureEngineer:
    """
    감정 데이터를 ML 특성으로 변환하는 엔지니어
    
    뉴스 감정분석 결과를 시계열 특성으로 변환하여
    ML 모델의 입력으로 사용할 수 있도록 합니다.
    """
    
    def __init__(self):
        """감정 특성 엔지니어 초기화"""
        self.feature_columns = []
        logger.info("sentiment_feature_engineer_initialized")

    def get_sentiment_features(
        self, 
        start_date: datetime, 
        end_date: datetime,
        symbol: Optional[str] = None
    ) -> pd.DataFrame:
        """
        지정된 기간의 감정 특성을 생성
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            symbol: 특정 심볼 필터 (None이면 전체)
            
        Returns:
            감정 특성 DataFrame (날짜 인덱스)
        """
        try:
            # 데이터베이스에서 감정 데이터 조회
            daily_sentiments = self._fetch_sentiment_data(start_date, end_date, symbol)
            
            if not daily_sentiments:
                logger.warning("no_sentiment_data_found", start_date=start_date, end_date=end_date)
                return self._create_empty_sentiment_features(start_date, end_date)
            
            # 감정 특성 생성
            sentiment_features = self._create_sentiment_features(daily_sentiments)
            
            logger.info(
                "sentiment_features_created", 
                start_date=start_date, 
                end_date=end_date,
                feature_count=len(sentiment_features.columns),
                data_points=len(sentiment_features)
            )
            
            return sentiment_features
            
        except Exception as e:
            logger.error("sentiment_features_creation_failed", error=str(e))
            return self._create_empty_sentiment_features(start_date, end_date)

    def _fetch_sentiment_data(
        self, 
        start_date: datetime, 
        end_date: datetime,
        symbol: Optional[str] = None
    ) -> List:
        """데이터베이스에서 감정 데이터 조회"""
        session = SessionLocal()
        try:
            query = session.query(
                func.date(ContentSentiment.analyzed_at).label('date'),
                func.count(ContentSentiment.id).label('news_count'),
                func.avg(ContentSentiment.sentiment_score).label('avg_sentiment'),
                func.avg(ContentSentiment.market_impact_score).label('avg_market_impact'),
                func.avg(ContentSentiment.confidence).label('avg_confidence'),
                func.avg(ContentSentiment.positive_score).label('avg_positive'),
                func.avg(ContentSentiment.negative_score).label('avg_negative'),
                func.avg(ContentSentiment.neutral_score).label('avg_neutral'),
                func.avg(ContentSentiment.compound_score).label('avg_compound')
            ).filter(
                ContentSentiment.analyzed_at >= start_date,
                ContentSentiment.analyzed_at <= end_date
            ).group_by(
                func.date(ContentSentiment.analyzed_at)
            ).order_by(
                func.date(ContentSentiment.analyzed_at)
            )
            
            # 특정 심볼 필터링 활성화
            if symbol:
                # 캐럿 제거 (^IXIC -> IXIC)
                clean_symbol = symbol.replace("^", "")
                logger.info(
                    "filtering_sentiment_by_symbol", 
                    original_symbol=symbol, 
                    clean_symbol=clean_symbol
                )
                
                # Content 테이블과 조인하여 심볼별 필터링
                query = query.join(ContentSentiment.content).filter(
                    ContentSentiment.content.has(symbol=clean_symbol)
                )
            else:
                logger.info("no_symbol_filter_applied_to_sentiment_data")
            
            return query.all()
            
        except Exception as e:
            logger.error("sentiment_data_fetch_failed", error=str(e), symbol=symbol)
            return []
        finally:
            session.close()

    def _create_sentiment_features(self, daily_sentiments: List) -> pd.DataFrame:
        """일별 감정 데이터를 특성으로 변환"""
        # DataFrame 생성
        df = pd.DataFrame([
            {
                'date': sentiment.date,
                'news_count': sentiment.news_count,
                'avg_sentiment': sentiment.avg_sentiment,
                'avg_market_impact': sentiment.avg_market_impact,
                'avg_confidence': sentiment.avg_confidence,
                'avg_positive': sentiment.avg_positive,
                'avg_negative': sentiment.avg_negative,
                'avg_neutral': sentiment.avg_neutral,
                'avg_compound': sentiment.avg_compound
            }
            for sentiment in daily_sentiments
        ])
        
        # 날짜를 인덱스로 설정
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        
        # 기본 특성들
        self.feature_columns = [
            'news_count', 'avg_sentiment', 'avg_market_impact', 
            'avg_confidence', 'avg_positive', 'avg_negative', 
            'avg_neutral', 'avg_compound'
        ]
        
        # 파생 특성 생성
        df = self._add_derived_features(df)
        
        return df

    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """파생 감정 특성 추가"""
        # 감정 변화율
        df['sentiment_change'] = df['avg_sentiment'].diff()
        df['market_impact_change'] = df['avg_market_impact'].diff()
        
        # 감정 변동성
        df['sentiment_volatility'] = df['avg_sentiment'].rolling(3).std()
        df['market_impact_volatility'] = df['avg_market_impact'].rolling(3).std()
        
        # 감정 이동평균
        df['sentiment_ma_3d'] = df['avg_sentiment'].rolling(3).mean()
        df['sentiment_ma_7d'] = df['avg_sentiment'].rolling(7).mean()
        df['sentiment_ma_14d'] = df['avg_sentiment'].rolling(14).mean()
        
        # 시장 영향도 이동평균
        df['market_impact_ma_3d'] = df['avg_market_impact'].rolling(3).mean()
        df['market_impact_ma_7d'] = df['avg_market_impact'].rolling(7).mean()
        
        # 뉴스 볼륨 특성
        df['news_count_ma_3d'] = df['news_count'].rolling(3).mean()
        df['news_count_ma_7d'] = df['news_count'].rolling(7).mean()
        
        # 감정 극성 특성
        df['sentiment_polarity'] = abs(df['avg_sentiment'])  # 감정 강도
        df['sentiment_direction'] = np.where(df['avg_sentiment'] > 0, 1, -1)  # 감정 방향
        
        # 복합 감정 특성
        df['positive_negative_ratio'] = df['avg_positive'] / (df['avg_negative'] + 1e-8)
        df['sentiment_confidence_weighted'] = df['avg_sentiment'] * df['avg_confidence']
        
        # 결측치 처리
        df = df.fillna(method='ffill').fillna(0)
        
        return df

    def _create_empty_sentiment_features(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """빈 감정 특성 DataFrame 생성 (훈련 시와 동일한 특성 수 유지)"""
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 기본 특성들 (훈련 시와 동일한 순서)
        base_features = [
            'news_count', 'avg_sentiment', 'avg_market_impact', 
            'avg_confidence', 'avg_positive', 'avg_negative', 
            'avg_neutral', 'avg_compound'
        ]
        
        # 파생 특성들 (훈련 시와 동일한 순서)
        derived_features = [
            'sentiment_change', 'market_impact_change',
            'sentiment_volatility', 'market_impact_volatility',
            'sentiment_ma_3d', 'sentiment_ma_7d', 'sentiment_ma_14d',
            'market_impact_ma_3d', 'market_impact_ma_7d',
            'news_count_ma_3d', 'news_count_ma_7d',
            'sentiment_polarity', 'sentiment_direction',
            'positive_negative_ratio', 'sentiment_confidence_weighted'
        ]
        
        # 추가 특성들 (훈련 시에 있었던 특성들)
        additional_features = [
            'sentiment_momentum', 'market_impact_momentum',
            'sentiment_acceleration'  # 3개만 추가하여 총 23개 유지
        ]
        
        all_features = base_features + derived_features + additional_features
        
        # 0으로 채워진 DataFrame 생성
        df = pd.DataFrame(0, index=date_range, columns=all_features)
        
        # 특성 컬럼 순서를 일관되게 유지
        self.feature_columns = all_features
        
        logger.info("empty_sentiment_features_created", feature_count=len(all_features))
        
        return df

    def get_feature_names(self) -> List[str]:
        """생성된 특성 이름들 반환"""
        return self.feature_columns.copy()

    def merge_with_price_data(self, price_df: pd.DataFrame, sentiment_df: pd.DataFrame) -> pd.DataFrame:
        """
        가격 데이터와 감정 데이터 병합
        
        Args:
            price_df: 가격 데이터 DataFrame
            sentiment_df: 감정 데이터 DataFrame
            
        Returns:
            병합된 DataFrame
        """
        # 날짜 인덱스 확인
        if not isinstance(price_df.index, pd.DatetimeIndex):
            price_df.index = pd.to_datetime(price_df.index)
        
        if not isinstance(sentiment_df.index, pd.DatetimeIndex):
            sentiment_df.index = pd.to_datetime(sentiment_df.index)
        
        # 외부 조인으로 병합 (가격 데이터 기준)
        merged_df = price_df.join(sentiment_df, how='left')
        
        # 감정 데이터 결측치 처리
        sentiment_columns = sentiment_df.columns
        merged_df[sentiment_columns] = merged_df[sentiment_columns].fillna(method='ffill').fillna(0)
        
        logger.info(
            "price_sentiment_data_merged", 
            original_price_rows=len(price_df),
            sentiment_features=len(sentiment_columns),
            merged_rows=len(merged_df)
        )
        
        return merged_df
