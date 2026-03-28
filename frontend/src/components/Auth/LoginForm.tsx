import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Shield, Mail, Lock, AlertCircle } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'

export default function LoginForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { login, isLoading, error, clearError } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await login(email, password)
      navigate('/')
    } catch { /* handled by store */ }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)] px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Shield className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white">Red Team SaaS</h1>
          <p className="text-[var(--color-text-secondary)] mt-2">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-[var(--color-bg-secondary)] rounded-xl border border-[var(--color-border)] p-8">
          {error && (
            <div className="flex items-center gap-2 p-3 mb-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
              <button type="button" onClick={clearError} className="ml-auto text-red-300 hover:text-red-100">&times;</button>
            </div>
          )}

          <div className="mb-4">
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-secondary)]" />
              <input
                type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white placeholder-[var(--color-text-secondary)] focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                placeholder="admin@redteam.local"
              />
            </div>
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-secondary)]" />
              <input
                type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white placeholder-[var(--color-text-secondary)] focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                placeholder="Enter your password"
              />
            </div>
          </div>

          <button
            type="submit" disabled={isLoading}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium rounded-lg transition-colors"
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>

          <p className="text-center text-sm text-[var(--color-text-secondary)] mt-4">
            Don't have an account?{' '}
            <Link to="/register" className="text-indigo-400 hover:text-indigo-300">Register</Link>
          </p>
        </form>
      </div>
    </div>
  )
}
