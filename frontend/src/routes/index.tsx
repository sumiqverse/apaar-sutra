import { createBrowserRouter } from "react-router-dom";
import { Shell } from "@/components/layout/Shell";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Dashboard } from "@/pages/Dashboard";
import { Health } from "@/pages/Health";
import { Login } from "@/pages/Login";
import { MfaEnroll } from "@/pages/MfaEnroll";
import { NotFound } from "@/pages/NotFound";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <Login />,
  },
  {
    path: "/mfa-enroll",
    element: (
      <ProtectedRoute>
        <MfaEnroll />
      </ProtectedRoute>
    ),
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <Shell />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
      {
        path: "health",
        element: <Health />,
      },
      {
        path: "*",
        element: <NotFound />,
      },
    ],
  },
]);
