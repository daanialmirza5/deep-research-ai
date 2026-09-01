"use client";

import { Activity, CheckCircle2, Clock } from "lucide-react";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  useAnalyticsActivity,
  useAnalyticsOverview,
  useAnalyticsUsage,
} from "@/hooks/use-analytics";

const RANGE_OPTIONS = [
  { label: "7 days", value: 7 },
  { label: "30 days", value: 30 },
  { label: "90 days", value: 90 },
];

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.round(seconds % 60);
  return `${minutes}m ${remainder}s`;
}

function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(0)}%`;
}

function formatEventType(eventType: string): string {
  return eventType.replace(/[._]/g, " ");
}

function KpiCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Activity;
  label: string;
  value: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-6">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon className="size-5" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const { data: overview, isLoading: overviewLoading } = useAnalyticsOverview(days);
  const { data: usage, isLoading: usageLoading } = useAnalyticsUsage(days);
  const { data: activity, isLoading: activityLoading } = useAnalyticsActivity(20);

  const hasSessions = (overview?.sessions_run ?? 0) > 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Analytics</h1>
          <p className="text-sm text-muted-foreground">
            Real session throughput, quality-gate outcomes, and per-agent
            token usage — computed live from your research sessions.
          </p>
        </div>
        <select
          className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-xs"
          value={days}
          onChange={(event) => setDays(Number(event.target.value))}
          aria-label="Date range"
        >
          {RANGE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard
          icon={Activity}
          label="Sessions run"
          value={overviewLoading ? "…" : String(overview?.sessions_run ?? 0)}
        />
        <KpiCard
          icon={Clock}
          label="Avg completion time"
          value={overviewLoading ? "…" : formatDuration(overview?.avg_completion_seconds ?? null)}
        />
        <KpiCard
          icon={CheckCircle2}
          label="Success rate"
          value={overviewLoading ? "…" : formatPercent(overview?.success_rate ?? 0)}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Sessions over time</CardTitle>
            <CardDescription>Research sessions created per day.</CardDescription>
          </CardHeader>
          <CardContent>
            {!hasSessions ? (
              <p className="py-16 text-center text-sm text-muted-foreground">
                No sessions in this range yet.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={overview?.sessions_over_time ?? []}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    stroke="var(--color-muted-foreground)"
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 12 }}
                    stroke="var(--color-muted-foreground)"
                  />
                  <Tooltip
                    contentStyle={{
                      background: "var(--color-card)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-md)",
                      fontSize: 12,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="count"
                    name="Sessions"
                    stroke="var(--color-chart-1)"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quality-gate rejection rate</CardTitle>
            <CardDescription>
              Share of runs the fact-checker/reviewer sent back for revision.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {overviewLoading || !overview?.agent_rejection_rates.some((r) => r.total_runs > 0) ? (
              <p className="py-16 text-center text-sm text-muted-foreground">
                {overviewLoading ? "Loading…" : "No agent runs in this range yet."}
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={overview.agent_rejection_rates}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis
                    dataKey="agent_name"
                    tick={{ fontSize: 12 }}
                    stroke="var(--color-muted-foreground)"
                  />
                  <YAxis
                    tickFormatter={(value: number) => `${Math.round(value * 100)}%`}
                    tick={{ fontSize: 12 }}
                    stroke="var(--color-muted-foreground)"
                  />
                  <Tooltip
                    formatter={(value) => formatPercent(Number(value))}
                    contentStyle={{
                      background: "var(--color-card)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-md)",
                      fontSize: 12,
                    }}
                  />
                  <Bar
                    dataKey="rejection_rate"
                    name="Rejection rate"
                    fill="var(--color-chart-2)"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Token usage by agent</CardTitle>
          <CardDescription>
            Real prompt/completion token counts extracted from each LLM call.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {usageLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : usage?.usage_by_agent.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="py-2 pr-4 font-medium">Agent</th>
                    <th className="py-2 pr-4 font-medium">Calls</th>
                    <th className="py-2 pr-4 font-medium">Prompt tokens</th>
                    <th className="py-2 pr-4 font-medium">Completion tokens</th>
                    <th className="py-2 pr-4 font-medium">Total tokens</th>
                  </tr>
                </thead>
                <tbody>
                  {usage.usage_by_agent.map((row) => (
                    <tr key={row.agent_name} className="border-b border-border last:border-0">
                      <td className="py-2 pr-4 capitalize">{row.agent_name.replace(/_/g, " ")}</td>
                      <td className="py-2 pr-4">{row.call_count}</td>
                      <td className="py-2 pr-4">{row.prompt_tokens.toLocaleString()}</td>
                      <td className="py-2 pr-4">{row.completion_tokens.toLocaleString()}</td>
                      <td className="py-2 pr-4">
                        {(row.prompt_tokens + row.completion_tokens).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No LLM usage recorded in this range yet.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent activity</CardTitle>
          <CardDescription>The latest events across your projects.</CardDescription>
        </CardHeader>
        <CardContent>
          {activityLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : activity?.length ? (
            <ul className="flex flex-col gap-2">
              {activity.map((item, index) => (
                <li
                  key={`${item.event_type}-${item.created_at}-${index}`}
                  className="flex items-center justify-between gap-3 border-b border-border py-2 text-sm last:border-0"
                >
                  <span className="capitalize">{formatEventType(item.event_type)}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {new Date(item.created_at).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No activity recorded yet.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
