import React from "react";
import { Outlet } from "react-router-dom";
import { Navbar } from "@/components/layout/Navbar";
import { Sidebar } from "@/components/layout/Sidebar";

export const Shell: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-6 md:p-10 max-w-7xl mx-auto w-full overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
