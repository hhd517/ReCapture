# photos/api/classify.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# ✅ Celery task만 호출 (웹 프로세스에서 모델 로딩 금지)
from photos.tasks.classify_photos import classify_unclassified_task


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def classify_unclassified(request):
    """
    ✅ 비동기 분류 시작 API
    - 웹 요청에서는 절대 모델을 로드/다운로드하지 않음
    - Celery background worker가 실제 분류 수행
    """
    user = request.user
    limit = int(request.data.get("limit", 200))

    task = classify_unclassified_task.delay(user.id, limit)

    return Response(
        {
            "success": True,
            "data": {
                "queued": True,
                "task_id": task.id,
                "limit": limit,
                "message": "분류 작업이 큐에 등록되었습니다. 잠시 후 결과가 반영됩니다.",
            },
        },
        status=202,
    )