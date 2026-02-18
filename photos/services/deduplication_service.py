from typing import List, Optional

from gallery.models import Photo


class DeduplicationService:
    """
    완전히 동일한 이미지(SHA-256 동일)만 중복으로 판단
    """

    @staticmethod
    def find_exact_duplicates(
        user,
        *,
        file_hash: str,
        exclude_photo_id: Optional[int] = None,
    ) -> List[Photo]:
        """
        같은 user + 같은 file_hash를 가진 사진 조회
        """
        qs = Photo.objects.filter(
            user=user,
            file_hash=file_hash,
            is_deleted=False,
        )

        if exclude_photo_id is not None:
            qs = qs.exclude(id=exclude_photo_id)

        return list(qs.order_by("created_at"))

    @staticmethod
    def find_original_for_hash(user, *, file_hash: str, current_photo_id: int) -> Optional[Photo]:
        """현재 photo_id보다 먼저 생성된(=id가 더 작은) 동일 hash 사진을 원본 후보로 선택."""
        if not file_hash:
            return None

        return (
            Photo.objects
            .filter(user=user, file_hash=file_hash, is_deleted=False)
            .filter(id__lt=current_photo_id)
            .order_by('id')
            .first()
        )

    @staticmethod
    def mark_exact_duplicate(photo: Photo, original: Photo) -> None:
        """
        photo를 original의 exact duplicate로 표시
        """
        if getattr(photo, 'duplicate_of_id', None) == original.id:
            return

        photo.duplicate_of = original
        photo.save(update_fields=["duplicate_of", "updated_at"])

    @staticmethod
    def check_exact_duplicate_and_mark(
        user,
        *,
        photo: Photo,
    ) -> Optional[Photo]:
        """
        photo 기준으로 exact duplicate 검사 후,
        있으면 DB에 duplicate_of 저장
        """
        # 업로드 단계에서 file_hash로 중복을 "막는" 경우엔 보통 여기로 오지 않는다.
        # 혹시라도 레이스/수동 삽입 등으로 중복 row가 존재할 때만 안전하게 마킹한다.
        original = DeduplicationService.find_original_for_hash(
            user,
            file_hash=photo.file_hash,
            current_photo_id=photo.id,
        )

        if original:
            DeduplicationService.mark_exact_duplicate(photo, original)
            return original

        return None