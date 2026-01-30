from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from gallery.models import Photo

@login_required
def photo_list(request):
    # 명세서 5번 통합 조회를 위한 데이터를 템플릿에 전달
    photos = Photo.objects.filter(user=request.user, is_trashed=False).order_by('-created_at')
    
    # render를 사용하면 gallery/photo_list.html 화면이 브라우저에 뜹니다.
    return render(request, 'gallery/photo_list.html', {
        'photos': photos,
    })

@login_required
def photo_detail(request, photoid):
    photo = get_object_or_404(Photo, id=photoid, user=request.user)
    return render(request, 'gallery/photo_detail.html', {'photo': photo})