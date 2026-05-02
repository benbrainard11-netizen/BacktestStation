import type { Config } from "tailwindcss";

/**
 * Tailwind reads from the CSS custom properties defined in app/globals.css so
 * the Tailwind utilities and the hand-rolled CSS classes share one source of
 * truth. Changing a hex value in globals.css updates both. The accent hue is
 * runtime-tunable via `--accent-h` on `<html>` (Settings → Appearance).
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Geist", "system-ui", "sans-serif"],
        mono: ["Geist Mono", "ui-monospace", "monospace"],
      },
      colors: {
        bg: {
          0: "var(--bg-0)",
          1: "var(--bg-1)",
          2: "var(--bg-2)",
          3: "var(--bg-3)",
          4: "var(--bg-4)",
        },
        ink: {
          0: "var(--ink-0)",
          1: "var(--ink-1)",
          2: "var(--ink-2)",
          3: "var(--ink-3)",
          4: "var(--ink-4)",
        },
        line: {
          DEFAULT: "var(--line)",
          2: "var(--line-2)",
          3: "var(--line-3)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          2: "var(--accent-2)",
          soft: "var(--accent-soft)",
          line: "var(--accent-line)",
          glow: "var(--accent-glow)",
        },
        pos: { DEFAULT: "var(--pos)", soft: "var(--pos-soft)" },
        neg: { DEFAULT: "var(--neg)", soft: "var(--neg-soft)" },
        warn: "var(--warn)",
        info: "var(--info)",
      },
      borderRadius: {
        DEFAULT: "var(--r)",
        lg: "var(--r-lg)",
      },
      keyframes: {
        "live-pulse": {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.55", transform: "scale(1.18)" },
        },
        blink: {
          "0%, 49%": { opacity: "1" },
          "50%, 100%": { opacity: "0.4" },
        },
      },
      animation: {
        "live-pulse": "live-pulse 1.6s ease-in-out infinite",
        blink: "blink 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
