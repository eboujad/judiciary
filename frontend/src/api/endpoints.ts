import { apiClient } from './client'
import type {
  AuthTokens, User, LawFirm, Lawyer,
  CaseListItem, CaseDetail, CourtForm,
  Payment, PaginatedResponse,
} from '@/types'

// ── Auth ──────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<AuthTokens>('/auth/login/', { email, password }),

  logout: (refresh: string) =>
    apiClient.post('/auth/logout/', { refresh }),

  me: () =>
    apiClient.get<User>('/auth/me/'),

  changePassword: (current_password: string, new_password: string, new_password_confirm: string) =>
    apiClient.post('/auth/change-password/', { current_password, new_password, new_password_confirm }),
}

// ── Firms ─────────────────────────────────────────────────────────────────
export const firmsApi = {
  list: () => apiClient.get<PaginatedResponse<LawFirm>>('/firms/'),
  mine: () => apiClient.get<LawFirm>('/firms/mine/'),
  create: (data: Record<string, string>) => apiClient.post<LawFirm>('/firms/', data),
  approve: (id: string) => apiClient.post<LawFirm>(`/firms/${id}/approve/`),

  lawyers: (firmId: string) =>
    apiClient.get<PaginatedResponse<Lawyer>>(`/firms/${firmId}/lawyers/`),

  createLawyer: (firmId: string, data: Record<string, string>) =>
    apiClient.post<Lawyer>(`/firms/${firmId}/lawyers/`, data),
}

// ── Court Forms (fee schedule) ────────────────────────────────────────────
export const formsApi = {
  list: (court?: string) =>
    apiClient.get<PaginatedResponse<CourtForm>>('/cases/forms/', { params: court ? { court } : {} }),
}

// ── Cases ─────────────────────────────────────────────────────────────────
export const casesApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<PaginatedResponse<CaseListItem>>('/cases/', { params }),

  get: (id: string) =>
    apiClient.get<CaseDetail>(`/cases/${id}/`),

  create: (data: {
    title: string
    court: string
    case_type: string
    description: string
    opposing_party_name: string
    relief_sought: string
    form_ids: string[]
  }) => apiClient.post<CaseDetail>('/cases/', data),

  submit: (id: string) =>
    apiClient.post<CaseDetail>(`/cases/${id}/submit/`),

  resubmit: (id: string) =>
    apiClient.post<CaseDetail>(`/cases/${id}/resubmit/`),

  // Accounts workflow
  accountsQueue: () =>
    apiClient.get<PaginatedResponse<CaseListItem>>('/cases/accounts/queue/'),

  accountsReview: (id: string, note: string, action: 'forward' | 'flag') =>
    apiClient.post<CaseDetail>(`/cases/${id}/accounts/review/`, { note, action }),

  // Registrar workflow
  registrarQueue: () =>
    apiClient.get<PaginatedResponse<CaseListItem>>('/cases/registrar/queue/'),

  registrarReview: (id: string, note: string, action: 'register' | 'reject') =>
    apiClient.post<CaseDetail>(`/cases/${id}/registrar/review/`, { note, action }),
}

// ── Documents ─────────────────────────────────────────────────────────────
export const documentsApi = {
  list: (caseId: string) =>
    apiClient.get(`/documents/cases/${caseId}/`),

  upload: (caseId: string, file: File, category: string, description: string) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('category', category)
    fd.append('description', description)
    return apiClient.post(`/documents/cases/${caseId}/upload/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  verify: (docId: string) =>
    apiClient.get(`/documents/${docId}/verify/`),

  remove: (docId: string) =>
    apiClient.delete(`/documents/${docId}/`),
}

// ── Payments ──────────────────────────────────────────────────────────────
export const paymentsApi = {
  get: (caseId: string) =>
    apiClient.get<Payment>(`/payments/cases/${caseId}/`),

  initiate: (caseId: string, payer_phone: string) =>
    apiClient.post<{ payment: Payment; payment_url: string }>(
      `/payments/cases/${caseId}/initiate/`, { payer_phone }
    ),

  mockConfirm: (reference: string) =>
    apiClient.post<{ payment: Payment }>('/payments/mock-confirm/', { reference }),
}

// ── Audit ─────────────────────────────────────────────────────────────────
export const auditApi = {
  forCase: (caseId: string) =>
    apiClient.get(`/audit/cases/${caseId}/`),

  list: (params?: Record<string, string>) =>
    apiClient.get('/audit/logs/', { params }),
}
