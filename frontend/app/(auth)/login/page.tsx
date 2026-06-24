'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ApiService } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { ShieldAlert, Loader2, Mail, Lock, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { motion } from 'framer-motion';

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await ApiService.login(email, password);
      setAuth(data.user, data.access_token, data.refresh_token);
      
      // Set cookies immediately so router.replace bypasses middleware properly
      const expires = new Date(Date.now() + 7 * 864e5).toUTCString();
      document.cookie = `securehall-auth-status=true; expires=${expires}; path=/; SameSite=Lax`;
      document.cookie = `securehall-auth-role=${data.user.role}; expires=${expires}; path=/; SameSite=Lax`;
      
      router.replace('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden">
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
        {/* Logo / brand */}
        <div className="text-center mb-10">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.15, duration: 0.4, ease: "easeOut" }}
            className="inline-flex items-center justify-center w-[72px] h-[72px] rounded-2xl mb-5 bg-primary text-primary-foreground shadow-xl shadow-primary/25"
          >
            <svg className="w-9 h-9" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </motion.div>
          <h1 className="text-[2rem] font-bold tracking-tight gradient-text drop-shadow-sm leading-tight">
            SecureHall-RAG
          </h1>
          <p className="text-base text-muted-foreground mt-2">
            Sign in to your workspace
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

            {/* Email */}
            <div className="mb-5">
              <label htmlFor="email" className="block text-sm font-medium text-foreground mb-2">
                Email address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-[18px] w-[18px] text-muted-foreground/70" />
                <Input
                  id="email" type="email" autoComplete="email" required
                  value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="pl-10 h-12 text-base rounded-xl bg-background/50 border-border/60 focus:bg-background transition-colors"
                />
              </div>
            </div>

            {/* Password */}
            <div className="mb-7">
              <label htmlFor="password" className="block text-sm font-medium text-foreground mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-[18px] w-[18px] text-muted-foreground/70" />
                <Input
                  id="password" type="password" autoComplete="current-password" required
                  value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="pl-10 h-12 text-base rounded-xl bg-background/50 border-border/60 focus:bg-background transition-colors"
                />
              </div>
            </div>

            {/* Submit */}
            <Button
              type="submit" disabled={loading}
              className="w-full h-12 text-base rounded-xl shadow-lg shadow-primary/20 font-semibold gap-2 transition-all duration-200"
            >
              {loading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Signing in…
                </>
              ) : (
                <>
                  Sign in
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </form>

          {/* Footer */}
          <p className="text-center text-muted-foreground text-sm mt-7 mb-5 leading-relaxed">
            No account?{' '}
            <Link href="/signup" className="text-primary font-semibold hover:underline underline-offset-2">
              Create one
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}

