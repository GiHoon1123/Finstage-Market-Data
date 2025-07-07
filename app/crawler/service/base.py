# abc는 "abstract base class"의 약자로, 추상 클래스를 만들기 위한 파이썬 모듈
# 추상 클래스는 "이 틀을 꼭 상속받아서 구현해야 한다"는 규칙을 만들고 싶을 때 사용
from abc import ABC, abstractmethod

from typing import List, Dict
from datetime import datetime
import hashlib

# BaseCrawler는 모든 크롤러들이 공통적으로 상속받을 추상 클래스
class BaseCrawler(ABC):
    
    # crawl() 함수는 반드시 상속받는 클래스에서 구현해야 함
    @abstractmethod
    def crawl(self) -> List[Dict]:
        """
        실제 크롤링 로직을 구현할 함수
        이걸 오버라이딩하지 않으면 오류 발생함
        """
        pass

    @staticmethod
    def generate_hash(text: str) -> str:
        """
        기사 내용이나 URL 등을 기준으로 중복 방지를 위한 고유 해시값 생성
        (SHA-256 방식으로 문자열을 암호화한 결과 반환)
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    @staticmethod
    def get_crawled_at() -> datetime:
        """
        크롤링 시각을 UTC 시간 기준으로 반환
        (DB 저장용)
        """
        return datetime.utcnow()
