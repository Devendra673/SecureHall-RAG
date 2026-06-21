"use client";

import React from "react";
import { useAuthStore } from "@/store/authStore";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { User, Mail, Shield, Calendar, CheckCircle2 } from "lucide-react";

export function UserProfile() {
  const { user, isProfileOpen, setProfileOpen } = useAuthStore();

  if (!user) return null;

  return (
    <Dialog open={isProfileOpen} onOpenChange={setProfileOpen}>
      <DialogContent className="sm:max-w-[440px]">
        <DialogHeader>
          <DialogTitle className="text-xl">User Profile</DialogTitle>
          <DialogDescription className="text-sm">
            Your account details and current role.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-5 py-4">
          {/* Avatar card */}
          <div className="flex items-center gap-4 border border-border/50 p-5 rounded-2xl bg-gradient-to-br from-muted/20 to-muted/5">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/15 to-primary/5 text-primary shrink-0 shadow-sm">
              <User className="h-7 w-7" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-lg font-bold leading-tight text-foreground">
                {user.full_name || user.username}
              </h3>
              <p className="truncate text-sm text-muted-foreground mt-0.5">
                @{user.username}
              </p>
            </div>
            <div className="shrink-0 text-xs font-semibold px-3 py-1 rounded-full bg-primary/15 text-primary border border-primary/20 capitalize">
              {user.role}
            </div>
          </div>

          {/* Detail rows */}
          <div className="space-y-3.5 px-1 text-[15px]">
            <div className="flex items-center gap-3.5 text-muted-foreground">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted/30">
                <Mail className="h-4 w-4" />
              </div>
              <span className="truncate">{user.email}</span>
            </div>
            <div className="flex items-center gap-3.5 text-muted-foreground">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted/30">
                <Shield className="h-4 w-4" />
              </div>
              <span className="capitalize">{user.role} Access Level</span>
            </div>
            <div className="flex items-center gap-3.5 text-muted-foreground">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted/30">
                <Calendar className="h-4 w-4" />
              </div>
              <span>Joined {new Date(user.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}</span>
            </div>
            <div className="flex items-center gap-3.5 text-muted-foreground">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              </div>
              <span className="text-emerald-600 dark:text-emerald-400 font-medium">Account verified</span>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
