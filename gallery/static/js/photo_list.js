function createSubCategory(parentId, csrfToken) {
    const subName = prompt('새로운 세부 폴더 이름을 입력하세요:');
    if (!subName) return;

    fetch(`/gallery/categories/add/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ 
            name: subName, 
            parent_id: parentId 
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('폴더 생성에 실패했습니다: ' + (data.error || '알 수 없는 오류'));
        }
    })
    .catch(err => {
        console.error('Error:', err);
        alert('서버와의 통신 중 오류가 발생했습니다.');
    });
}

let isEditMode = false;

// 페이지 로드 시 체크박스 클릭 이벤트 연결
document.addEventListener('DOMContentLoaded', function() {
    const editBtn = document.getElementById('editModeBtn');
    const moveBar = document.getElementById('moveControlBar');
    const bookmarkBtns = document.querySelectorAll('.bookmark-btn');
    const checkboxWrappers = document.querySelectorAll('.edit-checkbox-wrapper');
    const checkboxes = document.querySelectorAll('.photo-select-checkbox');

    // 1. 편집 모드 토글
    if (editBtn) {
        editBtn.addEventListener('click', () => {
            isEditMode = !isEditMode;
            moveBar.style.display = isEditMode ? 'flex' : 'none';
            bookmarkBtns.forEach(btn => btn.style.display = isEditMode ? 'none' : 'block');
            checkboxWrappers.forEach(wrapper => wrapper.style.display = isEditMode ? 'block' : 'none');
            if (!isEditMode) exitEditMode();
        });
    }

    // 2. 체크박스 클릭 시 숫자 업데이트 및 카드 강조 (✅ 이 부분이 추가되어야 함)
    checkboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            const selectedCount = document.querySelectorAll('.photo-select-checkbox:checked').length;
            document.getElementById('selectedCount').textContent = selectedCount;
            // 선택 시 카드 테두리 강조 효과
            cb.closest('.photo-card').classList.toggle('selected', cb.checked);
        });
    });
});

// 3. 사진 이동 실행 함수
async function moveSelectedPhotos() {
    const selectedIds = Array.from(document.querySelectorAll('.photo-select-checkbox:checked'))
                             .map(cb => cb.value);
    const categoryId = document.getElementById('targetCategory').value;

    if (selectedIds.length === 0) {
        alert('선택된 사진이 없습니다.');
        return;
    }
    if (!categoryId) {
        alert('이동할 폴더를 선택해주세요.');
        return;
    }

    try {
        const response = await fetch('/gallery/photos/move/', {
            method: 'POST',
            headers: {
                // 💡 상단에 정의한 CSRF_TOKEN 변수를 사용합니다.
                'X-CSRFToken': CSRF_TOKEN, 
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                photoIds: selectedIds, 
                categoryId: categoryId 
            })
        });

        const data = await response.json();

        if (data.success) {
            alert('이동이 완료되었습니다.');
            location.reload(); 
        } else {
            alert('이동 실패: ' + (data.message || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('Move error:', error);
        alert('서버와 통신 중 오류가 발생했습니다.');
    }
}

function exitEditMode() {
    // 1. 하단 플로팅 바 숨기기
    const moveBar = document.getElementById('moveControlBar');
    if (moveBar) moveBar.style.display = 'none';

    // 2. 체크박스 영역 숨기고 북마크 버튼 다시 보이기
    const bookmarkBtns = document.querySelectorAll('.bookmark-btn');
    const checkboxWrappers = document.querySelectorAll('.edit-checkbox-wrapper');
    
    bookmarkBtns.forEach(btn => btn.style.display = 'block');
    checkboxWrappers.forEach(wrapper => wrapper.style.display = 'none');

    // 3. 선택된 모든 체크박스 해제 및 카드 강조 효과 제거
    document.querySelectorAll('.photo-select-checkbox').forEach(cb => {
        cb.checked = false;
        cb.closest('.photo-card').classList.remove('selected');
    });

    // 4. 선택된 숫자 0으로 초기화
    const selectedCountSpan = document.getElementById('selectedCount');
    if (selectedCountSpan) selectedCountSpan.textContent = '0';

    // 5. 전역 변수 상태 업데이트 (편집 버튼 로직과 동기화)
    isEditMode = false; 
}