from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from gallery.models import Photo
import json

# 1. 휴지통 목록 조회 (GET)
@csrf_exempt
@login_required
def trash_list(request):
    # GET: 휴지통 목록 화면 보여주기
    if request.method == 'GET':
        trashed_photos = Photo.objects.filter(user=request.user, is_trashed=True)
        return render(request, 'gallery/trash_list.html', {'photos': trashed_photos})

    # POST: 휴지통으로 이동시키기
    elif request.method == 'POST':
        return move_to_trash(request)
    
@csrf_exempt
@login_required
def bulk_move_to_trash(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            photo_ids = data.get('photoIds', [])
            
            # 한 번의 쿼리로 여러 사진 업데이트
            Photo.objects.filter(id__in=photo_ids, user=request.user).update(
                is_trashed=True,
                trashed_at=timezone.now()
            )
            
            return JsonResponse({"success": True, "count": len(photo_ids)})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

# 2. 휴지통 이동 (POST)
@csrf_exempt
@login_required
def move_to_trash(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            photo_id = data.get('photoId')
            photo = get_object_or_404(Photo, id=photo_id, user=request.user)
            photo.is_trashed = True
            photo.trashed_at = timezone.now()
            photo.save()
            return JsonResponse({
                "success": True,
                "data": {"photoId": photo.id, "trashed": True, "expiresAt": photo.expires_at.isoformat()}
            })
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
        
@login_required
def bulk_restore_photos(request):
    """선택한 사진들을 휴지통에서 복구"""
    if request.method == 'POST':
        data = json.loads(request.body)
        photo_ids = data.get('photoIds', [])
        Photo.objects.filter(id__in=photo_ids, user=request.user).update(is_trashed=False, trashed_at=None)
        return JsonResponse({"success": True})

@login_required
def bulk_permanent_delete(request):
    """선택한 사진들을 DB에서 완전히 삭제"""
    if request.method == 'POST':
        data = json.loads(request.body)
        photo_ids = data.get('photoIds', [])
        # 실제 파일까지 삭제하려면 쿼리셋을 순회하며 delete() 호출
        photos = Photo.objects.filter(id__in=photo_ids, user=request.user)
        count = photos.count()
        photos.delete() 
        return JsonResponse({"success": True, "count": count})

@login_required
def empty_trash_all(request):
    """현재 사용자의 휴지통에 있는 모든 사진 영구 삭제"""
    if request.method == 'POST':
        # is_trashed=True인 모든 사진 필터링
        photos = Photo.objects.filter(user=request.user, is_trashed=True)
        count = photos.count()
        
        if count == 0:
            return JsonResponse({"success": False, "error": "비울 사진이 없습니다."})
            
        # DB 삭제 (실제 파일 삭제 로직이 모델에 연결되어 있다면 바로 삭제됨)
        photos.delete()
        
        return JsonResponse({"success": True, "count": count})

# 3. 복구 (POST)
@csrf_exempt
@login_required
def restore_photo(request, photoid):
    if request.method == 'POST':
        photo = get_object_or_404(Photo, id=photoid, user=request.user, is_trashed=True)
        photo.is_trashed = False
        photo.trashed_at = None
        photo.save()
        return JsonResponse({"success": True, "data": {"photoId": photo.id, "restored": True}})

# 4. 영구 삭제 (DELETE)
@csrf_exempt
@login_required
def permanent_delete(request, photoid):
    if request.method == 'DELETE':
        photo = get_object_or_404(Photo, id=photoid, user=request.user, is_trashed=True)
        if photo.image:
            photo.image.delete()
        photo.delete()
        return JsonResponse({"success": True, "data": {"photoId": photoid, "deletedPermanently": True}})