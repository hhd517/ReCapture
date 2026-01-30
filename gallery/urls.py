from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    path('', views.photo_list, name='photo_list'), # 메인 페이지
    path('photo/<int:pk>/', views.photo_detail, name='photo_detail'), # 사진 상세 및 수정
    path('photo/<int:pk>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'), # 북마크 토글
    path('trash/', views.trash_list, name='trash_list'), # 휴지통 목록
    path('photo/<int:pk>/restore/', views.restore_photo, name='restore_photo'), # 휴지통 복구
]