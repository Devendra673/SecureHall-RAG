/**
 * Layout for auth pages (login, signup)
 * Ensures dark background renders correctly without the main app's ThemeProvider
 * interfering with the standalone auth pages.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="dark">
      {children}
    </div>
  );
}
