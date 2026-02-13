# photos/api/google.py
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework import status

from photos.models import GoogleCredential
from photos.serializers.response import APIResponse
from photos.services.google_photos_service import GooglePhotosService
import os


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def google_status(request):
    """구글 포토 연동 상태 확인"""
    user = request.user
    try:
        google_cred = GoogleCredential.objects.get(user=user, is_active=True)
        response_data = APIResponse.success({
            "connected": True,
            "googleEmail": google_cred.google_email
        })
        return Response(response_data, status=status.HTTP_200_OK)
    except GoogleCredential.DoesNotExist:
        response_data = APIResponse.success({"connected": False})
        return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def google_authorize(request):
    """구글 OAuth 인증 URL 생성"""
    try:
        redirect_uri = os.getenv(
            'GOOGLE_PHOTOS_REDIRECT_URI',
            'http://localhost:8000/api/v1/photos/google/callback/'
        )

        auth_url, state = GooglePhotosService.get_authorization_url(redirect_uri)

        request.session['google_oauth_state'] = state
        request.session['google_oauth_user_id'] = request.user.id
        request.session.save()

        response_data = APIResponse.success({"authUrl": auth_url})
        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        response_data = APIResponse.error(
            code="GOOGLE_AUTH_ERROR",
            message=f"구글 인증 URL 생성 실패: {str(e)}"
        )
        return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET', 'POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def google_callback(request):
    """구글 OAuth 콜백 처리"""
    if request.method == 'GET':
        code = request.GET.get('code')
        if not code:
            return redirect('/gallery/?error=no_code')

        user_id = request.session.get('google_oauth_user_id')
        if not user_id:
            if request.user.is_authenticated:
                user_id = request.user.id
            else:
                return redirect('/accounts/login/?next=/gallery/')

        from django.contrib.auth.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return redirect('/accounts/login/?next=/gallery/')

        redirect_uri = os.getenv(
            'GOOGLE_PHOTOS_REDIRECT_URI',
            'http://localhost:8000/api/v1/photos/google/callback/'
        )

        try:
            token_data = GooglePhotosService.exchange_code_for_tokens(code, redirect_uri)

            # ✅ 기존 credential이 있으면 먼저 가져와서 refresh_token을 보존
            existing = GoogleCredential.objects.filter(user=user).first()

            new_refresh = token_data.get('refresh_token')
            if not new_refresh:
                # refresh_token이 안 내려오면 기존값 유지(없으면 빈 문자열로라도 유지)
                new_refresh = existing.refresh_token if existing else ""

            google_cred, created = GoogleCredential.objects.update_or_create(
                user=user,
                defaults={
                    'google_email': token_data.get('google_email') or (existing.google_email if existing else ""),
                    'access_token': token_data.get('access_token') or (existing.access_token if existing else ""),
                    'refresh_token': new_refresh,
                    'token_uri': token_data.get('token_uri') or (existing.token_uri if existing else "https://oauth2.googleapis.com/token"),
                    'client_id': token_data.get('client_id') or (existing.client_id if existing else ""),
                    'client_secret': token_data.get('client_secret') or (existing.client_secret if existing else ""),
                    'scopes': token_data.get('scopes') or (existing.scopes if existing else []),
                    'is_active': True
                }
            )

            # 세션 정리
            request.session.pop('google_oauth_user_id', None)
            request.session.pop('google_oauth_state', None)

            return redirect('/gallery/?google_connected=true')

        except Exception as e:
            print(f"Google callback error: {e}")
            import traceback
            traceback.print_exc()
            return redirect('/gallery/?error=google_auth_failed')


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def google_unlink(request):
    """구글 포토 연동 해제"""
    user = request.user
    try:
        google_cred = GoogleCredential.objects.get(user=user)
        google_cred.is_active = False
        google_cred.save(update_fields=["is_active"])
        response_data = APIResponse.success({"unlinked": True})
        return Response(response_data, status=status.HTTP_200_OK)

    except GoogleCredential.DoesNotExist:
        response_data = APIResponse.error(
            code="NOT_CONNECTED",
            message="연동된 구글 계정이 없습니다."
        )
        return Response(response_data, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        response_data = APIResponse.error(
            code="UNLINK_ERROR",
            message=f"연동 해제 실패: {str(e)}"
        )
        return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)