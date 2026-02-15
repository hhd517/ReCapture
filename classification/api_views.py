# classification/api_views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from classification.services.job_store import new_job, get_job
from classification.task import classify_batch_task


@api_view(["POST"])
def classify_unclassified_start(request):
    from gallery.models import Photo, Category

    # ✅ "분류 전" 카테고리 찾기 (중복 방지: 대분류만)
    unclassified = Category.objects.filter(name="분류 전", parent__isnull=True).order_by("id").first()
    if not unclassified:
        return Response({"detail": "분류 전 카테고리를 찾을 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

    # ✅ 해당 카테고리의 사진 id 전부 가져오기
    photo_ids = list(
        Photo.objects.filter(category=unclassified).values_list("id", flat=True)
    )

    if not photo_ids:
        return Response({"detail": "분류할 사진이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

    job_id = new_job(total=len(photo_ids))
    classify_batch_task.delay(job_id, photo_ids)

    return Response({"job_id": job_id, "total": len(photo_ids)}, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
def job_status(request, job_id: str):
    job = get_job(job_id)
    if not job:
        return Response({"detail": "job not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(job, status=status.HTTP_200_OK)