import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Health } from "@/pages/Health";

describe("Health Page Component", () => {
  it("renders system health diagnostics layout", () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <Health />
      </QueryClientProvider>
    );

    // Verify key headings and cards render
    expect(screen.getByText(/System Operational Status|सिस्टम परिचालन स्थिति/i)).toBeInTheDocument();
    expect(screen.getByText(/Backend API Liveness|बैकएंड एपीआई जीवंतता/i)).toBeInTheDocument();
    expect(screen.getByText(/PostgreSQL 16 Engine|पोस्टग्रेएसक्यूएल 16 डेटाबेस/i)).toBeInTheDocument();
    expect(screen.getByText(/Redis 7 Broker & Cache|रेडिस 7 ब्रोकर एवं कैश/i)).toBeInTheDocument();
  });
});
