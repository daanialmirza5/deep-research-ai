"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useProjects } from "@/hooks/use-projects";
import { useSessionReport, useSessions } from "@/hooks/use-sessions";
import type { SessionRead, SessionStatus } from "@/lib/types";

const STATUS_LABEL: Record<SessionStatus, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};

function SessionListItem({
  session,
  selected,
  onSelect,
}: {
  session: SessionRead;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      className={`flex w-full items-center justify-between gap-3 rounded-lg border p-3 text-left text-sm transition-colors ${
        selected ? "border-primary bg-primary/5" : "border-border hover:bg-accent"
      }`}
    >
      <span className="truncate">{session.query}</span>
      <span className="shrink-0 text-xs text-muted-foreground">
        {STATUS_LABEL[session.status]}
      </span>
    </button>
  );
}

function ReportView({ sessionId }: { sessionId: string }) {
  const { data: report, isLoading, isError } = useSessionReport(sessionId, true);

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading report…</p>;
  if (isError || !report) {
    return (
      <p className="text-sm text-muted-foreground">
        No report available for this session yet.
      </p>
    );
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{report.title}</h2>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>v{report.version}</span>
          <span className="capitalize">{report.status}</span>
          {report.quality_score !== null && (
            <span>quality {(report.quality_score * 100).toFixed(0)}%</span>
          )}
        </div>
      </div>
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown>{report.content_markdown}</ReactMarkdown>
      </div>
    </div>
  );
}

export default function ReportsPage() {
  const { data: projects } = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  const projectId = selectedProjectId ?? projects?.[0]?.id ?? null;
  const { data: sessions, isLoading: sessionsLoading } = useSessions(projectId);
  const sessionId = selectedSessionId ?? sessions?.[0]?.id ?? null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Reports</h1>
          <p className="text-sm text-muted-foreground">
            Every research session&apos;s final report, rendered from real pipeline output.
          </p>
        </div>
        <select
          className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-xs"
          value={projectId ?? ""}
          onChange={(event) => {
            setSelectedProjectId(event.target.value);
            setSelectedSessionId(null);
          }}
          aria-label="Select project"
        >
          {!projects?.length && <option value="">No projects yet</option>}
          {projects?.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
      </div>

      {!projectId ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center text-sm text-muted-foreground">
            <p>Create a project on the Workspace page to see its reports here.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle>Sessions</CardTitle>
              <CardDescription>
                {sessions?.length ?? 0} in this project
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {sessionsLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
              ) : sessions?.length ? (
                sessions.map((session) => (
                  <SessionListItem
                    key={session.id}
                    session={session}
                    selected={session.id === sessionId}
                    onSelect={() => setSelectedSessionId(session.id)}
                  />
                ))
              ) : (
                <p className="text-sm text-muted-foreground">
                  No sessions yet — start one from the Workspace page.
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Report</CardTitle>
            </CardHeader>
            <CardContent>
              {sessionId ? (
                <ReportView sessionId={sessionId} />
              ) : (
                <p className="text-sm text-muted-foreground">
                  Select a session to view its report.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
