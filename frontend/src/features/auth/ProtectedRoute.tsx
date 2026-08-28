import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./AuthContext";
import { FullPageLoader } from "../../components/FullPageLoader";

export function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <FullPageLoader />;
  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}
