import api from './api'
import type { AuthTokens, LoginCredentials, RegisterData, User } from '../types'

export const authService = {
  async login(creds: LoginCredentials): Promise<AuthTokens> {
    const { data } = await api.post('/auth/login', null, {
      params: { email: creds.email, password: creds.password },
    })
    return data
  },

  async register(data_: RegisterData): Promise<User> {
    const { data } = await api.post('/auth/register', data_)
    return data
  },

  async me(): Promise<User> {
    const { data } = await api.get('/auth/me', {
      params: { token: localStorage.getItem('access_token') },
    })
    return data
  },

  async refresh(refreshToken: string): Promise<AuthTokens> {
    const { data } = await api.post('/auth/refresh', null, {
      params: { refresh_token: refreshToken },
    })
    return data
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
}
