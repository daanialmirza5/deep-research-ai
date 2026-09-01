"use client";

import { FolderPlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useCurrentUser } from "@/hooks/use-auth";

export default function DashboardHomePage() {
  const { data: user } = useCurrentUser();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">
          Welcome back{user ? `, ${user.full_name.split(" ")[0]}` : ""}
        </h1>
        <p className="text-sm text-muted-foreground">{user?.email}</p>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Projects</CardTitle>
            <CardDescription>
              Organize research sessions by project.
            </CardDescription>
          </div>
          <Button
            disabled
            title="Project creation lands with the Research Pipeline phase"
          >
            <FolderPlus /> New Project
          </Button>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-12 text-center text-sm text-muted-foreground">
            <p>No projects yet.</p>
            <p>
              Project and research-session APIs land alongside the agent
              pipeline (Phase 8).
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
