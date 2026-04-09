"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import type { Portfolio } from "@/lib/types";
import { getPortfolios, checkHealth } from "@/lib/api";

interface AppState {
  portfolios: Portfolio[];
  activePortfolioId: string;
  activePortfolio: Portfolio | null;
  userId: string;
  backendOnline: boolean;
  loading: boolean;
  setActivePortfolioId: (id: string) => void;
  refresh: () => Promise<void>;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [userId] = useState("default_user");
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [activePortfolioId, setActivePortfolioId] = useState("");
  const [backendOnline, setBackendOnline] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [online, data] = await Promise.all([
        checkHealth(),
        getPortfolios(userId).catch(() => [] as Portfolio[]),
      ]);
      setBackendOnline(online);
      setPortfolios(data);
      if (data.length > 0 && !data.find((p) => p._id === activePortfolioId)) {
        setActivePortfolioId(data[0]._id);
      }
    } catch {
      setBackendOnline(false);
    } finally {
      setLoading(false);
    }
  }, [userId, activePortfolioId]);

  useEffect(() => {
    refresh();
    const interval = setInterval(async () => {
      const online = await checkHealth();
      setBackendOnline(online);
    }, 30_000);
    return () => clearInterval(interval);
  }, [refresh]);

  const activePortfolio =
    portfolios.find((p) => p._id === activePortfolioId) ?? null;

  return (
    <AppContext.Provider
      value={{
        portfolios,
        activePortfolioId,
        activePortfolio,
        userId,
        backendOnline,
        loading,
        setActivePortfolioId,
        refresh,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
