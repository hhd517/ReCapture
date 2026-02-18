import hashlib
import time
import uuid
from typing import Dict, Any, Tuple

from django.conf import settings


def _cloudinary_signature(params: Dict[str, Any], api_secret: str) -> str:
    """
    Cloudinary signature:
    - params를 key 기준 정렬해 key=value&... 생성
    - 뒤에 api_secret 붙이고 SHA1
    """
    signable = {}
    for k, v in params.items():
        if v is None:
            continue
        if k in ("file", "signature", "api_key"):
            continue
        signable[k] = v

    to_sign = "&".join(f"{k}={signable[k]}" for k in sorted(signable.keys()))
    raw = f"{to_sign}{api_secret}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _get_cloudinary_creds() -> Tuple[str, str, str]:
    """
    ✅ recapture2 기준(settings.py)에서 CLOUDINARY_STORAGE 딕셔너리를 사용하도록 맞춤
    """
    storage = getattr(settings, "CLOUDINARY_STORAGE", None) or {}

    cloud_name = storage.get("CLOUD_NAME") or getattr(settings, "CLOUDINARY_CLOUD_NAME", None)
    api_key = storage.get("API_KEY") or getattr(settings, "CLOUDINARY_API_KEY", None)
    api_secret = storage.get("API_SECRET") or getattr(settings, "CLOUDINARY_API_SECRET", None)

    if not (cloud_name and api_key and api_secret):
        raise ValueError("CLOUDINARY_ENV_MISSING")

    return cloud_name, api_key, api_secret


def issue_signed_upload_payload(
    *,
    user_id: int,
    filename: str,
    folder_prefix: str = "photos",
) -> Dict[str, Any]:
    """
    프론트가 Cloudinary로 직접 업로드할 때 필요한 payload 반환
    """
    cloud_name, api_key, api_secret = _get_cloudinary_creds()

    ts = int(time.time())
    folder = f"{folder_prefix}/{user_id}"
    public_id = f"{uuid.uuid4().hex}"

    params = {
        "timestamp": ts,
        "folder": folder,
        "public_id": public_id,
    }
    signature = _cloudinary_signature(params, api_secret)

    return {
        "cloud_name": cloud_name,
        "api_key": api_key,
        "timestamp": ts,
        "folder": folder,
        "public_id": public_id,
        "signature": signature,
        "upload_url": f"https://api.cloudinary.com/v1_1/{cloud_name}/auto/upload",
        "filename": filename,
    }