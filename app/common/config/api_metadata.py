"""API 메타데이터 설정"""

# 태그 메타데이터
tags_metadata = [
    {
        "name": "Company",
        "description": "기업 정보 관련 API",
        "externalDocs": {
            "description": "기업 정보 가이드",
            "url": "https://docs.finstage.com/company",
        },
    },
    {
        "name": "Company Financials",
        "description": "기업 재무제표 관련 API - 손익계산서, 재무상태표, 현금흐름표",
    },
    {
        "name": "Symbol",
        "description": "주식 심볼 관련 API - 심볼 조회 및 검색",
    },
    {
        "name": "Market Data",
        "description": "시장 데이터 관련 API - 실시간 가격, 차트 데이터",
        "externalDocs": {
            "description": "시장 데이터 가이드",
            "url": "https://docs.finstage.com/market-data",
        },
    },
    {
        "name": "Technical Analysis",
        "description": "기술적 분석 관련 API - 지표 계산, 신호 생성",
        "externalDocs": {
            "description": "기술적 분석 가이드",
            "url": "https://docs.finstage.com/technical-analysis",
        },
    },
    {
        "name": "Outcome Analysis",
        "description": "결과 분석 관련 API - 신호 성과 추적 및 분석",
    },
    {
        "name": "Pattern Analysis",
        "description": "패턴 분석 관련 API - 차트 패턴 인식 및 분석",
    },
    {
        "name": "ML Prediction",
        "description": "머신러닝 예측 관련 API - 모델 훈련, 예측, 백테스팅",
        "externalDocs": {
            "description": "ML 예측 가이드",
            "url": "https://docs.finstage.com/ml-prediction",
        },
    },
    {
        "name": "News Crawler",
        "description": "뉴스 크롤링 관련 API - 뉴스 수집 및 분석",
    },
    {
        "name": "Message Notification",
        "description": "메시지 알림 관련 API - 텔레그램, 이메일 알림",
    },
    {
        "name": "Testing",
        "description": "테스트 관련 API - 시스템 테스트 및 검증",
    },
    {
        "name": "Health Check",
        "description": "시스템 상태 확인 관련 API",
    },
]

# 공통 응답 예시 (ApiResponse 구조에 맞게 업데이트)
common_responses = {
    400: {
        "description": "잘못된 요청",
        "content": {
            "application/json": {
                "example": {
                    "status": 400,
                    "message": "요청 데이터가 올바르지 않습니다",
                    "data": None,
                }
            }
        },
    },
    401: {
        "description": "인증 실패",
        "content": {
            "application/json": {
                "example": {
                    "status": 401,
                    "message": "인증이 필요합니다",
                    "data": None,
                }
            }
        },
    },
    403: {
        "description": "권한 없음",
        "content": {
            "application/json": {
                "example": {
                    "status": 403,
                    "message": "접근 권한이 없습니다",
                    "data": None,
                }
            }
        },
    },
    404: {
        "description": "리소스 없음",
        "content": {
            "application/json": {
                "example": {
                    "status": 404,
                    "message": "요청한 리소스를 찾을 수 없습니다",
                    "data": None,
                }
            }
        },
    },
    422: {
        "description": "데이터 검증 실패",
        "content": {
            "application/json": {
                "example": {
                    "status": 422,
                    "message": "입력 데이터 검증에 실패했습니다",
                    "data": {
                        "details": {
                            "field": "symbol",
                            "message": "심볼은 필수 입력값입니다",
                        }
                    },
                }
            }
        },
    },
    500: {
        "description": "서버 내부 오류",
        "content": {
            "application/json": {
                "example": {
                    "status": 500,
                    "message": "서버에서 오류가 발생했습니다",
                    "data": None,
                }
            }
        },
    },
}

# 성공 응답 예시
success_response_example = {
    "status": 200,
    "message": "성공적으로 처리되었습니다",
    "data": {
        "example": "응답 데이터"
    }
}

# 페이징 응답 예시
paginated_response_example = {
    "status": 200,
    "message": "조회가 완료되었습니다",
    "data": {
        "items": [
            {"id": 1, "name": "예시 항목 1"},
            {"id": 2, "name": "예시 항목 2"}
        ],
        "pagination": {
            "page": 1,
            "size": 10,
            "total": 100,
            "total_pages": 10,
            "has_next": True,
            "has_prev": False
        }
    }
}
