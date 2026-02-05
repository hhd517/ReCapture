# photos/api/import_job.py
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework import status

from photos.models import GoogleCredential, ImportJob
from photos.serializers.photo import ImportGoogleRequestSerializer
from photos.serializers.response import APIResponse
from photos.services.import_service import ImportService
from photos.services.google_photos_service import GooglePhotosService
from photos.tasks.import_photos import import_google_photos_task


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def import_from_google(request):
    """
    (변경) 구글 포토 Import 시작:
    - 기존: 곧바로 전체 라이브러리 다운로드 task 실행
    - 변경: Picker 세션 생성 후 pickerUri/sessionId 반환
    """
    serializer = ImportGoogleRequestSerializer(data=request.data)
    if not serializer.is_valid():
        response_data = APIResponse.error(code="INVALID_REQUEST", message="잘못된 요청입니다.")
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    folder_id = serializer.validated_data.get("folderId")
    dedupe = serializer.validated_data.get("dedupe", True)

    try:
        google_cred = GoogleCredential.objects.get(user=user, is_active=True)
    except GoogleCredential.DoesNotExist:
        response_data = APIResponse.error(code="GOOGLE_NOT_CONNECTED", message="구글 연동이 필요합니다.")
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    try:
        job_id = ImportService.generate_job_id()

        import_job = ImportJob.objects.create(
            user=user,
            job_id=job_id,
            status="PICKING",  # 새 상태(권장): 사용자가 Picker에서 선택 중
            source="GOOGLE",
            folder_id=folder_id,
        )

        google_service = GooglePhotosService(google_credential=google_cred)
        session = google_service.create_picker_session()

        session_id = session.get("sessionId")
        picker_uri = session.get("pickerUri")

        # ImportJob 모델에 picker_session_id 필드가 없을 수도 있어서 안전 처리
        if hasattr(import_job, "picker_session_id"):
            import_job.picker_session_id = session_id
            import_job.save(update_fields=["picker_session_id"])

        response_data = APIResponse.success(
            {
                "jobId": job_id,
                "status": "PICKING",
                "sessionId": session_id,
                "pickerUri": picker_uri,
                "dedupe": dedupe,
            }
        )
        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        response_data = APIResponse.error(
            code="IMPORT_START_ERROR",
            message=f"Import 작업 시작 실패: {str(e)}",
        )
        return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def get_picker_session_status(request, session_id):
    """
    (신규) Picker 세션 상태 조회 (프론트 폴링용)
    """
    user = request.user

    try:
        google_cred = GoogleCredential.objects.get(user=user, is_active=True)
    except GoogleCredential.DoesNotExist:
        response_data = APIResponse.error(code="GOOGLE_NOT_CONNECTED", message="구글 연동이 필요합니다.")
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    try:
        google_service = GooglePhotosService(google_credential=google_cred)
        session = google_service.get_picker_session(session_id)

        response_data = APIResponse.success(
            {
                "sessionId": session_id,
                "session": session,
            }
        )
        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        response_data = APIResponse.error(
            code="PICKER_SESSION_ERROR",
            message=f"Picker 세션 조회 실패: {str(e)}",
        )
        return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def confirm_google_picker_selection(request):
    """
    (신규) Picker에서 선택 완료 후 다운로드 task 시작
    body 예시:
      {
        "jobId": "xxx",
        "sessionId": "sessions/...." or "....",
        "dedupe": true
      }
    """
    user = request.user

    job_id = request.data.get("jobId")
    session_id = request.data.get("sessionId")
    dedupe = request.data.get("dedupe", True)

    if not job_id or not session_id:
        response_data = APIResponse.error(code="INVALID_REQUEST", message="jobId와 sessionId는 필수입니다.")
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    try:
        job = ImportJob.objects.get(job_id=job_id, user=user)
    except ImportJob.DoesNotExist:
        response_data = APIResponse.error(code="JOB_NOT_FOUND", message="작업을 찾을 수 없습니다.")
        return Response(response_data, status=status.HTTP_404_NOT_FOUND)

    try:
        # 상태 업데이트
        job.status = "QUEUED"
        if hasattr(job, "picker_session_id"):
            job.picker_session_id = session_id
        job.save()

        # Celery 백그라운드 작업 시작 (이제 session_id를 넘겨야 함)
        import_google_photos_task.delay(
            user_id=user.id,
            job_id=job_id,
            folder_id=getattr(job, "folder_id", None),
            dedupe=dedupe,
            session_id=session_id,
        )

        response_data = APIResponse.success({"jobId": job_id, "status": "QUEUED"})
        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        response_data = APIResponse.error(
            code="IMPORT_CONFIRM_ERROR",
            message=f"Import 확인 처리 실패: {str(e)}",
        )
        return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def get_import_job_status(request, job_id):
    """Import 작업 진행 상황 조회"""
    user = request.user

    try:
        job = ImportJob.objects.get(job_id=job_id, user=user)

        progress = ImportService.calculate_progress(job)

        response_data = APIResponse.success(
            {
                "jobId": job.job_id,
                "status": job.status,
                "progress": progress,
            }
        )
        return Response(response_data, status=status.HTTP_200_OK)

    except ImportJob.DoesNotExist:
        response_data = APIResponse.error(code="JOB_NOT_FOUND", message="작업을 찾을 수 없습니다.")
        return Response(response_data, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        response_data = APIResponse.error(
            code="JOB_STATUS_ERROR",
            message=f"작업 상태 조회 실패: {str(e)}",
        )
        return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
