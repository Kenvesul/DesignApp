/**
 * components/LoadingSpinner.jsx
 *
 * Props:
 *   message — string (default "Calculating…")
 *   size    — "sm" | "md" | "lg" (default "md")
 */

export default function LoadingSpinner({ message = "Calculating…", size = "md" }) {
  const dims = { sm: "h-4 w-4", md: "h-8 w-8", lg: "h-12 w-12" };
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-4">
      <svg
        className={`animate-spin text-brand-600 ${dims[size] || dims.md}`}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-label="Loading"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10"
                stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
      </svg>
      <p className="text-sm text-gray-500 dark:text-gray-400">{message}</p>
    </div>
  );
}
