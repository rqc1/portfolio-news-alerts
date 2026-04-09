"use client";

import type { ReactNode } from "react";
import { AppProvider } from "@/hooks/use-app";
import { Sidebar } from "./sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <AppProvider>
      <div className="flex h-full">
        <Sidebar />
        <main className="ml-[260px] flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1280px] px-8 py-8">
            {children}
          </div>
        </main>
      </div>
    </AppProvider>
  );
}
