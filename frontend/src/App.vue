<script setup>
import { computed, onMounted, ref } from 'vue'

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
const adding = ref(false)
const notice = ref('')

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
  const response = await fetch(path, options)
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || '요청을 처리하지 못했습니다.')
  return data
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
  if (!videoUrl.value.trim() || !videoTitle.value.trim()) return
  adding.value = true
  error.value = ''
  try {
    await api('/api/videos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: videoUrl.value.trim(), title: videoTitle.value.trim() }),
    })
    notice.value = '영상을 등록했습니다. 자막 분석에는 몇 분이 걸릴 수 있어요.'
    videoUrl.value = ''
    videoTitle.value = ''
    showAdd.value = false
  } catch (exception) {
    error.value = exception.message
  } finally {
    adding.value = false
  }
}

onMounted(loadVideos)
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
        <button class="add-button" @click="showAdd = true"><span>＋</span> 영상 추가</button>
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
        <label>YouTube URL<input v-model="videoUrl" type="url" placeholder="https://youtube.com/watch?v=…" required /></label>
        <label>영상 제목<input v-model="videoTitle" placeholder="검색 목록에 표시할 제목" required /></label>
        <button class="modal-submit" :disabled="adding">{{ adding ? '등록 중…' : '분석 시작하기 ↗' }}</button>
      </form>
    </div>
  </div>
</template>
