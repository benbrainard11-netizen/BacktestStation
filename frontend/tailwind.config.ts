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
      boxShadow: {
        // Layered terminal depth: subtle inset top highlight + low outer
        // shadow. Use on panels and bordered cards.
        dim: "inset 0 1px 0 0 rgba(255,255,255,0.04), 0 1px 2px 0 rgba(0,0,0,0.45), 0 6px 14px -6px rgba(0,0,0,0.55)",
        "dim-hover":
          "inset 0 1px 0 0 rgba(255,255,255,0.07), 0 2px 4px 0 rgba(0,0,0,0.5), 0 12px 22px -8px rgba(0,0,0,0.6)",
        "edge-top": "inset 0 1px 0 0 rgba(255,255,255,0.05)",
        // Hero panel depth — slightly stronger ambient cast for the top
        // surface on /prop-simulator.
        hero: "inset 0 1px 0 0 rgba(255,255,255,0.06), 0 2px 4px 0 rgba(0,0,0,0.5), 0 18px 36px -10px rgba(0,0,0,0.65)",
      },
    },
  },
  plugins: [],
};

export default config;
