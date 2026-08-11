<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const query = ref('')
const selectedVideo = ref('')
const videos = ref([])
const results = ref([])
const searchedQuery = ref('')
const loading = ref(false)
const error = ref('')
const showAdd = ref(false)
const videoUrl = ref('')
const videoTitle = ref('')
const addMode = ref('single')
const batchInput = ref('')
const playlistUrl = ref('')
const adding = ref(false)
const notice = ref('')
const importProgress = ref(null)
const admin = ref(null)
const showLogin = ref(false)
const showManage = ref(false)
const loginUsername = ref('')
const loginPassword = ref('')
const authToken = ref(localStorage.getItem('admin_token') || '')
let progressTimer = null

const selectedTitle = computed(() =>
  videos.value.find((video) => video.video_id === selectedVideo.value)?.title || '모든 영상'
)

function formatTime(value) {
  const total = Math.max(0, Math.floor(Number(value) || 0))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  return [hours, minutes, seconds].map((part) => String(part).padStart(2, '0')).join(':')
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (authToken.value) headers.Authorization = `Bearer ${authToken.value}`
  const response = await fetch(path, { ...options, headers })
  const data = await response.json().catch(() => ({}))
  if (response.status === 401 && !path.endsWith('/login')) {
    admin.value = null
    authToken.value = ''
    localStorage.removeItem('admin_token')
  }
  if (!response.ok) throw new Error(data.detail || '요청을 처리하지 못했습니다.')
  return data
}

async function loginAdmin() {
  error.value = ''
  try {
    const data = await api('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: loginUsername.value.trim(), password: loginPassword.value }),
    })
    authToken.value = data.access_token
    localStorage.setItem('admin_token', data.access_token)
    admin.value = { username: data.username, role: data.role }
    loginPassword.value = ''
    showLogin.value = false
    notice.value = '관리자로 로그인했습니다.'
  } catch (exception) {
    error.value = exception.message
  }
}

async function logoutAdmin() {
  try { await api('/api/auth/logout', { method: 'POST' }) } catch (_) { /* 세션은 로컬에서도 제거한다. */ }
  authToken.value = ''
  admin.value = null
  localStorage.removeItem('admin_token')
  notice.value = '로그아웃했습니다.'
}

async function restoreAdmin() {
  if (!authToken.value) return
  try { admin.value = await api('/api/auth/me') } catch (_) { admin.value = null }
}

async function deleteVideo(video) {
  if (!video || !window.confirm(`“${video.title}” 영상을 검색 라이브러리에서 삭제할까요?`)) return
  error.value = ''
  try {
    await api(`/api/videos/${encodeURIComponent(video.video_id)}`, { method: 'DELETE' })
    videos.value = videos.value.filter((item) => item.video_id !== video.video_id)
    if (selectedVideo.value === video.video_id) selectedVideo.value = ''
    notice.value = '영상을 삭제했습니다.'
  } catch (exception) {
    error.value = exception.message
  }
}

async function pollImport(jobId) {
  clearTimeout(progressTimer)
  try {
    importProgress.value = await api(`/api/import-jobs/${jobId}`)
    if (['queued', 'reading', 'processing'].includes(importProgress.value.status)) {
      progressTimer = setTimeout(() => pollImport(jobId), 2000)
    } else {
      await loadVideos()
    }
  } catch (exception) {
    error.value = exception.message
  }
}

function trackImport(jobId) {
  importProgress.value = { job_id: jobId, status: 'queued', progress: 0, total: 0, processed: 0 }
  pollImport(jobId)
}

async function loadVideos() {
  try {
    const data = await api('/api/videos')
    videos.value = data.videos || []
  } catch (exception) {
    error.value = '서버에 연결할 수 없습니다. API 서버가 실행 중인지 확인해 주세요.'
  }
}

async function search() {
  if (!query.value.trim() || loading.value) return
  loading.value = true
  error.value = ''
  notice.value = ''
  try {
    const data = await api('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query.value.trim(),
        video_id: selectedVideo.value || null,
        top_k: 12,
      }),
    })
    searchedQuery.value = query.value.trim()
    results.value = data.results || []
  } catch (exception) {
    error.value = exception.message
  } finally {
    loading.value = false
  }
}

