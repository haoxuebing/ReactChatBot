const STORAGE_KEY = 'nicebing_username'
const MAX_USERNAME_LENGTH = 12

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

export { MAX_USERNAME_LENGTH, STORAGE_KEY }
