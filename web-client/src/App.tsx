import React, { useState } from "react";

type Descriptor = {
  celltype: string;
  diseasestatus: string;
  gender: string;
  smoker: string;
  age: string;
};

type GenerateResponse = {
  model_version: string;
  genes: string[];
  expression: number[];
};

const App: React.FC = () => {
  const [descriptor, setDescriptor] = useState<Descriptor>({
    celltype: "CD4 T cells",
    diseasestatus: "healthy",
    gender: "female",
    smoker: "no",
    age: "45",
  });

  const [seed, setSeed] = useState<string>("42");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateResponse | null>(null);

  const handleChange =
    (field: keyof Descriptor) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setDescriptor((prev) => ({
        ...prev,
        [field]: e.target.value,
      }));
    };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // Build request payload
      const body: any = {
        descriptor: descriptor,
      };
      if (seed.trim() !== "") {
        const seedNum = Number(seed);
        if (!Number.isNaN(seedNum)) {
          body.seed = seedNum;
        }
      }

      const resp = await fetch("/api/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`API error ${resp.status}: ${text}`);
      }

      const data = (await resp.json()) as GenerateResponse;
      setResult(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const renderResult = () => {
    if (!result) return null;

    const { model_version, genes, expression } = result;
    const n = Math.min(20, genes.length, expression.length);

    const rows: React.ReactElement[] = [];
    for (let i = 0; i < n; i++) {
      rows.push(
        <tr key={i}>
          <td>{i}</td>
          <td>{genes[i]}</td>
          <td>{expression[i].toFixed(4)}</td>
        </tr>
      );
    }

    return (
      <div style={{ marginTop: "2rem" }}>
        <h2>Generated Expression</h2>
        <p>
          <strong>Model version:</strong> {model_version}
        </p>
        <p>
          Showing first {n} genes (out of {genes.length})
        </p>
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              borderCollapse: "collapse",
              minWidth: "400px",
              fontSize: "0.9rem",
            }}
          >
            <thead>
              <tr>
                <th style={{ borderBottom: "1px solid #ccc", textAlign: "left", padding: "4px 8px" }}>#</th>
                <th style={{ borderBottom: "1px solid #ccc", textAlign: "left", padding: "4px 8px" }}>Gene</th>
                <th style={{ borderBottom: "1px solid #ccc", textAlign: "right", padding: "4px 8px" }}>Expression</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div
      style={{
        maxWidth: "800px",
        margin: "2rem auto",
        padding: "1.5rem",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
        border: "1px solid #eee",
        borderRadius: "8px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
      }}
    >
      <h1 style={{ marginBottom: "1rem" }}>
        Generative Genomics Sandbox
      </h1>
      <p style={{ marginBottom: "1.5rem", color: "#555" }}>
        Enter a simple experiment description and generate a synthetic gene
        expression profile using a conditional VAE trained on GSE60424.
      </p>

      <form onSubmit={handleSubmit}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "1rem",
          }}
        >
          <div>
            <label style={{ display: "block", fontWeight: 600 }}>
              Cell type
            </label>
            <input
              type="text"
              value={descriptor.celltype}
              onChange={handleChange("celltype")}
              style={{ width: "100%", padding: "6px 8px", marginTop: "4px" }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontWeight: 600 }}>
              Disease status
            </label>
            <input
              type="text"
              value={descriptor.diseasestatus}
              onChange={handleChange("diseasestatus")}
              style={{ width: "100%", padding: "6px 8px", marginTop: "4px" }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontWeight: 600 }}>
              Gender
            </label>
            <input
              type="text"
              value={descriptor.gender}
              onChange={handleChange("gender")}
              style={{ width: "100%", padding: "6px 8px", marginTop: "4px" }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontWeight: 600 }}>
              Smoker
            </label>
            <input
              type="text"
              value={descriptor.smoker}
              onChange={handleChange("smoker")}
              style={{ width: "100%", padding: "6px 8px", marginTop: "4px" }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontWeight: 600 }}>
              Age
            </label>
            <input
              type="text"
              value={descriptor.age}
              onChange={handleChange("age")}
              style={{ width: "100%", padding: "6px 8px", marginTop: "4px" }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontWeight: 600 }}>
              Seed (optional)
            </label>
            <input
              type="text"
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              style={{ width: "100%", padding: "6px 8px", marginTop: "4px" }}
            />
            <small style={{ color: "#777" }}>
              Same seed → same sample (deterministic).
            </small>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            marginTop: "1.5rem",
            padding: "8px 16px",
            fontSize: "1rem",
            fontWeight: 600,
            borderRadius: "4px",
            border: "none",
            cursor: "pointer",
            backgroundColor: loading ? "#999" : "#2563eb",
            color: "white",
          }}
        >
          {loading ? "Generating..." : "Generate Expression"}
        </button>
      </form>

      {error && (
        <div
          style={{
            marginTop: "1rem",
            padding: "0.75rem 1rem",
            borderRadius: "4px",
            backgroundColor: "#fee2e2",
            color: "#991b1b",
          }}
        >
          Error: {error}
        </div>
      )}

      {renderResult()}
    </div>
  );
};

export default App;
