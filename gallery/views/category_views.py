from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from gallery.models import Photo, Category
import json
from django.views.decorators.http import require_POST

@csrf_exempt
@login_required
def add_category(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name')
        parent_id = data.get('parent_id')
        
        parent = get_object_or_404(Category, id=parent_id, user=request.user)

        if Category.objects.filter(user=request.user, parent_id=parent_id, name=name).exists():
            return JsonResponse({"success": False, "error": "이미 존재하는 폴더 이름입니다."}, status=400)
        
        new_cat = Category.objects.create(
            user=request.user,
            name=name,
            parent=parent,
            category_key=f"sub_{timezone.now().timestamp()}" # 임의 키 생성
        )
        return JsonResponse({"success": True, "id": new_cat.id})
    
@require_POST
def move_photos(request):
    try:
        data = json.loads(request.body)
        photo_ids = data.get('photoIds', [])
        target_cat_id = data.get('categoryId')
        
        if not target_cat_id:
            return JsonResponse({'success': False, 'message': '대상 폴더를 선택해주세요.'})

        # 한꺼번에 업데이트 (효율적)
        Photo.objects.filter(id__in=photo_ids, user=request.user).update(category_id=target_cat_id)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
    
def get_sub_categories(request):
    """
    대분류 ID를 받아 그에 속한 소분류 목록을 반환하는 API
    """
    parent_id = request.GET.get('parent_id')
    
    if not parent_id:
        return JsonResponse({'success': False, 'message': '부모 ID가 없습니다.'}, status=400)
        
    # 부모 ID가 있고, 현재 로그인한 사용자의 카테고리만 필터링
    sub_categories = Category.objects.filter(parent_id=parent_id, user=request.user)
    
    data = [
        {'id': sub.id, 'name': sub.name} for sub in sub_categories
    ]
    
    return JsonResponse({
        'success': True, 
        'sub_categories': data
    })

@login_required
def edit_sub_category(request, sub_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_name = data.get('name')
            
            # 본인 카테고리인지 확인하며 가져오기
            category = get_object_or_404(Category, id=sub_id, user=request.user)
            category.name = new_name
            category.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def delete_sub_category(request, sub_id):
    if request.method == 'POST':
        try:
            category = get_object_or_404(Category, id=sub_id, user=request.user)
            parent_id = category.parent_id # 부모 카테고리 ID 보관
            
            # 💡 중요: 삭제되는 폴더 안의 사진들을 부모(대분류) 폴더로 이동
            Photo.objects.filter(category=category, user=request.user).update(category_id=parent_id)
            
            # 카테고리 삭제
            category.delete()
            
            return JsonResponse({
                'success': True, 
                'parent_id': parent_id # 삭제 후 부모 페이지로 리다이렉트하기 위해 전달
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)