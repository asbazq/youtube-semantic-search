import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'

function setup() {
  const pending = []
  const timers = new Map()
  let id = 0
  const script = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8')
    .split('<script setup>')[1].split('</script>')[0].replace(/^import .*$/gm, '')
  const context = vm.createContext({
    ref: value => ({ value }), computed: fn => ({ get value() { return fn() } }),
    watch() {}, onMounted() {}, onUnmounted() {},
    localStorage: { getItem() { return null } },
    createChatSessionId: () => `session-${++id}`, AbortController,
    setTimeout: fn => { timers.set(++id, fn); return id },
    clearTimeout: key => timers.delete(key),
    fetch: (path, options) => new Promise((resolve, reject) => {
      pending.push({ path, resolve: answer => resolve({ ok: true, status: 200, json: async () => answer }) })
      options.signal?.addEventListener('abort', () => reject(new Error('aborted')))
    }),
  })
  vm.runInContext(script + '\n globalThis.chat = { askChat, resetChat, chatQuestion, chatMessages, chatLoading, chatError }', context)
  return { ...context.chat, pending, timers }
}

test('two successive questions both finish and retain messages', async () => {
  const chat = setup()
  for (let n = 0; n < 2; n++) {
    chat.chatQuestion.value = `question ${n}`
    const request = chat.askChat()
    chat.pending.at(-1).resolve({ answer: `answer ${n}` })
    await request
    assert.equal(chat.chatLoading.value, false)
  }
  assert.equal(chat.chatMessages.value.length, 4)
  assert.equal(chat.timers.size, 0)
})

test('timeout unlocks the input and permits retry', async () => {
  const chat = setup()
  chat.chatQuestion.value = 'question'
  const request = chat.askChat()
  chat.timers.values().next().value()
  await request
  assert.equal(chat.chatLoading.value, false)
  assert.match(chat.chatError.value, /초과/)
  assert.equal(chat.chatQuestion.value, 'question')
  const retry = chat.askChat()
  chat.pending.at(-1).resolve({ answer: 'answer' })
  await retry
  assert.equal(chat.chatMessages.value.length, 2)
})

test('reset releases pending request without unlocking a newer request', async () => {
  const chat = setup()
  chat.chatQuestion.value = 'old'
  const old = chat.askChat()
  chat.resetChat()
  assert.equal(chat.chatLoading.value, false)
  chat.chatQuestion.value = 'new'
  const current = chat.askChat()
  await old
  assert.equal(chat.chatLoading.value, true)
  chat.pending.at(-1).resolve({ answer: 'new answer' })
  await current
  assert.equal(chat.chatLoading.value, false)
  assert.equal(chat.chatMessages.value.length, 2)
})
