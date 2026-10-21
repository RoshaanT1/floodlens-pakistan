/** Pakistan outline, traced from the OCHA district boundaries the dashboard uses. */
const OUTLINE = "M2.5 16.9L5.0 17.8L7.6 17.8L11.1 16.9L11.3 14.9L11.8 14.4L13.5 14.2L13.1 13.9L14.1 13.3L15.3 13.7L15.9 13.1L15.8 12.1L16.2 11.1L17.5 10.5L16.9 9.3L18.7 9.2L18.9 8.7L18.6 8.3L19.7 7.1L19.5 6.1L18.9 5.5L20.6 4.2L25.2 3.7L26.5 4.5L26.5 5.5L26.8 6.0L27.5 5.8L27.8 6.3L29.5 6.5L27.7 7.9L26.2 8.4L23.9 7.8L23.3 8.0L23.0 8.5L23.4 8.8L23.2 9.2L23.8 9.4L23.3 9.8L23.7 10.3L23.4 10.8L24.2 11.6L24.5 11.4L24.5 12.1L25.1 12.1L25.6 12.6L24.3 13.3L24.2 14.5L24.5 14.7L23.2 15.9L23.3 16.3L22.4 16.8L21.7 18.4L20.8 18.9L20.0 20.4L18.4 20.9L17.6 20.3L16.4 21.9L16.3 22.7L17.3 23.0L17.3 24.3L18.1 24.6L18.8 26.9L18.3 27.3L18.0 27.2L17.9 26.9L17.0 27.4L15.1 27.1L15.0 27.8L14.4 27.8L14.1 28.3L13.3 28.1L12.9 27.7L12.5 26.4L11.7 26.2L11.8 25.5L11.4 24.8L11.5 25.1L8.7 25.3L8.5 25.6L7.0 25.2L6.7 25.5L5.2 25.4L3.9 25.8L3.7 25.5L4.0 23.6L5.0 23.0L6.1 22.8L6.4 21.9L5.5 21.7L5.5 19.8L4.0 19.2L2.5 16.9Z";

export function PakistanMapIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" className={className} aria-hidden="true">
      <path d={OUTLINE} fill="currentColor" stroke="currentColor" strokeWidth={0.6} strokeLinejoin="round" />
    </svg>
  );
}
