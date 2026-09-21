import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { MethodologyPage } from "@/components/methodology/methodology-page";

afterEach(cleanup);

describe("MethodologyPage", () => {
  it("documents multi-season data, grounded retrieval, and gated predictions", () => {
    render(<MethodologyPage />);
    expect(screen.getByRole("heading", { name: "Data & Methodology" })).toBeInTheDocument();
    expect(screen.getByText("2021–22")).toBeInTheDocument();
    expect(screen.getByText("2026–27")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "AI Assistant data access" })).toBeInTheDocument();
    expect(screen.getByText(/PostgreSQL records are the factual authority/)).toBeInTheDocument();
    expect(screen.getByText(/not betting advice/)).toBeInTheDocument();
    expect(screen.getByText(/not affiliated with or endorsed by the NBA/)).toBeInTheDocument();
  });
});
