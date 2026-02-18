"""
주의:
이 앱은 TokenAuthentication + IsAuthenticated 전제를 기반으로 동작한다.
accounts 앱에서 토큰 발급 API가 반드시 선행되어야 한다.
"""


from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from gallery.models import Photo, Category
from photos.serializers.response import APIResponse
from photos.serializers.photo import PhotoSerializer
from photos.services.upload_service import save_raw_uploaded_file, calculate_sha256_file
from photos.tasks import process_uploaded_photo


# CSRF 체크 안 하는 SessionAuthentication
class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # CSRF 체크 비활성화


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def upload_photos(request):
    """
    ✅ 성능 개선 버전:
    - 요청에서는 "저장 + Photo row 생성"만 하고 즉시 응답
    - 해시/썸네일/중복검사/분류 등 무거운 작업은 Celery task에서 처리
    """
    user = request.user
    files = request.FILES.getlist("files")

    if not files:
        return Response(
            APIResponse.error("NO_FILES", "업로드할 파일이 없습니다."),
            status=status.HTTP_400_BAD_REQUEST,
        )

    # "분류 전" 카테고리 가져오기 (없으면 생성)
    unclassified_category, _ = Category.objects.get_or_create(
        user=user,
        name="분류 전",
        defaults={"category_key": None, "parent": None},
    )

    created = []
    skipped_duplicates = []

    for f in files:
        # 0) ✅ 업로드 전에 SHA256 계산 → 중복이면 Cloudinary 업로드 자체를 막음
        try:
            incoming_hash = calculate_sha256_file(f)
        except Exception as e:
            return Response(
                APIResponse.error("HASH_FAILED", f"해시 계산 실패: {e}"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 이미 동일 파일이 있으면 스킵
        if Photo.objects.filter(user=user, file_hash=incoming_hash, is_deleted=False).exists():
            skipped_duplicates.append({
                "filename": getattr(f, "name", "uploaded"),
                "file_hash": incoming_hash,
                "reason": "DUPLICATE_FILE_HASH",
            })
            continue

        # 1) ✅ 원본 저장만
        meta = save_raw_uploaded_file(user, f)

        # 2) ✅ Photo row 생성
        photo = Photo.objects.create(
            user=user,
            filename=meta["filename"],
            image=meta["storage_name"],  # Cloudinary key
            url=meta["url"],
            file_size=meta.get("file_size") or getattr(f, "size", None),
            category=unclassified_category,
            source="UPLOAD",
            # ✅ 업로드 단계에서 file_hash를 채워두면 중복 방지가 즉시 가능해짐
            file_hash=incoming_hash,
            # 아래는 task가 채움(또는 보강)
            phash=None,
            dhash=None,
            ahash=None,
            width=None,
            height=None,
            taken_at=None,
        )

        # 3) ✅ 비동기 후처리
        process_uploaded_photo.delay(photo.id)

        created.append(PhotoSerializer(photo).data)

    return Response(
        APIResponse.success(
            {
                "created": created,
                "skipped_duplicates": skipped_duplicates,
                "message": "업로드 완료! 백그라운드에서 처리 중입니다.",
            }
        ),
        status=status.HTTP_200_OK,
    )