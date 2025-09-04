// 전역 변수
let API_BASE_URL = 'http://localhost:8000';
let currentQuery = '';
let currentPaperId = '';

// DOM 요소
const searchForm = document.getElementById('searchForm');
const searchQuery = document.getElementById('searchQuery');
const searchBtn = document.getElementById('searchBtn');
const loadingSpinner = document.getElementById('loadingSpinner');
const searchResults = document.getElementById('searchResults');
const resultsList = document.getElementById('resultsList');
const resultsTitle = document.getElementById('resultsTitle');
const processingTime = document.getElementById('processingTime');

// 슬라이더 요소
const limitSlider = document.getElementById('limitSlider');
const limitValue = document.getElementById('limitValue');
const thresholdSlider = document.getElementById('thresholdSlider');
const thresholdValue = document.getElementById('thresholdValue');

// 상태 요소
const apiStatus = document.getElementById('apiStatus');
const totalPapers = document.getElementById('totalPapers');
const avgSearchTime = document.getElementById('avgSearchTime');
const totalSearches = document.getElementById('totalSearches');

// 모달 요소
const paperModal = new bootstrap.Modal(document.getElementById('paperModal'));
const modalPaperTitle = document.getElementById('modalPaperTitle');
const modalPaperAuthors = document.getElementById('modalPaperAuthors');
const modalPaperCategories = document.getElementById('modalPaperCategories');
const modalPaperDate = document.getElementById('modalPaperDate');
const modalPaperAbstract = document.getElementById('modalPaperAbstract');
const modalPaperSimilarity = document.getElementById('modalPaperSimilarity');
const modalPaperLink = document.getElementById('modalPaperLink');
const findSimilarBtn = document.getElementById('findSimilarBtn');

// 그래프 관련 요소
const networkGraph = document.getElementById('networkGraph');
const similarityThreshold = document.getElementById('similarityThreshold');
const graphLoading = document.getElementById('graphLoading');
const paperCount = document.getElementById('paperCount');

// 그래프 변수
let network = null;
let graphData = null;
let currentPapers = [];

// 초기화
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Initializing Paper Search Demo...');
    
    // API URL 가져오기
    try {
        const configResponse = await fetch('/config');
        const config = await configResponse.json();
        API_BASE_URL = config.apiUrl;
        console.log('API Base URL:', API_BASE_URL);
    } catch (error) {
        console.warn('Failed to get API config, using default URL:', error);
        API_BASE_URL = 'http://localhost:8000'; // 강제로 기본값 설정
    }
    
    // 이벤트 리스너 설정
    setupEventListeners();
    
    // API 상태 확인 (더 상세한 로그)
    console.log('Checking API status...');
    await checkApiStatus();
    
    // 통계 정보 로드
    console.log('Loading stats...');
    await loadStats();
    
    // 예시 검색어 제안
    showExampleQueries();
});

function setupEventListeners() {
    // 검색 폼
    searchForm.addEventListener('submit', handleSearch);
    
    // 슬라이더 업데이트
    limitSlider.addEventListener('input', function() {
        limitValue.textContent = this.value;
    });
    
    thresholdSlider.addEventListener('input', function() {
        thresholdValue.textContent = this.value;
    });
    
    // 그래프 유사도 슬라이더
    similarityThreshold.addEventListener('input', function() {
        thresholdValue.textContent = this.value;
        if (graphData) {
            updateGraphThreshold(parseFloat(this.value));
        }
    });
    
    // 유사 논문 찾기 버튼
    findSimilarBtn.addEventListener('click', async function() {
        if (currentPaperId) {
            paperModal.hide();
            await findSimilarPapers(currentPaperId);
        }
    });
    
    // 키보드 단축키 (Ctrl + Enter로 검색)
    searchQuery.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            handleSearch(e);
        }
    });
}

