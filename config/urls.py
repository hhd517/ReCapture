from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('classification/', include('classification.urls')),  # 추가
]