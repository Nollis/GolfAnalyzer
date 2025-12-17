import { goto } from '$app/navigation';
import { browser } from '$app/environment';
import { get, writable } from 'svelte/store';

const initialToken = browser ? localStorage.getItem('token') : null;

export const user = writable<any>(null);
export const token = writable<string | null>(initialToken);
export const isAuthenticated = writable<boolean>(!!initialToken);
export const authReady = writable<boolean>(!browser);

let initializing = false;

if (browser) {
    token.subscribe((value) => {
        if (value) {
            localStorage.setItem('token', value);
            isAuthenticated.set(true);
        } else {
            localStorage.removeItem('token');
            isAuthenticated.set(false);
            user.set(null);
        }
    });
}

export async function fetchUser(): Promise<boolean> {
    const currentToken = browser ? get(token) ?? localStorage.getItem('token') : null;
    if (!currentToken) {
        user.set(null);
        isAuthenticated.set(false);
        return false;
    }

    try {
        const res = await fetch('/api/v1/auth/me', {
            headers: { Authorization: `Bearer ${currentToken}` },
        });

        if (res.ok) {
            const data = await res.json();
            user.set(data);
            isAuthenticated.set(true);
            return true;
        }

        if (res.status === 401) {
            const path =
                typeof window !== 'undefined'
                    ? `${window.location.pathname}${window.location.search}`
                    : undefined;
            logout(true, path);
        } else {
            logout(false);
        }
        return false;
    } catch (e) {
        console.error('[auth.ts] fetchUser failed:', e);
        return false;
    }
}

export async function initializeAuth(): Promise<void> {
    if (!browser) {
        authReady.set(true);
        return;
    }

    if (get(authReady)) return;
    if (initializing) {
        return waitForAuthReady();
    }

    initializing = true;

    const hasToken = !!(get(token) || localStorage.getItem('token'));
    if (!hasToken) {
        isAuthenticated.set(false);
        user.set(null);
        authReady.set(true);
        initializing = false;
        return;
    }

    // If token is expired, clear it immediately to avoid false auth state
    const storedToken = get(token) ?? localStorage.getItem('token');
    if (storedToken && isTokenExpired(storedToken)) {
        logout(true);
        authReady.set(true);
        initializing = false;
        return;
    }

    await fetchUser();
    authReady.set(true);
    initializing = false;
}

export function waitForAuthReady(): Promise<void> {
    if (!browser || get(authReady)) return Promise.resolve();

    return new Promise((resolve) => {
        const unsubscribe = authReady.subscribe((ready) => {
            if (ready) {
                unsubscribe();
                resolve();
            }
        });
    });
}

export async function login(
    email: string,
    password: string,
): Promise<{ success: boolean; message?: string }> {
    try {
        const res = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ username: email, password }),
        });

        if (!res.ok) {
            let detail = 'Invalid email or password';
            try {
                const data = await res.json();
                detail = data?.detail || detail;
            } catch {
                // Ignore JSON parsing errors and fall back to the default message
            }
            return { success: false, message: detail };
        }

        const data = await res.json();
        token.set(data.access_token);

        const userLoaded = await fetchUser();
        authReady.set(true);

        if (!userLoaded) {
            token.set(null);
            return {
                success: false,
                message: 'Login succeeded, but loading your profile failed. Please try again.',
            };
        }

        return { success: true };
    } catch (e) {
        console.error('[auth.ts] login error:', e);
        return { success: false, message: 'Unable to reach the server. Please try again.' };
    }
}

export async function register(
    email: string,
    password: string,
    fullName: string,
    heightCm: number | null = null,
    age: number | null = null,
) {
    const res = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email,
            password,
            full_name: fullName,
            height_cm: heightCm ?? undefined,
            age: age ?? undefined,
        }),
    });

    return res.ok;
}

export function logout(redirectToLogin = true, redirectTo?: string) {
    token.set(null);
    user.set(null);
    isAuthenticated.set(false);
    authReady.set(true);

    if (browser) {
        localStorage.removeItem('token');
        if (redirectToLogin) {
            const target =
                redirectTo && redirectTo.trim().length > 0
                    ? `/login?redirectTo=${encodeURIComponent(redirectTo)}`
                    : '/login';
            goto(target);
        }
    }
}

function isTokenExpired(jwt: string): boolean {
    try {
        const parts = jwt.split('.');
        if (parts.length !== 3) return true;
        const payload = JSON.parse(atob(parts[1]));
        if (!payload?.exp) return true;
        const now = Math.floor(Date.now() / 1000);
        return payload.exp <= now;
    } catch {
        return true;
    }
}
