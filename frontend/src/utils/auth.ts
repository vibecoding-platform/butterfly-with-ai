/**
 * JWT authentication utilities for Supervisor access control
 */

export interface JWTPayload {
  sub?: string;
  email?: string;
  roles?: string[];
  permissions?: string[];
  isSupervisor?: boolean;
  exp?: number;
  iat?: number;
}

/**
 * Decode JWT token without verification (client-side only)
 */
export function decodeJWT(token: string): JWTPayload | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) {
      return null;
    }

    const payload = parts[1];
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decoded) as JWTPayload;
  } catch (error) {
    console.error('Failed to decode JWT:', error);
    return null;
  }
}

/**
 * Check if JWT token is expired
 */
export function isTokenExpired(payload: JWTPayload): boolean {
  if (!payload.exp) return true;
  return Date.now() >= payload.exp * 1000;
}

/**
 * Get JWT token from various sources
 */
export function getJWTToken(): string | null {
  // Try localStorage first
  const stored = localStorage.getItem('jwt_token') || localStorage.getItem('auth_token');
  if (stored) return stored;

  // Try sessionStorage
  const session = sessionStorage.getItem('jwt_token') || sessionStorage.getItem('auth_token');
  if (session) return session;

  // Try URL parameters (for direct links)
  const urlParams = new URLSearchParams(window.location.search);
  const urlToken = urlParams.get('token');
  if (urlToken) return urlToken;

  // Try cookies
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'jwt_token' || name === 'auth_token') {
      return decodeURIComponent(value);
    }
  }

  return null;
}

/**
 * Check if current user has supervisor privileges
 */
export function isSupervisor(): boolean {
  const token = getJWTToken();
  if (!token) return false;

  const payload = decodeJWT(token);
  if (!payload || isTokenExpired(payload)) return false;

  // Check multiple possible supervisor indicators
  if (payload.isSupervisor === true) return true;
  if (payload.roles?.includes('supervisor') || payload.roles?.includes('admin')) return true;
  if (payload.permissions?.includes('terminal:supervise') || payload.permissions?.includes('admin:all')) return true;

  return false;
}

/**
 * Get user information from JWT
 */
export function getCurrentUser(): { email?: string; roles?: string[]; isSupervisor: boolean } | null {
  const token = getJWTToken();
  if (!token) return null;

  const payload = decodeJWT(token);
  if (!payload || isTokenExpired(payload)) return null;

  return {
    email: payload.email,
    roles: payload.roles,
    isSupervisor: isSupervisor()
  };
}