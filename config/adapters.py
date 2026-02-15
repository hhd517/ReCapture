# config/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.utils import generate_unique_username

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        extra = sociallogin.account.extra_data or {}

        # ✅ 1. email 보정 (특히 kakao)
        if sociallogin.account.provider == "kakao":
            email = (extra.get("kakao_account") or {}).get("email")
            if email and not user.email:
                user.email = email

        # ✅ 2. 이름 보정 (google / naver / kakao 공통)
        if not user.first_name:
            user.first_name = (
                extra.get("given_name")
                or extra.get("name", "")
            )
        if not user.last_name:
            user.last_name = extra.get("family_name", "")

        # 🔥 3. username 무조건 생성 (제일 중요)
        if not user.username:
            base = (
                user.email.split("@")[0]
                if user.email
                else extra.get("name", "user")
            )
            user.username = generate_unique_username([base])

        user.save()
        return user

    # ✅ 로그인 완료 후 이동 URL
    def get_login_redirect_url(self, request):
        return "/"