async function addVideo() {
  if (adding.value) return
  adding.value = true
  error.value = ''
  try {
    if (addMode.value === 'single') {
      if (!videoUrl.value.trim() || !videoTitle.value.trim()) return
      await api('/api/videos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: videoUrl.value.trim(), title: videoTitle.value.trim() }),
      })
      notice.value = '영상을 등록했습니다. 자막 분석에는 몇 분이 걸릴 수 있어요.'
      videoUrl.value = ''
      videoTitle.value = ''
    } else if (addMode.value === 'batch') {
      const videosToAdd = parseBatchInput(batchInput.value)
      if (!videosToAdd.length) throw new Error('추가할 영상 목록을 입력해 주세요.')
      const data = await api('/api/videos/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ videos: videosToAdd }),
      })
      notice.value = `${data.total_queued}개 영상을 등록했습니다.${data.skipped.length ? ` 중복 ${data.skipped.length}개는 제외했어요.` : ''}`
      trackImport(data.job_id)
      batchInput.value = ''
    } else {
      if (!playlistUrl.value.trim()) throw new Error('재생목록 URL을 입력해 주세요.')
      const data = await api('/api/playlists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: playlistUrl.value.trim() }),
      })
      notice.value = '재생목록 전체를 등록했습니다. 영상 목록을 확인한 뒤 순서대로 분석합니다.'
      trackImport(data.job_id)
      playlistUrl.value = ''
    }
    showAdd.value = false
  } catch (exception) {
    error.value = exception.message
  } finally {
    adding.value = false
  }
}

function formatRemaining(value) {
  if (value == null) return '계산 중…'
  const minutes = Math.floor(value / 60)
  const seconds = Math.max(0, Math.round(value % 60))
  return minutes ? `약 ${minutes}분 ${seconds}초` : `약 ${seconds}초`
}

function parseBatchInput(value) {
  return value.split(/\r?\n/).map((line, index) => {
    const trimmed = line.trim()
    if (!trimmed) return null
    const separator = trimmed.includes('|') ? '|' : trimmed.includes('\t') ? '\t' : null
    if (!separator) throw new Error(`${index + 1}번째 줄을 "URL 또는 ID | 제목" 형식으로 입력해 주세요.`)
    const [source, ...titleParts] = trimmed.split(separator)
    const title = titleParts.join(separator).trim()
    if (!source.trim() || !title) throw new Error(`${index + 1}번째 줄의 URL/ID 또는 제목이 비어 있습니다.`)
    return { url: source.trim(), title }
  }).filter(Boolean)
}

onMounted(() => { loadVideos(); restoreAdmin() })
onUnmounted(() => clearTimeout(progressTimer))
</script>

