// Thin API client.
//
// The base URL is empty on purpose: in production FastAPI serves this bundle from
// the same origin, so there is no hostname baked into the build and nothing for a
// visitor in incognito to get wrong. VITE_API_BASE only exists for the case where
// someone wants to run the frontend against a different backend.

const BASE = import.meta.env.VITE_API_BASE || ''

const USER_TOKEN_KEY = 'onward.userToken'
const ADMIN_TOKEN_KEY = 'onward.adminToken'
const USERNAME_KEY = 'onward.username'

// Per-session flags that must be cleared whenever the signed-in account changes.
// Kept here rather than in the router so that logging out cannot leave the next
// account looking at the previous one's onboarding state.
export const session = {
  onboarded: false,
  reset() {
    session.onboarded = false
  }
}

export const tokens = {
  user: () => localStorage.getItem(USER_TOKEN_KEY),
  admin: () => localStorage.getItem(ADMIN_TOKEN_KEY),
  username: () => localStorage.getItem(USERNAME_KEY),
  setUser(token, username) {
    session.reset()
    localStorage.setItem(USER_TOKEN_KEY, token)
    if (username) localStorage.setItem(USERNAME_KEY, username)
  },
  setAdmin(token) {
    localStorage.setItem(ADMIN_TOKEN_KEY, token)
  },
  clearUser() {
    session.reset()
    localStorage.removeItem(USER_TOKEN_KEY)
    localStorage.removeItem(USERNAME_KEY)
  },
  clearAdmin() {
    localStorage.removeItem(ADMIN_TOKEN_KEY)
  }
}

// The most recent /chat trace id seen anywhere in the app. Set by ChatView on
// every turn; read by the bug report button, which lives in the global header
// and so has no view-local access to "what was the last agent trace".
export const lastTrace = { id: null }

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function request(path, { method = 'GET', body, auth = 'user' } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = auth === 'admin' ? tokens.admin() : auth === 'user' ? tokens.user() : null
  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body)
    })
  } catch {
    throw new ApiError('Could not reach the server. Is the backend running?', 0)
  }

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { detail: text }
    }
  }

  if (!response.ok) {
    const detail =
      (data && (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))) ||
      `Request failed (${response.status})`
    throw new ApiError(detail, response.status)
  }
  return data
}

export const api = {
  health: () => request('/health', { auth: null }),

  register: (username, password, accessCode) =>
    request('/auth/register', {
      method: 'POST',
      body: { username, password, access_code: accessCode || undefined },
      auth: null,
    }),
  login: (username, password) =>
    request('/auth/login', { method: 'POST', body: { username, password }, auth: null }),

  adminLogin: (password) =>
    request('/admin/login', { method: 'POST', body: { password }, auth: null }),
  adminPending: () => request('/admin/pending', { auth: 'admin' }),
  adminUsers: () => request('/admin/users', { auth: 'admin' }),
  adminApprove: (id) => request(`/admin/approve/${id}`, { method: 'POST', auth: 'admin' }),
  adminReject: (id) => request(`/admin/reject/${id}`, { method: 'POST', auth: 'admin' }),

  getProfile: () => request('/profile/me'),
  patchProfile: (patch) => request('/profile/me', { method: 'PATCH', body: patch }),
  logDeparture: (payload) =>
    request('/profile/me/departures', { method: 'POST', body: payload }),
  forgetMe: () => request('/profile/me', { method: 'DELETE' }),

  chat: (message) => request('/chat', { method: 'POST', body: { message } }),

  reportBug: (payload) => request('/bugs', { method: 'POST', body: payload }),
  adminBugs: () => request('/admin/bugs', { auth: 'admin' }),
  adminResolveBug: (id) => request(`/admin/bugs/${id}/resolve`, { method: 'POST', auth: 'admin' }),

  // structured travel memory: route, wishlist, reviews, onboarding
  getTravel: () => request('/travel/me'),
  addVisit: (payload) => request('/travel/me/visits', { method: 'POST', body: payload }),
  addWishlist: (payload) => request('/travel/me/wishlist', { method: 'POST', body: payload }),
  dropWishlist: (location) =>
    request(`/travel/me/wishlist/${encodeURIComponent(location)}`, { method: 'DELETE' }),
  saveReview: (payload) => request('/travel/me/reviews', { method: 'POST', body: payload }),
  setInterests: (interests) =>
    request('/travel/me/interests', { method: 'POST', body: interests }),
  setKeyInterests: (interests) =>
    request('/travel/me/interests/key', { method: 'POST', body: interests }),
  pendingReviews: () => request('/travel/me/pending-reviews'),

  // route editing: rate a stop, or drop one that was logged wrongly
  rateStop: (location, rating) =>
    request('/travel/me/history/rating', { method: 'POST', body: { location, rating } }),
  removeStop: (location) =>
    request(`/travel/me/history/${encodeURIComponent(location)}`, { method: 'DELETE' }),

  // onboarding: fixed questions from the backend, plain-text answers back
  startOnboarding: () => request('/travel/me/onboarding'),
  answerOnboarding: (step, text, skipped = false) =>
    request('/travel/me/onboarding/answer', {
      method: 'POST',
      body: { step, text, skipped }
    }),
  completeOnboarding: () => request('/travel/me/onboarding/complete', { method: 'POST' }),
  skipOnboarding: () => request('/travel/me/onboarding/skip', { method: 'POST' }),

  // memory debug page: read everything, delete anything
  getMemoryDebug: () => request('/memory/me'),
  deleteMemoryInterest: (interest) =>
    request(`/memory/me/interests/${encodeURIComponent(interest)}`, { method: 'DELETE' }),
  deleteMemoryPassport: (country) =>
    request(`/memory/me/passports/${encodeURIComponent(country)}`, { method: 'DELETE' }),
  clearMemoryProfileField: (field) =>
    request(`/memory/me/profile-field/${encodeURIComponent(field)}`, { method: 'DELETE' }),
  resetOnboardingDebug: () => request('/memory/me/onboarding/reset', { method: 'POST' }),

  // catch-up: "here's where we left off - what's changed?"
  getCatchup: () => request('/travel/me/catchup'),
  dismissCatchup: () => request('/travel/me/catchup/dismiss', { method: 'POST' }),
  updateCatchup: (message) =>
    request('/travel/me/catchup/update', { method: 'POST', body: { message } })
}
