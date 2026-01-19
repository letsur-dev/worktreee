"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface GraphItem {
  filename: string;
  issue_key: string;
  title?: string;
}

interface SyncLog {
  type: "fetching" | "fetched" | "done" | "error";
  message: string;
}

export default function GraphsPage() {
  const [graphs, setGraphs] = useState<GraphItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingKey, setSyncingKey] = useState<string | null>(null);
  const [syncLogs, setSyncLogs] = useState<SyncLog[]>([]);
  const [newIssueKey, setNewIssueKey] = useState("");

  useEffect(() => {
    fetchGraphs();
  }, []);

  async function fetchGraphs() {
    try {
      const res = await fetch("/api/graphs");
      if (res.ok) {
        const data = await res.json();
        setGraphs(data.graphs || []);
      }
    } catch (error) {
      console.error("Failed to fetch graphs:", error);
    } finally {
      setLoading(false);
    }
  }

  function syncGraph(issueKey: string) {
    setSyncingKey(issueKey);
    setSyncLogs([]);

    const eventSource = new EventSource(`/api/graphs/sync-stream/${issueKey}`);
    let fetchedCount = 0;

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "fetching") {
        setSyncLogs((prev) => [
          ...prev,
          { type: "fetching", message: `Fetching ${data.key}...` },
        ]);
      } else if (data.type === "fetched") {
        fetchedCount++;
        const detail = data.children ? ` (${data.children} children)` : "";
        setSyncLogs((prev) => [
          ...prev,
          { type: "fetched", message: `${data.key}${detail}` },
        ]);
      } else if (data.type === "done") {
        setSyncLogs((prev) => [
          ...prev,
          { type: "done", message: `Sync complete! ${fetchedCount} issues synced.` },
        ]);
        eventSource.close();
        setTimeout(() => {
          setSyncingKey(null);
          fetchGraphs();
        }, 1500);
      } else if (data.type === "error") {
        setSyncLogs((prev) => [
          ...prev,
          { type: "error", message: `Error: ${data.detail}` },
        ]);
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setSyncLogs((prev) => [...prev, { type: "error", message: "Connection lost" }]);
      eventSource.close();
      setSyncingKey(null);
    };
  }

  function generateGraph() {
    const key = newIssueKey.trim().toUpperCase();
    if (!key) return;
    setNewIssueKey("");
    syncGraph(key);
  }

  async function deleteGraph(issueKey: string) {
    if (!confirm(`${issueKey} 그래프를 삭제하시겠습니까?`)) return;

    try {
      const res = await fetch(`/api/graphs/${issueKey}`, { method: "DELETE" });
      if (res.ok) {
        setGraphs((prev) => prev.filter((g) => g.issue_key !== issueKey));
      } else {
        const data = await res.json();
        alert(data.detail || "삭제 실패");
      }
    } catch (error) {
      console.error("Failed to delete graph:", error);
      alert("삭제 중 오류가 발생했습니다.");
    }
  }

  if (loading) {
    return <div className="text-gray-400">Loading...</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-100 mb-6">Jira Graphs</h1>

      {/* New Graph Generator */}
      <div className="mb-6 flex gap-3">
        <input
          type="text"
          placeholder="Jira Issue Key (예: PRDEL-123)"
          value={newIssueKey}
          onChange={(e) => setNewIssueKey(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && generateGraph()}
          className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-gray-100 placeholder-gray-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
        />
        <button
          onClick={generateGraph}
          disabled={!newIssueKey.trim() || syncingKey !== null}
          className="px-6 py-3 bg-brand-500 hover:bg-brand-600 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed rounded-xl font-medium transition"
        >
          Generate
        </button>
      </div>

      {graphs.length === 0 ? (
        <p className="text-gray-400">생성된 그래프가 없습니다.</p>
      ) : (
        <div className="space-y-2">
          {graphs.map((graph) => (
            <div
              key={graph.filename}
              className="flex items-center justify-between bg-gray-900 rounded-xl px-5 py-4 border border-gray-800"
            >
              <div className="flex items-center gap-4">
                <Link
                  href={`/api/graphs/files/${graph.filename}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand-400 hover:underline font-medium"
                >
                  {graph.issue_key}
                </Link>
                {graph.title && (
                  <span className="text-gray-400 text-sm truncate max-w-md">
                    {graph.title}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => syncGraph(graph.issue_key)}
                  disabled={syncingKey !== null}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition"
                >
                  Sync
                </button>
                <button
                  onClick={() => deleteGraph(graph.issue_key)}
                  disabled={syncingKey !== null}
                  className="px-3 py-2 bg-gray-700 hover:bg-red-600 disabled:bg-gray-800 disabled:text-gray-500 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition"
                  title="삭제"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Sync Modal */}
      {syncingKey && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-xl p-6 w-[500px] max-h-[400px] overflow-hidden border border-gray-700 shadow-2xl">
            <h3 className="text-lg font-semibold text-gray-100 mb-4">
              Syncing {syncingKey}...
            </h3>
            <div className="space-y-1 max-h-[280px] overflow-y-auto font-mono text-sm">
              {syncLogs.map((log, i) => (
                <div
                  key={i}
                  className={
                    log.type === "fetching"
                      ? "text-gray-400"
                      : log.type === "fetched"
                      ? "text-success-400"
                      : log.type === "done"
                      ? "text-brand-400 font-semibold"
                      : "text-error-400"
                  }
                >
                  {log.type === "fetching" && "⏳ "}
                  {log.type === "fetched" && "✅ "}
                  {log.type === "done" && "🎉 "}
                  {log.type === "error" && "❌ "}
                  {log.message}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