<template>
  <div class="page-shell">
    <header class="nav">
      <a class="brand" href="#" aria-label="Rhino Strength 홈">
        <img src="/rhino-strength-logo.png" alt="" />
        <span>RHINO <b>STRENGTH</b></span>
      </a>
      <nav>
        <a href="#search">검색</a>
        <button v-if="admin" class="add-button" @click="showAdd = true"><span>＋</span> 영상 추가</button>
        <button v-if="admin" class="manage-button" @click="showManage = true">영상 관리</button>
        <button v-if="admin" class="auth-button" @click="logoutAdmin">{{ admin.username }} · 로그아웃</button>
        <button v-else class="auth-button" @click="showLogin = true">ADMIN 로그인</button>
      </nav>
    </header>

    <main>
      <section id="search" class="hero">
        <div class="eyebrow"><span></span> RHINO STRENGTH VIDEO ARCHIVE</div>
        <h1>운동의 답을<br /><em>영상 속에서.</em></h1>
        <p class="hero-copy">라이노스트렝스 영상 속 운동 동작과 코칭 내용을 이해하고,<br />궁금한 내용이 나오는 정확한 순간을 찾아드립니다.</p>

        <form class="search-box" @submit.prevent="search">
          <div class="search-main">
            <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="m20 20-4-4"></path></svg>
            <input v-model="query" placeholder="예: 스쿼트할 때 무릎이 아픈 이유" aria-label="검색어" />
            <button :disabled="loading || !query.trim()" type="submit">
              <span v-if="!loading">검색하기</span><span v-else>찾는 중…</span>
              <span class="arrow">↗</span>
            </button>
          </div>
          <div class="search-filter">
            <span>검색 범위</span>
            <select v-model="selectedVideo" aria-label="검색할 영상">
              <option value="">모든 영상</option>
              <option v-for="video in videos" :key="video.video_id" :value="video.video_id">{{ video.title }}</option>
            </select>
          </div>
        </form>
        <div class="suggestions">
          <span>이렇게 검색해 보세요</span>
          <button v-for="sample in ['벤치프레스 견갑 고정', '허리 통증 없는 데드리프트', '하체 운동 루틴']" :key="sample" @click="query = sample; search()">{{ sample }}</button>
        </div>
      </section>

      <section v-if="error || notice" class="message" :class="{ error }">{{ error || notice }}</section>

      <section v-if="importProgress" class="import-progress" :class="importProgress.status">
        <div class="progress-heading">
          <div>
            <span class="section-label">IMPORT PROGRESS</span>
            <h3 v-if="importProgress.status === 'reading'">재생목록 영상 확인 중…</h3>
            <h3 v-else-if="importProgress.status === 'complete'">모든 영상 분석 완료</h3>
            <h3 v-else-if="importProgress.status === 'partial'">분석 완료 · {{ importProgress.failed }}개 실패</h3>
            <h3 v-else-if="importProgress.status === 'failed'">가져오기에 실패했습니다</h3>
            <h3 v-else>{{ importProgress.current_title || '분석 준비 중…' }}</h3>
          </div>
          <strong v-if="importProgress.total">{{ importProgress.processed }} / {{ importProgress.total }}</strong>
        </div>
        <div class="progress-track"><span :style="{ width: `${importProgress.progress || 0}%` }"></span></div>
        <div class="progress-meta">
          <span>{{ importProgress.progress || 0 }}%</span>
          <span v-if="importProgress.status === 'processing'">예상 남은 시간 {{ formatRemaining(importProgress.remaining_seconds) }}</span>
          <span v-else-if="importProgress.status === 'reading'">영상 수를 불러오고 있습니다</span>
          <span v-else-if="importProgress.error">{{ importProgress.error }}</span>
        </div>
      </section>

      <section v-if="searchedQuery || loading" class="results-section">
        <div class="results-heading">
          <div>
            <span class="section-label">SEARCH RESULTS</span>
            <h2>“{{ searchedQuery || query }}”</h2>
          </div>
          <p v-if="!loading"><strong>{{ results.length }}</strong>개의 장면 · {{ selectedTitle }}</p>
        </div>

        <div v-if="loading" class="loading-grid">
          <div v-for="number in 3" :key="number" class="skeleton"></div>
        </div>
        <div v-else-if="results.length" class="result-grid">
          <a v-for="(result, index) in results" :key="`${result.video_id}-${result.start_time}`" class="result-card" :href="result.youtube_url" target="_blank" rel="noopener">
            <div class="thumbnail">
              <img :src="`https://i.ytimg.com/vi/${result.video_id}/mqdefault.jpg`" :alt="result.video_title" />
              <span class="rank">{{ String(index + 1).padStart(2, '0') }}</span>
              <span class="timestamp">{{ formatTime(result.start_time) }}</span>
              <span class="play">▶</span>
            </div>
            <div class="card-body">
              <div class="card-meta"><span>{{ Math.round(result.score * 100) }}% 일치</span><span>{{ formatTime(result.start_time) }} — {{ formatTime(result.end_time) }}</span></div>
              <h3>{{ result.video_title }}</h3>
              <p>{{ result.text }}</p>
              <div class="watch">YouTube에서 이 장면 보기 <span>↗</span></div>
            </div>
          </a>
        </div>
        <div v-else class="empty-state"><span>⌁</span><h3>일치하는 장면을 찾지 못했어요</h3><p>조금 더 넓은 의미의 문장으로 다시 검색해 보세요.</p></div>
      </section>
    </main>

    <footer><span>RHINO STRENGTH</span><p>더 강해지기 위한 답을 찾아드립니다.</p><small>© 2026 RHINO STRENGTH</small></footer>

    <div v-if="showAdd" class="modal-backdrop" @click.self="showAdd = false">
      <form class="modal" @submit.prevent="addVideo">
        <button class="modal-close" type="button" @click="showAdd = false">×</button>
        <span class="section-label">ADD TO LIBRARY</span>
        <h2>새 영상 추가</h2>
        <p>라이노스트렝스 YouTube 영상의 자막을 분석해 운동 검색 라이브러리에 추가합니다.</p>
        <div class="add-tabs" role="tablist" aria-label="영상 추가 방식">
          <button type="button" :class="{ active: addMode === 'single' }" @click="addMode = 'single'">한 개 추가</button>
          <button type="button" :class="{ active: addMode === 'batch' }" @click="addMode = 'batch'">여러 개 추가</button>
          <button type="button" :class="{ active: addMode === 'playlist' }" @click="addMode = 'playlist'">재생목록 추가</button>
        </div>
        <template v-if="addMode === 'single'">
          <label>YouTube URL 또는 영상 ID<input v-model="videoUrl" type="text" placeholder="https://youtube.com/watch?v=… 또는 dQw4w9WgXcQ" required /></label>
          <label>영상 제목<input v-model="videoTitle" placeholder="검색 목록에 표시할 제목" required /></label>
        </template>
        <template v-else-if="addMode === 'batch'">
          <label>영상 목록<textarea v-model="batchInput" rows="8" placeholder="dQw4w9WgXcQ | 첫 번째 영상 제목&#10;https://youtu.be/abcdefghijk | 두 번째 영상 제목" required></textarea></label>
          <p class="batch-help">한 줄에 하나씩 <b>URL 또는 ID | 영상 제목</b> 형식으로 입력하세요. 최대 100개까지 등록할 수 있습니다.</p>
        </template>
        <template v-else>
          <label>YouTube 재생목록 URL 또는 ID<input v-model="playlistUrl" type="text" placeholder="PLFZbtclGCQITquPgFaWUVMeM5X8dny1G1" required /></label>
          <p class="batch-help">전체 YouTube 주소, <b>list=PL…</b>, 또는 <b>PL…</b> 재생목록 ID만 입력해도 포함된 영상을 모두 가져옵니다.</p>
        </template>
        <button class="modal-submit" :disabled="adding">{{ adding ? '등록 중…' : addMode === 'batch' ? '모두 분석 시작하기 ↗' : addMode === 'playlist' ? '재생목록 전체 분석하기 ↗' : '분석 시작하기 ↗' }}</button>
      </form>
    </div>

    <div v-if="showLogin" class="modal-backdrop" @click.self="showLogin = false">
      <form class="modal login-modal" @submit.prevent="loginAdmin">
        <button class="modal-close" type="button" @click="showLogin = false">×</button>
        <span class="section-label">ADMIN ACCESS</span>
        <h2>관리자 로그인</h2>
        <p>영상 추가와 삭제는 ADMIN 계정으로 로그인한 경우에만 가능합니다.</p>
        <label>아이디<input v-model="loginUsername" autocomplete="username" required /></label>
        <label>비밀번호<input v-model="loginPassword" type="password" autocomplete="current-password" required /></label>
        <button class="modal-submit">로그인 ↗</button>
      </form>
    </div>

    <div v-if="showManage" class="modal-backdrop" @click.self="showManage = false">
      <section class="modal manage-modal">
        <button class="modal-close" type="button" @click="showManage = false">×</button>
        <span class="section-label">ADMIN LIBRARY</span>
        <h2>영상 관리</h2>
        <p>검색 라이브러리에 등록된 영상입니다. 삭제하면 해당 영상의 임베딩 데이터가 DB에서 제거됩니다.</p>
        <div v-if="videos.length" class="manage-list">
          <div v-for="video in videos" :key="video.video_id" class="manage-item">
            <div><strong>{{ video.title }}</strong><small>{{ video.video_id }}</small></div>
            <button type="button" @click="deleteVideo(video)">DB에서 삭제</button>
          </div>
        </div>
        <div v-else class="manage-empty">등록된 영상이 없습니다.</div>
      </section>
    </div>
  </div>
</template>
