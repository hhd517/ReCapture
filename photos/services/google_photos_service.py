# photos/services/google_photos_service.py
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleAuthRequest

import os
import requests


class GooglePhotosService:
    """Google Photos Picker API 연동 서비스"""

    SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/photospicker.mediaitems.readonly",
    ]

    PICKER_BASE_URL = "https://photospicker.googleapis.com/v1"

    def __init__(self, google_credential=None):
        self.google_credential = google_credential
        self.credentials = None

        if google_credential:
            self.credentials = self._build_credentials(google_credential)

    def _build_credentials(self, google_credential):
        """GoogleCredential 모델로부터 Credentials 객체 생성"""
        return Credentials(
            token=google_credential.access_token,
            refresh_token=google_credential.refresh_token,
            token_uri=google_credential.token_uri,
            client_id=google_credential.client_id,
            client_secret=google_credential.client_secret,
            scopes=google_credential.scopes,
        )

    def _save_refreshed_token(self):
        """refresh로 갱신된 access_token을 DB에 반영"""
        if not self.google_credential:
            return
        if not self.credentials or not self.credentials.token:
            return

        self.google_credential.access_token = self.credentials.token

        # refresh_token은 보통 그대로지만, 갱신되면 반영
        if getattr(self.credentials, "refresh_token", None):
            self.google_credential.refresh_token = self.credentials.refresh_token

        # scopes 반영
        try:
            if getattr(self.credentials, "scopes", None):
                self.google_credential.scopes = self.credentials.scopes
        except Exception:
            pass

        self.google_credential.save(update_fields=["access_token", "refresh_token", "scopes", "updated_at"])

    def _refresh_force(self) -> bool:
        """
        ✅ expiry 정보가 없어도 401이 오면 refresh가 필요할 수 있음.
        refresh_token이 있으면 무조건 refresh 시도.
        """
        if not self.credentials:
            return False
        if not getattr(self.credentials, "refresh_token", None):
            return False

        try:
            self.credentials.refresh(GoogleAuthRequest())
            self._save_refreshed_token()
            return True
        except Exception:
            return False

    def _auth_headers(self):
        if not self.credentials:
            raise ValueError("Google credentials not set")

        if not self.credentials.token:
            raise ValueError("Google credentials token missing")

        return {"Authorization": f"Bearer {self.credentials.token}"}

    @staticmethod
    def get_authorization_url(redirect_uri):
        """OAuth 인증 URL 생성"""
        client_config = {
            "web": {
                "client_id": os.getenv("GOOGLE_PHOTOS_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_PHOTOS_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=GooglePhotosService.SCOPES,
            redirect_uri=redirect_uri,
        )

        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        return auth_url, state

    @staticmethod
    def exchange_code_for_tokens(code, redirect_uri):
        """인증 코드를 토큰으로 교환"""
        client_config = {
            "web": {
                "client_id": os.getenv("GOOGLE_PHOTOS_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_PHOTOS_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=GooglePhotosService.SCOPES,
            redirect_uri=redirect_uri,
        )

        flow.fetch_token(code=code)
        credentials = flow.credentials

        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()

        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,  # None일 수 있음
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "google_email": user_info.get("email"),
        }

    # -------------------------
    # Picker API 핵심 플로우
    # -------------------------

    def create_picker_session(self):
        """Picker 세션 생성"""
        url = f"{self.PICKER_BASE_URL}/sessions"
        resp = requests.post(url, headers=self._auth_headers(), json={})

        # ✅ 401이면 만료/무효 토큰 가능 → 강제 refresh 후 1회 재시도
        if resp.status_code == 401:
            if self._refresh_force():
                resp = requests.post(url, headers=self._auth_headers(), json={})

        resp.raise_for_status()
        data = resp.json()

        return {
            "sessionId": data.get("id"),
            "pickerUri": data.get("pickerUri"),
            "raw": data,
        }

    def get_picker_session(self, session_id):
        """세션 상태 조회"""
        if not session_id:
            raise ValueError("session_id is required")

        url = f"{self.PICKER_BASE_URL}/sessions/{session_id}"
        resp = requests.get(url, headers=self._auth_headers())

        if resp.status_code == 401:
            if self._refresh_force():
                resp = requests.get(url, headers=self._auth_headers())

        resp.raise_for_status()
        return resp.json()

    def list_picked_media_items(self, session_id, page_size=100, page_token=None):
        """유저가 Picker에서 선택한 미디어 아이템 목록 조회"""
        if not session_id:
            raise ValueError("session_id is required")

        url = f"{self.PICKER_BASE_URL}/mediaItems"
        params = {"sessionId": session_id, "pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(url, headers=self._auth_headers(), params=params)

        if resp.status_code == 401:
            if self._refresh_force():
                resp = requests.get(url, headers=self._auth_headers(), params=params)

        resp.raise_for_status()
        data = resp.json()

        return {
            "items": data.get("mediaItems", []),
            "nextPageToken": data.get("nextPageToken"),
        }

    # -------------------------
    # 기존 이름 유지용 (호환)
    # -------------------------

    def get_photos(self, page_size=100, page_token=None, session_id=None):
        return self.list_picked_media_items(
            session_id=session_id,
            page_size=page_size,
            page_token=page_token,
        )

    def get_photos_since(self, since_date, page_size=100):
        raise NotImplementedError(
            "Google Photos Picker API에서는 날짜 기반 전체 조회(get_photos_since)를 지원하지 않습니다. "
            "사용자가 Picker에서 선택한 항목만 가져올 수 있습니다."
        )

    def download_photo(self, media_item, save_path):
        """사진 다운로드"""
        base_url = media_item.get("baseUrl")
        if not base_url:
            media_file = media_item.get("mediaFile") or {}
            base_url = media_file.get("baseUrl")

        if not base_url:
            raise ValueError("No baseUrl in media item")

        download_url = f"{base_url}=d"

        resp = requests.get(download_url, headers=self._auth_headers(), timeout=60)

        if resp.status_code == 401:
            if self._refresh_force():
                resp = requests.get(download_url, headers=self._auth_headers(), timeout=60)

        resp.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(resp.content)

        return save_path