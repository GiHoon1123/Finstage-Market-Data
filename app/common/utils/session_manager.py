"""
데이터베이스 세션 관리 유틸리티
"""

from contextlib import contextmanager
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal


@contextmanager
def session_scope():
    """
    세션 컨텍스트 매니저

    사용 예:
    with session_scope() as session:
        # 세션 사용
        session.query(...)
    # 자동으로 세션 닫힘
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


class SessionManager:
    """
    세션 관리 클래스

    서비스 클래스에서 상속하여 사용:
    class MyService(SessionManager):
        def some_method(self):
            session = self.get_session()
            # 세션 사용
    """

    def __init__(self):
        self._session = None

    def get_session(self) -> Session:
        """세션 가져오기 (없으면 생성)"""
        if self._session is None:
            self._session = SessionLocal()
        return self._session

    def close_session(self):
        """세션 닫기"""
        if self._session is not None:
            self._session.close()
            self._session = None

    def __del__(self):
        """소멸자에서 세션 정리"""
        self.close_session()