async function checkApiStatus() {
    console.log('Attempting to check API status at:', `${API_BASE_URL}/health`);
    
    // API 상태 표시를 "확인중..."으로 설정
    apiStatus.textContent = '확인중...';
    apiStatus.className = 'badge bg-secondary';
    
    try {
        const response = await axios.get(`${API_BASE_URL}/health`, {
            timeout: 5000, // 5초 타임아웃
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log('API health check successful:', response.data);
        apiStatus.textContent = '온라인';
        apiStatus.className = 'badge status-online';
        
    } catch (error) {
        console.error('API health check failed - Error details:', error);
        console.error('Error message:', error.message);
        console.error('Error response:', error.response);
        
        apiStatus.textContent = '오프라인';
        apiStatus.className = 'badge status-offline';
    }
}

async function loadStats() {
    console.log('Attempting to load stats from:', `${API_BASE_URL}/stats`);
    
    try {
        const response = await axios.get(`${API_BASE_URL}/stats`, {
            timeout: 5000, // 5초 타임아웃
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const stats = response.data;
        console.log('Stats loaded successfully:', stats);
        
        totalPapers.textContent = stats.total_papers || '0';
        avgSearchTime.textContent = stats.avg_search_time 
            ? `${Math.round(stats.avg_search_time)}ms`
            : '-';
        totalSearches.textContent = stats.total_searches || '0';
        
    } catch (error) {
        console.error('Failed to load stats - Error details:', error);
        console.error('Error message:', error.message);
        console.error('Error response:', error.response);
        
        // 기본값으로 설정
        totalPapers.textContent = '-';
        avgSearchTime.textContent = '-';
        totalSearches.textContent = '-';
    }
}

async function handleSearch(e) {
    e.preventDefault();
    
    const query = searchQuery.value.trim();
    if (!query) {
        alert('검색어를 입력해주세요.');
        return;
    }
    
    currentQuery = query;
    await performSearch(query);
}

async function performSearch(query) {
    const limit = parseInt(limitSlider.value);
    const threshold = parseFloat(thresholdSlider.value);
    
    // 고급 검색 옵션 수집
    const advancedOptions = getAdvancedSearchOptions();
    const isAdvancedSearch = Object.keys(advancedOptions).length > 0;
    
    // UI 상태 업데이트
    showLoading(true);
    searchResults.style.display = 'none';
    searchBtn.disabled = true;
    
    try {
        console.log(`Searching for: "${query}" (limit: ${limit}, threshold: ${threshold})`);
        console.log('Advanced options:', advancedOptions);
        
        let response;
        
        if (isAdvancedSearch) {
            // 고급 검색 API 사용
            response = await axios.post(`${API_BASE_URL}/search/advanced`, {
                query: query,
                limit: limit,
                similarity_threshold: threshold,
                ...advancedOptions
            });
        } else {
            // 기본 검색 API 사용
            response = await axios.post(`${API_BASE_URL}/search`, {
                query: query,
                limit: limit,
                similarity_threshold: threshold
            });
        }
        
        const data = response.data;
        console.log('Search results:', data);
        
        // 검색 결과와 그래프 데이터 모두 표시
        await Promise.all([
            displaySearchResults(data),
            loadGraphData(query, limit, threshold, advancedOptions, isAdvancedSearch)
        ]);
        
    } catch (error) {
        console.error('Search failed:', error);
        showErrorMessage('검색에 실패했습니다. API 서버를 확인해주세요.');
    } finally {
        showLoading(false);
        searchBtn.disabled = false;
    }
}

// 고급 검색 옵션 수집 함수
function getAdvancedSearchOptions() {
    const options = {};
    
    // 논문 소스
    const paperSource = document.getElementById('paperSource')?.value;
    if (paperSource) options.paper_source = paperSource;
    
    // 연도 범위
    const yearFrom = document.getElementById('yearFrom')?.value;
    const yearTo = document.getElementById('yearTo')?.value;
    if (yearFrom) options.year_from = parseInt(yearFrom);
    if (yearTo) options.year_to = parseInt(yearTo);
    
    // 최소 인용수
    const minCitations = document.getElementById('minCitations')?.value;
    if (minCitations) options.min_citations = parseInt(minCitations);
    
    // 저널명
    const journalName = document.getElementById('journalName')?.value;
    if (journalName) options.journal_name = journalName;
    
    // 오픈 액세스만
    const openAccessOnly = document.getElementById('openAccessOnly')?.checked;
    if (openAccessOnly) options.open_access_only = true;
    
    return options;
}

async function findSimilarPapers(paperId) {
    const limit = parseInt(limitSlider.value);
    
    showLoading(true);
    searchResults.style.display = 'none';
    
    try {
        console.log(`Finding similar papers for: ${paperId}`);
        
        const response = await axios.post(`${API_BASE_URL}/similar`, {
            paper_id: paperId,
            limit: limit
        });
        
        const data = response.data;
        console.log('Similar papers:', data);
        
        displaySearchResults(data);
        
    } catch (error) {
        console.error('Similar search failed:', error);
        showErrorMessage('유사 논문 검색에 실패했습니다.');
    } finally {
        showLoading(false);
    }
}

function displaySearchResults(data) {
    const { papers, total, processing_time, query } = data;
    
    // 결과 헤더 업데이트
    resultsTitle.textContent = `"${query}" 검색 결과 (${total}개)`;
    processingTime.textContent = `처리시간: ${processing_time}초`;
    
    // 논문 개수 업데이트
    paperCount.textContent = `${papers.length}개`;
    
    // 결과 목록 클리어
    resultsList.innerHTML = '';
    
    // 현재 논문 목록 저장
    currentPapers = papers;
    
    if (papers.length === 0) {
        resultsList.innerHTML = `
            <div class="alert alert-info m-3">
                <i class="fas fa-info-circle me-2"></i>
                검색 결과가 없습니다. 다른 검색어를 시도해보세요.
            </div>
        `;
    } else {
        papers.forEach((paper, index) => {
            const paperCard = createCompactPaperCard(paper, index);
            resultsList.appendChild(paperCard);
        });
    }
    
    // 결과 표시
    searchResults.style.display = 'block';
    searchResults.scrollIntoView({ behavior: 'smooth' });
    
    // 통계 업데이트
    setTimeout(loadStats, 1000);
}

function createPaperCard(paper, index) {
    const col = document.createElement('div');
    col.className = 'col-md-6 col-lg-4';
    
    const similarityClass = getSimilarityClass(paper.similarity);
    const similarityText = paper.similarity ? (paper.similarity * 100).toFixed(1) + '%' : 'N/A';
    
    // 초록 요약 (150자)
    const abstractPreview = paper.abstract 
        ? (paper.abstract.length > 150 
            ? paper.abstract.substring(0, 150) + '...'
            : paper.abstract)
        : '초록 정보 없음';
    
    // 논문 소스와 추가 메타데이터
    const sourceIcon = paper.paper_source === 'openalex' 
        ? '<i class="fas fa-university me-1"></i>' 
        : '<i class="fas fa-archive me-1"></i>';
    
    const sourceBadge = 'OpenAlex';
    
    const citationInfo = paper.cited_by_count 
        ? `<small class="text-muted"><i class="fas fa-quote-right me-1"></i>인용 ${paper.cited_by_count}회</small>`
        : '';
    
    const journalInfo = paper.journal_name 
        ? `<small class="text-muted d-block"><i class="fas fa-book me-1"></i>${paper.journal_name}</small>`
        : '';
    
    col.innerHTML = `
        <div class="card paper-card fade-in" style="animation-delay: ${index * 0.1}s">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="paper-title flex-grow-1">${paper.title}</h6>
                    <span class="badge bg-info ms-2">${sourceBadge}</span>
                </div>
                <p class="paper-authors">
                    <i class="fas fa-users me-1"></i>
                    ${paper.authors.slice(0, 3).join(', ')}
                    ${paper.authors.length > 3 ? ` 외 ${paper.authors.length - 3}명` : ''}
                </p>
                ${journalInfo}
                <p class="paper-abstract">${abstractPreview}</p>
                <div class="paper-meta mb-2">
                    <div class="mb-1">
                        ${paper.categories.map(cat => 
                            `<span class="badge bg-secondary category-badge">${cat}</span>`
                        ).join('')}
                        ${(paper.concepts || []).slice(0, 2).map(concept => 
                            `<span class="badge bg-success concept-badge">${concept}</span>`
                        ).join('')}
                    </div>
                    ${citationInfo}
                    ${paper.similarity ? `<div class="similarity-score ${similarityClass}">
                        ${sourceIcon}유사도 ${similarityText}
                    </div>` : ''}
                </div>
                <div class="d-flex justify-content-between align-items-center mt-2 pt-2 border-top">
                    <button class="btn btn-outline-primary btn-sm" onclick="showPaperModal(arguments[0])" data-paper='${JSON.stringify(paper).replace(/'/g, "&#39;")}'>
                        <i class="fas fa-info-circle me-1"></i>자세히
                    </button>
                    <button class="btn btn-success btn-sm pdf-btn" onclick="downloadPDFDirect(arguments[0], this)" data-paper='${JSON.stringify(paper).replace(/'/g, "&#39;")}'>
                        <i class="fas fa-download me-1"></i>PDF
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // 클릭 이벤트 (카드 body만, 버튼 제외)
    const cardBody = col.querySelector('.card-body');
    const buttons = col.querySelectorAll('button');
    
    cardBody.addEventListener('click', (e) => {
        // 버튼 클릭시에는 모달을 열지 않음
        if (!e.target.closest('button')) {
            showPaperModal(paper);
        }
    });
    
    // 버튼 이벤트 설정
    buttons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const paperData = JSON.parse(btn.dataset.paper);
            
            if (btn.classList.contains('pdf-btn')) {
                downloadPDFDirect(paperData, btn);
            } else {
                showPaperModal(paperData);
            }
        });
    });
    
    return col;
}

function getSimilarityClass(similarity) {
    if (!similarity) return '';
    if (similarity >= 0.8) return 'similarity-high';
    if (similarity >= 0.6) return 'similarity-medium';
    return 'similarity-low';
}

function showPaperModal(paper) {
    currentPaperId = paper.openalex_id || paper.doi;
    
    modalPaperTitle.textContent = paper.title;
    modalPaperAuthors.textContent = paper.authors.join(', ');
    
    // 카테고리와 개념 표시
    let badgeHTML = paper.categories.map(cat => 
        `<span class="badge bg-primary me-1">${cat}</span>`
    ).join('');
    
    if (paper.concepts && paper.concepts.length > 0) {
        badgeHTML += paper.concepts.slice(0, 3).map(concept => 
            `<span class="badge bg-success me-1">${concept}</span>`
        ).join('');
    }
    
    modalPaperCategories.innerHTML = badgeHTML;
    
    // 날짜 정보 (연도 우선)
    const dateInfo = paper.publication_year 
        ? `${paper.publication_year}년`
        : (paper.published_date || '날짜 정보 없음');
    modalPaperDate.textContent = dateInfo;
    modalPaperAbstract.textContent = paper.abstract || '초록 정보 없음';
    
    if (paper.similarity) {
        modalPaperSimilarity.textContent = `${(paper.similarity * 100).toFixed(1)}%`;
        modalPaperSimilarity.className = `badge ${getSimilarityClass(paper.similarity)}`;
    } else {
        modalPaperSimilarity.textContent = 'N/A';
        modalPaperSimilarity.className = 'badge bg-secondary';
    }
    
    // PDF 링크 설정
    if (paper.pdf_url) {
        modalPaperLink.href = paper.pdf_url;
        modalPaperLink.style.display = 'inline-block';
        modalPaperLink.innerHTML = '<i class="fas fa-file-pdf me-1"></i>PDF 보기';
    } else if (paper.doi) {
        // DOI가 있으면 Sci-Hub 링크로 연결 시도
        modalPaperLink.href = '#';
        modalPaperLink.style.display = 'inline-block';
        modalPaperLink.innerHTML = '<i class="fas fa-download me-1"></i>PDF 다운로드';
        modalPaperLink.onclick = () => openPDFFromDOI(paper.doi);
    } else {
        modalPaperLink.style.display = 'none';
    }
    
    // 추가 메타데이터 표시 (모달 내)
    updateModalMetadata(paper);
    
    paperModal.show();
}

// DOI로부터 PDF 열기
async function openPDFFromDOI(doi) {
    try {
        const response = await axios.post(`${API_BASE_URL}/pdf`, {
            doi: doi
        });
        
        const pdfData = response.data;
        if (pdfData.available && pdfData.pdf_url) {
            window.open(pdfData.pdf_url, '_blank');
        } else {
            // Sci-Hub URL로 리다이렉트
            window.open(`https://sci-hub.se/${doi}`, '_blank');
        }
    } catch (error) {
        console.error('PDF fetch failed:', error);
        // 실패시 직접 Sci-Hub로
        window.open(`https://sci-hub.se/${doi}`, '_blank');
    }
}

// 토스트 알림 표시
function showToast(message, type = 'info', duration = 3000) {
    // 토스트 컨테이너 생성 (없는 경우)
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // 토스트 생성
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Bootstrap 토스트 초기화 및 표시
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // 자동 제거
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, duration + 1000);
}

// 직접 PDF 다운로드 (검색 결과 카드에서)
async function downloadPDFDirect(paper, buttonElement) {
    const originalHTML = buttonElement.innerHTML;
    const originalDisabled = buttonElement.disabled;
    
    try {
        // 버튼을 로딩 상태로 변경
        buttonElement.disabled = true;
        buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>로딩...';
        
        // 1. OpenAlex 직접 링크가 있는 경우
        if (paper.pdf_url && paper.open_access_status && 
            ['gold', 'green', 'hybrid', 'bronze'].includes(paper.open_access_status)) {
            window.open(paper.pdf_url, '_blank');
            showToast('오픈 액세스 논문 PDF를 열었습니다.', 'success');
            return;
        }
        
        // 2. DOI를 통한 Sci-Hub 검색
        if (paper.doi) {
            showToast('Sci-Hub에서 PDF를 검색 중입니다...', 'info');
            
            const response = await axios.post(`${API_BASE_URL}/pdf`, {
                doi: paper.doi
            });
            
            const pdfData = response.data;
            if (pdfData.available && pdfData.pdf_url) {
                window.open(pdfData.pdf_url, '_blank');
                showToast('Sci-Hub에서 PDF를 찾았습니다!', 'success');
            } else {
                // API에서 찾지 못한 경우 직접 Sci-Hub로
                window.open(`https://sci-hub.se/${paper.doi}`, '_blank');
                showToast('Sci-Hub 웹사이트로 이동합니다.', 'warning');
            }
        } else if (paper.pdf_url) {
            // DOI는 없지만 PDF URL이 있는 경우
            window.open(paper.pdf_url, '_blank');
            showToast('논문 PDF를 열었습니다.', 'success');
        } else {
            // DOI도 PDF URL도 없는 경우
            showToast('이 논문의 PDF 링크를 찾을 수 없습니다.', 'warning');
        }
        
    } catch (error) {
        console.error('PDF download failed:', error);
        
        // 에러 발생 시 Sci-Hub 직접 시도
        if (paper.doi) {
            window.open(`https://sci-hub.se/${paper.doi}`, '_blank');
            showToast('연결 오류가 발생하여 Sci-Hub 웹사이트로 이동합니다.', 'warning');
        } else {
            showToast('PDF 다운로드에 실패했습니다. 나중에 다시 시도해주세요.', 'danger');
        }
        
    } finally {
        // 버튼을 원래 상태로 복원
        setTimeout(() => {
            buttonElement.disabled = originalDisabled;
            buttonElement.innerHTML = originalHTML;
        }, 1000); // 1초 후 복원
    }
}

// 모달의 추가 메타데이터 업데이트
function updateModalMetadata(paper) {
    // 기존 메타데이터 섹션이 있다면 업데이트, 없다면 생성
    let metadataSection = document.getElementById('modalMetadata');
    if (!metadataSection) {
        metadataSection = document.createElement('div');
        metadataSection.id = 'modalMetadata';
        metadataSection.className = 'mt-3 pt-3 border-top';
        
        // 모달 body에 추가
        const modalBody = document.querySelector('#paperModal .modal-body');
        modalBody.appendChild(metadataSection);
    }
    
    let metadataHTML = '';
    
    if (paper.journal_name) {
        metadataHTML += `<p><strong><i class="fas fa-book me-2"></i>저널:</strong> ${paper.journal_name}</p>`;
    }
    
    if (paper.cited_by_count !== null && paper.cited_by_count !== undefined) {
        metadataHTML += `<p><strong><i class="fas fa-quote-right me-2"></i>인용수:</strong> ${paper.cited_by_count.toLocaleString()}회</p>`;
    }
    
    if (paper.fwci) {
        metadataHTML += `<p><strong><i class="fas fa-chart-line me-2"></i>영향력 지수:</strong> ${paper.fwci.toFixed(2)}</p>`;
    }
    
    if (paper.open_access_status) {
        const statusText = {
            'gold': '골드 오픈액세스',
            'green': '그린 오픈액세스', 
            'hybrid': '하이브리드 오픈액세스',
            'closed': '구독 논문'
        }[paper.open_access_status] || paper.open_access_status;
        
        metadataHTML += `<p><strong><i class="fas fa-unlock me-2"></i>접근성:</strong> ${statusText}</p>`;
    }
    
    const sourceText = 'OpenAlex';
    metadataHTML += `<p><strong><i class="fas fa-database me-2"></i>출처:</strong> ${sourceText}</p>`;
    
    if (paper.doi) {
        metadataHTML += `<p><strong><i class="fas fa-link me-2"></i>DOI:</strong> <code>${paper.doi}</code></p>`;
    }
    
    metadataSection.innerHTML = metadataHTML || '<p class="text-muted">추가 메타데이터 없음</p>';
}

function showLoading(show) {
    loadingSpinner.style.display = show ? 'block' : 'none';
}

function showErrorMessage(message) {
    resultsList.innerHTML = `
        <div class="col-12">
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
        </div>
    `;
    searchResults.style.display = 'block';
}

function showExampleQueries() {
    const examples = [
        'transformer attention mechanism',
        'deep learning neural network',
        'computer vision CNN',
        'natural language processing',
        'generative adversarial network'
    ];
    
    searchQuery.placeholder = `검색어를 입력하세요 (예: ${examples[Math.floor(Math.random() * examples.length)]})`;
}

// 키보드 단축키 안내
console.log('키보드 단축키:');
console.log('- Ctrl + Enter: 검색 실행');
console.log('- Escape: 모달 닫기');

// Escape 키로 모달 닫기
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && paperModal._isShown) {
        paperModal.hide();
    }
});

