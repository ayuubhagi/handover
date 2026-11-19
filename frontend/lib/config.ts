export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";
// Public demo backend (DEMO_MODE=true): roles log in through POST /demo/login, no passcodes in the bundle.
export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
