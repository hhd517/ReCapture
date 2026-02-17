"""
주의:
이 앱은 TokenAuthentication + IsAuthenticated 전제를 기반으로 동작한다.
accounts 앱에서 토큰 발급 API가 반드시 선행되어야 한다.
"""

from django.core.files.storage import default_storage

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from gallery.models import Photo, Category
from photos.serializers.response import APIResponse
from photos.serializers.photo import PhotoSerializer
from photos.services.upload_service import save_uploaded_file
from photos.services.deduplication_service import DeduplicationService


# CSRF 체크 안 하는 SessionAuthentication
class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # CSRF 체크 비활성화


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def upload_photos(request):
    """
    (5) 직접 업로드
    - SHA-256 기준 완전히 동일한 파일만 중복 처리
    - 업로드된 사진은 자동으로 "분류 전" 카테고리에 넣기
    - 저장소는 default_storage(운영: Cloudinary)를 전제로 함
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
    duplicates = []

    for f in files:
        # ✅ upload_service는 반드시 다음 값을 포함하도록 수정되어야 함:
        # - meta["storage_name"] : default_storage에 저장된 name(key)
        # - meta["thumb_storage_name"] (선택이지만 있으면 좋음)
        # - meta["url"], meta["thumb_url"] : 절대 URL(Cloudinary)
        meta = save_uploaded_file(user, f)

        # 1) Exact 중복 사전 체크 (SHA-256)
        existing = Photo.objects.filter(
            user=user,
            file_hash=meta["file_hash"],
            is_deleted=False,
        ).first()

        if existing:
            # ✅ 방금 업로드한 파일이 "이미 중복"이면 스토리지에서 제거(비용/용량 방지)
            # (로컬 경로 _final_path/_thumb_path 삭제 로직 제거)
            try:
                storage_name = meta.get("storage_name")
                if storage_name:
                    default_storage.delete(storage_name)
            except Exception:
                pass

            try:
                thumb_storage_name = meta.get("thumb_storage_name")
                if thumb_storage_name:
                    default_storage.delete(thumb_storage_name)
            except Exception:
                pass

            duplicates.append(
                {
                    "filename": meta["filename"],
                    "existingPhotoId": existing.id,
                }
            )
            continue

        # 2) Photo 생성 ("분류 전" 카테고리에 자동 할당)
        # ✅ image 필드에는 "스토리지 key(name)"를 저장해야 함 (Cloudinary storage 기준)
        photo = Photo.objects.create(
            user=user,
            filename=meta["filename"],
            image=meta["storage_name"],   # ✅ Cloudinary storage key (예: photos/1/uuid.jpg)
            url=meta["url"],              # ✅ Cloudinary absolute URL
            file_size=meta["file_size"],
            file_hash=meta["file_hash"],
            phash=meta["phash"],
            dhash=meta["dhash"],
            ahash=meta["ahash"],
            width=meta["width"],
            height=meta["height"],
            taken_at=meta["taken_at"],
            source="UPLOAD",
            category=unclassified_category,
        )

        # 3) 생성 직후 exact duplicate 재확인 + 마킹
        DeduplicationService.check_exact_duplicate_and_mark(
            user,
            photo=photo,
        )

        created.append(PhotoSerializer(photo).data)

    return Response(
        APIResponse.success({"created": created, "duplicates": duplicates}),
        status=status.HTTP_200_OK,
    )