# classification/services/classifier.py

import re
import os
import sys

# 상위 폴더 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .ocr_service import OCRService
except ImportError:
    from ocr_service import OCRService

class ImageClassifier:
    """이미지 1차 분류 서비스 (영수증/수업자료/정보캡처/기타)"""
    
    def __init__(self):
        self.ocr_service = OCRService()
    
    def classify(self, image_path):
        """
        이미지 분류
        
        Args:
            image_path (str): 이미지 파일 경로
            
        Returns:
            dict: {
                'category': 'receipt' | 'study' | 'info' | 'misc',
                'confidence': 0.0 ~ 1.0,
                'scores': {...},
                'ocr_text': str
            }
        """
        # OCR 텍스트 추출
        ocr_result = self.ocr_service.extract_text(image_path)
        text = ocr_result['full_text']
        
        # 점수 계산
        scores = self._calculate_scores(text)
        
        # 카테고리 결정
        max_score = max(scores.values())
        category = max(scores, key=scores.get)
        total_score = sum(scores.values())
        
        # 확신도 계산
        confidence = max_score / total_score if total_score > 0 else 0
        
        # 점수가 너무 낮으면 misc
        if max_score < 5:
            category = 'misc'
            confidence = 0.3
        
        return {
            'category': category,
            'confidence': confidence,
            'scores': scores,
            'ocr_text': text
        }
    
    def _calculate_scores(self, text):
        """규칙 기반 점수 계산"""
        scores = {
            'receipt': 0,
            'study': 0,
            'info': 0,
            'misc': 0
        }
        
        text_lower = text.lower()
        
        # === 영수증 규칙 ===
        # 영수증 키워드 (점수 높임)
        receipt_keywords = ['합계', '카드', '승인', 'vat', '부가세', '결제', '영수증', 
                           '총액', '과세', '면세', '현금', '받은금액']
        for kw in receipt_keywords:
            if kw in text_lower:
                scores['receipt'] += 3
        
        # 금액 패턴 (원 포함)
        money_pattern = r'\d{1,3}(?:,\d{3})*원|\d+원'
        money_matches = re.findall(money_pattern, text)
        scores['receipt'] += len(money_matches) * 2
        
        # 숫자가 많은 라인 (영수증 특징)
        number_lines = len(re.findall(r'\d{3,}', text))
        if number_lines > 5:
            scores['receipt'] += 5
        
        # 날짜 패턴
        date_pattern = r'\d{4}[-./]\d{1,2}[-./]\d{1,2}|\d{2}[-./]\d{2}'
        if re.search(date_pattern, text):
            scores['receipt'] += 2
        
        # === 수업자료 규칙 ===
        # 수업 키워드
        study_keywords = ['정의', '정리', '증명', '예제', 'theorem', 'lemma', 
                         '함수', '미분', '적분', '조건', 'proof', '공식', 'definition']
        for kw in study_keywords:
            if kw in text_lower:
                scores['study'] += 3
        
        # 수식 기호
        math_symbols = ['∫', '∑', '√', '∂', '∆', 'α', 'β', 'π', '≤', '≥', '≠']
        symbol_count = sum(text.count(s) for s in math_symbols)
        if symbol_count > 3:
            scores['study'] += 4
        
        # === 정보캡처 규칙 ===
        # 정보캡처 키워드
        info_keywords = ['예약', '쿠폰', '링크', '배송', '주문', '코드', '인증번호', 'qr']
        for kw in info_keywords:
            if kw in text_lower:
                scores['info'] += 3
        
        # URL 패턴
        url_pattern = r'https?://|www\.'
        if re.search(url_pattern, text_lower):
            scores['info'] += 4
        
        return scores


# 테스트용
if __name__ == "__main__":
    classifier = ImageClassifier()
    
    # 테스트 이미지 경로
    test_image = "test_data/study/study1.png"
    
    if os.path.exists(test_image):
        print(" 분류 시작...\n")
        result = classifier.classify(test_image)
        
        print(f" 카테고리: {result['category']}")
        print(f" 확신도: {result['confidence']:.0%}")
        print(f" 점수: {result['scores']}")
        print(f"\n OCR 텍스트:\n{result['ocr_text'][:200]}...")
    else:
        print(f" 테스트 이미지가 없습니다: {test_image}")