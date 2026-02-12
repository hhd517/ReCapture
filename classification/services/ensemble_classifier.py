# services/ensemble_classifier.py
import os
import sys
import re

# 프로젝트 루트 경로 설정 (services 폴더의 상위 폴더를 참조하기 위함)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.google_ocr_service import GoogleOCRService
from services.image_classifier import ImageClassifier
from services.text_classifier import TextClassifier
from services.ocr_cache import OCRCache


class EnsembleClassifier:
    """
    ✅ 개선된 앙상블 (최종 4카테고리)
    - Vision First
    - OCR trigger를 conf 뿐 아니라 "margin"도 사용
    - 텍스트 강한 클래스는 더 신뢰(클래스별 threshold)
    - finance/info/study_note는 텍스트 힌트로 보정
    """

    # ✅ 4카테고리
    CATS = [
        "finance",
        "study_note",
        "info",
        "others",
    ]

    CATEGORY_KR = {
        "finance": "결제/예약",
        "study_note": "학습/노트",
        "info": "정보",
        "others": "기타",
    }

    # OCR이 강한 클래스(문서류)
    OCR_STRONG = {"finance", "info", "study_note"}

    # ✅ 클래스별 텍스트 override threshold (4카테고리)
    TEXT_OVERRIDE_TH = {
        "finance": 0.72,
        "info": 0.75,
        "study_note": 0.75,
        "others": 0.90,
    }

    def __init__(self):
        print("🚀 통합 분류 시스템 초기화 중...\n")

        # OCR 서비스
        try:
            self.ocr = GoogleOCRService()
        except Exception as e:
            print(f"⚠️ Google OCR 초기화 실패: {e}")
            print("   -> google_credentials.json 경로/환경변수를 확인하세요.")
            self.ocr = None

        # OCR 캐시
        self.ocr_cache = OCRCache(cache_dir="ocr_cache")

        # 이미지 모델
        self.image_clf = ImageClassifier()

        # 텍스트 모델(없어도 돌아가게)
        try:
            self.text_clf = TextClassifier()
        except Exception as e:
            print(f"⚠️ TextClassifier 로드 실패 → 텍스트 보정 스킵: {e}")
            self.text_clf = None

        # OCR 트리거 (문서성/텍스트성 강한 것들)
        self.ocr_triggers = ["finance", "info", "study_note"]

        print("✅ 모든 모델 로드 완료!\n")

    def _get_ocr_text_cached(self, image_path: str, logs: list) -> str:
        if self.ocr is None:
            logs.append("⚠️ OCR 서비스가 없어 OCR 스킵")
            return ""

        cached = self.ocr_cache.load(image_path)
        if cached is not None:
            logs.append("⚡ OCR CACHE HIT (재호출 없음)")
            if isinstance(cached, dict):
                return cached.get("full_text", "") or ""
            return str(cached)

        logs.append("🧠 OCR CACHE MISS (OCR 호출)")
        ocr_result = self.ocr.extract_text(image_path)

        if isinstance(ocr_result, dict):
            self.ocr_cache.save(image_path, ocr_result)
            return ocr_result.get("full_text", "") or ""

        wrapped = {"full_text": str(ocr_result)}
        self.ocr_cache.save(image_path, wrapped)
        return wrapped["full_text"]

    # ✅ 텍스트 힌트 점수(가벼운 규칙 기반) - 4카테고리
    def _text_hint_scores(self, text: str):
        t = (text or "")
        tl = t.lower()

        scores = {"finance": 0, "study_note": 0, "info": 0}

        # -----------------------
        # finance 힌트 (결제/예약/주문/영수증 다 포함)
        # -----------------------
        if re.search(r"\d{1,3}(?:,\d{3})*원|\d+원", t):
            scores["finance"] += 3

        for kw in [
            # 영수증/결제
            "합계", "승인", "카드", "영수증", "부가세", "vat", "과세", "면세", "총액", "결제",
            # 예약/티켓
            "예약", "티켓", "예매", "좌석", "체크인", "출발", "도착", "탑승", "호텔", "숙소",
            # 쇼핑/주문
            "주문", "배송", "상품", "옵션", "수량", "장바구니", "구매", "반품", "교환", "결제완료",
        ]:
            if kw.lower() in tl:
                scores["finance"] += 2

        # -----------------------
        # study_note 힌트
        # -----------------------
        for kw in ["정리", "정의", "증명", "theorem", "lemma", "proof", "예제", "공식", "미분", "적분"]:
            if kw.lower() in tl:
                scores["study_note"] += 2

        # -----------------------
        # info 힌트
        # -----------------------
        if re.search(r"https?://|www\.", tl):
            scores["info"] += 4
        for kw in ["링크", "주소", "전화", "메일", "인증", "코드", "qr", "바코드"]:
            if kw.lower() in tl:
                scores["info"] += 2

        return scores

    def classify(self, image_path: str):
        logs = []

        # ---------------------------------------------------
        # Step 1. 비전 모델 (+ margin)
        # ---------------------------------------------------
        if hasattr(self.image_clf, "predict_proba"):
            img_cat, img_conf, img2_cat, img2_conf, margin = self.image_clf.predict_proba(image_path)
            logs.append(
                f"👁️ 비전 top1: {img_cat} ({img_conf*100:.1f}%), top2: {img2_cat} ({img2_conf*100:.1f}%), margin={margin:.3f}"
            )
        else:
            img_cat, img_conf = self.image_clf.predict(image_path)
            img2_cat, img2_conf, margin = None, 0.0, 1.0
            logs.append(f"👁️ 비전 예측: {img_cat} ({img_conf*100:.1f}%)")

        final_cat, final_conf = img_cat, img_conf

        ocr_text = ""
        text_cat, text_conf = None, 0.0

        # ---------------------------------------------------
        # Step 2. OCR 발동 조건 강화
        # - trigger OR conf 낮음 OR margin 낮음(애매함)
        # ---------------------------------------------------
        is_trigger = img_cat in self.ocr_triggers
        is_uncertain = img_conf < 0.60
        is_ambiguous = margin < 0.12

        if is_trigger or is_uncertain or is_ambiguous:
            logs.append(f"🚨 OCR 시작 (trigger={is_trigger}, uncertain={is_uncertain}, ambiguous={is_ambiguous})")

            # 텍스트 모델 없으면 OCR 텍스트만 기록하고 종료
            if self.text_clf is None:
                ocr_text = self._get_ocr_text_cached(image_path, logs)
                logs.append("⚠️ 텍스트 모델 없음 → 이미지 결과 유지")
            else:
                try:
                    ocr_text = self._get_ocr_text_cached(image_path, logs)
                    cleaned = (ocr_text or "").strip()

                    if len(cleaned) < 3:
                        logs.append("❌ OCR 글자 거의 없음 → 이미지 결과 유지")
                    else:
                        # ---------------------------------------------------
                        # Step 3. 텍스트 모델
                        # ---------------------------------------------------
                        text_cat, text_conf = self.text_clf.predict(cleaned)
                        logs.append(f"🧠 텍스트 예측: {text_cat} ({text_conf*100:.1f}%)")

                        # ---------------------------------------------------
                        # Step 3.5 텍스트 힌트 보정 (finance/info/study_note)
                        # ---------------------------------------------------
                        hints = self._text_hint_scores(cleaned)
                        best_hint = max(hints, key=hints.get)
                        best_hint_score = hints[best_hint]

                        if best_hint_score >= 4:
                            boosted = min(text_conf + 0.08, 0.98)
                            logs.append(
                                f"✨ 텍스트 힌트 강함: {best_hint} (score={best_hint_score}) → conf boost {text_conf:.2f}->{boosted:.2f}"
                            )
                            text_conf = boosted
                            # 힌트가 강한데 text 라벨이 애매하면 힌트를 후보로 올림
                            if (text_cat not in self.CATS) or (text_conf < 0.80):
                                text_cat = best_hint

                        # ---------------------------------------------------
                        # Step 4. 최종 판결 (클래스별 threshold)
                        # ---------------------------------------------------
                        if text_cat in self.CATS:
                            th = self.TEXT_OVERRIDE_TH.get(text_cat, 0.85)

                            # (1) 텍스트가 충분히 강하면 덮어쓰기
                            if text_conf >= th:
                                final_cat, final_conf = text_cat, text_conf
                                logs.append(f"✅ 텍스트 덮어쓰기 (th={th:.2f})")

                            # (2) 의견 일치면 확신도 증가
                            elif text_cat == img_cat:
                                final_conf = min((img_conf + text_conf) / 2 + 0.08, 0.99)
                                logs.append("✅ 의견 일치 → 확신도 증가")

                            else:
                                logs.append("ℹ️ 텍스트가 애매 → 이미지 유지")
                        else:
                            logs.append("ℹ️ 텍스트 라벨이 4카테고리 밖 → 이미지 유지")

                except Exception as e:
                    logs.append(f"⚠️ OCR/텍스트 파이프라인 실패: {e}")

        else:
            logs.append("💨 시각 정보 확실함 (OCR 생략)")

        return {
            "category": final_cat,
            "final_category_kr": self.CATEGORY_KR.get(final_cat, "알수없음"),
            "confidence": round(float(final_conf), 4),
            "image_result": {"category": img_cat, "confidence": float(img_conf)},
            "text_result": {"category": text_cat, "confidence": float(text_conf)},
            "ocr_text_preview": (ocr_text or "")[:100],
            "logs": logs,
        }


