import json
from sqlalchemy import select
from app.company.infra.model.symbol.entity.symbol import Symbol
from app.common.infra.database.config.database_config import SessionLocal

FILE_PATH = "app/common/infra/data/nasdaq_full_tickers.json"

# 나스닥 100 기업 심볼과 한글 이름 매핑
NASDAQ_100_COMPANIES = {
    "AAPL": "애플",
    "MSFT": "마이크로소프트",
    "GOOGL": "알파벳 A",
    "GOOG": "알파벳 C",
    "AMZN": "아마존",
    "NVDA": "엔비디아",
    "TSLA": "테슬라",
    "META": "메타",
    "AVGO": "브로드컴",
    "NFLX": "넷플릭스",
    "ADBE": "어도비",
    "ORCL": "오라클",
    "CRM": "세일즈포스",
    "CSCO": "시스코",
    "QCOM": "퀄컴",
    "INTU": "인튜이트",
    "AMD": "AMD",
    "INTC": "인텔",
    "CMCSA": "컴캐스트",
    "PEP": "펩시코",
    "COST": "코스트코",
    "AMGN": "암젠",
    "TMUS": "T-모바일",
    "AMAT": "어플라이드 머티리얼즈",
    "BKNG": "부킹홀딩스",
    "GILD": "길리어드",
    "REGN": "리제네론",
    "SBUX": "스타벅스",
    "LRCX": "램 리서치",
    "ISRG": "인튜이티브 서지컬",
    "PYPL": "페이팔",
    "ABNB": "에어비앤비",
    "VRTX": "버텍스",
    "PANW": "팰로알토네트웍스",
    "MDLZ": "몬델리즈",
    "LULU": "룰루레몬",
    "KLAC": "KLA",
    "MRVL": "마벨",
    "SNPS": "시놉시스",
    "CDNS": "케이던스",
    "CHTR": "차터커뮤니케이션즈",
    "DDOG": "데이터독",
    "ASML": "ASML",
    "ORLY": "오라일리",
    "CRWD": "크라우드스트라이크",
    "WDAY": "워크데이",
    "ADSK": "오토데스크",
    "BIIB": "바이오젠",
    "PAYX": "페이첵스",
    "NXPI": "NXP",
    "FTNT": "포티넷",
    "FANG": "디아만트백 에너지",
    "MNST": "몬스터 베버리지",
    "MRNA": "모더나",
    "FAST": "파스날",
    "PCAR": "팩카",
    "CTSH": "코그니잔트",
    "ODFL": "올드 도미니언",
    "VRSK": "베리스크",
    "DXCM": "덱스컴",
    "CSGP": "코스타그룹",
    "SGEN": "시애틀 제네틱스",
    "IDXX": "아이덱스",
    "ANSS": "안시스",
    "MCHP": "마이크로칩",
    "ALGN": "얼라인",
    "EBAY": "이베이",
    "CPRT": "코파트",
    "SPLK": "스플렁크",
    "DLTR": "달러트리",
    "ILMN": "일루미나",
    "MTCH": "매치그룹",
    "SIRI": "시리우스XM",
    "PLTR": "팰런티어",
    "TEAM": "아틀라시안",
    "ZBRA": "제브라",
    "ROKU": "로쿠",
    "ENPH": "엔페이즈",
    "BNTX": "바이온테크",
    "HOOD": "로빈후드",
    "COIN": "코인베이스",
    "RIVN": "리비안",
    "SMCI": "슈퍼마이크로",
    "MELI": "메르카도리브레",
    "DKNG": "드래프트킹스",
    "SAIA": "사이아",
    "PLUG": "플러그파워",
    "CCOI": "코그넌트",
    "TTWO": "테이크투",
    "GEHC": "GE 헬스케어",
    "PGEN": "프리시전바이오사이언스",
    "FITB": "피프스써드뱅코프",
    "EXPE": "익스피디아",
    "STLD": "스틸다이내믹스",
    "CTAS": "신타스",
    "FLEX": "플렉스",
    "ICLR": "아이콘",
    "CERE": "세레스",
    "ALNY": "알나일램",
    "PTCT": "PTC 테라퓨틱스",
    "MPWR": "몬놀리식 파워"
}

def import_nasdaq100_symbols():
    """나스닥 100 기업들을 한글 이름과 함께 DB에 저장"""
    
    # JSON 파일 읽기
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # 나스닥 100 기업들만 필터링
    nasdaq100_records = []
    for item in raw:
        if ("symbol" in item and "name" in item and "country" in item and 
            item["symbol"] in NASDAQ_100_COMPANIES):
            nasdaq100_records.append({
                "symbol": item["symbol"],
                "name": item["name"],
                "korea_name": NASDAQ_100_COMPANIES[item["symbol"]],
                "country": item["country"],
            })

    print(f"📊 나스닥 100 기업 중 {len(nasdaq100_records)}개 기업 데이터 발견")
    
    # 찾지 못한 심볼들 체크
    found_symbols = {record["symbol"] for record in nasdaq100_records}
    missing_symbols = set(NASDAQ_100_COMPANIES.keys()) - found_symbols
    if missing_symbols:
        print(f"⚠️  JSON에서 찾지 못한 심볼들 ({len(missing_symbols)}개):")
        for symbol in sorted(missing_symbols):
            print(f"    - {symbol}: {NASDAQ_100_COMPANIES[symbol]}")
    
    # 추가로 발견된 심볼들도 체크
    available_symbols = {item["symbol"] for item in raw if "symbol" in item}
    nasdaq100_in_json = set(NASDAQ_100_COMPANIES.keys()) & available_symbols
    print(f"✓ JSON에서 발견된 나스닥 100 심볼: {len(nasdaq100_in_json)}개")
    print(f"✓ 실제 추출된 데이터: {len(nasdaq100_records)}개")

    session = SessionLocal()
    inserted = 0
    skipped = 0

    try:
        for record in nasdaq100_records:
            symbol = record["symbol"]
            korea_name = record["korea_name"]

            # 이미 존재하는지 확인
            exists = session.scalar(
                select(Symbol).where(Symbol.symbol == symbol)
            )

            if exists:
                print(f"[→] Skipped (exists): {symbol} - {korea_name}")
                skipped += 1
                continue

            # 존재하지 않으면 insert (korea_name 포함)
            session.add(Symbol(
                symbol=record["symbol"],
                name=record["name"],
                korea_name=record["korea_name"],
                country=record["country"]
            ))
            print(f"[+] Added: {symbol} - {korea_name}")
            inserted += 1

        session.commit()
        print(f"\n[✓] 나스닥 100 기업 임포트 완료: {inserted}개 추가, {skipped}개 건너뜀")
        
    except Exception as e:
        session.rollback()
        print(f"[✗] Error during import: {e}")
        raise
    finally:
        session.close()


def run_import():
    print(">>> 나스닥 100 기업 데이터 임포트 시작 (한글 이름 포함)...")
    import_nasdaq100_symbols()
    print(">>> 완료.")


if __name__ == "__main__":
    run_import()