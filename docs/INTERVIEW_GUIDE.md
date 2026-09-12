# Deep Research AI — Interview Guide & Technical Defense

## 1. Pitches
- **30-Second Pitch**: "Deep Research AI is a 10-agent autonomous research system built with LangGraph. It recursively decomposes complex research questions, executes parallel multi-source web retrieval, fact-checks extracted claims, and compiles fully grounded, cited reports."
- **2-Minute Pitch**: "Standard single-prompt LLM research suffers from hallucinations, source bias, and shallow analysis. Deep Research AI replaces single-shot generation with a 10-agent cyclic LangGraph pipeline. A Planning Agent breaks research goals into structured sub-hypotheses; a Search Agent dispatches targeted web queries; an Extraction Agent filters noise; a Fact-Checking Agent validates claims across disparate sources; and a Citation Agent ensures every paragraph maps to an exact verified URL. If the Reviewer detects evidence gaps, it routes the workflow back to planning for targeted exploration before compiling the final report."

## 2. Key Technical Q&A
- **Q: Why use a cyclical graph instead of a linear DAG pipeline?**
  - **A**: True research is inherently iterative. If the initial search for a technical query returns conflicting claims or insufficient data, a linear pipeline produces an incomplete draft. LangGraph's cyclical graph allows the Reviewer agent to dynamically route back to the Search Agent with refined search queries until epistemic confidence thresholds are met.
- **Q: How do you prevent infinite loops in the agent cycle?**
  - **A**: We enforce a strict hard recursion depth limit (`max_iterations = 3`) within the LangGraph State and conditional edge router. If confidence is still unmet at max depth, the system compiles the report with transparent 'Unresolved Discrepancy' annotations.
