import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { Scale, Eye, EyeOff } from 'lucide-react'
import { authApi } from '@/api/endpoints'
import { useAuthStore } from '@/stores/authStore'
import { getApiError } from '@/api/client'
import { Spinner } from '@/components/ui/Spinner'

interface FormData { email: string; password: string }

export function Login() {
  const navigate    = useNavigate()
  const login       = useAuthStore((s) => s.login)
  const [showPw, setShowPw] = useState(false)

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>()

  const onSubmit = async (data: FormData) => {
    try {
      const res = await authApi.login(data.email, data.password)
      login(res.data.user, res.data.access, res.data.refresh)
      toast.success(`Welcome, ${res.data.user.first_name}.`)
      navigate('/dashboard')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 bg-gold-dim border border-gold-border rounded-xl flex items-center justify-center mb-4">
            <Scale size={28} className="text-gold" />
          </div>
          <h1 className="text-2xl font-serif text-ink text-center">Gambia Judiciary</h1>
          <p className="text-sm text-muted mt-1">E-Filing & Case Management</p>
        </div>

        {/* Card */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Sign In</h2>
          </div>

          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="form-group">
              <label className="form-label">Email address</label>
              <input
                type="email"
                className="form-input"
                placeholder="you@firm.gm"
                autoComplete="email"
                {...register('email', {
                  required: 'Email is required',
                  pattern: { value: /\S+@\S+\.\S+/, message: 'Invalid email' },
                })}
              />
              {errors.email && <span className="form-error">{errors.email.message}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  className="form-input pr-10"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  {...register('password', { required: 'Password is required' })}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-ink"
                >
                  {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              {errors.password && <span className="form-error">{errors.password.message}</span>}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary btn w-full justify-center mt-2"
            >
              {isSubmitting ? <Spinner size="sm" /> : 'Sign In'}
            </button>
          </form>

          <p className="text-center text-xs text-muted mt-4">
            Authorised users only. Access is logged and audited.
          </p>
        </div>

        <p className="text-center text-xs text-muted/50 mt-6 font-mono">
          Gambia Judiciary © {new Date().getFullYear()}
        </p>
      </div>
    </div>
  )
}
