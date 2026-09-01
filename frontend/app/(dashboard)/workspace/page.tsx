"use client";

import { CheckCircle2, Circle, Sparkles, XCircle } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useSessionEvents } from "@/hooks/use-session-events";
import { useCreateSession, useSession, useSessions } from "@/hooks/use-sessions";
import { useCreateProject, useProjects } from "@/hooks/use-projects";
import type { SessionStatus } from "@/lib/types";

// The 10 LangGraph nodes in their canonical pipeline order (ai/graph/state.py's
// AgentName) — the fact_checker->research and reviewer->writer revision loops
// mean a node can complete more than once, so "done" below means "has
// completed at least once", not "will never run again".
export const AGENT_NODES = [
  "planner",
  "research",
  "retriever",
  "summarizer",
  "fact_checker",
  "writer",
  "reviewer",
  "citation",
  "evaluation",
  "memory",
] as const;

const STATUS_LABEL: Record<SessionStatus, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};

export function AgentProgressList({
  completedNodes,
  latestNode,
}: {
  completedNodes: Set<string>;
  latestNode: string | null;
}) {
  return (
    <ul className="flex flex-col gap-2">
      {AGENT_NODES.map((node) => {
        const done = completedNodes.has(node);
        const isLatest = node === latestNode;
        return (
          <li
            key={node}
            className={`flex items-center gap-2 text-sm capitalize ${
              done ? "text-foreground" : "text-muted-foreground"
            }`}
          >
            {done ? (
              <CheckCircle2
                className={`size-4 ${isLatest ? "text-primary" : "text-emerald-600 dark:text-emerald-400"}`}
              />
            ) : (
              <Circle className="size-4" />
            )}
            {node.replace(/_/g, " ")}
            {isLatest && <span className="text-xs text-primary">(latest)</span>}
          </li>
        );
      })}
    </ul>
  );
}

export default function WorkspacePage() {
  const { data: projects } = useProjects();
  const createProject = useCreateProject();
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [newProjectName, setNewProjectName] = useState("");
  const [query, setQuery] = useState("");
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const projectId = selectedProjectId ?? projects?.[0]?.id ?? null;

  const { data: sessions } = useSessions(projectId);
  const createSession = useCreateSession(projectId ?? "");
  const { data: activeSession } = useSession(activeSessionId);
  const events = useSessionEvents(activeSessionId, activeSession?.status ?? null);

  const status = events.status ?? activeSession?.status ?? null;
  const completedNodes = new Set(events.nodeUpdates.map((update) => update.node));
  const latestNode = events.nodeUpdates.at(-1)?.node ?? null;

  async function handleCreateProject() {
    if (!newProjectName.trim()) return;
    const project = await createProject.mutateAsync({ name: newProjectName.trim() });
    setSelectedProjectId(project.id);
    setNewProjectName("");
  }

  async function handleSubmitQuery() {
    if (!query.trim() || !projectId) return;
    const session = await createSession.mutateAsync(query.trim());
    setActiveSessionId(session.id);
    setQuery("");
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Research Workspace</h1>
          <p className="text-sm text-muted-foreground">
            Submit a query and watch the real multi-agent pipeline run live.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-xs"
            value={projectId ?? ""}
            onChange={(event) => {
              setSelectedProjectId(event.target.value);
              setActiveSessionId(null);
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
          <Input
            placeholder="New project name"
            value={newProjectName}
            onChange={(event) => setNewProjectName(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && handleCreateProject()}
            className="w-40"
          />
          <Button
            variant="outline"
            onClick={handleCreateProject}
            disabled={createProject.isPending || !newProjectName.trim()}
          >
            + Project
          </Button>
        </div>
      </div>

      {!projectId ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center text-sm text-muted-foreground">
            <p>Create a project above to start a research session.</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle>New research query</CardTitle>
              <CardDescription>
                Kicks off the real Planner → ... → Memory pipeline
                (`POST /projects/{"{id}"}/sessions`) and streams its progress below.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex items-center gap-3">
              <Input
                placeholder="What would you like to research?"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && handleSubmitQuery()}
              />
              <Button
                onClick={handleSubmitQuery}
                disabled={createSession.isPending || !query.trim()}
              >
                <Sparkles /> Research
              </Button>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Agent progress</CardTitle>
                <CardDescription>
                  {activeSessionId ? (
                    <span data-testid="session-status">
                      {status ? STATUS_LABEL[status] : "…"}
                      {events.detail ? ` — ${events.detail}` : ""}
                    </span>
                  ) : (
                    "Submit a query to start a session."
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {activeSessionId ? (
                  <AgentProgressList completedNodes={completedNodes} latestNode={latestNode} />
                ) : (
                  <p className="text-sm text-muted-foreground">No active session.</p>
                )}
                {status === "completed" && (
                  <div className="mt-4 flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="size-4" /> Done — view the full report on the
                    Reports page.
                  </div>
                )}
                {status === "failed" && (
                  <div className="mt-4 flex items-center gap-2 text-sm text-destructive">
                    <XCircle className="size-4" /> This session failed.
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Live trace</CardTitle>
                <CardDescription>Each agent&apos;s output as it streams in.</CardDescription>
              </CardHeader>
              <CardContent>
                {events.nodeUpdates.length ? (
                  <ul className="flex max-h-80 flex-col gap-3 overflow-y-auto">
                    {events.nodeUpdates.map((update, index) => (
                      <li key={index} className="rounded-lg border border-border p-3 text-sm">
                        <div className="mb-1 text-xs font-medium text-muted-foreground capitalize">
                          {update.node.replace(/_/g, " ")}
                        </div>
                        {update.messages.map((message, messageIndex) => (
                          <p key={messageIndex} className="line-clamp-4 whitespace-pre-wrap">
                            {message}
                          </p>
                        ))}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">Nothing streamed yet.</p>
                )}
              </CardContent>
            </Card>
          </div>

          <div>
            <h2 className="mb-3 text-sm font-medium text-muted-foreground">
              {sessions?.length ?? 0} session{sessions?.length === 1 ? "" : "s"} in this
              project
            </h2>
            {sessions?.length ? (
              <div className="flex flex-col gap-2">
                {sessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => setActiveSessionId(session.id)}
                    className={`flex items-center justify-between gap-3 rounded-lg border p-3 text-left text-sm transition-colors ${
                      session.id === activeSessionId
                        ? "border-primary bg-primary/5"
                        : "border-border hover:bg-accent"
                    }`}
                  >
                    <span className="truncate">{session.query}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {STATUS_LABEL[session.status]}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No sessions yet — submit a query above.
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
