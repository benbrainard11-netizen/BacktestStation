import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Single font family across the app. `font-mono` resolves to the
        // same Work Sans family but turns on tabular numerals via globals.
        sans: ["var(--font-work-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-work-sans)", "system-ui", "sans-serif"],
      },
      colors: {
        // Direction A — warm-leaning stone, dark only.
        bg: "#0c0a09",
        surface: "#16140f",
        "surface-alt": "#1c1a17",
        border: {
          DEFAULT: "#2a2724",
          strong: "#3a3633",
        },
        text: {
          DEFAULT: "#f5f4f2",
          dim: "#a8a29e",
          mute: "#6b6661",
        },
        // Single accent (slightly desaturated indigo).
        accent: "#8b95ff",
        // Semantic — used for P&L sign, win/loss, drift severity.
        pos: "#4ade80",
        neg: "#f87171",
        warn: "#fbbf24",
      },
      boxShadow: {
        // Legacy depth tokens kept for pre-rework pages. New Direction A
        // surfaces use border + surface elevation only — no shadows.
        dim: "inset 0 1px 0 0 rgba(255,255,255,0.04), 0 1px 2px 0 rgba(0,0,0,0.45), 0 6px 14px -6px rgba(0,0,0,0.55)",
        "dim-hover":
          "inset 0 1px 0 0 rgba(255,255,255,0.07), 0 2px 4px 0 rgba(0,0,0,0.5), 0 12px 22px -8px rgba(0,0,0,0.6)",
        "edge-top": "inset 0 1px 0 0 rgba(255,255,255,0.05)",
        hero: "inset 0 1px 0 0 rgba(255,255,255,0.06), 0 2px 4px 0 rgba(0,0,0,0.5), 0 18px 36px -10px rgba(0,0,0,0.65)",
      },
      keyframes: {
        "heartbeat-pulse": {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        "heartbeat-pulse": "heartbeat-pulse 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
