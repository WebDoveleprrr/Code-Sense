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
      .attr("class", "link")
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
      });

    // Node circles
    node.append("circle")
      .attr("r", NODE_RADIUS)
      .attr("fill", (d) => langColor(d.language) + "22")
      .attr("stroke", (d) => langColor(d.language))
      .attr("stroke-width", 1.5);

    // Node labels
    node.append("text")
      .attr("dy", NODE_RADIUS + 14)
      .attr("text-anchor", "middle")
      .text((d) => {
        const name = d.label || d.id;
        const short = name.split("/").pop().replace(/\.\w+$/, "");
        return truncate(short, 16);
      });

    // Simulation
    simulationRef.current = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(edges).id((d) => d.id).distance(120).strength(0.5))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide(NODE_RADIUS + 20))
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

  return (
    <div className="p-8 max-w-7xl mx-auto h-screen flex flex-col">
      <SectionHeader
        title="Dependency Graph"
        subtitle="Visual import and dependency mapping across your codebase"
      />

      {/* Controls */}
      <div className="flex items-center gap-3 mb-4 flex-shrink-0">
        <div className="w-72">
          <RepoSelector value={repoId} onChange={setRepoId} />
        </div>
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
          <div className="flex items-center gap-3 text-xs font-mono text-frost-dim">
            <Badge variant="acid">{graphData.nodes?.length || 0} nodes</Badge>
            <Badge variant="plasma">{graphData.edges?.length || 0} edges</Badge>
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
            <div className="h-full bg-ink-950 rounded-xl border border-ink-600 flex items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <Spinner size={32} />
                <p className="text-xs font-mono text-frost-dim">Building dependency graph…</p>
              </div>
            </div>
          ) : graphData?.nodes?.length > 0 ? (
            <GraphCanvas
              nodes={graphData.nodes}
              edges={graphData.edges || []}
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
          <div className="w-64 flex-shrink-0 animate-slide-up">
            <Card className="h-full">
              <div className="flex items-center gap-2 mb-4">
                <Info size={14} className="text-acid" />
                <span className="font-mono text-xs font-bold text-acid uppercase tracking-widest">
                  Node Detail
                </span>
              </div>

              <div className="space-y-3 text-xs font-mono">
                <div>
                  <p className="text-frost-dim mb-1">ID / File</p>
                  <p className="text-frost break-all">{selectedNode.id}</p>
                </div>

                {selectedNode.label && selectedNode.label !== selectedNode.id && (
                  <div>
                    <p className="text-frost-dim mb-1">Label</p>
                    <p className="text-frost">{selectedNode.label}</p>
                  </div>
                )}

                {selectedNode.language && (
                  <div>
                    <p className="text-frost-dim mb-1">Language</p>
                    <Badge variant="acid">{selectedNode.language}</Badge>
                  </div>
                )}

                {selectedNode.type && (
                  <div>
                    <p className="text-frost-dim mb-1">Type</p>
                    <Badge variant="plasma">{selectedNode.type}</Badge>
                  </div>
                )}

                {selectedNode.imports?.length > 0 && (
                  <div>
                    <p className="text-frost-dim mb-1">Imports ({selectedNode.imports.length})</p>
                    <ul className="space-y-1 max-h-40 overflow-y-auto">
                      {selectedNode.imports.map((imp) => (
                        <li key={imp} className="text-frost-dim truncate">
                          → {imp}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-frost-dim hover:text-danger transition-colors mt-2"
                >
                  × Deselect
                </button>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
