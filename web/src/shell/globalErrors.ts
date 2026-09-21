/** Errors no React boundary can catch: one thrown in an event handler, in a timer, or a promise nobody
 * handled. They are logged with where they came from and otherwise left alone; a tap that failed must not
 * take the screen with it. The same message is logged only a few times, so a loop of them cannot fill the
 * journal. Returns the way to stop listening. */
const MAX_PER_MESSAGE = 3;

export function installGlobalErrorHandlers(): () => void {
  const seen = new Map<string, number>();
  const worthLogging = (message: string): boolean => {
    const n = (seen.get(message) ?? 0) + 1;
    seen.set(message, n);
    return n <= MAX_PER_MESSAGE;
  };
  const onError = (e: ErrorEvent) => {
    const message = e.error instanceof Error ? e.error.message : e.message;
    if (worthLogging(`error:${message}`)) {
      console.error('[sos] uncaught error', { message, source: e.filename, line: e.lineno, column: e.colno, page: window.location.pathname, stack: e.error instanceof Error ? e.error.stack : undefined });
    }
    e.preventDefault();
  };
  const onRejection = (e: PromiseRejectionEvent) => {
    const reason = e.reason as unknown;
    const message = reason instanceof Error ? reason.message : String(reason);
    if (worthLogging(`rejection:${message}`)) {
      console.error('[sos] unhandled rejection', { message, page: window.location.pathname, stack: reason instanceof Error ? reason.stack : undefined });
    }
    e.preventDefault();
  };
  window.addEventListener('error', onError);
  window.addEventListener('unhandledrejection', onRejection);
  return () => {
    window.removeEventListener('error', onError);
    window.removeEventListener('unhandledrejection', onRejection);
  };
}
