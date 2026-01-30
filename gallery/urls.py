from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    # 사진 상세 및 수정
    path('photo/<int:pk>/', views.photo_detail, name='photo_detail'),
    # 북마크 토글
    path('photo/<int:pk>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    # 휴지통 목록
    path('trash/', views.trash_list, name='trash_list'),
]