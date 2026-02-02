# photos/api/google.py
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication

# CSRF 체크 안 하는 SessionAuthentication
class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return

from rest_framework.response import Response
from rest_framework import status
from photos.models import GoogleCredential
from photos.serializers.google import (
    GoogleCallbackSerializer,
    GoogleStatusResponseSerializer,
    GoogleAuthorizeResponseSerializer,
    GoogleCallbackResponseSerializer,
    GoogleUnlinkResponseSerializer
)
from photos.serializers.response import APIResponse
from photos.services.google_photos_service import GooglePhotosService
import os

# 1. 구글 연동 상태 조회
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
        response_data = APIResponse.success({
            "connected": False
        })
        
        return Response(response_data, status=status.HTTP_200_OK)


# 2. 구글 연동 시작 (URL 발급)
@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def google_authorize(request):
    """구글 OAuth 인증 URL 생성"""
    
    try:
        # 환경 변수에서 redirect URI 가져오기
        redirect_uri = os.getenv('GOOGLE_PHOTOS_REDIRECT_URI', 'http://localhost:8000/api/v1/photos/google/callback/')
        
        # 인증 URL 생성
        auth_url, state = GooglePhotosService.get_authorization_url(redirect_uri)
        
        # state와 user_id를 세션에 저장 (CSRF 방지)
        request.session['google_oauth_state'] = state
        request.session['google_oauth_user_id'] = request.user.id  # ← 추가!
        request.session.save()  # ← 명시적 저장
        
        response_data = APIResponse.success({
            "authUrl": auth_url
        })
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        response_data = APIResponse.error(
            code="GOOGLE_AUTH_ERROR",
            message=f"구글 인증 URL 생성 실패: {str(e)}"
        )
        
        return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 3. 구글 연동 완료 (콜백)
@csrf_exempt
@api_view(['GET', 'POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def google_callback(request):
    """구글 OAuth 콜백 처리"""
    
    # GET 요청 처리 (Google에서 리디렉션)
    if request.method == 'GET':
        code = request.GET.get('code')
        state = request.GET.get('state')
        
        if not code:
            return redirect('/gallery/?error=no_code')
        
        # 세션에서 user_id 가져오기
        user_id = request.session.get('google_oauth_user_id')
        
        if not user_id:
            # 세션 없으면 로그인된 유저 확인
            if request.user.is_authenticated:
                user_id = request.user.id
            else:
                return redirect('/accounts/login/?next=/gallery/')
        
        # User 객체 가져오기
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return redirect('/accounts/login/?next=/gallery/')
        
        # Redirect URI
        redirect_uri = os.getenv('GOOGLE_PHOTOS_REDIRECT_URI', 
                                'http://localhost:8000/api/v1/photos/google/callback/')
        
        try:
            # 인증 코드를 토큰으로 교환
            token_data = GooglePhotosService.exchange_code_for_tokens(code, redirect_uri)
            
            # DB에 저장 또는 업데이트
            google_cred, created = GoogleCredential.objects.update_or_create(
                user=user,
                defaults={
                    'google_email': token_data['google_email'],
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data['refresh_token'],
                    'token_uri': token_data['token_uri'],
                    'client_id': token_data['client_id'],
                    'client_secret': token_data['client_secret'],
                    'scopes': token_data['scopes'],
                    'is_active': True
                }
            )
            
            # 세션 정리
            if 'google_oauth_user_id' in request.session:
                del request.session['google_oauth_user_id']
            if 'google_oauth_state' in request.session:
                del request.session['google_oauth_state']
            
            # 성공 시 갤러리로 리디렉션
            return redirect('/gallery/?google_connected=true')
        
        except Exception as e:
            print(f"Google callback error: {e}")
            import traceback
            traceback.print_exc()
            return redirect(f'/gallery/?error=google_auth_failed')


# 4. 구글 연동 해제
@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def google_unlink(request):
    """구글 포토 연동 해제"""
    user = request.user
    
    try:
        google_cred = GoogleCredential.objects.get(user=user)
        google_cred.is_active = False
        google_cred.save()
        
        response_data = APIResponse.success({
            "unlinked": True
        })
        
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