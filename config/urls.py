from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect,render
from django.conf import settings
from django.conf.urls.static import static


def home(request):
    # 로그인 상태면 서비스(갤러리)로
    if request.user.is_authenticated:
        return redirect('/gallery/')
    # 비로그인 상태면 메인 랜딩 페이지 렌더
    return render(request, "home.html")

urlpatterns = [
    path('', home),

    path('admin/', admin.site.urls),

    # ✅ 우리가 만든 signup/done 같은 커스텀 경로를 먼저 잡고
    path("accounts/", include("accounts.urls")),

    # ✅ 그 다음 allauth 기본 경로들(login, signup, social)
    path('accounts/', include('allauth.urls')),

    # ✅ API는 별도 prefix로 유지 (좋음)
    path('api/v1/accounts/', include('accounts.urls')),

    # apps
    path('gallery/', include('gallery.urls')),
    path('api/v1/photos/', include('photos.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)