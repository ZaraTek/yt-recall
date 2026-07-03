import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import NewVideo from "./pages/NewVideo";
import Library from "./pages/Library";
import VideoDetail from "./pages/VideoDetail";

export default function App() {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div className="center-screen">
        <div className="spinner" />
      </div>
    );
  }

  if (!token) {
    return <Login />;
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<NewVideo />} />
        <Route path="/library" element={<Library />} />
        <Route path="/videos/:id" element={<VideoDetail />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
