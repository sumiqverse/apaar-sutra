import { createBrowserRouter } from "react-router-dom";
import { Shell } from "@/components/layout/Shell";
import { Dashboard } from "@/pages/Dashboard";
import { Health } from "@/pages/Health";
import { NotFound } from "@/pages/NotFound";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Shell />,
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
