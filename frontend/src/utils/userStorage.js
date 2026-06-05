const STORAGE_KEY = 'nicebing_username'
const RECENT_USERS_KEY = 'nicebing_recent_users'
const MAX_USERNAME_LENGTH = 12
const MAX_RECENT_USERS = 10

export function getUsername() {
  return localStorage.getItem(STORAGE_KEY)
}

export function hasUsername() {
  return !!getUsername()
}

export function saveUsername(name) {
  const trimmed = (name || '').trim().slice(0, MAX_USERNAME_LENGTH)
  if (!trimmed) {
    return null
  }
  localStorage.setItem(STORAGE_KEY, trimmed)
  return trimmed
}

export function clearUsername() {
  localStorage.removeItem(STORAGE_KEY)
}

export function generateAnonymousUsername() {
  const suffix = Math.random().toString(36).slice(2, 6)
  return `访客-${suffix}`.slice(0, MAX_USERNAME_LENGTH)
}

export function ensureUsername() {
  let name = getUsername()
  if (!name) {
    name = generateAnonymousUsername()
    saveUsername(name)
  }
  addRecentUser(name)
  return name
}

export function getRecentUsers() {
  try {
    const raw = localStorage.getItem(RECENT_USERS_KEY)
    const list = raw ? JSON.parse(raw) : []
    return Array.isArray(list) ? list.filter(Boolean) : []
  } catch {
    return []
  }
}

export function addRecentUser(name) {
  const trimmed = (name || '').trim().slice(0, MAX_USERNAME_LENGTH)
  if (!trimmed) return
  const recent = getRecentUsers().filter(u => u !== trimmed)
  recent.unshift(trimmed)
  localStorage.setItem(RECENT_USERS_KEY, JSON.stringify(recent.slice(0, MAX_RECENT_USERS)))
}

export { MAX_USERNAME_LENGTH, STORAGE_KEY }
