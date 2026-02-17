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

# ✅ Worker 프로세스에서만 모델을 1번 로드하도록 싱글턴 + Lock
_clf = None
_lock = threading.Lock()


def _get_classifier():
    """
    ✅ 매우 중요:
    - classification/services/ensemble_classifier 를 여기(함수 내부)에서 import해서
      웹(gunicorn) 프로세스에서 무거운 import/로드가 발생하지 않게 함.
    - Worker 프로세스에서만 최초 1회 로드
    """
    global _clf
    if _clf is None:
        with _lock:
            if _clf is None:
                from classification.services.ensemble_classifier import EnsembleClassifier

                _clf = EnsembleClassifier()
    return _clf


def _get_photo_url(photo: Photo) -> str:
    """
    Cloudinary/remote storage 환경에서는 photo.image.path 가 없거나 NotImplemented일 수 있음.
    따라서 url 우선 사용.
    """
    if photo.url:
        return photo.url

    # ImageField의 url이 존재하면 사용
    try:
        return photo.image.url
    except Exception:
        return ""


def _get_local_image_path(photo: Photo) -> str:
    """
    1) 로컬 파일 경로가 가능한 스토리지면 photo.image.path 사용
    2) 불가능하면(Cloudinary 등) photo.url을 다운로드해서 임시파일 경로 반환
    """
    # 1) 로컬 경로 시도
    try:
        p = photo.image.path  # Cloudinary면 NotImplementedError 날 수 있음
        if p and os.path.exists(p):
            return p
    except Exception:
        pass

    # 2) URL 다운로드
    url = _get_photo_url(photo)
    if not url:
        raise ValueError("Photo has no accessible url/path for classification")

    suffix = os.path.splitext(photo.filename or "")[1] or ".jpg"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_path = tmp.name
    tmp.close()

    try:
        # stream 다운로드
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

    return tmp_path


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def classify_unclassified_task(self, user_id: int, limit: int = 200):
    """
    ✅ 분류 전(또는 category null) 사진들을 limit개까지 분류해서 DB에 반영.
    - web 프로세스에서는 이 로직이 절대 실행되지 않음.
    - worker에서만 모델 로드/추론 수행.
    """
    user = User.objects.get(id=user_id)

    # '분류 전' 카테고리 확보
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
        tmp_path = None
        try:
            img_path = _get_local_image_path(photo)

            # URL 다운로드한 임시파일인지 여부 체크(로컬 path면 tmp_path=None)
            try:
                # 로컬 path면 img_path==photo.image.path 가능, 임시파일이면 tmp로 생성된 경로
                # 여기서는 "임시파일을 생성한 경우"에만 tmp_path를 따로 들고 있다가 삭제
                if photo.url and img_path and os.path.exists(img_path):
                    # Cloudinary 환경이면 대부분 임시파일
                    # 단, photo.url 있어도 로컬 스토리지일 수 있으니 안전하게 조건 완화 X
                    # -> 아래에서 로컬 path 여부를 정확히 못 가리니, 생성 시에만 tmp_path를 잡기 위해
                    #    _get_local_image_path 내에서 임시파일 생성 시 tmp_path로 반환되므로
                    pass
            except Exception:
                pass

            # 분류
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

            # 혹시 과거에 name은 같은데 category_key가 비어있게 만들어진 케이스 보정
            if target_cat.category_key is None and target_cat.parent is None and key is not None:
                target_cat.category_key = key
                target_cat.save(update_fields=["category_key"])

            photo.category = target_cat
            photo.save(update_fields=["category"])

            ok += 1

        except Exception:
            fail += 1

        finally:
            # _get_local_image_path에서 URL 다운로드로 만든 임시파일 제거
            # (로컬 스토리지는 photo.image.path라서 지우면 안 됨)
            try:
                # 임시파일은 기본적으로 /tmp에 생김. 로컬 path인 경우는 보통 MEDIA_ROOT 아래.
                # 간단한 휴리스틱: /tmp 또는 NamedTemporaryFile 경로면 삭제
                if "tmp" in (img_path or "") and os.path.exists(img_path):
                    os.remove(img_path)
            except Exception:
                pass

    return {"ok": ok, "fail": fail}