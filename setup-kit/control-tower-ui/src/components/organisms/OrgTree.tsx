'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { AgentNode, type AgentNodeData } from '@/components/molecules/AgentNode';

interface OrgTreeProps {
  agents: (AgentNodeData & { parent_id: string | null })[];
  onNodeClick: (id: string) => void;
}

interface LayoutNode {
  agent: AgentNodeData & { parent_id: string | null };
  x: number;
  y: number;
  children: LayoutNode[];
}

const COL_GAP = 40;
const NODE_W = 160;
const LEVEL_H = 120;

function layout(
  agents: (AgentNodeData & { parent_id: string | null })[],
  parentId: string | null,
  depth: number
): { root: LayoutNode | null; subWidth: number }[] {
  const children = agents.filter((a) => a.parent_id === parentId);
  return children.map((child) => {
    const subChildren = layout(agents, child.id, depth + 1);
    const subWidth = Math.max(
      NODE_W,
      subChildren.reduce((acc, c, i) => acc + c.subWidth + (i > 0 ? COL_GAP : 0), 0)
    );
    return {
      root: {
        agent: child,
        x: 0,
        y: depth * LEVEL_H + 60,
        children: subChildren.map((c) => c.root!).filter(Boolean),
      },
      subWidth,
    };
  });
}

function position(nodes: { root: LayoutNode | null; subWidth: number }[], startX: number) {
  let cursor = startX;
  for (const n of nodes) {
    if (!n.root) continue;
    const center = cursor + n.subWidth / 2;
    n.root.x = center;
    // Position this node's children centered under it
    const childWidth = n.root.children.length
      ? n.root.children.reduce((acc, c, i) => {
          const w = widthOf(c);
          return acc + w + (i > 0 ? COL_GAP : 0);
        }, 0)
      : 0;
    let childCursor = center - childWidth / 2;
    for (const child of n.root.children) {
      const w = widthOf(child);
      child.x = childCursor + w / 2;
      positionChildren(child);
      childCursor += w + COL_GAP;
    }
    cursor += n.subWidth + COL_GAP;
  }
}

function widthOf(node: LayoutNode): number {
  if (node.children.length === 0) return NODE_W;
  const childrenWidth = node.children.reduce(
    (acc, c, i) => acc + widthOf(c) + (i > 0 ? COL_GAP : 0),
    0
  );
  return Math.max(NODE_W, childrenWidth);
}

function positionChildren(node: LayoutNode) {
  if (node.children.length === 0) return;
  const childWidth = node.children.reduce(
    (acc, c, i) => acc + widthOf(c) + (i > 0 ? COL_GAP : 0),
    0
  );
  let cursor = node.x - childWidth / 2;
  for (const child of node.children) {
    const w = widthOf(child);
    child.x = cursor + w / 2;
    positionChildren(child);
    cursor += w + COL_GAP;
  }
}

function flatten(n: LayoutNode): LayoutNode[] {
  return [n, ...n.children.flatMap(flatten)];
}

export function OrgTree({ agents, onNodeClick }: OrgTreeProps) {
  const root = agents.find((a) => a.parent_id === null);
  if (!root) {
    return (
      <div className="flex items-center justify-center h-48 text-text-muted text-sm">
        No agents running. Spawn the Meta Agent to begin.
      </div>
    );
  }

  // Build the tree rooted at "root"
  const rootNode: LayoutNode = {
    agent: root,
    x: 0,
    y: 60,
    children: layout(agents, root.id, 1)
      .map((c) => c.root)
      .filter((c): c is LayoutNode => c !== null),
  };

  const totalWidth = Math.max(NODE_W, widthOf(rootNode));
  const SVG_W = Math.max(800, totalWidth + 120);
  const SVG_H = Math.max(360, 80 + LEVEL_H * 3);

  rootNode.x = SVG_W / 2;
  positionChildren(rootNode);

  const allNodes = flatten(rootNode);
  const edges: React.ReactNode[] = [];

  const addEdges = (n: LayoutNode) => {
    for (const c of n.children) {
      const startX = n.x;
      const startY = n.y + 32;
      const endX = c.x;
      const endY = c.y - 32;
      const midY = (startY + endY) / 2;
      edges.push(
        <motion.path
          key={`edge-${n.agent.id}-${c.agent.id}`}
          d={`M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`}
          fill="none"
          stroke="#2A2D38"
          strokeWidth={1.5}
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.1 }}
        />
      );
      addEdges(c);
    }
  };
  addEdges(rootNode);

  return (
    <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="w-full h-full" aria-label="Agent org chart">
      <AnimatePresence>{edges}</AnimatePresence>
      <AnimatePresence>
        {allNodes.map((n) => (
          <AgentNode key={n.agent.id} agent={n.agent} onClick={onNodeClick} x={n.x} y={n.y} />
        ))}
      </AnimatePresence>
    </svg>
  );
}
