import { redirect } from '@sveltejs/kit';

export const load = () => {
    // History is consolidated into the dashboard; keep the route for backward compatibility.
    throw redirect(307, '/dashboard');
};
