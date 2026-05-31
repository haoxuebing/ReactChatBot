const STORAGE_KEY = 'nicebing_username'
const DEFAULT_USERNAME = 'user'
const MAX_USERNAME_LENGTH = 12

export function getUsername() {
  return localStorage.getItem(STORAGE_KEY)
}

export function hasUsername() {
  return !!getUsername()
}

export function saveUsername(name) {
  const trimmed = (name || '').trim().slice(0, MAX_USERNAME_LENGTH)
  const finalName = trimmed || DEFAULT_USERNAME
  localStorage.setItem(STORAGE_KEY, finalName)
  return finalName
}

export { DEFAULT_USERNAME, MAX_USERNAME_LENGTH, STORAGE_KEY }
