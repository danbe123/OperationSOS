import { Component, type ErrorInfo, type ReactNode } from 'react';
import { EmergencyNumbers } from '../components/EmergencyNumbers';
import { reloadOnce } from './reload';

/** A chunk that no longer exists: a tab left open across an update. */
export const STALE_CHUNK = /dynamically imported module|Importing a module script failed|ChunkLoadError|Loading chunk/i;

type State = { error: Error | null; attempt: number };

/** The last line: whatever throws above or beside the router (the providers, the theme, the kiosk
 * layer) ends up here, on a page that assumes nothing else works. It says what happened in one line,
 * offers Try again (which remounts the whole app) and Go to Now, and shows the emergency numbers as plain
 * text. It reloads the page once for the person, at most once a minute, because a fresh page clears most
 * faults; a fault a reload does not clear stays on this page instead of looping. */
export class AppErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null, attempt: 0 };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[sos] the app crashed above the router', { message: error.message, stack: error.stack, componentStack: info.componentStack });
    reloadOnce();
  }

  render() {
    if (!this.state.error) return <div key={this.state.attempt} className="app-root">{this.props.children}</div>;
    return (
      <main className="crash" role="alert">
        <h1>Something went wrong with the screen</h1>
        <p>The box itself is still running. Try again, or go back to the front door.</p>
        <div className="row">
          <button type="button" className="btn btn-primary" onClick={() => this.setState((s) => ({ error: null, attempt: s.attempt + 1 }))}>Try again</button>
          <a className="btn" href="/">Go to Now</a>
        </div>
        <EmergencyNumbers />
      </main>
    );
  }
}
