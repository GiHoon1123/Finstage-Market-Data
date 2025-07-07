from deep_translator import GoogleTranslator

def translate_to_korean(text: str) -> str:
    try:
        return GoogleTranslator(source='auto', target='ko').translate(text)
    except Exception as e:
        print(f"❌ 번역 실패: {e}")
        return ""
