/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        pipeline: {
          queued: "#6B7280",
          coding: "#3B82F6",
          testing: "#F59E0B",
          review: "#8B5CF6",
          merged: "#10B981",
          failed: "#EF4444",
        },
      },
    },
  },
  plugins: [],
};
