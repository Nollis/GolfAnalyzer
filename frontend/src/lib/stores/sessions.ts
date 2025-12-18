import { writable } from 'svelte/store';

interface DashboardStats {
    total_sessions: number;
    average_score: number;
    last_session_date: string | null;
    personal_bests: {
        driver: number | null;
        iron: number | null;
        wedge: number | null;
    };
}

interface Session {
    session_id: string;
    scores: {
        overall_score: number;
    };
    metadata: {
        club_type: string;
        view: string;
    };
    is_personal_best: boolean;
    created_at?: string;
}

interface Drill {
    id: string;
    title: string;
    description: string;
    category: string;
    difficulty: string;
    video_url?: string;
    target_metric?: string;
}

// Stores
export const dashboardStats = writable<DashboardStats | null>(null);
export const recentSessions = writable<Session[]>([]);
export const sessionsLoaded = writable<boolean>(false);
export const drills = writable<Drill[]>([]);
export const drillsLoaded = writable<boolean>(false);
export const lastFetchTime = writable<number>(0); // To support stale-while-revalidate logic if needed
