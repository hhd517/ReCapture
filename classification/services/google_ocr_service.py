# classification/services/google_ocr_service.py

import os
import json
import base64
import logging
from typing import Optional

from google.cloud import vision
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


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
        logger.info("🔧 Google OCR Service init() 호출")
        self.client = self._init_client()
        logger.info("✅ Google OCR client 준비 완료")

    def _load_service_account_info(self) -> Optional[dict]:
        b64 = os.getenv("GOOGLE_CREDENTIALS_B64", "").strip()
        if b64:
            logger.info("🔑 OCR Credential source: GOOGLE_CREDENTIALS_B64")
            try:
                raw = base64.b64decode(b64).decode("utf-8")
                return json.loads(raw)
            except Exception as e:
                logger.exception("❌ GOOGLE_CREDENTIALS_B64 디코딩/파싱 실패")
                raise RuntimeError(f"GOOGLE_CREDENTIALS_B64 디코딩/파싱 실패: {e}")

        raw_json = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
        if raw_json:
            logger.info("🔑 OCR Credential source: GOOGLE_CREDENTIALS_JSON")
            try:
                return json.loads(raw_json)
            except Exception as e:
                logger.exception("❌ GOOGLE_CREDENTIALS_JSON 파싱 실패")
                raise RuntimeError(f"GOOGLE_CREDENTIALS_JSON 파싱 실패: {e}")

        return None

    def _init_client(self) -> vision.ImageAnnotatorClient:
        info = self._load_service_account_info()

        # 1) env JSON/B64가 있으면 그걸로 인증
        if info is not None:
            try:
                creds = service_account.Credentials.from_service_account_info(info)
                logger.info("✅ Google OCR 인증 성공 (env JSON/B64)")
                return vision.ImageAnnotatorClient(credentials=creds)
            except Exception:
                logger.exception("❌ Google OCR 인증 실패 (env JSON/B64)")
                raise

        # 2) GOOGLE_APPLICATION_CREDENTIALS(파일 경로)가 있으면 구글 기본 방식 사용
        gac = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if gac:
            logger.info(f"🔑 OCR Credential source: GOOGLE_APPLICATION_CREDENTIALS (path={gac})")
            try:
                client = vision.ImageAnnotatorClient()
                logger.info("✅ Google OCR 인증 성공 (GOOGLE_APPLICATION_CREDENTIALS)")
                return client
            except Exception:
                logger.exception("❌ Google OCR 인증 실패 (GOOGLE_APPLICATION_CREDENTIALS)")
                raise

        # 3) 아무 것도 없으면 명확하게 실패
        logger.warning("⚠️ Google OCR 자격증명 미설정 (env 없음)")
        raise FileNotFoundError(
            "Google OCR 자격증명이 없습니다. "
            "Render 환경변수에 GOOGLE_CREDENTIALS_B64(권장) 또는 GOOGLE_CREDENTIALS_JSON을 설정하세요."
        )

    def extract_text(self, image_path: str) -> dict:
        """
        이미지에서 OCR 텍스트 추출
        반환 포맷은 기존 코드가 기대하는 형태( dict with full_text )로 유지
        """
        # 🔍 OCR이 실제 호출되는지 확인용 로그
        try:
            size = os.path.getsize(image_path)
        except Exception:
            size = -1
        logger.info(f"🧾 OCR extract_text() 호출: path={image_path} size={size}B")

        try:
            with open(image_path, "rb") as f:
                content = f.read()

            image = vision.Image(content=content)
            response = self.client.text_detection(image=image)

            if response.error and response.error.message:
                logger.error(f"❌ Vision OCR error: {response.error.message}")
                raise RuntimeError(f"Vision OCR error: {response.error.message}")

            texts = response.text_annotations
            full_text = texts[0].description if texts else ""

            # 민감정보 보호: 원문 전체는 안 찍고 길이만 출력
            logger.info(
                f"✅ OCR 완료: annotations={len(texts)} full_text_len={len(full_text)}"
            )

            # 원하면 아주 일부만 확인 (개인정보/민감정보 위험 있으니 기본은 OFF)
            preview = os.getenv("OCR_LOG_PREVIEW", "0").strip() == "1"
            if preview and full_text:
                safe_preview = full_text.replace("\n", " ")[:80]
                logger.info(f"🔎 OCR preview(80 chars): {safe_preview}")

            return {
                "full_text": full_text,
                "raw": [t.description for t in texts[:10]],
            }

        except Exception:
            logger.exception("❌ OCR 처리 중 예외 발생")
            raise