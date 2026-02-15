# accounts/forms.py
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class ProfileUpdateForm(forms.ModelForm):
    """
    마이페이지에서 username/email 수정용
    """
    class Meta:
        model = User
        fields = ["username", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "mp-input", "placeholder": "사용자 이름"}),
            "email": forms.EmailInput(attrs={"class": "mp-input", "placeholder": "이메일 주소"}),
        }

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not username:
            raise forms.ValidationError("이름(사용자 이름)은 비워둘 수 없어요.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        # 이메일은 선택으로 두고 싶으면 빈 값 허용
        return email