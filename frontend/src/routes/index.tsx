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
import { ReportsConsole } from "@/pages/ReportsConsole";
import { AdminConsole } from "@/pages/AdminConsole";
import { DeveloperDocs } from "@/pages/DeveloperDocs";
import { DemoGuide } from "@/pages/DemoGuide";
import { NotFound } from "@/pages/NotFound";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <Login />,
  },
  {
    path: "/demo-guide",
    element: <DemoGuide />,
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
        path: "reports",
        element: <ReportsConsole />,
      },
      {
        path: "admin",
        element: <AdminConsole />,
      },
      {
        path: "developers",
        element: <DeveloperDocs />,
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
        path: "demo-guide",
        element: <DemoGuide />,
      },
      {
        path: "*",
        element: <NotFound />,
      },
    ],
  },
]);
