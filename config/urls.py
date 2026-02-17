from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect, render
from django.conf import settings
from django.conf.urls.static import static


def home(request):
    # 로그인 상태면 서비스(갤러리)로
    if request.user.is_authenticated:
        return redirect("/gallery/")
    # 비로그인 상태면 메인 랜딩 페이지 렌더
    return render(request, "home.html")


urlpatterns = [
    path("", home),

    path("admin/", admin.site.urls),

    # ✅ 웹(페이지)용 accounts (너희 커스텀)
    path("accounts/", include("accounts.urls")),

    # ✅ allauth 기본 경로는 prefix 분리(충돌 방지)
    path("auth/", include("allauth.urls")),

    # ✅ API는 별도 prefix로 유지
    path("api/v1/accounts/", include("accounts.urls")),

    # apps
    path("gallery/", include("gallery.urls")),
    path("api/v1/photos/", include("photos.urls")),
]

# ✅ 개발환경에서만 MEDIA 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)