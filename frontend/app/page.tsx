import {
  ArrowRight,
  BookOpen,
  Database,
  FileOutput,
  Globe,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardTitle,
} from "@/components/ui/card";

const PIPELINE = [
  "Planner",
  "Research",
  "Retriever",
  "Fact Checker",
  "Writer",
  "Reviewer",
  "Citation",
];

const FEATURES = [
  {
    icon: Globe,
    title: "Web, Arxiv & Semantic Scholar search",
    description:
      "Agents pull from live web search, academic papers, and your own documents.",
  },
  {
    icon: Database,
    title: "Knowledge base",
    description:
      "Every uploaded PDF, DOCX, or imported page is chunked, embedded, and searchable.",
  },
  {
    icon: ShieldCheck,
    title: "Fact-checked, cited reports",
    description:
      "Claims are verified against retrieved sources before a report is finalized.",
  },
  {
    icon: FileOutput,
    title: "Export anywhere",
    description:
      "Markdown, PDF, DOCX, or HTML — the finished report, your format.",
  },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6">
        <span className="text-sm font-semibold tracking-tight">
          DeepResearch AI
        </span>
        <nav className="flex items-center gap-2">
          <Button variant="ghost" asChild>
            <Link href="/login">Sign in</Link>
          </Button>
          <Button asChild>
            <Link href="/register">
              Get started <ArrowRight />
            </Link>
          </Button>
        </nav>
      </header>

      <main className="flex-1">
        <section className="mx-auto flex max-w-4xl flex-col items-center gap-8 px-6 py-24 text-center">
          <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
            Multi-agent research, from question to cited report
          </h1>
          <p className="max-w-2xl text-lg text-muted-foreground">
            A team of specialized AI agents plans, searches, verifies, writes,
            and cites — while you watch every step happen live.
          </p>
          <Button size="lg" asChild>
            <Link href="/register">
              Start researching <ArrowRight />
            </Link>
          </Button>

          <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-sm text-muted-foreground">
            {PIPELINE.map((step, i) => (
              <span key={step} className="flex items-center gap-2">
                <span className="rounded-full border border-border bg-card px-3 py-1">
                  {step}
                </span>
                {i < PIPELINE.length - 1 && <ArrowRight className="size-3" />}
              </span>
            ))}
          </div>
        </section>

        <section className="mx-auto grid max-w-5xl gap-4 px-6 pb-24 sm:grid-cols-2">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <Card key={title}>
              <CardContent className="flex gap-4 pt-6">
                <Icon className="mt-1 size-5 shrink-0 text-primary" />
                <div className="flex flex-col gap-1">
                  <CardTitle className="text-base">{title}</CardTitle>
                  <CardDescription>{description}</CardDescription>
                </div>
              </CardContent>
            </Card>
          ))}
        </section>
      </main>

      <footer className="border-t border-border py-8">
        <div className="mx-auto flex max-w-6xl items-center px-6 text-sm text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <BookOpen className="size-4" /> DeepResearch AI — MIT licensed
          </span>
        </div>
      </footer>
    </div>
  );
}
