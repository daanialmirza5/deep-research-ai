import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AGENT_NODES, AgentProgressList } from "@/app/(dashboard)/workspace/page";

describe("AgentProgressList", () => {
  it("renders every canonical pipeline node", () => {
    render(<AgentProgressList completedNodes={new Set()} latestNode={null} />);

    for (const node of AGENT_NODES) {
      expect(screen.getByText(node.replace(/_/g, " "))).toBeInTheDocument();
    }
  });

  it("marks nodes that have completed at least once as done, others as pending", () => {
    render(
      <AgentProgressList
        completedNodes={new Set(["planner", "research"])}
        latestNode="research"
      />,
    );

    expect(screen.getByText("planner").closest("li")).toHaveClass("text-foreground");
    expect(screen.getByText("retriever").closest("li")).toHaveClass(
      "text-muted-foreground",
    );
  });

  it("flags the most recently completed node as the latest", () => {
    render(
      <AgentProgressList
        completedNodes={new Set(["planner", "research"])}
        latestNode="research"
      />,
    );

    const researchItem = screen.getByText("research").closest("li");
    expect(researchItem).toHaveTextContent("(latest)");
    const plannerItem = screen.getByText("planner").closest("li");
    expect(plannerItem).not.toHaveTextContent("(latest)");
  });

  it("keeps a re-entered node (revision loop) marked done, not pending", () => {
    // fact_checker can route back to research (see ai/graph/routing.py) — a
    // node that has already completed once must stay "done" even though the
    // pipeline isn't finished overall.
    render(
      <AgentProgressList
        completedNodes={new Set(["fact_checker", "research"])}
        latestNode="research"
      />,
    );

    expect(screen.getByText("fact checker").closest("li")).toHaveClass(
      "text-foreground",
    );
  });
});
