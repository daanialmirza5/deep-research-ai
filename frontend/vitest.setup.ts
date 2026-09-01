import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// vitest.config.ts doesn't set `test.globals: true`, so `afterEach` isn't on
// globalThis — Testing Library's own auto-cleanup only self-registers when
// it detects that global, so without this it silently never runs, leaking
// each render() into the next test in the same file (caught live: a second
// render() in the same describe block made `getByRole` see duplicate nav
// links from the still-mounted first render).
afterEach(() => cleanup());
