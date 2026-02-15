from django.urls import path
from . import views
from classification import api_views

urlpatterns = [
    path('classify/', views.classify_image, name='classify'),
    path('test/', views.test_page, name='test'),
    path("api/v1/photos/classify/batch", api_views.classify_batch_start),
    path("api/v1/jobs/<str:job_id>", api_views.job_status),
    path("api/v1/photos/classify/unclassified", api_views.classify_unclassified_start),
]