/**
 * Auth store — persisted to localStorage so the user stays logged in
 * across page refreshes. Tokens are stored in memory for the session
 * and only the refresh token is persisted long-term.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, UserRole } from '@/types'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean

  login: (user: User, access: string, refresh: string) => void
  logout: () => void
  setAccessToken: (token: string) => void
  updateUser: (user: Partial<User>) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      login: (user, access, refresh) =>
        set({ user, accessToken: access, refreshToken: refresh, isAuthenticated: true }),

      logout: () =>
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false }),

      setAccessToken: (token) => set({ accessToken: token }),

      updateUser: (partial) =>
        set((state) => ({ user: state.user ? { ...state.user, ...partial } : null })),
    }),
    {
      name: 'judiciary-auth',
      // Only persist refresh token and user — not the short-lived access token
      partialize: (state) => ({
        user: state.user,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
)

// Convenience selectors
export const useUser = () => useAuthStore((s) => s.user)
export const useRole = (): UserRole | null => useAuthStore((s) => s.user?.role ?? null)
export const useIsAuthenticated = () => useAuthStore((s) => s.isAuthenticated)
