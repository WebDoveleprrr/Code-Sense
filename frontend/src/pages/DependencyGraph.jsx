// src/pages/DependencyGraph.jsx
import React, { useState, useEffect, useRef, useCallback } from "react";
import * as d3 from "d3";
import { useSearchParams } from "react-router-dom";
import { GitBranch, ZoomIn, ZoomOut, Maximize2, RefreshCw, Info } from "lucide-react";
import toast from "react-hot-toast";
import { dependencyApi } from "../services/api";
import { Card, Button, SectionHeader, EmptyState, ErrorAlert, Spinner, Badge } from "../components/ui";
import RepoSelector from "../components/ui/RepoSelector";
import { langColor, truncate } from "../utils/helpers";

const NODE_RADIUS = 18;

function GraphCanvas({ nodes, edges, onNodeClick }) {
  const svgRef = useRef(null);
  const simulationRef = useRef(null);

  useEffect(() => {
    if (!nodes.length || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = svgRef.current.clientWidth || 800;
    const height = svgRef.current.clientHeight || 600;

    const g = svg.append("g");

    // Zoom
    const zoom = d3.zoom()
      .scaleExtent([0.2, 4])
      .on("zoom", (event) => g.attr("transform", event.transform));
    svg.call(zoom);

    // Arrow marker
    svg.append("defs").append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "-0 -5 10 10")
      .attr("refX", NODE_RADIUS + 8)
      .attr("refY", 0)
      .attr("orient", "auto")
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "rgba(0,255,136,0.4)");

    // Build link and node data
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));

    const links = g.append("g").selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", "rgba(0, 255, 136, 0.15)")
      .attr("stroke-width", 1.5)
      .attr("marker-end", "url(#arrowhead)");

    const node = g.append("g").selectAll(".node")
      .data(nodes)
      .join("g")
      .attr("class", "node")
      .style("cursor", "pointer")
      .call(
        d3.drag()
          .on("start", (event, d) => {
            if (!event.active) simulationRef.current?.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulationRef.current?.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      )
      .on("click", (event, d) => {
        event.stopPropagation();
        onNodeClick(d);
      })
      .on("mouseover", (event, d) => {
        links
          .attr("stroke", (l) => {
            if (l.source.id === d.id) return "rgba(0, 255, 136, 0.8)"; // Outgoing (Acid)
            if (l.target.id === d.id) return "rgba(244, 63, 94, 0.8)"; // Incoming (Rose)
            return "rgba(255, 255, 255, 0.03)";
          })
          .attr("stroke-width", (l) => l.source.id === d.id || l.target.id === d.id ? 2.5 : 1);
        
        node.style("opacity", (n) => {
          if (n.id === d.id) return 1.0;
          const isNeighbor = edges.some(e => 
            (e.source.id === d.id && e.target.id === n.id) || 
            (e.target.id === d.id && e.source.id === n.id)
          );
          return isNeighbor ? 1.0 : 0.25;
        });
      })
      .on("mouseout", () => {
        links
          .attr("stroke", "rgba(0, 255, 136, 0.15)")
          .attr("stroke-width", 1.5);
        node.style("opacity", 1.0);
      });

    // Node circles
    node.append("circle")
      .attr("r", NODE_RADIUS)
      .attr("fill", (d) => langColor(d.language))
      .attr("fill-opacity", 0.15)
      .attr("stroke", (d) => langColor(d.language))
      .attr("stroke-width", 2.0);

    // Node labels
    node.append("text")
      .attr("dy", NODE_RADIUS + 14)
      .attr("text-anchor", "middle")
      .attr("fill", "#E2E8F0")
      .attr("font-size", "10px")
      .attr("font-family", "monospace")
      .text((d) => {
        const name = d.label || d.id;
        const short = name.split("/").pop().replace(/\.\w+$/, "");
        return truncate(short, 16);
      });

    // Simulation
    simulationRef.current = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(edges).id((d) => d.id).distance(140).strength(0.4))
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide(NODE_RADIUS + 25))
      .on("tick", () => {
        links
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x2", (d) => d.target.x)
          .attr("y2", (d) => d.target.y);
        node.attr("transform", (d) => `translate(${d.x},${d.y})`);
      });

    // Reset zoom on canvas click
    svg.on("click", () => onNodeClick(null));

    // Center fit on load
    setTimeout(() => {
      svg.call(zoom.transform, d3.zoomIdentity.translate(width / 4, height / 4).scale(0.8));
    }, 800);

    return () => {
      simulationRef.current?.stop();
    };
  }, [nodes, edges, onNodeClick]);

  const handleZoom = (dir) => {
    const svg = d3.select(svgRef.current);
    const zoom = d3.zoom().scaleExtent([0.2, 4]);
    svg.call(zoom.scaleBy, dir > 0 ? 1.3 : 0.75);
  };

  return (
    <div className="relative w-full h-full bg-ink-950 rounded-xl overflow-hidden border border-ink-600">
      <svg ref={svgRef} width="100%" height="100%" />
      <div className="absolute top-3 right-3 flex flex-col gap-1">
        <button
          onClick={() => handleZoom(1)}
          className="w-8 h-8 glass rounded-lg flex items-center justify-center text-frost-dim hover:text-acid transition-colors"
        >
          <ZoomIn size={14} />
        </button>
        <button
          onClick={() => handleZoom(-1)}
          className="w-8 h-8 glass rounded-lg flex items-center justify-center text-frost-dim hover:text-acid transition-colors"
        >
          <ZoomOut size={14} />
        </button>
      </div>
    </div>
  );
}

