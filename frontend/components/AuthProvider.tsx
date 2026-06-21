'use client';

/**
 * Phase 7.4 — AuthProvider
 * Syncs Zustand auth state to cookies so Next.js middleware can read them.
 * Also provides a logout function accessible throughout the app.
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

function setCookie(name: string, value: string, days = 7) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function deleteCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated && user) {
      // Sync to cookies for middleware
      setCookie('securehall-auth-status', 'true');
      setCookie('securehall-auth-role', user.role);
    } else {
      deleteCookie('securehall-auth-status');
      deleteCookie('securehall-auth-role');
    }
  }, [isAuthenticated, user]);

  return <>{children}</>;
}

/**
 * useLogout — call this to clear auth state and redirect to /login
 */
export function useLogout() {
  const { logout } = useAuthStore();
  const router = useRouter();

  return () => {
    logout();
    deleteCookie('securehall-auth-status');
    deleteCookie('securehall-auth-role');
    router.replace('/login');
  };
}
