import { createBrowserRouter } from "react-router-dom";
import { Shell } from "@/components/layout/Shell";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Dashboard } from "@/pages/Dashboard";
import { InstitutionDashboard } from "@/pages/InstitutionDashboard";
import { Health } from "@/pages/Health";
import { Login } from "@/pages/Login";
import { MfaEnroll } from "@/pages/MfaEnroll";
import { Ingestion } from "@/pages/Ingestion";
import { VerifierPortal } from "@/pages/VerifierPortal";
import { StudentConsentPortal } from "@/pages/StudentConsentPortal";
import { TamperDemo } from "@/pages/TamperDemo";
import { PublicVerification } from "@/pages/PublicVerification";
import { NotFound } from "@/pages/NotFound";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <Login />,
  },
  {
    path: "/verify/:token",
    element: <PublicVerification />,
  },
  {
    path: "/demo/tamper",
    element: <TamperDemo />,
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
        path: "institution-dashboard",
        element: <InstitutionDashboard />,
      },
      {
        path: "verifier",
        element: <VerifierPortal />,
      },
      {
        path: "student/consent",
        element: <StudentConsentPortal />,
      },
      {
        path: "tamper-demo",
        element: <TamperDemo />,
      },
      {
        path: "ingestion",
        element: <Ingestion />,
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
