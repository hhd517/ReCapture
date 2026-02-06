# services/ensemble_classifier.py
import os
import sys

# 최종 파이프라인(실제 분류기)
# 프로젝트 루트 경로 설정 (services 폴더의 상위 폴더를 참조하기 위함)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.google_ocr_service import GoogleOCRService
from services.image_classifier import ImageClassifier
from services.text_classifier import TextClassifier

# ✅ 학습 때 쓰던 OCR 캐시
from services.ocr_cache import OCRCache


class EnsembleClassifier:
    """
    🚀 스마트 통합 분류기 (4개 카테고리 최적화 버전)
    카테고리: finance(금융), study_note(학습), info(정보), others(기타)
    전략: Vision First (속도) -> Text Confirmation (정확도)
    """

    def __init__(self):
        print("🚀 통합 분류 시스템 초기화 중...\n")

        # ✅ OCR 서비스 초기화
        try:
            self.ocr = GoogleOCRService()
        except Exception as e:
            print(f"⚠️ Google OCR 초기화 실패: {e}")
            print("   -> google_credentials.json 경로/환경변수를 확인하세요.")
            self.ocr = None  # OCR을 못 쓰면 이미지 모델만이라도 돌리게

        # ✅ OCR 캐시 초기화 (학습 때랑 동일)
        # 실행 위치(CWD)가 classification이면 classification/ocr_cache 를 쓰게 됨
        self.ocr_cache = OCRCache(cache_dir="ocr_cache")

        # ✅ 분류기 로드
        self.image_clf = ImageClassifier()
        self.text_clf = TextClassifier()

        # 🚦 OCR 검문이 필요한 카테고리 (Trigger)
        self.ocr_triggers = ['finance', 'info', 'study_note']

        print("✅ 모든 모델 로드 완료!\n")

    def _get_ocr_text_cached(self, image_path: str, logs: list) -> str:
        """
        (1) 캐시 있으면 캐시 사용
        (2) 캐시 없으면 OCR 호출 후 캐시에 저장
        반환: full_text 문자열
        """
        if self.ocr is None:
            logs.append("⚠️ OCR 서비스가 없어 OCR 스킵")
            return ""

        # 1) 캐시 로드 (sha256 파일명 기반)
        cached = self.ocr_cache.load(image_path)
        if cached is not None:
            logs.append("⚡ OCR CACHE HIT (재호출 없음)")
            if isinstance(cached, dict):
                return cached.get("full_text", "") or ""
            return str(cached)

        logs.append("🧠 OCR CACHE MISS (OCR 호출)")

        # 2) OCR 호출
        ocr_result = self.ocr.extract_text(image_path)

        # 3) 캐시에 저장 (학습 때처럼 dict를 저장)
        if isinstance(ocr_result, dict):
            self.ocr_cache.save(image_path, ocr_result)
            return ocr_result.get("full_text", "") or ""
        else:
            wrapped = {"full_text": str(ocr_result)}
            self.ocr_cache.save(image_path, wrapped)
            return wrapped["full_text"]

    def classify(self, image_path: str):
        """
        Args:
            image_path (str): 이미지 경로
        Returns:
            dict: 최종 분류 결과 (한국어 포함)
        """
        logs = []

        # ---------------------------------------------------
        # Step 1. 비전 모델 (속도 빠름 ⚡)
        # ---------------------------------------------------
        img_cat, img_conf = self.image_clf.predict(image_path)
        logs.append(f"👁️ 비전 예측: {img_cat} ({img_conf*100:.1f}%)")

        final_cat = img_cat
        final_conf = img_conf

        ocr_text = ""
        text_cat = None
        text_conf = 0.0

        # ---------------------------------------------------
        # Step 2. OCR 발동 조건 체크 (Smart Trigger 🚦)
        # ---------------------------------------------------
        is_document = img_cat in self.ocr_triggers
        is_uncertain = img_conf < 0.6

        if is_document or is_uncertain:
            logs.append(f"🚨 OCR 검문 시작 (사유: {img_cat} 타입 or 확신 부족)")

            try:
                # ✅ (캐시) OCR 텍스트 얻기
                ocr_text = self._get_ocr_text_cached(image_path, logs)

                if len((ocr_text or "").strip()) < 5:
                    logs.append("❌ OCR 글자 거의 없음 → 이미지 결과 유지")
                else:
                    # -----------------------------------------------
                    # Step 3. 텍스트 모델 (정확도 높음 🧠)
                    # -----------------------------------------------
                    text_cat, text_conf = self.text_clf.predict(ocr_text)
                    logs.append(f"🧠 텍스트 예측: {text_cat} ({text_conf*100:.1f}%)")

                    # -----------------------------------------------
                    # Step 4. 최종 판결 (Conflict Resolution)
                    # -----------------------------------------------
                    if text_conf > 0.8:
                        final_cat = text_cat
                        final_conf = text_conf
                        logs.append("✅ 텍스트 확신 높음 → 결과 덮어쓰기")

                    elif img_cat != text_cat:
                        if text_cat != 'others':
                            final_cat = text_cat
                            final_conf = text_conf
                            logs.append("✅ 의견 불일치 → 텍스트 결과 우선")
                        else:
                            logs.append("✅ 텍스트가 others → 이미지 결과 유지")

                    else:
                        final_conf = min((img_conf + text_conf) / 2 + 0.1, 0.99)
                        logs.append("✅ 의견 일치 → 확신도 증가")

            except Exception as e:
                logs.append(f"⚠️ OCR/텍스트 파이프라인 실패: {e}")

        else:
            logs.append("💨 시각 정보 확실함 (OCR 생략)")

        # ---------------------------------------------------
        # Step 5. 한국어 변환 및 반환
        # ---------------------------------------------------
        category_kr_map = {
            'finance': '결제/금융',
            'study_note': '학습/노트',
            'info': '정보',
            'others': '기타(비정보)'
        }

        return {
            'category': final_cat,
            'final_category_kr': category_kr_map.get(final_cat, '알수없음'),
            'confidence': round(float(final_conf), 4),
            'image_result': {'category': img_cat, 'confidence': float(img_conf)},
            'text_result': {'category': text_cat, 'confidence': float(text_conf)},
            'ocr_text_preview': (ocr_text or "")[:100],
            'logs': logs
        }


