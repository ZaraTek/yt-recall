import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { AUTH_DISABLED, useAuth } from "../auth/AuthContext";

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand">
          <span className="dot" />
          YouTube Recall
        </NavLink>
        <nav>
          <NavLink to="/" end>
            New
          </NavLink>
          <NavLink to="/library">Library</NavLink>
          {user && (
            <div className="user-chip">
              {user.picture && <img src={user.picture} alt={user.name} />}
              {!AUTH_DISABLED && (
                <button className="btn btn-ghost" onClick={logout}>
                  Sign out
                </button>
              )}
            </div>
          )}
        </nav>
      </header>
      <main className="container">{children}</main>
    </div>
  );
}
