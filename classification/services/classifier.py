# classification/services/classifier.py
import re
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .ocr_service import OCRService
except ImportError:
    from ocr_service import OCRService


class ImageClassifier:
    """규칙 기반 분류 (✅ 9카테고리 버전)"""

    CATS = [
        "booking",
        "food",
        "info",
        "nature",
        "others",
        "people",
        "receipt",
        "shopping",
        "study_note",
    ]

    def __init__(self):
        self.ocr_service = OCRService()

    def classify(self, image_path):
        ocr_result = self.ocr_service.extract_text(image_path)
        text = ocr_result.get("full_text", "") or ""
        scores = self._calculate_scores(text)

        max_score = max(scores.values()) if scores else 0
        category = max(scores, key=scores.get) if scores else "others"
        total_score = sum(scores.values()) if scores else 0

        confidence = (max_score / total_score) if total_score > 0 else 0.0

        # 너무 애매하면 others
        if max_score < 5:
            category = "others"
            confidence = 0.30

        return {
            "category": category,
            "confidence": float(confidence),
            "scores": scores,
            "ocr_text": text,
        }

    def _calculate_scores(self, text: str):
        scores = {c: 0 for c in self.CATS}
        t = (text or "")
        tl = t.lower()

        # =======================
        # receipt (영수증)
        # =======================
        receipt_keywords = ["합계", "카드", "승인", "vat", "부가세", "결제", "영수증", "총액", "과세", "면세", "현금"]
        for kw in receipt_keywords:
            if kw.lower() in tl:
                scores["receipt"] += 3

        money_pattern = r"\d{1,3}(?:,\d{3})*원|\d+원"
        scores["receipt"] += len(re.findall(money_pattern, t)) * 2

        if len(re.findall(r"\d{3,}", t)) > 5:
            scores["receipt"] += 5

        # =======================
        # study_note (학습)
        # =======================
        study_keywords = ["정의", "정리", "증명", "예제", "theorem", "lemma", "proof", "공식", "definition", "미분", "적분"]
        for kw in study_keywords:
            if kw.lower() in tl:
                scores["study_note"] += 3

        math_symbols = ["∫", "∑", "√", "∂", "∆", "α", "β", "π", "≤", "≥", "≠"]
        if sum(t.count(s) for s in math_symbols) > 3:
            scores["study_note"] += 4

        # =======================
        # booking (예약/티켓)
        # =======================
        booking_keywords = ["예약", "티켓", "예매", "좌석", "탑승", "항공", "출발", "도착", "체크인", "숙소", "호텔"]
        for kw in booking_keywords:
            if kw.lower() in tl:
                scores["booking"] += 3

        # =======================
        # shopping (쇼핑/주문)
        # =======================
        shopping_keywords = ["주문", "배송", "구매", "장바구니", "결제완료", "상품", "옵션", "수량", "교환", "반품"]
        for kw in shopping_keywords:
            if kw.lower() in tl:
                scores["shopping"] += 3

        # =======================
        # info (정보캡처)
        # =======================
        info_keywords = ["링크", "코드", "인증번호", "qr", "바코드", "주소", "전화", "메일"]
        for kw in info_keywords:
            if kw.lower() in tl:
                scores["info"] += 3

        if re.search(r"https?://|www\.", tl):
            scores["info"] += 4

        # =======================
        # food (음식) - 매우 약한 힌트
        # =======================
        food_keywords = ["kcal", "칼로리", "단백질", "지방", "탄수화물", "원재료", "알레르기"]
        for kw in food_keywords:
            if kw.lower() in tl:
                scores["food"] += 2

        # =======================
        # people / nature는 OCR만으로는 약해서 기본 0 유지
        # (이미지 모델이 담당)
        # =======================

        return scores
