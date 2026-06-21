import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PROTECTED_ROUTES = ['/chat', '/documents', '/history', '/settings'];
const ADMIN_ROUTES = ['/admin'];
const AUTH_ROUTES = ['/login', '/signup'];

function getAuthFromRequest(request: NextRequest) {
  const authCookie = request.cookies.get('securehall-auth-role');
  const isAuth = request.cookies.get('securehall-auth-status')?.value === 'true';
  return {
    isAuthenticated: isAuth,
    role: authCookie?.value ?? null,
  };
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const { isAuthenticated, role } = getAuthFromRequest(request);

  if (AUTH_ROUTES.some(r => pathname.startsWith(r))) {
    if (isAuthenticated) {
      return NextResponse.redirect(new URL('/', request.url));
    }
    return NextResponse.next();
  }

  // The root path '/' is our main app which requires auth
  if (pathname === '/' || PROTECTED_ROUTES.some(r => pathname.startsWith(r))) {
    if (!isAuthenticated) {
      const url = new URL('/login', request.url);
      url.searchParams.set('from', pathname);
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  if (ADMIN_ROUTES.some(r => pathname.startsWith(r))) {
    if (!isAuthenticated) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
    if (role !== 'admin' && role !== 'hr') {
      return NextResponse.redirect(new URL('/', request.url));
    }
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/',
    '/chat/:path*',
    '/documents/:path*',
    '/history/:path*',
    '/settings/:path*',
    '/admin/:path*',
    '/login',
    '/signup',
  ],
};