export default function DependencyGraph() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  // Search and Filter States
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedType, setSelectedType] = useState("all");

  const fetchGraph = useCallback(async () => {
    if (!repoId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await dependencyApi.buildGraph(repoId);
      setGraphData(data);
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }, [repoId]);

  useEffect(() => {
    if (repoId) fetchGraph();
  }, [repoId, fetchGraph]);

  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node);
  }, []);

  // Filter nodes based on search and type
  const filteredNodes = graphData?.nodes
    ? graphData.nodes.filter((n) => {
        const matchesSearch =
          searchTerm === "" ||
          n.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
          n.label.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesType =
          selectedType === "all" ||
          n.type?.toLowerCase() === selectedType.toLowerCase();
        return matchesSearch && matchesType;
      })
    : [];

  const visibleNodeIds = new Set(filteredNodes.map((n) => n.id));

  // Keep edges that connect visible nodes
  const filteredEdges = graphData?.edges
    ? graphData.edges.filter((e) => {
        const sourceId = typeof e.source === "object" ? e.source.id : e.source;
        const targetId = typeof e.target === "object" ? e.target.id : e.target;
        return visibleNodeIds.has(sourceId) && visibleNodeIds.has(targetId);
      })
    : [];

  // Calculate imports and imported-by dynamically for selectedNode
  const nodeImports = graphData?.edges && selectedNode
    ? graphData.edges
        .filter((e) => {
          const sourceId = typeof e.source === "object" ? e.source.id : e.source;
          return sourceId === selectedNode.id;
        })
        .map((e) => {
          const targetId = typeof e.target === "object" ? e.target.id : e.target;
          return targetId;
        })
    : [];

  const nodeImportedBy = graphData?.edges && selectedNode
    ? graphData.edges
        .filter((e) => {
          const targetId = typeof e.target === "object" ? e.target.id : e.target;
          return targetId === selectedNode.id;
        })
        .map((e) => {
          const sourceId = typeof e.source === "object" ? e.source.id : e.source;
          return sourceId;
        })
    : [];

  return (
    <div className="p-8 max-w-7xl mx-auto h-screen flex flex-col font-sans">
      <SectionHeader
        title="Dependency Graph"
        subtitle="Visual import and dependency mapping across your codebase"
      />

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4 mb-4 flex-shrink-0 p-4 bg-slate-900/30 border border-slate-800 rounded-2xl">
        <div className="w-64">
          <RepoSelector value={repoId} onChange={setRepoId} />
        </div>

        {/* Search Box */}
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search nodes..."
          className="px-4 py-2 bg-slate-950/80 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-purple-500/40 text-sm w-48"
        />

        {/* Node Type Filter */}
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="px-4 py-2 bg-slate-950/80 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/40 text-sm"
        >
          <option value="all">All Types</option>
          <option value="file">File</option>
          <option value="class">Class</option>
          <option value="function">Function</option>
          <option value="method">Method</option>
        </select>

        <Button
          onClick={fetchGraph}
          disabled={!repoId || loading}
          loading={loading}
          variant="secondary"
          icon={<RefreshCw size={13} />}
          size="sm"
        >
          Reload
        </Button>

        {graphData && (
          <div className="flex items-center gap-3 text-xs font-mono ml-auto">
            <Badge variant="acid">{filteredNodes.length} nodes</Badge>
            <Badge variant="plasma">{filteredEdges.length} edges</Badge>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-4">
          <ErrorAlert message={error} onRetry={fetchGraph} />
        </div>
      )}

      {/* Main area */}
      <div className="flex-1 min-h-0 flex gap-4">
        {/* Graph */}
        <div className="flex-1 min-h-0">
          {loading ? (
            <div className="h-full bg-slate-950/20 rounded-2xl border border-slate-800 flex items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <Spinner size={32} />
                <p className="text-xs font-mono text-slate-400 animate-pulse">Building dependency graph…</p>
              </div>
            </div>
          ) : filteredNodes.length > 0 ? (
            <GraphCanvas
              nodes={filteredNodes}
              edges={filteredEdges}
              onNodeClick={handleNodeClick}
            />
          ) : (
            <div className="h-full">
              <EmptyState
                icon={GitBranch}
                title="No dependency data"
                description="Select an indexed repository to visualize its import graph."
              />
            </div>
          )}
        </div>

        {/* Selected node info */}
        {selectedNode && (
          <div className="w-80 flex-shrink-0 animate-slide-up h-full overflow-y-auto">
            <Card className="h-full flex flex-col space-y-4 border border-slate-800 bg-slate-900/60 backdrop-blur-md p-5 rounded-2xl scrollbar-thin">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 flex-shrink-0">
                <div className="flex items-center gap-2">
                  <Info size={14} className="text-purple-400" />
                  <span className="font-mono text-xs font-bold text-purple-400 uppercase tracking-widest">
                    Node Metadata
                  </span>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-slate-500 hover:text-rose-400 text-lg transition-colors font-bold"
                >
                  &times;
                </button>
              </div>

              <div className="space-y-4 text-xs font-mono flex-1 overflow-y-auto pr-1">
                <div>
                  <p className="text-slate-500 font-semibold mb-1 uppercase tracking-wider text-[10px]">Symbol Name</p>
                  <p className="text-slate-200 text-sm font-bold truncate">{selectedNode.label || selectedNode.id.split('/').pop()}</p>
                </div>

                <div>
                  <p className="text-slate-500 font-semibold mb-1 uppercase tracking-wider text-[10px]">Node Type</p>
                  <span className="px-2 py-0.5 rounded bg-purple-500/10 border border-purple-500/20 text-purple-400 text-[10px] font-bold uppercase">
                    {selectedNode.type || "file"}
                  </span>
                </div>

                <div>
                  <p className="text-slate-500 font-semibold mb-1 uppercase tracking-wider text-[10px]">Source File</p>
                  <p className="text-slate-300 break-all leading-relaxed bg-slate-950/50 p-2 border border-slate-800/40 rounded-xl">
                    {selectedNode.file_path || selectedNode.id}
                  </p>
                </div>

                {selectedNode.start_line !== undefined && (
                  <div>
                    <p className="text-slate-500 font-semibold mb-1 uppercase tracking-wider text-[10px]">Line Range</p>
                    <p className="text-slate-300 text-xs">
                      L{selectedNode.start_line} – L{selectedNode.end_line}
                    </p>
                  </div>
                )}

                {selectedNode.language && (
                  <div>
                    <p className="text-slate-500 font-semibold mb-1 uppercase tracking-wider text-[10px]">Language</p>
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold uppercase">
                      {selectedNode.language}
                    </span>
                  </div>
                )}

                {/* Imports */}
                <div>
                  <p className="text-slate-500 font-semibold mb-1.5 uppercase tracking-wider text-[10px] flex items-center justify-between">
                    <span>Dependencies / Imports</span>
                    <span className="text-[9px] text-slate-600 bg-slate-950 px-1.5 py-0.5 rounded">{nodeImports.length}</span>
                  </p>
                  <div className="max-h-36 overflow-y-auto space-y-1.5 scrollbar-thin">
                    {nodeImports.length > 0 ? (
                      nodeImports.map((imp, idx) => (
                        <div key={idx} className="p-1.5 bg-slate-950/30 border border-slate-800/40 rounded text-[10px] text-slate-300 truncate font-mono">
                          &rarr; {imp.split('/').pop()}
                        </div>
                      ))
                    ) : (
                      <div className="text-[10px] text-slate-600 italic">None detected</div>
                    )}
                  </div>
                </div>

                {/* Imported By */}
                <div>
                  <p className="text-slate-500 font-semibold mb-1.5 uppercase tracking-wider text-[10px] flex items-center justify-between">
                    <span>Imported By / Referenced By</span>
                    <span className="text-[9px] text-slate-600 bg-slate-950 px-1.5 py-0.5 rounded">{nodeImportedBy.length}</span>
                  </p>
                  <div className="max-h-36 overflow-y-auto space-y-1.5 scrollbar-thin">
                    {nodeImportedBy.length > 0 ? (
                      nodeImportedBy.map((imp, idx) => (
                        <div key={idx} className="p-1.5 bg-slate-950/30 border border-slate-800/40 rounded text-[10px] text-slate-300 truncate font-mono">
                          &larr; {imp.split('/').pop()}
                        </div>
                      ))
                    ) : (
                      <div className="text-[10px] text-slate-600 italic">None detected</div>
                    )}
                  </div>
                </div>

              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
