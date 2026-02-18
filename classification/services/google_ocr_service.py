# classification/services/google_ocr_service.py

import os
import json
import base64
from typing import Optional

from google.cloud import vision
from google.oauth2 import service_account


class GoogleOCRService:
    """
    Google Cloud Vision OCR Service
    - ✅ 파일(classification/google_credentials.json) 없이 환경변수만으로 인증 가능
    - 지원 환경변수 우선순위:
        1) GOOGLE_CREDENTIALS_B64  (권장: 서비스계정 JSON 전체를 base64로 인코딩)
        2) GOOGLE_CREDENTIALS_JSON (서비스계정 JSON 문자열)
        3) GOOGLE_APPLICATION_CREDENTIALS (구글 표준: 파일 경로)
    """

    def __init__(self):
        self.client = self._init_client()

    def _load_service_account_info(self) -> Optional[dict]:
        b64 = os.getenv("GOOGLE_CREDENTIALS_B64", "").strip()
        if b64:
            try:
                raw = base64.b64decode(b64).decode("utf-8")
                return json.loads(raw)
            except Exception as e:
                raise RuntimeError(f"GOOGLE_CREDENTIALS_B64 디코딩/파싱 실패: {e}")

        raw_json = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
        if raw_json:
            try:
                return json.loads(raw_json)
            except Exception as e:
                raise RuntimeError(f"GOOGLE_CREDENTIALS_JSON 파싱 실패: {e}")

        return None

    def _init_client(self) -> vision.ImageAnnotatorClient:
        info = self._load_service_account_info()

        # 1) env JSON/B64가 있으면 그걸로 인증
        if info is not None:
            creds = service_account.Credentials.from_service_account_info(info)
            return vision.ImageAnnotatorClient(credentials=creds)

        # 2) GOOGLE_APPLICATION_CREDENTIALS(파일 경로)가 있으면 구글 기본 방식 사용
        #    (이 경우는 파일 기반이지만, 표준 env라서 fallback으로 허용)
        gac = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if gac:
            # vision lib가 내부적으로 파일을 읽음
            return vision.ImageAnnotatorClient()

        # 3) 아무 것도 없으면 명확하게 실패
        raise FileNotFoundError(
            "Google OCR 자격증명이 없습니다. "
            "Render 환경변수에 GOOGLE_CREDENTIALS_B64(권장) 또는 GOOGLE_CREDENTIALS_JSON을 설정하세요."
        )

    def extract_text(self, image_path: str) -> dict:
        """
        이미지에서 OCR 텍스트 추출
        반환 포맷은 기존 코드가 기대하는 형태( dict with full_text )로 유지
        """
        with open(image_path, "rb") as f:
            content = f.read()

        image = vision.Image(content=content)
        response = self.client.text_detection(image=image)

        if response.error and response.error.message:
            raise RuntimeError(f"Vision OCR error: {response.error.message}")

        texts = response.text_annotations
        full_text = texts[0].description if texts else ""

        return {
            "full_text": full_text,
            "raw": [t.description for t in texts[:10]],
        }