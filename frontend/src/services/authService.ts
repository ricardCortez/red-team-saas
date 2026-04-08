import api from './api'
import type { AuthTokens, LoginCredentials, RegisterData, User } from '../types'

export const authService = {
  async login(creds: LoginCredentials): Promise<AuthTokens> {
    const { data } = await api.post('/auth/login', {
      email: creds.email,
      password: creds.password,
    })
    return data
  },

  async register(data_: RegisterData): Promise<User> {
    const { data } = await api.post('/auth/register', data_)
    return data
  },

  async me(): Promise<User> {
    // The Bearer token is attached automatically by the api interceptor.
    const { data } = await api.get('/auth/me')
    return data
  },

  async refresh(refreshToken: string): Promise<AuthTokens> {
    const { data } = await api.post('/auth/refresh', { refresh_token: refreshToken })
    return data
  },

  async updateProfile(data: { full_name?: string }): Promise<User> {
    const { data: res } = await api.put('/auth/me', data)
    return res
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await api.post('/auth/me/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
}