if __name__ == "__main__":
    clf = EnsembleClassifier()

    # ✅ 4카테고리 테스트 구조
    TEST_ROOT = "test_data"
    CATS = ["finance", "study_note", "info", "others"]
    EXTS = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif")

    PER_CLASS_LIMIT = 50

    stats = {c: {"total": 0, "correct": 0} for c in CATS}
    confusion = {t: {p: 0 for p in CATS} for t in CATS}

    total = 0
    correct_total = 0

    img_correct_total = 0
    img_stats = {c: {"total": 0, "correct": 0} for c in CATS}

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

            pred_final = result["category"]
            pred_img = result["image_result"]["category"]

            total += 1
            stats[true_cat]["total"] += 1
            img_stats[true_cat]["total"] += 1

            is_correct = (pred_final == true_cat)
            if is_correct:
                correct_total += 1
                stats[true_cat]["correct"] += 1

            is_img_correct = (pred_img == true_cat)
            if is_img_correct:
                img_correct_total += 1
                img_stats[true_cat]["correct"] += 1

            pred_key = pred_final if pred_final in CATS else "others"
            confusion[true_cat][pred_key] += 1

            print(f"\n📄 {true_cat}/{fn}")
            print(
                f"🏆 최종: {result['final_category_kr']} ({result['confidence']*100:.1f}%) "
                f"{'✅' if is_correct else '❌'}"
            )
            print(
                f"   - image: {result['image_result']['category']} "
                f"({result['image_result']['confidence']*100:.1f}%)"
                f"{' ✅' if is_img_correct else ''}"
            )
            print(f"   - text : {result['text_result']['category']} ({result['text_result']['confidence']*100:.1f}%)")
            print(f"   - ocr  : {result['ocr_text_preview'].replace(chr(10), ' ')[:80]}...")
            for log in result["logs"]:
                print(f"   {log}")

            print("-" * 70)

    def pct(a, b):
        return (a / b * 100.0) if b else 0.0

    print("\n" + "=" * 70)
    print("📊 SUMMARY REPORT")
    print("=" * 70)

    print(f"✅ Final Accuracy: {correct_total}/{total} = {pct(correct_total, total):.2f}%")
    print(f"🖼️ Image-only Accuracy: {img_correct_total}/{total} = {pct(img_correct_total, total):.2f}%")

    print("\n📌 Per-class Accuracy (Final):")
    for c in CATS:
        t = stats[c]["total"]
        k = stats[c]["correct"]
        print(f" - {c:10s}: {k:4d}/{t:4d} = {pct(k, t):6.2f}%")

    print("\n📌 Per-class Accuracy (Image-only):")
    for c in CATS:
        t = img_stats[c]["total"]
        k = img_stats[c]["correct"]
        print(f" - {c:10s}: {k:4d}/{t:4d} = {pct(k, t):6.2f}%")

    print("\n📌 Confusion Matrix (counts) [TRUE -> PRED]")
    header = "TRUE\\PRED".ljust(12) + "".join([p.rjust(12) for p in CATS])
    print(header)
    print("-" * len(header))
    for t in CATS:
        row = t.ljust(12)
        for p in CATS:
            row += str(confusion[t][p]).rjust(12)
        print(row)

    print(f"\n✅ Done. total tested = {total}")
