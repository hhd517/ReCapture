from django.contrib import admin
from .models import Photo, Category, Notification

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_key', 'parent', 'user']
    list_filter = ['category_key', 'user']

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'category', 'is_bookmarked', 'is_trashed', 'created_at']
    list_filter = ['user', 'category', 'is_bookmarked', 'is_trashed']
    search_fields = ['memo']

admin.site.register(Notification)