/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Fixes the Firebase "Continue with Google" popup flow. Without this,
  // the browser's default strict Cross-Origin-Opener-Policy blocks
  // Firebase's internal window.closed check (used to detect when the
  // Google sign-in popup closes), which breaks/hangs the popup flow and
  // logs "Cross-Origin-Opener-Policy policy would block the
  // window.closed call" in the console. "same-origin-allow-popups"
  // keeps normal cross-origin isolation while explicitly allowing this
  // one specific check Firebase needs.
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Cross-Origin-Opener-Policy",
            value: "same-origin-allow-popups",
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
