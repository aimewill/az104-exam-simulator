const API_BASE = '/api';

// Token storage helpers
export const getToken = () => localStorage.getItem('token');
export const setToken = (token) => localStorage.setItem('token', token);
export const removeToken = () => localStorage.removeItem('token');

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const token = getToken();
  
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
    },
    ...options,
  };

  const response = await fetch(url, config);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  
  // Handle CSV downloads
  if (response.headers.get('content-type')?.includes('text/csv')) {
    return response.blob();
  }
  
  return response.json();
}

// Import endpoints
export const importApi = {
  getStatus: () => request('/import/status'),
  scan: () => request('/import/scan', { method: 'POST' }),
  run: (edits = []) => request('/import/run', { 
    method: 'POST',
    body: JSON.stringify({ edits }),
  }),
  getReport: () => request('/import/report'),
};

// Session endpoints
export const sessionApi = {
  start: (mode, timeLimitMinutes = null) => request('/session/start', {
    method: 'POST',
    body: JSON.stringify({ mode, time_limit_minutes: timeLimitMinutes }),
  }),
  get: (sessionId) => request(`/session/${sessionId}`),
  getQuestions: (sessionId) => request(`/session/${sessionId}/questions`),
  getStudyQuestions: () => request('/session/study'),
  markStudySeen: (questionId) => request(`/session/study/${questionId}/seen`, { method: 'POST' }),
  getQuestion: (sessionId, index) => request(`/session/${sessionId}/question/${index}`),
  answer: (sessionId, questionId, selected, flagged = false) => request(`/session/answer?session_id=${sessionId}`, {
    method: 'POST',
    body: JSON.stringify({ question_id: questionId, selected, flagged }),
  }),
  submit: (sessionId) => request(`/session/${sessionId}/submit`, { method: 'POST' }),
  getResults: (sessionId) => request(`/session/${sessionId}/results`),
  getNavigator: (sessionId) => request(`/session/${sessionId}/navigator`),
  // Timer endpoints
  getTime: (sessionId) => request(`/session/${sessionId}/time`),
  pause: (sessionId) => request(`/session/${sessionId}/pause`, { method: 'POST' }),
  resume: (sessionId) => request(`/session/${sessionId}/resume`, { method: 'POST' }),
};

// Dashboard endpoints
export const dashboardApi = {
  get: () => request('/dashboard'),
  getDomains: () => request('/domains'),
  exportMissed: () => request('/export/missed.csv'),
  getQuestionStats: () => request('/stats/questions'),
};

// Auth endpoints
export const authApi = {
  register: (email, password, displayName = null) => request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, display_name: displayName }),
  }),
  login: (email, password) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  }),
  me: () => request('/auth/me'),
};
