"""
데이터베이스 세션 관리 유틸리티

세션 관리를 효율적으로 하여 연결 풀 고갈 문제를 해결합니다.
"""

from contextlib import contextmanager
from typing import Generator, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.common.infra.database.config.database_config import SessionLocal
import logging

# 로거 설정
logger = logging.getLogger("db_session")
logger.setLevel(logging.INFO)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    세션 컨텍스트 매니저 - 트랜잭션 자동 관리

    사용 예:
    with session_scope() as session:
        # 세션 사용
        session.query(...)
    # 자동으로 커밋 또는 롤백 후 세션 닫힘
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"데이터베이스 오류: {e}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"일반 오류: {e}")
        raise
    finally:
        session.close()


class DatabaseSessionManager:
    """
    데이터베이스 세션 관리 클래스

    서비스 클래스에서 상속하여 사용:
    class MyService(DatabaseSessionManager):
        def some_method(self):
            with self.get_session_context() as session:
                # 세션 사용
    """

    def __init__(self):
        self._session = None

    @contextmanager
    def get_session_context(self) -> Generator[Session, None, None]:
        """
        세션 컨텍스트 매니저 - 세션 자동 관리

        사용 예:
        with service.get_session_context() as session:
            # 세션 사용
        """
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"데이터베이스 오류: {e}")
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"일반 오류: {e}")
            raise
        finally:
            session.close()

    def execute_in_session(self, operation: callable, *args, **kwargs) -> Any:
        """
        세션 내에서 작업 실행 - 세션 자동 관리

        Args:
            operation: 실행할 함수 (첫 번째 인자로 세션을 받음)
            args, kwargs: operation에 전달할 추가 인자

        Returns:
            operation의 반환값

        사용 예:
        def do_something(session, arg1, arg2):
            # 세션 사용
            return result

        result = service.execute_in_session(do_something, arg1, arg2)
        """
        with self.get_session_context() as session:
            return operation(session, *args, **kwargs)

    def close(self):
        """모든 리소스 정리"""
        if self._session is not None:
            self._session.close()
            self._session = None

    def __del__(self):
        """소멸자에서 세션 정리"""
        self.close()


# 전역 세션 관리자 인스턴스
db_session_manager = DatabaseSessionManager()


def get_session_manager() -> DatabaseSessionManager:
    """전역 세션 관리자 인스턴스 반환"""
    return db_session_manager
