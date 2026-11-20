"""
engine/graph.py
Conflict Graph representation using pure Python dict[node, set[node]] with typed edges.
Part of Nia's deliverables.
"""

from enum import Enum
from typing import Dict, Set, List, Tuple, Optional, Any
from .models import SessionNode


class EdgeType(str, Enum):
    FACULTY = "FACULTY"                     # Same faculty teaching both sessions
    DIVISION = "DIVISION"                   # Same division attending both theory sessions
    BATCH_DIVISION = "BATCH_DIVISION"       # Batch lab vs whole division theory clash
    BATCH_BATCH = "BATCH_BATCH"             # Same batch attending two different labs


class ConflictGraph:
    def __init__(self, nodes: Optional[List[SessionNode]] = None):
        self.nodes: Dict[str, SessionNode] = {}
        self.adj: Dict[str, Set[str]] = {}
        self.edge_types: Dict[Tuple[str, str], EdgeType] = {}

        if nodes:
            for n in nodes:
                self.add_node(n)
            self.build_all_conflicts()

    def add_node(self, node: SessionNode) -> None:
        self.nodes[node.id] = node
        if node.id not in self.adj:
            self.adj[node.id] = set()

    def add_edge(self, u_id: str, v_id: str, edge_type: EdgeType) -> None:
        if u_id == v_id:
            return
        if u_id not in self.adj:
            self.adj[u_id] = set()
        if v_id not in self.adj:
            self.adj[v_id] = set()

        self.adj[u_id].add(v_id)
        self.adj[v_id].add(u_id)

        # Store undirected edge type
        key1 = (u_id, v_id)
        key2 = (v_id, u_id)
        self.edge_types[key1] = edge_type
        self.edge_types[key2] = edge_type

    def has_edge(self, u_id: str, v_id: str) -> bool:
        return v_id in self.adj.get(u_id, set())

    def get_edge_type(self, u_id: str, v_id: str) -> Optional[EdgeType]:
        return self.edge_types.get((u_id, v_id))

    def neighbors(self, node_id: str) -> Set[str]:
        return self.adj.get(node_id, set())

    def degree(self, node_id: str) -> int:
        return len(self.adj.get(node_id, set()))

    def max_degree(self) -> int:
        return max((len(nbrs) for nbrs in self.adj.values()), default=0)

    def average_degree(self) -> float:
        if not self.nodes:
            return 0.0
        return sum(len(nbrs) for nbrs in self.adj.values()) / len(self.nodes)

    def num_vertices(self) -> int:
        return len(self.nodes)

    def num_edges(self) -> int:
        return sum(len(nbrs) for nbrs in self.adj.values()) // 2

    def build_all_conflicts(self) -> None:
        """
        Examines all pairs of session nodes and establishes typed conflict edges.
        """
        node_list = list(self.nodes.values())
        n = len(node_list)

        for i in range(n):
            u = node_list[i]
            for j in range(i + 1, n):
                v = node_list[j]

                # 1. Faculty Conflict: same faculty cannot be in two places at once
                if u.faculty_id == v.faculty_id:
                    self.add_edge(u.id, v.id, EdgeType.FACULTY)
                    continue

                # 2. Division & Batch Conflicts:
                if u.division_id == v.division_id:
                    # Case A: Both are whole division theory sessions
                    if u.batch_id is None and v.batch_id is None:
                        self.add_edge(u.id, v.id, EdgeType.DIVISION)
                        continue

                    # Case B: One is whole division, one is a batch lab -> Clash!
                    # Whole division lecture cannot run while any batch of that division is in a lab.
                    if (u.batch_id is None and v.batch_id is not None) or (u.batch_id is not None and v.batch_id is None):
                        self.add_edge(u.id, v.id, EdgeType.BATCH_DIVISION)
                        continue

                    # Case C: Both are batch sessions
                    # If they are for the SAME batch -> Clash!
                    # If they are for DIFFERENT batches -> NO clash (they run in parallel labs!)
                    if u.batch_id is not None and v.batch_id is not None:
                        if u.batch_id == v.batch_id:
                            self.add_edge(u.id, v.id, EdgeType.BATCH_BATCH)
                            continue

    def chromatic_lower_bound(self) -> int:
        """
        Computes lower bound for chromatic number:
        chi(G) >= max(omega(G), max_faculty_load, max_division_load)
        """
        # Lower bound by faculty workload
        faculty_loads: Dict[str, int] = {}
        for node in self.nodes.values():
            faculty_loads[node.faculty_id] = faculty_loads.get(node.faculty_id, 0) + node.duration_periods
        max_fac = max(faculty_loads.values(), default=0)

        # Lower bound by division workload
        div_loads: Dict[str, int] = {}
        for node in self.nodes.values():
            if node.batch_id is None:
                div_loads[node.division_id] = div_loads.get(node.division_id, 0) + node.duration_periods
        max_div = max(div_loads.values(), default=0)

        # Greedy clique heuristic on conflict graph
        # Sort nodes by degree descending
        sorted_nodes = sorted(self.nodes.keys(), key=lambda nid: self.degree(nid), reverse=True)
        max_clique_size = 0
        clique: List[str] = []
        for nid in sorted_nodes:
            if all(self.has_edge(nid, member) for member in clique):
                clique.append(nid)
        max_clique_size = len(clique)

        return max(max_fac, max_div, max_clique_size)

    def to_visualization_dict(self, max_nodes: int = 120) -> Dict[str, Any]:
        """
        Prepares node-link format for D3/vis.js/SVG graph visualization.
        """
        sampled_keys = list(self.nodes.keys())[:max_nodes]
        key_set = set(sampled_keys)

        nodes_data = []
        for k in sampled_keys:
            node = self.nodes[k]
            nodes_data.append({
                "id": node.id,
                "label": f"{node.subject_id} ({node.faculty_id})",
                "subject": node.subject_id,
                "faculty": node.faculty_id,
                "division": node.division_id,
                "batch": node.batch_id,
                "is_lab": node.is_lab,
                "degree": self.degree(node.id)
            })

        edges_data = []
        seen = set()
        for u in sampled_keys:
            for v in self.adj[u]:
                if v in key_set:
                    edge_key = tuple(sorted([u, v]))
                    if edge_key not in seen:
                        seen.add(edge_key)
                        etype = self.edge_types.get((u, v), EdgeType.DIVISION)
                        edges_data.append({
                            "source": u,
                            "target": v,
                            "type": etype.value
                        })

        return {
            "nodes": nodes_data,
            "links": edges_data,
            "metrics": {
                "vertex_count": self.num_vertices(),
                "edge_count": self.num_edges(),
                "max_degree": self.max_degree(),
                "avg_degree": round(self.average_degree(), 2),
                "chromatic_lower_bound": self.chromatic_lower_bound()
            }
        }
