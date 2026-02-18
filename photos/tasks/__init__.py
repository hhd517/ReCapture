# photos/tasks/__init__.py

# Celery autodiscover_tasks()가 photos.tasks를 import할 때
# 이곳에서 하위 task 모듈들을 함께 import해서 등록되게 한다.

from .import_photos import import_google_photos_task  # noqa: F401
from .classify_photos import classify_unclassified_task  # noqa: F401
from .upload_tasks import process_uploaded_photo

__all__ = [
    "import_google_photos_task",
    "classify_unclassified_task",
    "process_uploaded_photo",
]