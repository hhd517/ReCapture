from django.contrib import admin
from .models import Photo

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    # 관리자 목록 화면에서 보여줄 필드들
    list_display = ('id', 'user', 'category_main', 'is_confirmed', 'is_bookmarked', 'is_trashed', 'created_at')
    
    # 클릭해서 들어가지 않아도 바로 필터링할 수 있는 옵션
    list_filter = ('is_confirmed', 'is_bookmarked', 'is_trashed', 'category_main')
    
    # 검색 기능 (유저 이름이나 메모로 검색 가능)
    search_fields = ('user__username', 'memo', 'category_main')