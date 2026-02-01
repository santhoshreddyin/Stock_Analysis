/**
 * Graph Visualization Component
 * Displays entity relationships in a force-directed graph
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { stockAPI } from '../services/api';
import './GraphView.css';

const GraphView = ({ symbol = null }) => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const graphRef = useRef();

  const fetchGraphData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await stockAPI.getGraphData(symbol);
      
      // Transform data for ForceGraph2D
      const transformedData = {
        nodes: data.nodes.map(node => ({
          id: node.id,
          name: node.label,
          type: node.type,
          symbol: node.symbol,
          mentionCount: node.mentionCount,
          properties: node.properties,
          val: Math.sqrt(node.mentionCount || 1) * 2 // Size based on mentions
        })),
        links: data.edges.map(edge => ({
          source: edge.source,
          target: edge.target,
          type: edge.type,
          weight: edge.weight,
          context: edge.context
        }))
      };
      
      setGraphData(transformedData);
      setError(null);
    } catch (err) {
      setError('Failed to load graph data: ' + err.message);
      console.error('Error fetching graph data:', err);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    fetchGraphData();
  }, [fetchGraphData]);

  const getNodeColor = (node) => {
    const colors = {
      company: '#3b82f6',
      person: '#10b981',
      event: '#f59e0b',
      topic: '#8b5cf6'
    };
    return colors[node.type] || '#6b7280';
  };

  const getLinkColor = (link) => {
    const colors = {
      mentions: '#94a3b8',
      affects: '#ef4444',
      competes_with: '#f59e0b',
      partners_with: '#10b981'
    };
    return colors[link.type] || '#cbd5e1';
  };

  const handleNodeClick = (node) => {
    setSelectedNode(node);
  };

  const handleBackgroundClick = () => {
    setSelectedNode(null);
  };

  if (loading) {
    return <div className="graph-loading">Loading graph data...</div>;
  }

  if (error) {
    return <div className="graph-error">{error}</div>;
  }

  if (graphData.nodes.length === 0) {
    return (
      <div className="graph-empty">
        <p>No graph data available</p>
        <p className="graph-hint">News analysis data will appear here once the News Analyst collects information</p>
      </div>
    );
  }

  return (
    <div className="graph-view">
      <div className="graph-header">
        <h2>Entity Relationship Graph</h2>
        {symbol && <p className="graph-filter">Showing data for: {symbol}</p>}
        <button onClick={fetchGraphData} className="refresh-button">
          Refresh
        </button>
      </div>

      <div className="graph-legend">
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#3b82f6' }}></span>
          Company
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#10b981' }}></span>
          Person
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#f59e0b' }}></span>
          Event
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#8b5cf6' }}></span>
          Topic
        </div>
      </div>

      <div className="graph-container">
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          nodeLabel="name"
          nodeColor={getNodeColor}
          linkColor={getLinkColor}
          linkWidth={link => Math.sqrt(link.weight || 1)}
          linkDirectionalParticles={2}
          linkDirectionalParticleWidth={2}
          onNodeClick={handleNodeClick}
          onBackgroundClick={handleBackgroundClick}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const label = node.name;
            const fontSize = 12 / globalScale;
            ctx.font = `${fontSize}px Sans-Serif`;

            // Draw node circle
            ctx.beginPath();
            ctx.arc(node.x, node.y, node.val, 0, 2 * Math.PI, false);
            ctx.fillStyle = getNodeColor(node);
            ctx.fill();

            // Draw label
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#ffffff';
            ctx.fillText(label, node.x, node.y + node.val + fontSize);
          }}
          cooldownTicks={100}
          onEngineStop={() => graphRef.current.zoomToFit(400)}
        />
      </div>

      {selectedNode && (
        <div className="node-details">
          <div className="node-details-header">
            <h3>{selectedNode.name}</h3>
            <button onClick={() => setSelectedNode(null)} className="close-button">×</button>
          </div>
          <div className="node-details-content">
            <p><strong>Type:</strong> {selectedNode.type}</p>
            {selectedNode.symbol && <p><strong>Symbol:</strong> {selectedNode.symbol}</p>}
            <p><strong>Mentions:</strong> {selectedNode.mentionCount}</p>
            {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
              <div>
                <strong>Properties:</strong>
                <pre>{JSON.stringify(selectedNode.properties, null, 2)}</pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default GraphView;
