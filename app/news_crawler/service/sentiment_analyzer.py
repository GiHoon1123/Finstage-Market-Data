from typing import Dict, Any, Optional
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class SentimentAnalyzer:
    """
    VADER Lexicon 기반 감정분석 서비스
    
    금융 뉴스에 특화된 감정분석을 제공하며,
    시장 영향도를 고려한 감정 점수를 계산합니다.
    """
    
    def __init__(self):
        """감정분석기 초기화"""
        self.analyzer = SentimentIntensityAnalyzer()
        self._setup_financial_lexicon()
        
        logger.info("sentiment_analyzer_initialized")

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
            'loss': -1.2, 'deficit': -1.1, 'decline': -1.0, 'weak': -0.9,
            'miss': -1.3, 'disappoint': -1.2, 'underperform': -1.1, 'downgrade': -1.2,
            'bearish': -1.3, 'negative': -1.0, 'weak': -0.9, 'poor': -1.0
        }
        
        # 긴급도 키워드 (시장 영향도 증가)
        urgency_words = {
            'urgent': 1.5, 'breaking': 1.4, 'exclusive': 1.3, 'flash': 1.4,
            'alert': 1.3, 'warning': -1.2, 'crisis': -1.5, 'emergency': -1.4
        }
        
        # Lexicon 업데이트
        self.analyzer.lexicon.update(positive_financial_words)
        self.analyzer.lexicon.update(negative_financial_words)
        self.analyzer.lexicon.update(urgency_words)

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        텍스트의 감정분석 수행
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            감정분석 결과 딕셔너리
        """
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
            
            logger.debug(
                "sentiment_analysis_completed",
                text_length=len(text),
                sentiment_label=sentiment_label,
                sentiment_score=scores['compound'],
                market_impact=market_impact_score
            )
            
            return result
            
        except Exception as e:
            logger.error("sentiment_analysis_failed", error=str(e), text_preview=text[:100])
            return self._get_neutral_result()

    def _determine_sentiment_label(self, compound_score: float) -> str:
        """복합 점수로 감정 라벨 결정"""
        if compound_score >= 0.05:
            return 'positive'
        elif compound_score <= -0.05:
            return 'negative'
        else:
            return 'neutral'

    def _calculate_market_impact(self, text: str, scores: Dict[str, float]) -> float:
        """시장 영향도 점수 계산"""
        # 기본 감정 점수
        base_impact = scores['compound']
        
        # 긴급도 키워드 확인
        urgency_multiplier = 1.0
        urgency_patterns = [
            r'\b(urgent|breaking|exclusive|flash|alert)\b',
            r'\b(crisis|emergency|warning)\b',
            r'\b(immediate|instant|sudden)\b'
        ]
        
        for pattern in urgency_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                urgency_multiplier = 1.3
                break
        
        # 금융 키워드 확인
        financial_multiplier = 1.0
        financial_patterns = [
            r'\b(earnings|revenue|profit|loss)\b',
            r'\b(stock|market|trading|price)\b',
            r'\b(quarterly|annual|report)\b'
        ]
        
        for pattern in financial_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                financial_multiplier = 1.2
                break
        
        return base_impact * urgency_multiplier * financial_multiplier

    def _calculate_confidence(self, scores: Dict[str, float]) -> float:
        """분석 신뢰도 계산"""
        # 중립 점수가 낮을수록 (긍정/부정이 명확할수록) 신뢰도 높음
        confidence = 1.0 - scores['neu']
        
        # 최소 신뢰도 보장
        return max(confidence, 0.3)

    def _get_neutral_result(self) -> Dict[str, Any]:
        """중립 결과 반환 (분석 실패 시)"""
        return {
            'sentiment_score': 0.0,
            'sentiment_label': 'neutral',
            'confidence': 0.5,
            'positive_score': 0.0,
            'negative_score': 0.0,
            'neutral_score': 1.0,
            'compound_score': 0.0,
            'market_impact_score': 0.0,
            'is_market_sensitive': False
        }
