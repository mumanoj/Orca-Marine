/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        marine: {
          dark: "#050B14",       // Deep abyss black/blue
          navy: "#0A192F",       // Deep ocean navy
          navyLight: "#172A45",  // Mid-ocean navy
          teal: "#00B4D8",       // Bright water teal
          tealDark: "#0077B6",   // Muted deep teal
          glass: "rgba(10, 25, 47, 0.7)", // Glassmorphic background
        },
        sand: {
          light: "#F4F1DE",      // Sandy cream light
          muted: "#E0A96D",      // Sandy tan
          dark: "#A67B5B",       // Sandy brown
        },
        hazard: {
          amber: "#D97706",      // Warning amber
          red: "#DC2626",        // Critical danger red
        }
      }
    },
  },
  plugins: [],
}
