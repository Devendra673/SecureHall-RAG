'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ApiService } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { ShieldAlert, Loader2, ArrowRight, Mail, User, Lock, KeyRound } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { motion } from 'framer-motion';

const fields = [
  { id: 'full_name',  label: 'Full name',        type: 'text',     placeholder: 'Jane Smith',      autoComplete: 'name',         required: false, icon: User },
  { id: 'email',     label: 'Email address',     type: 'email',    placeholder: 'you@company.com', autoComplete: 'email',        required: true,  icon: Mail },
  { id: 'username',  label: 'Username',           type: 'text',     placeholder: 'jane_smith',      autoComplete: 'username',     required: true,  icon: User },
  { id: 'password',  label: 'Password',           type: 'password', placeholder: '8+ characters',   autoComplete: 'new-password', required: true,  icon: Lock },
  { id: 'confirm',   label: 'Confirm password',   type: 'password', placeholder: '••••••••',        autoComplete: 'new-password', required: true,  icon: KeyRound },
];

type FormState = { full_name: string; email: string; username: string; password: string; confirm: string };

export default function SignupPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [form, setForm] = useState<FormState>({ full_name: '', email: '', username: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const update = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [field]: e.target.value }));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (form.password !== form.confirm) { setError('Passwords do not match'); return; }
    if (form.password.length < 8) { setError('Password must be at least 8 characters'); return; }
    setLoading(true);
    try {
      const data = await ApiService.register(form.email, form.username, form.password, form.full_name);
      setAuth(data.user, data.access_token, data.refresh_token);
      
      // Set cookies immediately so router.replace bypasses middleware properly
      const expires = new Date(Date.now() + 7 * 864e5).toUTCString();
      document.cookie = `securehall-auth-status=true; expires=${expires}; path=/; SameSite=Lax`;
      document.cookie = `securehall-auth-role=${data.user.role}; expires=${expires}; path=/; SameSite=Lax`;
      
      router.replace('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden py-10">
      {/* Animated gradient orbs — matches the chat mesh background */}
      <div className="absolute inset-0 z-0 overflow-hidden">
        <div className="absolute top-[-20%] left-[-15%] w-[50%] h-[50%] rounded-full blur-[120px] pointer-events-none opacity-30 bg-[oklch(0.6_0.15_250)] dark:bg-[oklch(0.3_0.15_260)] animate-[pulse-mesh_20s_ease-in-out_infinite_alternate]" />
        <div className="absolute bottom-[-20%] right-[-15%] w-[50%] h-[50%] rounded-full blur-[120px] pointer-events-none opacity-25 bg-[oklch(0.7_0.12_280)] dark:bg-[oklch(0.2_0.12_280)] animate-[pulse-mesh_25s_ease-in-out_infinite_alternate-reverse]" />
        <div className="absolute top-[30%] left-[30%] w-[40%] h-[40%] rounded-full blur-[140px] pointer-events-none opacity-20 bg-[oklch(0.65_0.1_220)] dark:bg-[oklch(0.25_0.1_240)] animate-[pulse-mesh_30s_ease-in-out_infinite_alternate]" />
      </div>

      {/* Card wrapper */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="relative w-full max-w-[440px] mx-4 z-10"
      >
        {/* Brand */}
        <div className="text-center mb-10">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.15, duration: 0.4, ease: "easeOut" }}
            className="inline-flex items-center justify-center w-[72px] h-[72px] rounded-2xl mb-5 bg-primary text-primary-foreground shadow-xl shadow-primary/25"
          >
            <svg className="w-9 h-9" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
          </motion.div>
          <h1 className="text-[2rem] font-bold tracking-tight gradient-text drop-shadow-sm leading-tight">
            Create account
          </h1>
          <p className="text-base text-muted-foreground mt-2">
            Join SecureHall-RAG workspace
          </p>
        </div>

        {/* Glass card — matching the chat's glass-panel style */}
        <div className="glass-panel rounded-2xl border border-border/50 shadow-xl shadow-black/5 dark:shadow-black/30 p-8 md:p-10 backdrop-blur-xl bg-card">
          <form onSubmit={handleSubmit}>

            {/* Error */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2.5 bg-destructive/10 border border-destructive/20 text-destructive rounded-xl px-4 py-3.5 mb-6"
              >
                <ShieldAlert className="h-4 w-4 shrink-0" />
                <p className="text-sm font-medium m-0 leading-snug">{error}</p>
              </motion.div>
            )}

            {/* Fields */}
            {fields.map(({ id, label, type, placeholder, autoComplete, required, icon: Icon }, idx) => (
              <motion.div
                key={id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + idx * 0.05, duration: 0.3 }}
                className="mb-4"
              >
                <label htmlFor={id} className="block text-sm font-medium text-foreground mb-2">
                  {label}
                </label>
                <div className="relative">
                  <Icon className="absolute left-3.5 top-1/2 -translate-y-1/2 h-[18px] w-[18px] text-muted-foreground/70" />
                  <Input
                    id={id} type={type} autoComplete={autoComplete}
                    required={required}
                    value={form[id as keyof FormState]}
                    onChange={update(id)}
                    placeholder={placeholder}
                    className="pl-10 h-12 text-base rounded-xl bg-background/50 border-border/60 focus:bg-background transition-colors"
                  />
                </div>
              </motion.div>
            ))}

            {/* Submit */}
            <Button
              type="submit" disabled={loading}
              className="w-full h-12 text-base rounded-xl mt-5 shadow-lg shadow-primary/20 font-semibold gap-2 transition-all duration-200"
            >
              {loading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Creating account…
                </>
              ) : (
                <>
                  Create account
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </form>

          {/* Footer */}
          <p className="text-center text-muted-foreground text-sm mt-7 mb-2 leading-relaxed">
            Already have an account?{' '}
            <Link href="/login" className="text-primary font-semibold hover:underline underline-offset-2">
              Sign in
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
