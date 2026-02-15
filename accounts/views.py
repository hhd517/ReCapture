from django.shortcuts import render, redirect
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from .forms import ProfileUpdateForm

@login_required
def mypage(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "회원정보가 저장되었습니다.")
            return redirect("accounts:mypage")
        else:
            messages.error(request, "입력값을 다시 확인해주세요.")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, "accounts/mypage.html", {"user": request.user, "form": form})

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

@login_required
def profile_edit(request):
    # ✅ 소셜 로그인 유저 차단: 비밀번호가 없는 계정이면 접근 불가
    if not request.user.has_usable_password():
        return HttpResponseForbidden("소셜 로그인 계정은 이 페이지를 사용할 수 없습니다.")

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "회원정보가 저장되었습니다.")
            return redirect("accounts:profile_edit")
        messages.error(request, "입력값을 다시 확인해주세요.")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, "accounts/profile_edit.html", {"form": form, "user": request.user})