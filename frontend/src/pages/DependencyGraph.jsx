import React, { useState, useEffect, useRef, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { GitBranch, Loader2, ZoomIn, ZoomOut, Maximize, Search, Search as SearchIcon, Filter } from "lucide-react";
import { dependencyApi } from "../services/api";
import { useRepository } from "../hooks/useRepositories";
import RepoSelector from "../components/ui/RepoSelector";
import toast from "react-hot-toast";
import * as d3 from "d3";

export default function DependencyGraph() {
  const [searchParams] = useSearchParams();
  const [repoId, setRepoId] = useState(searchParams.get("repo") || "");
  const { repo } = useRepository(repoId);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const isRepoReady = repo ? repo.status === "ready" : false;

  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const nodeRefs = useRef([]);
  const edgeRefs = useRef([]);
  const labelRefs = useRef([]);
  
  const [hoveredNode, setHoveredNode] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  
  const [metrics, setMetrics] = useState({ modules: 0, dependencies: 0, connections: 0, rootNodes: 0, leafNodes: 0 });

  const degrees = useMemo(() => {
    const inDeg = {};
    const outDeg = {};
    graphData.nodes.forEach(n => { inDeg[n.id] = 0; outDeg[n.id] = 0; });
    graphData.edges.forEach(e => {
      const src = typeof e.source === 'object' ? e.source.id : e.source;
      const tgt = typeof e.target === 'object' ? e.target.id : e.target;
      if (outDeg[src] !== undefined) outDeg[src]++;
      if (inDeg[tgt] !== undefined) inDeg[tgt]++;
    });
    return { inDeg, outDeg };
  }, [graphData]);

  useEffect(() => {
    if (!graphData.nodes.length) return;
    setMetrics({
      modules: graphData.nodes.length,
      dependencies: graphData.edges.length,
      connections: graphData.edges.length,
      rootNodes: graphData.nodes.filter(n => degrees.inDeg[n.id] === 0 && degrees.outDeg[n.id] > 0).length,
      leafNodes: graphData.nodes.filter(n => degrees.outDeg[n.id] === 0 && degrees.inDeg[n.id] > 0).length,
      isolatedNodes: graphData.nodes.filter(n => degrees.inDeg[n.id] === 0 && degrees.outDeg[n.id] === 0).length
    });
  }, [graphData, degrees]);

  const adjacency = useMemo(() => {
    const adj = {};
    graphData.nodes.forEach(n => adj[n.id] = new Set([n.id]));
    graphData.edges.forEach(e => {
      const src = typeof e.source === 'object' ? e.source.id : e.source;
      const tgt = typeof e.target === 'object' ? e.target.id : e.target;
      if (!adj[src]) adj[src] = new Set([src]);
      if (!adj[tgt]) adj[tgt] = new Set([tgt]);
      adj[src].add(tgt);
      adj[tgt].add(src);
    });
    return adj;
  }, [graphData]);

  const searchMatches = useMemo(() => {
    if (!searchQuery) return null;
    const lower = searchQuery.toLowerCase();
    const matches = new Set();
    graphData.nodes.forEach(n => {
      if (n.label?.toLowerCase().includes(lower)) matches.add(n.id);
    });
    return matches;
  }, [searchQuery, graphData]);

  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const handleMouseDown = (e) => { setIsDragging(true); setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y }); };
  const handleMouseMove = (e) => { if (isDragging) setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y }); };
  const handleMouseUp = () => setIsDragging(false);
  
  const abortControllerRef = useRef(null);

  useEffect(() => {
    if (repoId && isRepoReady) {
      loadGraph();
    }
    return () => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, [repoId, isRepoReady]);

  const loadGraph = async () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError(null);
    try {
      const res = await dependencyApi.buildGraph(repoId, { signal: controller.signal });
      
      if (!res.success) {
        throw new Error(res.error || "Failed to build dependency graph.");
      }
      
      if (!res.nodes || res.nodes.length === 0) {
        setGraphData({ nodes: [], edges: [] });
        return;
      }
      
      // Force simulation to calculate layout
      const nodes = res.nodes.map(n => ({...n, x: Math.random() * 800, y: Math.random() * 600}));
      const edges = res.edges.map(e => ({...e}));
      
      setGraphData({ nodes, edges });
      setZoom(1);
      setPan({ x: 0, y: 0 });
    } catch (err) {
      if (err.name === 'CanceledError' || err.message === 'canceled' || err.code === 'ERR_CANCELED') {
        return;
      }
      setError(err.message || "An error occurred.");
      toast.error("Graph calculation failed");
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  };

  const [hideIsolated, setHideIsolated] = useState(false);

  useEffect(() => {
    if (!graphData.nodes.length) return;

    // Filter isolated nodes if requested
    const filteredNodes = hideIsolated 
      ? graphData.nodes.filter(n => degrees.inDeg[n.id] > 0 || degrees.outDeg[n.id] > 0)
      : graphData.nodes;

    const nodes = filteredNodes.map((n, i) => {
      // Deterministic initial placement in a spiral
      const radius = Math.sqrt(i) * 10;
      const angle = i * 137.5 * (Math.PI / 180);
      return { ...n, x: Math.cos(angle) * radius, y: Math.sin(angle) * radius, vx: 0, vy: 0 };
    });
    const links = graphData.edges.map(e => ({ ...e, source: e.source, target: e.target }));

    nodeRefs.current = nodeRefs.current.slice(0, nodes.length);
    edgeRefs.current = edgeRefs.current.slice(0, links.length);
    labelRefs.current = labelRefs.current.slice(0, nodes.length);

    const isLarge = nodes.length > 200;
    const isHuge = nodes.length > 500;
    
    // For very large graphs, we need much stronger repulsion but also stronger centering
    const chargeStrength = isHuge ? -400 : isLarge ? -250 : -300;
    const distanceMax = isHuge ? 1200 : 800;
    const linkDistance = isHuge ? 25 : isLarge ? 50 : 80;
    const collideRadius = isHuge ? 15 : isLarge ? 25 : 35;
    const alphaDecay = isHuge ? 0.05 : 0.02; // Settle faster
    const edgeStrength = isHuge ? 0.3 : 1;

    const simulation = d3.forceSimulation(nodes)
      .alphaDecay(alphaDecay)
      .velocityDecay(0.4)
      .force("link", d3.forceLink(links).id(d => d.id).distance(linkDistance).strength(edgeStrength))
      .force("charge", d3.forceManyBody().strength(chargeStrength).distanceMax(distanceMax))
      .force("x", d3.forceX(0).strength(isHuge ? 0.06 : 0.03))
      .force("y", d3.forceY(0).strength(isHuge ? 0.06 : 0.03))
      .force("collide", d3.forceCollide().radius(collideRadius).iterations(isHuge ? 2 : 3))
      .on("tick", () => {
        links.forEach((link, i) => {
          const el = edgeRefs.current[i];
          if (el && link.source.x !== undefined && link.target.x !== undefined) {
            const dx = link.target.x - link.source.x;
            const dy = link.target.y - link.source.y;
            const length = Math.sqrt(dx * dx + dy * dy);
            const angle = Math.atan2(dy, dx) * (180 / Math.PI);
            el.style.left = `calc(50% + ${link.source.x}px)`;
            el.style.top = `calc(50% + ${link.source.y}px)`;
            el.style.width = `${length}px`;
            el.style.transform = `rotate(${angle}deg)`;
          }
        });

        nodes.forEach((node, i) => {
          const el = nodeRefs.current[i];
          if (el && node.x !== undefined) {
            el.style.left = `calc(50% + ${node.x}px)`;
            el.style.top = `calc(50% + ${node.y}px)`;
          }
          
          const labelEl = labelRefs.current[i];
          if (labelEl && node.x !== undefined) {
            labelEl.style.left = `calc(50% + ${node.x}px)`;
            labelEl.style.top = `calc(50% + ${node.y}px)`;
          }
        });
      });

    return () => simulation.stop();
  }, [graphData]);

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-slate-950 font-sans">
      <div className="relative z-50 h-16 px-6 border-b border-slate-800 flex items-center justify-between shrink-0 bg-slate-950/50 backdrop-blur-md">
        <h2 className="text-lg font-semibold text-slate-50 flex items-center gap-2">
          <GitBranch size={20} className="text-indigo-400" /> Dependency Graph
        </h2>
        <div className="flex items-center gap-4">
          <div className="relative">
            <SearchIcon size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search Node..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-50 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 w-64"
            />
          </div>
          <div className="w-64">
            <RepoSelector value={repoId} onChange={setRepoId} />
          </div>
        </div>
      </div>

      {!repoId ? (
        <div className="flex-1 flex flex-col items-center justify-center">
          <GitBranch size={48} className="text-slate-600 mb-4" />
          <h3 className="text-xl font-semibold text-slate-50 mb-2">No repository selected</h3>
          <p className="text-slate-400">Select a repository to view its dependency graph.</p>
        </div>
      ) : !isRepoReady ? (
        <div className="flex-1 flex flex-col items-center justify-center">
          <Loader2 className="animate-spin text-indigo-500 mb-4" size={40} />
          <p className="text-slate-400">Waiting for repository to finish indexing...</p>
        </div>
      ) : loading ? (
        <div className="flex-1 flex flex-col items-center justify-center">
          <Loader2 className="animate-spin text-indigo-500 mb-4" size={40} />
          <p className="text-slate-400">Rendering graph...</p>
        </div>
      ) : error ? (
        <div className="flex-1 flex flex-col items-center justify-center">
          <GitBranch size={48} className="text-red-500 mb-4" />
          <h3 className="text-xl font-semibold text-slate-50 mb-2">Failed to load graph</h3>
          <p className="text-slate-400">{error}</p>
        </div>
      ) : graphData.nodes.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center">
          <GitBranch size={48} className="text-slate-600 mb-4" />
          <h3 className="text-xl font-semibold text-slate-50 mb-2">No dependencies found</h3>
          <p className="text-slate-400">This repository does not have a recognizable dependency graph.</p>
        </div>
      ) : (
        <div className="flex-1 relative flex overflow-hidden">
          <div 
            className="flex-1 relative bg-[#020617] overflow-hidden cursor-move" 
            style={{ backgroundImage: 'radial-gradient(#1e293b 1px, transparent 1px)', backgroundSize: '40px 40px' }}
            onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}
          >
            <div className="absolute top-20 left-1/2 -translate-x-1/2 z-50 pointer-events-none">
              {searchQuery && searchMatches && searchMatches.size === 0 && (
                <div className="bg-slate-900 border border-slate-700 px-4 py-2 rounded-lg shadow-lg text-slate-300 text-sm">
                  No matching nodes found.
                </div>
              )}
            </div>

            <div className="absolute bottom-6 left-6 flex flex-col gap-2 z-20">
              <button onClick={() => setZoom(z => Math.min(z + 0.2, 3))} className="w-10 h-10 bg-slate-900 border border-slate-700 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shadow-lg">
                <ZoomIn size={18} />
              </button>
              <button onClick={() => setZoom(z => Math.max(z - 0.2, 0.5))} className="w-10 h-10 bg-slate-900 border border-slate-700 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shadow-lg">
                <ZoomOut size={18} />
              </button>
              <button onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }} className="w-10 h-10 bg-slate-900 border border-slate-700 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shadow-lg mt-2">
                <Maximize size={18} />
              </button>
            </div>

            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div 
                className="relative w-96 h-96 transition-transform duration-75"
                style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
              >
                {/* 1. Edges Layer (z-0) */}
                {graphData.edges.map((link, i) => {
                  const srcId = typeof link.source === 'object' ? link.source.id : link.source;
                  const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
                  const isConnectedToHover = hoveredNode && (srcId === hoveredNode || tgtId === hoveredNode);
                  const isConnectedToSelected = selectedNode && (srcId === selectedNode || tgtId === selectedNode);
                  const isFaded = (hoveredNode && !isConnectedToHover) || (selectedNode && !isConnectedToSelected);
                  const isSearchFaded = searchMatches && !(searchMatches.has(srcId) && searchMatches.has(tgtId));
                  const isActive = isConnectedToHover || isConnectedToSelected;
                  
                  return (
                    <div 
                      key={`edge-${i}`}
                      ref={(el) => (edgeRefs.current[i] = el)}
                      className={`absolute h-[1px] origin-left z-0 transition-opacity duration-300 ${
                        isActive 
                          ? 'bg-indigo-400 opacity-100 z-10' 
                          : isFaded || isSearchFaded 
                            ? 'bg-slate-600 opacity-10' 
                            : 'bg-indigo-500/50'
                      }`}
                    />
                  );
                })}

                {/* 2. Nodes Layer (z-10) */}
                {graphData.nodes.map((node, i) => {
                  const isHovered = hoveredNode === node.id;
                  const isSelected = selectedNode === node.id;
                  const isNeighbor = (hoveredNode && adjacency[hoveredNode]?.has(node.id)) || (selectedNode && adjacency[selectedNode]?.has(node.id));
                  const isSearchMatch = searchMatches?.has(node.id);
                  const isFaded = ((hoveredNode || selectedNode) && !isNeighbor) || (searchMatches && !isSearchMatch);
                  
                  return (
                    <div
                      key={node.id}
                      ref={(el) => (nodeRefs.current[i] = el)}
                      title={node.label || node.id}
                      onMouseEnter={() => setHoveredNode(node.id)}
                      onMouseLeave={() => setHoveredNode(null)}
                      onClick={() => setSelectedNode(node.id === selectedNode ? null : node.id)}
                      className={`absolute w-6 h-6 rounded-full flex items-center justify-center z-10 transform -translate-x-1/2 -translate-y-1/2 pointer-events-auto cursor-pointer transition-all duration-300 ${
                        isHovered || isSelected || isSearchMatch
                          ? 'bg-indigo-500 shadow-[0_0_20px_rgba(79,70,229,0.8)] scale-125 z-30' 
                          : isNeighbor
                            ? 'bg-indigo-400 scale-110 z-20'
                            : isFaded
                              ? 'bg-slate-800 border border-slate-700 opacity-30 grayscale'
                              : 'bg-slate-700 border-2 border-indigo-400'
                      }`}
                    />
                  );
                })}

                {/* 3. Labels Layer (z-20) */}
                {graphData.nodes.map((node, i) => {
                  const isHovered = hoveredNode === node.id;
                  const isSelected = selectedNode === node.id;
                  const isNeighbor = (hoveredNode && adjacency[hoveredNode]?.has(node.id)) || (selectedNode && adjacency[selectedNode]?.has(node.id));
                  const isSearchMatch = searchMatches?.has(node.id);
                  const showLabel = zoom >= 1.5 || isHovered || isSelected || isNeighbor || isSearchMatch;
                  
                  return (
                    <div
                      key={`label-${node.id}`}
                      ref={(el) => (labelRefs.current[i] = el)}
                      className={`absolute z-20 pointer-events-none transform -translate-x-1/2 -translate-y-1/2 transition-opacity duration-200 ${
                        showLabel ? 'opacity-100' : 'opacity-0'
                      }`}
                    >
                      <span className={`absolute top-4 text-[10px] whitespace-nowrap px-1.5 py-0.5 rounded pointer-events-none ${
                        isHovered || isSelected || isSearchMatch ? 'text-white bg-indigo-600 font-bold z-30' : 'text-slate-300 bg-slate-900/80'
                      }`}>
                        {node.label || ''}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="w-80 border-l border-slate-800 bg-slate-950 p-6 flex flex-col">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-6">Graph Metrics</h3>
            
            <div className="space-y-4">
              <MetricCard label="Modules" value={metrics.modules} />
              <MetricCard label="Dependencies" value={metrics.dependencies} />
              <MetricCard label="Root Nodes" value={metrics.rootNodes} />
              <MetricCard label="Leaf Nodes" value={metrics.leafNodes} />
              <MetricCard label="Isolated" value={metrics.isolatedNodes} />
            </div>

            <div className="mt-8 border-t border-slate-800 pt-6">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Filter size={16} /> Filters
              </h3>
              <div className="space-y-3">
                <label className="flex items-center gap-3 text-sm text-slate-300 cursor-pointer">
                  <input type="checkbox" 
                    checked={hideIsolated} 
                    onChange={(e) => setHideIsolated(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-indigo-500 focus:ring-indigo-500" 
                  />
                  Hide Isolated Nodes
                </label>
              </div>
            </div>

            <div className="mt-8 border-t border-slate-800 pt-6">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Legend</h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-3 text-slate-300">
                  <div className="w-4 h-4 rounded-full bg-slate-700 border-2 border-indigo-400"></div> Default Node
                </div>
                <div className="flex items-center gap-3 text-slate-300">
                  <div className="w-4 h-4 rounded-full bg-indigo-500 shadow-[0_0_10px_rgba(79,70,229,0.8)]"></div> Hovered / Searched
                </div>
                <div className="flex items-center gap-3 text-slate-300">
                  <div className="w-4 h-4 rounded-full bg-indigo-400"></div> Adjacent Node
                </div>
                <div className="flex items-center gap-3 text-slate-300">
                  <div className="w-4 h-[2px] bg-indigo-500/50"></div> Dependency Link
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, valueColor = "text-slate-50" }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-glass">
      <span className="block text-xs font-medium text-slate-500 mb-1">{label}</span>
      <span className={`text-2xl font-bold ${valueColor}`}>{value}</span>
    </div>
  );
}
