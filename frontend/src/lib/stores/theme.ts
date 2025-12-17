import { writable } from 'svelte/store';
import { browser } from '$app/environment';

// Default to light if no preference is found
const defaultValue = 'light';

// Get initial value from local storage or system preference
const initialValue = browser
    ? window.localStorage.getItem('theme') ??
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : defaultValue;

export const theme = writable<string>(initialValue);

theme.subscribe((value) => {
    if (browser) {
        try {
            window.localStorage.setItem('theme', value);
        } catch (e) {
            console.warn('Unable to save theme preference:', e);
        }

        try {
            const html = document.documentElement;
            if (value === 'dark') {
                html.classList.add('dark');
            } else {
                html.classList.remove('dark');
            }
        } catch (e) {
            console.error('Unable to update theme classes:', e);
        }
    }
});
