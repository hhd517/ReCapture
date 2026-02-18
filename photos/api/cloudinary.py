from django.db import IntegrityError, transaction
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from gallery.models import Photo, Category
from photos.serializers.response import APIResponse
from photos.serializers.photo import PhotoSerializer
from photos.serializers.cloudinary import (
    CloudinarySignRequestSerializer,
    CloudinaryConfirmRequestSerializer,
    CloudinaryConfirmBatchRequestSerializer,
)
from photos.services.cloudinary_sign_service import issue_signed_upload_payload
from photos.tasks import process_uploaded_photo


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


def _is_valid_cloudinary_secure_url(url: str) -> bool:
    # 최소 검증(허용 도메인)
    allowed = ("https://res.cloudinary.com/", "https://cloudinary.com/", "https://")
    return url.startswith(allowed)


def _is_valid_public_id_for_user(public_id: str, user_id: int) -> bool:
    # sign 단계에서 folder = photos/<user_id> 로 강제하므로 최소 검증
    # cloudinary 결과 public_id는 보통 "photos/<user_id>/<uuid>" 형태
    prefix = f"photos/{user_id}/"
    return public_id.startswith(prefix)


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def get_cloudinary_signature(request):
    user = request.user

    ser = CloudinarySignRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(
            APIResponse.error("INVALID_REQUEST", "요청 값이 올바르지 않습니다.", ser.errors),
            status=status.HTTP_400_BAD_REQUEST,
        )

    filename = ser.validated_data["filename"]
    file_hash = ser.validated_data["file_hash"]

    if Photo.objects.filter(user=user, file_hash=file_hash, is_deleted=False).exists():
        return Response(
            APIResponse.success({"duplicate": True, "reason": "DUPLICATE_FILE_HASH"}),
            status=status.HTTP_200_OK,
        )

    try:
        payload = issue_signed_upload_payload(user_id=user.id, filename=filename)
    except ValueError as e:
        return Response(
            APIResponse.error("SIGN_FAILED", str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        APIResponse.success({"duplicate": False, "payload": payload}),
        status=status.HTTP_200_OK,
    )


def _get_unclassified_category(user):
    return Category.objects.get_or_create(
        user=user,
        name="분류 전",
        defaults={"category_key": None, "parent": None},
    )[0]


def _confirm_one(user, data):
    filename = data["filename"]
    file_hash = data["file_hash"]
    public_id = data["public_id"]
    secure_url = data["secure_url"]
    file_size = data.get("bytes")
    width = data.get("width")
    height = data.get("height")

    # ✅ Cloudinary 결과 최소 검증
    if not _is_valid_public_id_for_user(public_id, user.id):
        return "INVALID_PUBLIC_ID", None
    if not _is_valid_cloudinary_secure_url(secure_url):
        return "INVALID_SECURE_URL", None

    # ✅ 중복 방어
    existing = Photo.objects.filter(user=user, file_hash=file_hash, is_deleted=False).first()
    if existing:
        return "DUPLICATE_FILE_HASH", existing

    unclassified = _get_unclassified_category(user)

    try:
        photo = Photo.objects.create(
            user=user,
            filename=filename,
            image=public_id,
            url=secure_url,
            file_size=file_size,
            file_hash=file_hash,
            width=width,
            height=height,
            source="UPLOAD",
            category=unclassified,
            processing_status="PENDING",
            processing_error=None,
        )
    except IntegrityError:
        existing = Photo.objects.filter(user=user, file_hash=file_hash, is_deleted=False).first()
        return "DUPLICATE_FILE_HASH", existing

    process_uploaded_photo.delay(photo.id)
    return None, photo


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def confirm_cloudinary_upload(request):
    user = request.user

    ser = CloudinaryConfirmRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(
            APIResponse.error("INVALID_REQUEST", "요청 값이 올바르지 않습니다.", ser.errors),
            status=status.HTTP_400_BAD_REQUEST,
        )

    reason, photo_obj = _confirm_one(user, ser.validated_data)

    if reason == "DUPLICATE_FILE_HASH":
        return Response(
            APIResponse.success({
                "duplicate": True,
                "reason": reason,
                "photo": PhotoSerializer(photo_obj).data if photo_obj else None,
            }),
            status=status.HTTP_200_OK,
        )

    if reason is not None:
        return Response(
            APIResponse.error(reason, "Cloudinary 업로드 결과 검증 실패"),
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        APIResponse.success({
            "duplicate": False,
            "photo": PhotoSerializer(photo_obj).data,
        }),
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def confirm_cloudinary_upload_batch(request):
    user = request.user

    ser = CloudinaryConfirmBatchRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(
            APIResponse.error("INVALID_REQUEST", "요청 값이 올바르지 않습니다.", ser.errors),
            status=status.HTTP_400_BAD_REQUEST,
        )

    items = ser.validated_data["items"]

    created = []
    duplicates = []
    invalid = []
    failed = []

    for idx, item in enumerate(items):
        try:
            with transaction.atomic():
                reason, photo_obj = _confirm_one(user, item)
        except Exception as e:
            failed.append({"index": idx, "error": str(e)})
            continue

        if reason == "DUPLICATE_FILE_HASH":
            duplicates.append({
                "index": idx,
                "reason": reason,
                "photo": PhotoSerializer(photo_obj).data if photo_obj else None,
            })
        elif reason in ("INVALID_PUBLIC_ID", "INVALID_SECURE_URL"):
            invalid.append({
                "index": idx,
                "reason": reason,
            })
        elif reason is None:
            created.append(PhotoSerializer(photo_obj).data)
        else:
            failed.append({"index": idx, "error": reason})

    return Response(
        APIResponse.success({
            "created": created,
            "duplicates": duplicates,
            "invalid": invalid,
            "failed": failed,
        }),
        status=status.HTTP_200_OK,
    )