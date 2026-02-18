from django.urls import path
from photos.api import google, upload, import_job, photos, dedupe, classify, cloudinary, processing

app_name = "photos"

urlpatterns = [
    # 구글 연동
    path("google/status", google.google_status, name="google-status"),
    path("google/authorize", google.google_authorize, name="google-authorize"),
    path("google/callback/", google.google_callback, name="google-callback"),
    path("google/unlink", google.google_unlink, name="google-unlink"),

    # 서버 중계 업로드(기존)
    path("upload", upload.upload_photos, name="upload-photos"),

    # Cloudinary Direct Upload
    path("cloudinary/sign", cloudinary.get_cloudinary_signature, name="cloudinary-sign"),
    path("cloudinary/confirm", cloudinary.confirm_cloudinary_upload, name="cloudinary-confirm"),
    path("cloudinary/confirm-batch", cloudinary.confirm_cloudinary_upload_batch, name="cloudinary-confirm-batch"),

    # ✅ 처리상태/재처리
    path("processing", processing.list_processing_queue, name="processing-list"),
    path("processing/<int:photo_id>/retry", processing.retry_processing, name="processing-retry"),

    # Google Photos Import
    path("import/google", import_job.import_from_google, name="import-google"),
    path("import/google/session/<str:session_id>", import_job.get_picker_session_status, name="import-google-session-status"),
    path("import/google/confirm", import_job.confirm_google_picker_selection, name="import-google-confirm"),
    path("import/jobs/<str:job_id>", import_job.get_import_job_status, name="import-job-status"),

    # 사진 CRUD
    path("", photos.list_photos, name="list-photos"),
    path("<int:photo_id>", photos.get_photo_detail, name="photo-detail"),
    path("<int:photo_id>/update", photos.update_photo, name="update-photo"),
    path("<int:photo_id>/delete", photos.delete_photo, name="delete-photo"),

    # 중복 제거
    path("dedupe/check", dedupe.check_duplicates, name="dedupe-check"),

    # 사진 분류(미분류)
    path("classify", classify.classify_unclassified, name="classify-unclassified"),
]