if __name__ == "__main__":
    clf = EnsembleClassifier()

    TEST_ROOT = "test_data"
    CATS = ["finance", "info", "others", "study_note"]
    EXTS = (".jpg", ".jpeg", ".png", ".webp")

    # 폴더당 몇 장 테스트할지 (None이면 전부)
    PER_CLASS_LIMIT = 50

    total = 0

    if not os.path.isdir(TEST_ROOT):
        print(f"\n⚠️ {TEST_ROOT} 폴더가 없습니다.")
        raise SystemExit(0)

    print(f"\n📸 test_root = {TEST_ROOT}")
    print("=" * 70)

    for true_cat in CATS:
        cat_dir = os.path.join(TEST_ROOT, true_cat)
        if not os.path.isdir(cat_dir):
            print(f"⚠️ 폴더 없음: {cat_dir}")
            continue

        files = [f for f in os.listdir(cat_dir) if f.lower().endswith(EXTS)]
        files.sort()
        if PER_CLASS_LIMIT is not None:
            files = files[:PER_CLASS_LIMIT]

        print(f"\n🗂️ [{true_cat}] {len(files)}장 테스트 시작")

        for fn in files:
            img_path = os.path.join(cat_dir, fn)
            result = clf.classify(img_path)
            total += 1

            print(f"\n📄 {true_cat}/{fn}")
            print(f"🏆 최종: {result['final_category_kr']} ({result['confidence']*100:.1f}%)")
            print(f"   - image: {result['image_result']['category']} ({result['image_result']['confidence']*100:.1f}%)")
            print(f"   - text : {result['text_result']['category']} ({result['text_result']['confidence']*100:.1f}%)")
            print(f"   - ocr  : {result['ocr_text_preview'].replace(chr(10), ' ')[:80]}...")
            for log in result["logs"]:
                print(f"   {log}")

            print("-" * 70)

    print(f"\n✅ Done. total tested = {total}")
