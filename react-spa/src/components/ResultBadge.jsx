/**
 * components/ResultBadge.jsx
 *
 * EC7 check indicator badge.
 *
 * Props:
 *   passes — bool | null  (null → pending/unknown)
 *   size   — "sm" | "md" | "lg" (default "md")
 */

export default function ResultBadge({ passes, size = "md" }) {
  const sizes = { sm: "text-xs px-2 py-0.5", md: "text-sm px-3 py-1", lg: "text-base px-4 py-1.5" };
  const cls = sizes[size] || sizes.md;

  if (passes === null || passes === undefined) {
    return (
      <span className={`badge-warn ${cls} rounded-full font-semibold`}>
        — Pending
      </span>
    );
  }
  return passes ? (
    <span className={`badge-pass ${cls} rounded-full font-semibold`}>
      ✓ PASS
    </span>
  ) : (
    <span className={`badge-fail ${cls} rounded-full font-semibold`}>
      ✗ FAIL
    </span>
  );
}
