import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export const user = writable(null);
export const token = writable(browser ? localStorage.getItem('token') : null);
export const isAuthenticated = writable(false);

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

export async function login(email, password) {
    console.log("[auth.ts] login called with", email);
    try {
        console.log("[auth.ts] executing fetch...");
        const res = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ username: email, password }),
        });
        console.log("[auth.ts] fetch returned, status:", res.status, res.statusText);

        if (res.ok) {
            const data = await res.json();
            console.log("[auth.ts] login successful, setting token");
            token.set(data.access_token);
            await fetchUser();
            return true;
        }
        console.log("[auth.ts] login failed, res.ok is false");
        return false;
    } catch (e) {
        console.error("[auth.ts] fetch threw error:", e);
        throw e;
    }
}

export async function register(email, password, fullName) {
    const res = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: fullName }),
    });

    return res.ok;
}

import { goto } from '$app/navigation';

export function logout() {
    token.set(null);
    if (browser) {
        goto('/login');
    }
}

export async function fetchUser() {
    const t = browser ? localStorage.getItem('token') : null;
    if (!t) return;

    const res = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${t}` },
    });

    if (res.ok) {
        const data = await res.json();
        user.set(data);
    } else {
        logout();
    }
}
