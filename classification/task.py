# classification/tasks.py

from celery import shared_task
from django.db import transaction
from classification.services.job_store import get_job  # 추가 import
from classification.services.job_store import update_job, inc_done, inc_failed

# ✅ 너희 메인 로직 import
from classification.services.ensemble_classifier import EnsembleClassifier
# ✅ (중요) 모델은 한 번만 로드해서 재사용 (매 사진마다 로드하면 느려짐)
_CLF = None
def get_classifier():
    global _CLF
    if _CLF is None:
        _CLF = EnsembleClassifier()
    return _CLF


def classify_one_photo(photo_id: int) -> None:
    """
    photo_id로:
    1) 이미지 파일 path 확보
    2) EnsembleClassifier.classify(path) 실행
    3) 결과(category/confidence 등)를 DB에 저장
    """

    # ⚠️ 너희 앱 모델 경로에 맞게 수정
    from gallery.models import Photo, Category  # 예시: gallery 앱에 Photo/Category가 있는 경우

    photo = Photo.objects.select_related("category").get(id=photo_id)

    # ✅ 파일 경로 얻기 (ImageField/FileField라면 보통 .path 가능)
    # - S3 같은 원격 스토리지면 .path가 없을 수 있음 → 그 경우는 별도 다운로드 로직 필요
    image_path = photo.image.path  # 여기서 photo.image 가 ImageField라는 전제 (필드명 다르면 수정)

    clf = get_classifier()
    result = clf.classify(image_path)  # ✅ 핵심 호출
    final_key = result["category"]      # finance / study_note / info / others
    confidence = result.get("confidence")
    logs = result.get("logs", [])

    # ✅ final_key → Category 매핑 (너희 DB 구조에 맞게 수정)
    # (예) Category.category_key 가 finance/info/... 로 저장되어 있다면:
    new_cat = Category.objects.get(category_key=final_key)

    # ✅ DB 업데이트 (필드명은 너희 모델에 맞게 수정)
    with transaction.atomic():
        photo.category = new_cat

        # 선택: confidence/log 저장 필드가 있다면 사용
        if hasattr(photo, "confidence"):
            photo.confidence = confidence

        if hasattr(photo, "classify_logs"):
            # TextField에 저장하는 예시
            photo.classify_logs = "\n".join(str(x) for x in logs)

        photo.save()

        # classification/tasks.py (맨 아래에 추가)


@shared_task(bind=True)
def classify_batch_task(self, job_id: str, photo_ids: list[int]):
    total = len(photo_ids)
    update_job(job_id, status="running", total=total, message=f"0/{total} 분류중...")

    for idx, pid in enumerate(photo_ids, start=1):
        update_job(job_id, current_photo_id=pid, message=f"{idx-1}/{total} 분류중...")
        try:
            classify_one_photo(pid)
            inc_done(job_id)
        except Exception:
            inc_failed(job_id, pid)

    job = get_job(job_id) or {}
    done = int(job.get("done", 0))
    failed = int(job.get("failed", 0))
    update_job(
        job_id,
        status="done",
        current_photo_id=None,
        message=f"완료! {done}/{total} (실패 {failed})",
    )
    return job_id