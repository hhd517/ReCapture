from django.shortcuts import render, redirect
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required

@login_required
def mypage(request):
    # 내 정보 조회
    return render(request, 'accounts/mypage.html', {'user': request.user})

def logout_view(request):
    # 로그아웃 처리
    auth_logout(request)
    return redirect('gallery:photo_list')

def signup_done(request):
    # 직접 접근/새로고침 방지 (선택)
    if not request.session.pop("signup_done", False):
        return redirect("/accounts/signup/")

    # ✅ 핵심: 회원가입 직후 남아있는 로그인 세션을 강제로 끊기
    auth_logout(request)

    # ✅ 세션을 통째로 초기화해서(쿠키 유지하더라도) "로그인 상태"가 남지 않게 함
    request.session.flush()

    return render(request, "account/signup_done.html")