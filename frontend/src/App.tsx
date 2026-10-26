import React, { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { router } from "@/routes";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

import { ThemeProvider } from "@/lib/themeContext";

export const App: React.FC = () => {
  useEffect(() => {
    const handleExpired = () => {
      window.location.href = "/login";
    };
    window.addEventListener("apaar:session_expired", handleExpired);
    return () => window.removeEventListener("apaar:session_expired", handleExpired);
  }, []);

  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ThemeProvider>
  );
};

export default App;
