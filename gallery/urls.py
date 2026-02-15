from django.urls import path

from . import views
from classification import api_views as api_views

from .views import bookmark_views
from .views import base_views
from .views import category_views
from .views import trash_views
from .views import memo_views

app_name = 'gallery'

urlpatterns = [
    path('', views.photo_list, name='home'),

    # 사진/갤러리
    path('photos/', views.photo_list, name='photo_list'),
    path('photos/<int:photoid>/', views.photo_detail, name='photo_detail'),
    path('photos/<int:photo_id>/bookmark/', bookmark_views.toggle_bookmark, name='toggle_bookmark'),
    path('photos/move/', category_views.move_photos, name='move_photos'),

    # 북마크
    path('bookmarks/', views.bookmark_list, name='bookmark_list'),
    path('bookmarks/add/', views.add_bookmark, name='add_bookmark'),
    path('bookmarks/<int:photoid>/', views.delete_bookmark, name='delete_bookmark'),

    # 메모
    path('memos/photos/<int:photoid>/', memo_views.manage_memo, name='manage_memo'),

    # 리마인드
    path('reminders/', views.manage_reminders, name='manage_reminders'),
    path('reminders/<str:reminderId>/', views.edit_reminder, name='edit_reminder'),

    # 휴지통
    path('trash/', views.trash_list, name='trash_list'),
    path('trash/<int:photoid>/restore/', views.restore_photo, name='restore_photo'),
    path('trash/<int:photoid>/', views.permanent_delete, name='permanent_delete'),
    path('photos/bulk-trash/', trash_views.bulk_move_to_trash, name='bulk_trash'),
    path('photos/bulk-restore/', trash_views.bulk_restore_photos, name='bulk_restore'),
    path('photos/bulk-permanent-delete/', trash_views.bulk_permanent_delete, name='bulk_permanent_delete'),
    path('photos/empty-trash/', trash_views.empty_trash_all, name='empty_trash_all'),

    # 카테고리/서브카테고리
    path('categories/add/', views.add_category, name='add_category'),
    path('api/sub-categories/', category_views.get_sub_categories, name='get_sub_categories'),
    path('api/sub-categories/<int:sub_id>/edit/', category_views.edit_sub_category, name='edit_sub_category'),
    path('api/sub-categories/<int:sub_id>/delete/', category_views.delete_sub_category, name='delete_sub_category'),

    # 설정
    path('settings/', base_views.settings_view, name='settings'),

    # ✅ 분류 진행 API
    path('api/v1/photos/classify/unclassified', api_views.classify_unclassified_start),
    path('api/v1/jobs/<str:job_id>', api_views.job_status),
]