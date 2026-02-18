from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from gallery.models import Photo
from photos.serializers.response import APIResponse
from photos.serializers.photo import PhotoSerializer
from photos.tasks import process_uploaded_photo


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def list_processing_queue(request):
    """
    미처리/실패만 빠르게 조회
    query:
      - status=PENDING|PROCESSING|FAILED (없으면 PENDING+PROCESSING+FAILED)
      - limit (기본 50, 최대 200)
    """
    user = request.user
    status_q = request.query_params.get("status")
    limit = int(request.query_params.get("limit", 50))
    limit = max(1, min(limit, 200))

    qs = Photo.objects.filter(user=user, is_deleted=False)

    if status_q:
        qs = qs.filter(processing_status=status_q)
    else:
        qs = qs.filter(processing_status__in=["PENDING", "PROCESSING", "FAILED"])

    items = qs.order_by("-created_at")[:limit]
    data = PhotoSerializer(items, many=True).data

    return Response(APIResponse.success({"items": data}), status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def retry_processing(request, photo_id: int):
    """
    FAILED / PENDING 사진 재처리
    """
    user = request.user
    photo = Photo.objects.filter(user=user, id=photo_id, is_deleted=False).first()

    if not photo:
        return Response(
            APIResponse.error("NOT_FOUND", "사진을 찾을 수 없습니다."),
            status=status.HTTP_404_NOT_FOUND,
        )

    if photo.processing_status not in ("FAILED", "PENDING"):
        return Response(
            APIResponse.error("NOT_RETRYABLE", "재처리 가능한 상태가 아닙니다."),
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 상태 리셋 후 재큐잉
    Photo.objects.filter(id=photo_id).update(
        processing_status="PENDING",
        processing_error=None,
    )
    process_uploaded_photo.delay(photo_id)

    photo.refresh_from_db()
    return Response(
        APIResponse.success({"photo": PhotoSerializer(photo).data}),
        status=status.HTTP_200_OK,
    )