# config/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        if sociallogin.account.provider == "kakao":
            extra = sociallogin.account.extra_data or {}
            email = (extra.get("kakao_account") or {}).get("email")
            if email and not user.email:
                user.email = email
                user.save(update_fields=["email"])
        return user

    # ✅ 로그인 완료 후 이동 URL 강제
    def get_login_redirect_url(self, request):
        return "/"