from __future__ import annotations

import logging
from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Set, Tuple

import networkx as nx
import numpy as np
from community import community_louvain
from git import Repo

from app.schemas.git_analysis import FileCouplingData
from app.services.commit_parser import CommitParser

logger = logging.getLogger(__name__)


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    if not set_a and not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union > 0 else 0.0


class CouplingAnalyzer:
    def __init__(self) -> None:
        self.commit_parser = CommitParser()

    def calculate_file_coupling(self, repo: Repo, min_coupling: float = 0.3, max_commits: int | None = None) -> List[FileCouplingData]:
        file_changes = self.commit_parser.build_change_index(repo, max_commits=max_commits)
        files = list(file_changes.keys())
        results: List[FileCouplingData] = []
        for i, a in enumerate(files):
            for b in files[i + 1 :]:
                score = jaccard_similarity(file_changes[a], file_changes[b])
                if score >= min_coupling:
                    times_together = len(file_changes[a] & file_changes[b])
                    total_a = len(file_changes[a])
                    total_b = len(file_changes[b])
                    confidence = min(1.0, times_together / max(1, min(total_a, total_b)))
                    results.append(
                        FileCouplingData(
                            file_a=a,
                            file_b=b,
                            coupling_score=score,
                            times_together=times_together,
                            confidence=confidence,
                        )
                    )
        results.sort(key=lambda x: x.coupling_score, reverse=True)
        return results

    def detect_logical_modules(self, coupling_data: List[FileCouplingData], threshold: float = 0.6) -> List[List[str]]:
        G = nx.Graph()
        for cd in coupling_data:
            if cd.coupling_score >= threshold:
                G.add_edge(cd.file_a, cd.file_b, weight=cd.coupling_score)
        if G.number_of_edges() == 0:
            return []
        partition = community_louvain.best_partition(G, weight="weight")
        modules: Dict[int, List[str]] = defaultdict(list)
        for node, part in partition.items():
            modules[part].append(node)
        return list(modules.values())

    def identify_architectural_violations(self, coupling_data: List[FileCouplingData], rules: List[dict]) -> List[dict]:
        violations: List[dict] = []
        # Example rule format: {"name": "API-DB isolation", "deny": [("/api/", "/db/")], "severity": "high"}
        for cd in coupling_data:
            for rule in rules:
                severity = rule.get("severity", "medium")
                for a_pat, b_pat in rule.get("deny", []):
                    if a_pat in cd.file_a and b_pat in cd.file_b:
                        violations.append({"rule": rule.get("name", "unnamed"), "pair": (cd.file_a, cd.file_b), "severity": severity})
                    if a_pat in cd.file_b and b_pat in cd.file_a:
                        violations.append({"rule": rule.get("name", "unnamed"), "pair": (cd.file_b, cd.file_a), "severity": severity})
        return violations

    def calculate_coupling_matrix(self, file_list: List[str], repo: Repo) -> np.ndarray:
        file_changes = self.commit_parser.build_change_index(repo)
        n = len(file_list)
        M = np.zeros((n, n), dtype=float)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = file_list[i], file_list[j]
                score = jaccard_similarity(file_changes.get(a, set()), file_changes.get(b, set()))
                M[i, j] = M[j, i] = score
        return M

    def get_most_coupled_files(self, repo: Repo, top_n: int = 20) -> List[Tuple[str, str, float]]:
        data = self.calculate_file_coupling(repo, min_coupling=0.0)
        pairs = [(d.file_a, d.file_b, d.coupling_score) for d in data]
        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs[:top_n]
