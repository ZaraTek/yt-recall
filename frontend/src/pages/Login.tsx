import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "../auth/AuthContext";

export default function Login() {
  const { login } = useAuth();

  return (
    <div className="center-screen">
      <div className="card" style={{ maxWidth: 420, textAlign: "center" }}>
        <div
          className="brand"
          style={{
            justifyContent: "center",
            fontSize: 26,
            fontWeight: 800,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <span className="dot" style={{ width: 16, height: 16 }} />
          YouTube Recall
        </div>
        <p className="muted" style={{ marginTop: 12 }}>
          Turn any YouTube video into summaries and active-recall practice.
          Sign in to build your learning library.
        </p>
        <div
          style={{ display: "flex", justifyContent: "center", marginTop: 24 }}
        >
          <GoogleLogin
            onSuccess={(cred) => {
              if (cred.credential) login(cred.credential);
            }}
            onError={() => alert("Google sign-in failed. Please try again.")}
          />
        </div>
      </div>
    </div>
  );
}
