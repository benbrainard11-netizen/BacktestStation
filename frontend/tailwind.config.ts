import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Single font family across the app. `font-mono` still works for
        // existing usages, it just resolves to Work Sans with tabular
        // numerals applied via the .font-mono rule in globals.css.
        sans: ["var(--font-work-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-work-sans)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
