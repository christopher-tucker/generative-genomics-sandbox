import React, { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";

type GeneRecord = {
  id: string;
  symbol: string;
  expression: number;
};

type VolcanoPlotProps = {
  genes: GeneRecord[];
};

const VolcanoPlot: React.FC<VolcanoPlotProps> = ({ genes }) => {
  const plotRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!plotRef.current || genes.length === 0) return;

    const exprValues = genes.map((g) => g.expression);
    const meanExpr = exprValues.reduce((a, b) => a + b, 0) / exprValues.length;

    const x = genes.map((g) => g.expression - meanExpr);
    const y = x.map((v) => Math.abs(v));
    const text = genes.map(
      (g) => `${g.symbol} (${g.id})<br>expr=${g.expression.toFixed(3)}`
    );

    const trace = {
      x,
      y,
      text,
      mode: "markers",
      type: "scatter",
      hovertemplate:
        "%{text}<br>Δexpr=%{x:.3f}<br>|Δexpr|=%{y:.3f}<extra></extra>",
      marker: { size: 8 },
    };

    const layout = {
      title: "Pseudo-volcano: centered expression vs. deviation",
      xaxis: { title: "Centered expression (expression \u2212 mean)" },
      yaxis: { title: "|Centered expression|" },
      margin: { t: 40, r: 20, b: 60, l: 60 },
      height: 400,
    };

    Plotly.newPlot(plotRef.current, [trace], layout, {
      displayModeBar: false,
      responsive: true,
    });

    const handleResize = () =>
      plotRef.current && Plotly.Plots.resize(plotRef.current);
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (plotRef.current) Plotly.purge(plotRef.current);
    };
  }, [genes]);

  return (
    <div style={{ marginTop: "2rem" }}>
      <h2>Volcano-style view</h2>
      <p style={{ color: "#555", fontSize: "0.9rem" }}>
        Each point is a gene. Left/right = difference from mean expression.
        Vertical = magnitude of that change.
      </p>
      <div ref={plotRef} />
    </div>
  );
};

export default VolcanoPlot;
