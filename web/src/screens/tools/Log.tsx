import { Navigate } from 'react-router';

/** The log lives under the situation sheet now: what happened belongs beside what is working, not
 * on a tool screen of its own. Old links, bookmarks and the kiosk's tile all land there. */
export function Log() {
  return <Navigate to="/situation#log" replace />;
}
