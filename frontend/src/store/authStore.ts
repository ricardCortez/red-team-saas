import { create } from 'zustand'
import type { User } from '../types'
import { authService } from '../services/authService'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  register: (data: { email: string; username: string; password: string; full_name: string }) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
  setUser: (user: User) => void
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null })
    try {
      const tokens = await authService.login({ email, password })
      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
      const user = await authService.me()
      set({ user, isAuthenticated: true, isLoading: false })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Login failed'
      set({ error: msg, isLoading: false })
      throw err
    }
  },

  register: async (data) => {
    set({ isLoading: true, error: null })
    try {
      await authService.register(data)
      set({ isLoading: false })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Registration failed'
      set({ error: msg, isLoading: false })
      throw err
    }
  },

  logout: () => {
    authService.logout()
    set({ user: null, isAuthenticated: false })
  },

  fetchUser: async () => {
    try {
      const user = await authService.me()
      set({ user, isAuthenticated: true })
    } catch (err: any) {
      // Only clear auth on explicit 401 — not on network errors or timeouts
      if (err?.response?.status === 401) {
        set({ user: null, isAuthenticated: false })
        authService.logout()
      }
    }
  },

  setUser: (user: User) => set({ user }),

  clearError: () => set({ error: null }),
}))
