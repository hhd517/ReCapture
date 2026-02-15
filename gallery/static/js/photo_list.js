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

// 대분류 선택 시 소분류 목록을 업데이트하는 함수
async function updateSubCategoryOptions() {
    const parentId = document.getElementById('targetCategory').value;
    const subSelect = document.getElementById('targetSubCategory');
    
    // 선택을 초기화했을 경우 소분류 드롭다운 숨김
    if (!parentId) {
        subSelect.style.display = 'none';
        return;
    }

    try {
        // 서버로부터 해당 대분류의 소분류 리스트를 가져옴
        const response = await fetch(`/gallery/api/sub-categories/?parent_id=${parentId}`);
        const data = await response.json();

        if (data.success && data.sub_categories.length > 0) {
            // 옵션 초기화
            subSelect.innerHTML = '<option value="">소분류 선택 (선택 사항)</option>';
            
            // 가져온 데이터로 옵션 추가
            data.sub_categories.forEach(sub => {
                const option = document.createElement('option');
                option.value = sub.id;
                option.textContent = sub.name;
                subSelect.appendChild(option);
            });
            
            subSelect.style.display = 'inline-block'; // 소분류가 있으면 보여줌
        } else {
            subSelect.style.display = 'none'; // 소분류가 없으면 숨김
        }
    } catch (error) {
        console.error('Sub-category fetch error:', error);
    }
}

// 이동 실행 함수 수정 (소분류 ID 우선 적용)
async function moveSelectedPhotos() {
    const selectedIds = Array.from(document.querySelectorAll('.photo-select-checkbox:checked')).map(cb => cb.value);
    
    const parentId = document.getElementById('targetCategory').value;
    const subId = document.getElementById('targetSubCategory').value;
    
    // 소분류가 선택되었다면 소분류 ID를 사용하고, 아니면 대분류 ID를 사용
    const targetId = subId || parentId;

    if (selectedIds.length === 0 || !targetId) {
        alert('사진과 이동할 폴더를 모두 선택해주세요!');
        return;
    }

    const response = await fetch('/gallery/photos/move/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': CSRF_TOKEN,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            photoIds: selectedIds, 
            categoryId: targetId // 최종 결정된 ID 전송
        })
    });

    if ((await response.json()).success) {
        location.reload();
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

async function deleteSelectedPhotos() {
    const selectedIds = Array.from(document.querySelectorAll('.photo-select-checkbox:checked'))
                             .map(cb => cb.value);

    if (selectedIds.length === 0) {
        alert('삭제할 사진을 선택해주세요.');
        return;
    }

    if (!confirm(`선택한 ${selectedIds.length}장의 사진을 휴지통으로 보낼까요?`)) {
        return;
    }

    try {
        // 기존 trash_views.py의 로직을 활용할 수 있도록 요청을 보냅니다.
        const response = await fetch('/gallery/photos/bulk-trash/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': CSRF_TOKEN,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ photoIds: selectedIds })
        });

        const data = await response.json();

        if (data.success) {
            alert('휴지통으로 이동되었습니다.');
            location.reload();
        } else {
            alert('삭제 실패: ' + (data.error || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('Delete error:', error);
        alert('서버와 통신 중 오류가 발생했습니다.');
    }
}

// 1. 소분류 이름 수정
async function editSubCategory(subId, currentName) {
    const newName = prompt('수정할 폴더 이름을 입력하세요:', currentName);
    if (!newName || newName === currentName) return;

    try {
        const response = await fetch(`/gallery/api/sub-categories/${subId}/edit/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': CSRF_TOKEN,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: newName })
        });
        const data = await response.json();
        if (data.success) location.reload();
    } catch (e) {
        alert('수정 실패');
    }
}

// 2. 소분류 삭제
async function deleteSubCategory(subId, subName) {
    if (!confirm(`'${subName}' 폴더를 삭제할까요? 폴더 안의 사진들은 대분류(미분류)로 이동됩니다.`)) {
        return;
    }

    try {
        const response = await fetch(`/gallery/api/sub-categories/${subId}/delete/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': CSRF_TOKEN }
        });
        const data = await response.json();
        if (data.success) {
            // 현재 보고 있던 폴더를 삭제했다면 부모 폴더로 이동
            location.href = `?category_id=${data.parent_id}`;
        }
    } catch (e) {
        alert('삭제 실패');
    }
}

let isSubEditMode = false;

function toggleSubEditMode(btn) {
    isSubEditMode = !isSubEditMode;
    const iconContainers = document.querySelectorAll('.sub-management-icons');
    
    if (isSubEditMode) {
        // 편집 모드 ON
        iconContainers.forEach(el => el.style.display = 'flex');
        btn.style.background = '#007bff';
        btn.style.color = 'white';
        btn.innerHTML = '<i class="fa-solid fa-check"></i>'; // 체크 아이콘으로 변경
    } else {
        // 편집 모드 OFF
        iconContainers.forEach(el => el.style.display = 'none');
        btn.style.background = '#f1f1f1';
        btn.style.color = '#666';
        btn.innerHTML = '<i class="fa-solid fa-gear"></i>'; // 다시 톱니바퀴로
    }
}

async function classifyPhotos() {
    // ✅ “분류 전 전체” 분류 시작
    document.getElementById('importProgress').style.display = 'block';
    document.getElementById('importStatus').textContent = `📂 분류 시작...`;
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressText').textContent = `0 / 0`;

    const res = await fetch('/gallery/api/v1/photos/classify/unclassified', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CSRF_TOKEN,
        },
        body: JSON.stringify({}),
    });

    if (!res.ok) {
        const txt = await res.text();
        alert('분류 시작 실패: ' + txt);
        return;
    }

    const data = await res.json();
    const jobId = data.job_id;
    const total = data.total;

    document.getElementById('importStatus').textContent = `📂 ${total}장 분류 시작...`;
    document.getElementById('progressText').textContent = `0 / ${total}`;

    startClassifyPolling(jobId, total);
}

let classifyPollingInterval = null;

function startClassifyPolling(jobId, total) {
    if (classifyPollingInterval) clearInterval(classifyPollingInterval);

    classifyPollingInterval = setInterval(async () => {
        const res = await fetch(`/gallery/api/v1/jobs/${jobId}`); // ✅ /gallery 붙임
        if (!res.ok) return;

        const job = await res.json();

        const done = job.done || 0;
        const percent = Math.round((done / total) * 100);

        document.getElementById('importStatus').textContent =
            `🧠 ${job.message || '분류중...'}`;
        document.getElementById('progressBar').style.width = `${percent}%`;
        document.getElementById('progressText').textContent = `${done} / ${total}`;

        if (job.status === 'done') {
            clearInterval(classifyPollingInterval);
            classifyPollingInterval = null;

            document.getElementById('importStatus').textContent =
                `✅ 분류 완료! (실패 ${job.failed || 0}장)`;

            setTimeout(() => location.reload(), 1000);
        }
    }, 800);
}