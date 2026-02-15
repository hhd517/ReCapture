from allauth.account.adapter import DefaultAccountAdapter
from allauth.utils import generate_unique_username
from django.urls import reverse

class CustomAccountAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        base = "user"
        if getattr(user, "email", None):
            base = user.email.split("@")[0]
        user.username = generate_unique_username([base])

class AccountAdapter(DefaultAccountAdapter):
    def get_signup_redirect_url(self, request):
        request.session["signup_done"] = True
        return reverse("accounts:signup_done")  