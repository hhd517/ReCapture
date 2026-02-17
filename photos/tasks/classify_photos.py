# photos/tasks/classify_photos.py

import os
import tempfile
import threading

import requests
from celery import shared_task
from django.contrib.auth.models import User
from django.db.models import Q

from gallery.models import Photo, Category


LABEL_TO_CATEGORY = {
    "finance": ("finance", "결제/예약"),
    "study_note": ("study_note", "학습/노트"),
    "info": ("info", "정보"),
    "others": ("others", "기타"),
}

_clf = None
_lock = threading.Lock()


def _get_classifier():
    """
    매우 중요:
    - 모델 관련 import를 함수 내부에서 해서
      web(gunicorn) 프로세스에서 무거운 import/로드가 발생하지 않게 함.
    - worker 프로세스에서만 최초 1회 로드
    """
    global _clf
    if _clf is None:
        with _lock:
            if _clf is None:
                from classification.services.ensemble_classifier import EnsembleClassifier

                _clf = EnsembleClassifier()
    return _clf


def _get_accessible_url(photo: Photo) -> str:
    if getattr(photo, "url", None):
        return photo.url
    try:
        return photo.image.url
    except Exception:
        return ""


def _get_local_image_path(photo: Photo):
    """
    반환: (path, is_temp)
    - 로컬 스토리지면 photo.image.path 사용
    - Cloudinary 등 path 불가면 url 다운로드 후 임시파일 반환
    """
    # 1) 로컬 path 시도
    try:
        p = photo.image.path
        if p and os.path.exists(p):
            return p, False
    except Exception:
        pass

    # 2) URL 다운로드
    url = _get_accessible_url(photo)
    if not url:
        raise ValueError("Photo has no accessible url/path for classification")

    suffix = os.path.splitext(getattr(photo, "filename", "") or "")[1] or ".jpg"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_path = tmp.name
    tmp.close()

    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

    return tmp_path, True


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def classify_unclassified_task(self, user_id: int, limit: int = 200):
    user = User.objects.get(id=user_id)

    unclassified_cat, _ = Category.objects.get_or_create(
        user=user,
        name="분류 전",
        defaults={"category_key": None, "parent": None},
    )

    qs = (
        Photo.objects.filter(user=user)
        .filter(Q(category=unclassified_cat) | Q(category__isnull=True))
        .order_by("id")[:limit]
    )

    if not qs.exists():
        return {"ok": 0, "fail": 0}

    clf = _get_classifier()

    ok, fail = 0, 0
    for photo in qs:
        img_path, is_temp = None, False
        try:
            img_path, is_temp = _get_local_image_path(photo)

            out = clf.classify(img_path)
            label = out.get("category")
            if not label:
                raise ValueError("EnsembleClassifier returned empty category")

            key, name = LABEL_TO_CATEGORY.get(label, ("others", "기타"))

            target_cat, _ = Category.objects.get_or_create(
                user=user,
                name=name,
                defaults={"category_key": key, "parent": None},
            )

            # 과거 데이터 보정
            if target_cat.category_key is None and key is not None:
                target_cat.category_key = key
                target_cat.save(update_fields=["category_key"])

            photo.category = target_cat
            photo.save(update_fields=["category"])

            ok += 1

        except Exception:
            fail += 1

        finally:
            if is_temp and img_path:
                try:
                    os.remove(img_path)
                except OSError:
                    pass

    return {"ok": ok, "fail": fail}