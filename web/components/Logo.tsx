import { APP_NAME } from "@/lib/config";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-extrabold tracking-tight ${className}`}>
      <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
        <circle cx="16" cy="16" r="14" fill="#c8f135" />
        <path d="M5 11c6 2 10 7 11 19M27 21c-6-2-10-7-11-19" stroke="#0b1220" strokeWidth="2" fill="none" strokeLinecap="round" />
      </svg>
      {APP_NAME}
    </span>
  );
}
