"use client";

import {
  CheckCircle2,
  Clock,
  Link as LinkIcon,
  Loader2,
  Search,
  Trash2,
  Upload,
  XCircle,
} from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  useDeleteDocument,
  useDocuments,
  useImportUrl,
  useKnowledgeBaseSearch,
  useUploadDocument,
} from "@/hooks/use-knowledge-base";
import { useCreateProject, useProjects } from "@/hooks/use-projects";
import type { DocumentStatus, DocumentWithChunkCount } from "@/lib/types";

const STATUS_META: Record<
  DocumentStatus,
  { label: string; className: string; icon: typeof Clock }
> = {
  pending: {
    label: "Pending",
    className: "text-muted-foreground",
    icon: Clock,
  },
  processing: {
    label: "Processing",
    className: "text-amber-600 dark:text-amber-400",
    icon: Loader2,
  },
  indexed: {
    label: "Indexed",
    className: "text-emerald-600 dark:text-emerald-400",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    className: "text-destructive",
    icon: XCircle,
  },
};

function StatusBadge({ status }: { status: DocumentStatus }) {
  const meta = STATUS_META[status];
  const Icon = meta.icon;
  return (
    <span
      data-testid="document-status"
      className={`inline-flex items-center gap-1 text-xs font-medium ${meta.className}`}
    >
      <Icon className={status === "processing" ? "size-3 animate-spin" : "size-3"} />
      {meta.label}
    </span>
  );
}

function DocumentCard({
  document,
  onDelete,
  isDeleting,
}: {
  document: DocumentWithChunkCount;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-2 p-4">
        <div className="flex items-start justify-between gap-2">
          <p
            className="truncate text-sm font-medium"
            title={document.original_filename ?? undefined}
          >
            {document.original_filename ?? "(untitled)"}
          </p>
          <Button
            variant="ghost"
            size="icon"
            className="size-7 shrink-0 text-muted-foreground hover:text-destructive"
            onClick={onDelete}
            disabled={isDeleting}
            aria-label="Delete document"
          >
            <Trash2 className="size-3.5" />
          </Button>
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="uppercase">{document.source_type}</span>
          <span>
            {document.chunk_count} chunk{document.chunk_count === 1 ? "" : "s"}
          </span>
        </div>
        <StatusBadge status={document.status} />
      </CardContent>
    </Card>
  );
}

export default function KnowledgeBasePage() {
  const { data: projects } = useProjects();
  const createProject = useCreateProject();
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [newProjectName, setNewProjectName] = useState("");
  const [importUrlValue, setImportUrlValue] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const projectId = selectedProjectId ?? projects?.[0]?.id ?? null;

  const { data: documents, isLoading: documentsLoading } = useDocuments(projectId);
  const uploadDocument = useUploadDocument(projectId ?? "");
  const importUrl = useImportUrl(projectId ?? "");
  const deleteDocument = useDeleteDocument(projectId ?? "");
  const { data: searchResults, isFetching: searching } = useKnowledgeBaseSearch(
    projectId,
    searchQuery,
  );

  async function handleCreateProject() {
    if (!newProjectName.trim()) return;
    const project = await createProject.mutateAsync({ name: newProjectName.trim() });
    setSelectedProjectId(project.id);
    setNewProjectName("");
  }

  function handleFileChosen(files: FileList | null) {
    const file = files?.[0];
    if (!file || !projectId) return;
    uploadDocument.mutate(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleImportUrl() {
    if (!importUrlValue.trim() || !projectId) return;
    importUrl.mutate(importUrlValue.trim());
    setImportUrlValue("");
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Knowledge Base</h1>
          <p className="text-sm text-muted-foreground">
            Upload documents or import a URL/YouTube video, then search across
            everything you&apos;ve indexed.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-xs"
            value={projectId ?? ""}
            onChange={(event) => setSelectedProjectId(event.target.value)}
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
            <p>Create a project above to start building its knowledge base.</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Search</CardTitle>
              <CardDescription>
                Semantic search over every indexed chunk in this project (real
                pgvector cosine similarity — Phase 9).
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="relative">
                <Search className="pointer-events-none absolute top-2.5 left-3 size-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  placeholder="Search this project's knowledge base…"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
              </div>
              {searching && (
                <p className="text-sm text-muted-foreground">Searching…</p>
              )}
              {searchQuery.trim() && !searching && (
                <div className="flex flex-col gap-3">
                  {searchResults?.length ? (
                    searchResults.map((result) => (
                      <div
                        key={`${result.document_id}-${result.chunk_index}`}
                        className="rounded-lg border border-border p-3 text-sm"
                      >
                        <div className="mb-1 text-xs text-muted-foreground">
                          score {result.score.toFixed(3)}
                        </div>
                        <p className="line-clamp-3">{result.chunk_text}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No matching chunks yet.
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Add a source</CardTitle>
              <CardDescription>
                PDF, DOCX, TXT, CSV, Markdown, a web page URL, or a YouTube
                video — each processes to &quot;Indexed&quot; in the background.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center gap-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt,.csv,.md,.markdown"
                className="hidden"
                onChange={(event) => handleFileChosen(event.target.files)}
              />
              <Button
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadDocument.isPending}
              >
                <Upload /> Upload file
              </Button>
              <div className="flex items-center gap-2">
                <Input
                  placeholder="https://... or a YouTube link"
                  value={importUrlValue}
                  onChange={(event) => setImportUrlValue(event.target.value)}
                  onKeyDown={(event) => event.key === "Enter" && handleImportUrl()}
                  className="w-72"
                />
                <Button
                  variant="outline"
                  onClick={handleImportUrl}
                  disabled={importUrl.isPending || !importUrlValue.trim()}
                >
                  <LinkIcon /> Import
                </Button>
              </div>
            </CardContent>
          </Card>

          <div>
            <h2 className="mb-3 text-sm font-medium text-muted-foreground">
              {documents?.length ?? 0} document
              {documents?.length === 1 ? "" : "s"}
            </h2>
            {documentsLoading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : documents?.length ? (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {documents.map((document) => (
                  <DocumentCard
                    key={document.id}
                    document={document}
                    onDelete={() => deleteDocument.mutate(document.id)}
                    isDeleting={deleteDocument.isPending}
                  />
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-12 text-center text-sm text-muted-foreground">
                <p>No documents yet — upload a file or import a URL above.</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