// ==================== 그래프 관련 함수들 ====================

// 컴팩트 논문 카드 생성
function createCompactPaperCard(paper, index) {
    const card = document.createElement('div');
    card.className = 'paper-card-compact';
    card.dataset.paperId = paper.id;
    card.dataset.paperIndex = index;
    
    const similarityText = paper.similarity ? (paper.similarity * 100).toFixed(1) + '%' : 'N/A';
    const authors = paper.authors.slice(0, 3).join(', ') + (paper.authors.length > 3 ? '...' : '');
    
    card.innerHTML = `
        <div class="paper-title">${paper.title}</div>
        <div class="paper-authors">${authors}</div>
        <div class="paper-meta">
            <div class="d-flex justify-content-between align-items-center">
                <span class="text-muted">
                    <i class="fas fa-quote-right me-1"></i>${paper.cited_by_count || 0}
                    ${paper.publication_year ? '• ' + paper.publication_year : ''}
                </span>
                <div>
                    <span class="similarity-badge badge bg-primary me-1">${similarityText}</span>
                    <button class="btn btn-success btn-sm pdf-btn-compact" onclick="event.stopPropagation(); downloadPDFDirect(arguments[0], this)" data-paper='${JSON.stringify(paper).replace(/'/g, "&#39;")}'>
                        <i class="fas fa-download"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // 클릭 이벤트
    card.addEventListener('click', (e) => {
        // 버튼 클릭시에는 모달을 열지 않음
        if (!e.target.closest('.pdf-btn-compact')) {
            selectPaper(paper, index);
            showPaperModal(paper);
        }
    });
    
    // PDF 버튼 이벤트
    const pdfBtn = card.querySelector('.pdf-btn-compact');
    if (pdfBtn) {
        pdfBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const paperData = JSON.parse(pdfBtn.dataset.paper);
            downloadPDFDirect(paperData, pdfBtn);
        });
    }
    
    return card;
}

// 논문 선택
function selectPaper(paper, index) {
    // 이전 선택 해제
    document.querySelectorAll('.paper-card-compact').forEach(card => {
        card.classList.remove('selected');
    });
    
    // 현재 선택
    const selectedCard = document.querySelector(`[data-paper-index="${index}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }
    
    // 그래프에서 해당 노드 하이라이트
    if (network && network.body.nodes[paper.id]) {
        network.selectNodes([paper.id]);
        network.focus(paper.id, {
            scale: 1.2,
            animation: true
        });
    }
}

// 그래프 데이터 로드
async function loadGraphData(query, limit, threshold, advancedOptions, isAdvancedSearch) {
    try {
        console.log('Loading graph data...');
        showGraphLoading(true);
        
        let response;
        if (isAdvancedSearch) {
            response = await axios.post(`${API_BASE_URL}/graph-data`, {
                query: query,
                limit: limit,
                similarity_threshold: threshold,
                ...advancedOptions
            });
        } else {
            response = await axios.post(`${API_BASE_URL}/graph-data`, {
                query: query,
                limit: limit,
                similarity_threshold: threshold
            });
        }
        
        graphData = response.data;
        console.log('Graph data loaded:', graphData);
        
        createGraph(graphData);
        
    } catch (error) {
        console.error('Failed to load graph data:', error);
        showGraphError();
    } finally {
        showGraphLoading(false);
    }
}

// 그래프 생성
function createGraph(data) {
    if (!data || !data.nodes || !data.edges) {
        console.error('Invalid graph data:', data);
        return;
    }
    
    const nodes = new vis.DataSet(data.nodes);
    const edges = new vis.DataSet(data.edges);
    
    const graphDataSets = {
        nodes: nodes,
        edges: edges
    };
    
    const options = {
        nodes: {
            shape: 'circle',
            borderWidth: 2,
            borderWidthSelected: 3,
            font: {
                size: 12,
                color: '#343434'
            }
        },
        edges: {
            smooth: {
                enabled: true,
                type: 'dynamic',
                roundness: 0.5
            },
            width: 1
        },
        physics: {
            enabled: true,
            stabilization: { iterations: 100 },
            barnesHut: {
                gravitationalConstant: -8000,
                centralGravity: 0.3,
                springLength: 95,
                springConstant: 0.04,
                damping: 0.09
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 200,
            hideEdgesOnDrag: false,
            hideNodesOnDrag: false
        }
    };
    
    // 기존 네트워크 정리
    if (network) {
        network.destroy();
    }
    
    // 새 네트워크 생성
    network = new vis.Network(networkGraph, graphDataSets, options);
    
    // 이벤트 리스너 설정
    setupGraphEventListeners();
    
    console.log(`Graph created with ${data.nodes.length} nodes and ${data.edges.length} edges`);
}

// 그래프 이벤트 리스너 설정
function setupGraphEventListeners() {
    // 노드 클릭
    network.on('click', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = graphData.nodes.find(n => n.id === nodeId);
            if (node && node.paper_data) {
                showPaperModal(node.paper_data);
                highlightPaperInList(nodeId);
            }
        }
    });
    
    // 노드 더블클릭 - 유사 논문 로드
    network.on('doubleClick', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = graphData.nodes.find(n => n.id === nodeId);
            if (node && node.paper_data) {
                loadSimilarPapers(node.paper_data.openalex_id || node.paper_data.doi);
            }
        }
    });
    
    // 호버 효과
    network.on('hoverNode', function(params) {
        networkGraph.style.cursor = 'pointer';
    });
    
    network.on('blurNode', function(params) {
        networkGraph.style.cursor = 'default';
    });
}

