from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', lambda request: redirect('/accounts/login/')),

    path('admin/', admin.site.urls),

    # ✅ allauth가 /accounts/ 를 "먼저" 먹게 해야 함
    path('accounts/', include('allauth.urls')),

    # ✅ 너희 accounts 앱은 다른 prefix로 빼기 (충돌 방지)
    path('api/v1/accounts/', include('accounts.urls')),

    # apps
    path('gallery/', include('gallery.urls')),
    path('api/v1/photos/', include('photos.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)