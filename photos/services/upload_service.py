# photos/services/upload_service.py

import uuid
import hashlib
from datetime import datetime
from typing import Dict, Optional

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile


from PIL import Image, ExifTags, ImageOps
import imagehash


# =========================
# Hash Utils (bytes 기반)
# =========================

def _calculate_sha256_bytes(data: bytes) -> str:
    sha256 = hashlib.sha256()
    sha256.update(data)
    return sha256.hexdigest()


def _calculate_image_hashes(image: Image.Image) -> Dict[str, str]:
    # imagehash는 RGB/그레이 모두 동작하지만, 일관성을 위해 RGB 기준으로 계산
    return {
        "phash": str(imagehash.phash(image)),
        "dhash": str(imagehash.dhash(image)),
        "ahash": str(imagehash.average_hash(image)),
    }


# =========================
# Image Utils
# =========================

def _extract_exif_taken_at(image: Image.Image) -> Optional[datetime]:
    """
    EXIF DateTimeOriginal 추출. 없으면 None.
    """
    try:
        exif = image._getexif()
        if not exif:
            return None

        for tag, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag)
            if tag_name == "DateTimeOriginal":
                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None
    return None


def _create_thumbnail(image: Image.Image, size=(300, 300)) -> Image.Image:
    thumb = image.copy()
    thumb.thumbnail(size)
    return thumb


def _pil_to_jpeg_bytes(image: Image.Image, quality: int) -> bytes:
    """
    PIL Image -> JPEG bytes
    - 알파 채널이 있으면 흰 배경으로 합성
    """
    from io import BytesIO

    img = image

    # 알파가 있는 경우(예: PNG) → 흰 배경에 합성 후 RGB로 저장
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        # alpha channel 가져오기
        if img.mode == "RGBA":
            alpha = img.split()[-1]
            bg.paste(img, mask=alpha)
        elif img.mode == "LA":
            alpha = img.split()[-1]
            bg.paste(img.convert("RGBA"), mask=alpha)
        else:
            # P mode with transparency
            bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
        img = bg
    else:
        img = img.convert("RGB")

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


# =========================
# Main Service
# =========================

def save_uploaded_file(user, uploaded_file: UploadedFile) -> Dict:
    """
    업로드된 이미지 파일을 default_storage(운영: Cloudinary)에 저장하고 메타데이터 추출

    반환값:
    - storage_name: 원본 이미지가 저장된 storage key(name)  (DB image 필드에 저장)
    - thumb_storage_name: 썸네일 저장된 storage key(name)   (선택 활용)
    - url / thumb_url: 절대 URL
    """
    user_id = user.id
    original_name = getattr(uploaded_file, "name", "uploaded")

    # 1) 원본 파일 bytes 확보
    try:
        file_bytes = uploaded_file.read()
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
    except Exception as e:
        raise ValueError(f"FILE_READ_FAILED: {e}")

    if not file_bytes:
        raise ValueError("EMPTY_FILE")

    # 2) PIL 로드 + EXIF 회전 보정 + RGB 통일
    from io import BytesIO

    try:
        image = Image.open(BytesIO(file_bytes))
        # 폰 사진 회전 EXIF 반영(가장 흔한 운영 이슈)
        image = ImageOps.exif_transpose(image)
    except Exception as e:
        raise ValueError(f"INVALID_IMAGE: {e}")

    width, height = image.size
    file_size = len(file_bytes)

    # 3) 해시/메타
    file_hash = _calculate_sha256_bytes(file_bytes)

    # hash는 RGB 기반으로 통일(알파/팔레트 제거)
    image_for_hash = image.convert("RGB")
    image_hashes = _calculate_image_hashes(image_for_hash)

    taken_at = _extract_exif_taken_at(image)

    # 4) 저장 파일명(확장자/실데이터 불일치 방지 위해 jpg 고정)
    unique_name = f"{uuid.uuid4().hex}.jpg"

    # Cloudinary에 저장될 “경로(폴더)”를 name에 포함시켜 관리
    photo_key = f"photos/{user_id}/{unique_name}"
    thumb_key = f"thumbnails/{user_id}/{unique_name}"

    saved_photo_name = None
    saved_thumb_name = None

    try:
        # 5) 원본/썸네일을 JPEG bytes로 만들어 storage에 저장
        photo_bytes = _pil_to_jpeg_bytes(image, quality=95)

        thumb_image = _create_thumbnail(image)
        thumb_bytes = _pil_to_jpeg_bytes(thumb_image, quality=85)

        saved_photo_name = default_storage.save(photo_key, ContentFile(photo_bytes))
        saved_thumb_name = default_storage.save(thumb_key, ContentFile(thumb_bytes))

        photo_url = default_storage.url(saved_photo_name)
        thumb_url = default_storage.url(saved_thumb_name)

    except Exception as e:
        # partial upload 정리(운영에서 비용/찌꺼기 방지)
        try:
            if saved_photo_name:
                default_storage.delete(saved_photo_name)
        except Exception:
            pass
        try:
            if saved_thumb_name:
                default_storage.delete(saved_thumb_name)
        except Exception:
            pass

        raise ValueError(f"STORAGE_SAVE_FAILED: {e}")

    return {
        "filename": original_name,                 # 표시용 원래 파일명
        "storage_name": saved_photo_name,          # ✅ DB image 필드에 넣을 값
        "thumb_storage_name": saved_thumb_name,    # ✅ 썸네일도 저장해두면 추후 활용 가능
        "url": photo_url,                          # ✅ Cloudinary absolute URL
        "thumb_url": thumb_url,                    # ✅ Cloudinary absolute URL
        "file_size": file_size,
        "width": width,
        "height": height,
        "taken_at": taken_at,
        "file_hash": file_hash,
        "phash": image_hashes["phash"],
        "dhash": image_hashes["dhash"],
        "ahash": image_hashes["ahash"],
    }

def save_raw_uploaded_file(user, uploaded_file: UploadedFile) -> Dict:
    """
    ✅ 성능 개선용: '저장만' 한다.
    - PIL ❌
    - 해시 ❌
    - 썸네일 ❌
    """
    user_id = user.id
    original_name = getattr(uploaded_file, "name", "uploaded")

    try:
        file_bytes = uploaded_file.read()
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
    except Exception as e:
        raise ValueError(f"FILE_READ_FAILED: {e}")

    if not file_bytes:
        raise ValueError("EMPTY_FILE")

    # 원본 포맷 유지(그대로 업로드). 키만 uuid로.
    unique_name = f"{uuid.uuid4().hex}.jpg"
    photo_key = f"photos/{user_id}/{unique_name}"
    saved_name = None
    try:
        saved_name = default_storage.save(photo_key, ContentFile(file_bytes))
        photo_url = default_storage.url(saved_name)
    except Exception as e:
        try:
            if saved_name:
                default_storage.delete(saved_name)
        except Exception:
            pass
        raise ValueError(f"STORAGE_SAVE_FAILED: {e}")

    return {
        "filename": original_name,
        "storage_name": saved_name,   # Photo.image에 저장할 key
        "url": photo_url,
        "file_size": len(file_bytes),
    }


def read_storage_bytes(storage_name: str) -> bytes:
    """
    ✅ 비동기 task에서 storage(Cloudinary)로부터 bytes 다시 읽기
    """
    with default_storage.open(storage_name, "rb") as f:
        return f.read()