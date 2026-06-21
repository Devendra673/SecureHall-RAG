"use client";

/**
 * Header — Premium Interactive Light Theme
 *
 * Features:
 *  • SecureHall-RAG logo with subtle pulse on hover
 *  • Backend status indicator (online / no documents / offline)
 *  • Dark / Light / System theme toggle
 *  • User menu dropdown
 *  • Responsive: hamburger on mobile, full bar on md+
 *  • Smooth Framer Motion interactions
 */

import React, { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun, Monitor, Menu, User, Shield, WifiOff, Database } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/authStore";
import { useSettingsStore } from "@/store/store";
import { useLogout } from "@/components/AuthProvider";
import { useRouter } from "next/navigation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useHealthCheck, BackendStatus } from "@/hooks/useHealthCheck";
import { motion } from "framer-motion";

interface HeaderProps {
  onMenuClick?: () => void;
}

// ── Status indicator pill ─────────────────────────────────────────────────────

function StatusPill({ status }: { status: BackendStatus }) {
  if (status === "checking") {
    return (
      <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground px-2 py-0.5 rounded-full border">
        <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-pulse" />
        Connecting…
      </span>
    );
  }
  if (status === "offline") {
    return (
      <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-semibold text-destructive px-2 py-0.5 rounded-full border border-destructive/30 bg-destructive/5">
        <WifiOff className="h-3 w-3" />
        Backend offline
      </span>
    );
  }
  if (status === "no_documents") {
    return (
      <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-medium text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-full border border-amber-400/30 bg-amber-50 dark:bg-amber-900/20">
        <Database className="h-3 w-3" />
        No documents indexed
      </span>
    );
  }
  // online
  return (
    <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-700 dark:text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-400/30 bg-emerald-50 dark:bg-emerald-900/20">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
      Online
    </span>
  );
}

// ── Theme icon ────────────────────────────────────────────────────────────────
function ThemeIcon({ theme, mounted }: { theme: string | undefined; mounted: boolean }) {
  if (!mounted) return <Monitor className="h-4 w-4" />;
  if (theme === "dark") return <Moon className="h-4 w-4" />;
  if (theme === "light") return <Sun className="h-4 w-4" />;
  return <Monitor className="h-4 w-4" />;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function Header({ onMenuClick }: HeaderProps) {
  const { theme, setTheme } = useTheme();
  const { status } = useHealthCheck();
  const [mounted, setMounted] = useState(false);
  const { user, isAuthenticated, setProfileOpen } = useAuthStore();
  const { setSettingsOpen } = useSettingsStore();
  const logout = useLogout();
  const router = useRouter();

  useEffect(() => {
    setMounted(true);
  }, []);

  const cycleTheme = () => {
    const next = theme === "dark" ? "light" : theme === "light" ? "system" : "dark";
    setTheme(next);
  };

  return (
    <header
      className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b px-5 md:px-8 transition-all shadow-sm"
      role="banner"
    >
      {/* Left: hamburger + logo */}
      <div className="flex items-center gap-3">
        {onMenuClick && (
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden h-9 w-9 hover:bg-primary/10 hover:text-primary transition-colors"
              onClick={onMenuClick}
              aria-label="Open navigation menu"
              id="mobile-menu-btn"
            >
              <Menu className="h-5 w-5" />
            </Button>
          </motion.div>
        )}

        {/* Logo */}
        <motion.div
          className="flex items-center gap-2.5 cursor-default select-none"
          whileHover={{ scale: 1.03 }}
          transition={{ type: "spring", stiffness: 400, damping: 20 }}
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-md shadow-primary/20">
            <Shield className="h-[18px] w-[18px]" />
          </div>
          <span className="text-[17px] font-bold tracking-tight hidden sm:inline-block">
            SecureHall
            <span className="text-primary/70 font-normal">-RAG</span>
          </span>
        </motion.div>

        {/* Backend status indicator */}
        <StatusPill status={status} />
      </div>

      {/* Right: user menu */}
      <div className="flex items-center gap-2">
        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger
            className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-primary/10 hover:text-primary text-muted-foreground transition-all hover:scale-105 active:scale-95 outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Open user menu"
            id="user-menu-btn"
          >
            <User className="h-4 w-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-44 glass-panel border shadow-lg">
            <div className="px-2 py-1.5 text-sm font-semibold text-muted-foreground">
              {mounted && isAuthenticated && user ? user.full_name || user.username : "SecureHall-RAG v1.1"}
            </div>
            <DropdownMenuSeparator />
            {mounted && isAuthenticated ? (
              <>
                <DropdownMenuItem id="menu-profile" className="cursor-pointer hover:bg-primary/5 focus:bg-primary/5" onClick={() => setProfileOpen(true)}>Profile</DropdownMenuItem>
                <DropdownMenuItem id="menu-preferences" className="cursor-pointer hover:bg-primary/5 focus:bg-primary/5" onClick={() => setSettingsOpen(true)}>Preferences</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  id="menu-logout"
                  className="text-destructive focus:text-destructive cursor-pointer hover:bg-destructive/5 focus:bg-destructive/5"
                  onClick={() => logout()}
                >
                  Log out
                </DropdownMenuItem>
              </>
            ) : (
              <>
                <DropdownMenuItem
                  id="menu-login"
                  className="cursor-pointer hover:bg-primary/5 focus:bg-primary/5"
                  onClick={() => router.push("/login")}
                >
                  Log in
                </DropdownMenuItem>
                <DropdownMenuItem
                  id="menu-signup"
                  className="cursor-pointer hover:bg-primary/5 focus:bg-primary/5"
                  onClick={() => router.push("/signup")}
                >
                  Sign up
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}