// 리스트에서 논문 하이라이트
function highlightPaperInList(nodeId) {
    const paperCard = document.querySelector(`[data-paper-id="${nodeId}"]`);
    if (paperCard) {
        // 이전 선택 해제
        document.querySelectorAll('.paper-card-compact').forEach(card => {
            card.classList.remove('selected');
        });
        
        // 현재 선택
        paperCard.classList.add('selected');
        paperCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// 유사도 임계값 업데이트
function updateGraphThreshold(threshold) {
    if (!network || !graphData) return;
    
    const filteredEdges = graphData.edges.filter(edge => edge.value >= threshold);
    
    network.setData({
        nodes: graphData.nodes,
        edges: filteredEdges
    });
    
    console.log(`Graph updated with threshold ${threshold}: ${filteredEdges.length} edges`);
}

// 그래프 로딩 표시
function showGraphLoading(show) {
    if (graphLoading) {
        graphLoading.style.display = show ? 'block' : 'none';
    }
}

// 그래프 오류 표시
function showGraphError() {
    if (networkGraph) {
        networkGraph.innerHTML = `
            <div class="d-flex align-items-center justify-content-center h-100">
                <div class="text-center text-muted">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                    <p>그래프 데이터를 로드할 수 없습니다.</p>
                </div>
            </div>
        `;
    }
}