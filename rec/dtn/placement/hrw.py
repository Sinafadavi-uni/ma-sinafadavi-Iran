"""
Highest Random Weight (HRW) hashing implementation.

This module provides a pure implementation of the HRW algorithm
used for deterministic data placement in distributed systems.

Design principles:
- Stateless
- Deterministic
- Independent from membership or node health
"""

import hashlib
from typing import Dict, Iterable, List


def _hash_value(value: str) -> int:
    """
    Compute a stable integer hash for a given string using SHA-256.

    Parameters
    ----------
    value : str
        Input string to be hashed.

    Returns
    -------
    int
        Integer representation of the hash.
    """
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest, 16)


def compute_weight(key: str, node_id: str) -> int:
    """
    Compute the HRW weight for a (key, node) pair.

    The weight is calculated deterministically by hashing the
    concatenation of the data identifier and the node identifier.

    Parameters
    ----------
    key : str
        Unique identifier of the data item.
    node_id : str
        Unique identifier of the node.

    Returns
    -------
    int
        HRW weight for the given pair.
    """
    combined = f"{key}:{node_id}"
    return _hash_value(combined)


def rank_nodes(key: str, nodes: Iterable[str]) -> Dict[str, int]:
    """
    Rank nodes based on their HRW weights for a given key.

    Parameters
    ----------
    key : str
        Data identifier.
    nodes : Iterable[str]
        Iterable of node identifiers.

    Returns
    -------
    Dict[str, int]
        Mapping from node_id to computed weight.
    """
    weights: Dict[str, int] = {}

    for node_id in nodes:
        weights[node_id] = compute_weight(key, node_id)

    return weights


def hrw_select(
    key: str,
    nodes: Iterable[str],
    replicas: int = 1,
) -> List[str]:
    """
    Select top-N nodes for the given key using HRW.

    Notes
    -----
    - This function does NOT check node liveness.
    - Membership filtering must be done before calling this function.
    - Adding or removing nodes affects only a minimal subset of mappings.

    Parameters
    ----------
    key : str
        Data identifier.
    nodes : Iterable[str]
        Candidate nodes.
    replicas : int, optional
        Number of desired replicas (default is 1).

    Returns
    -------
    List[str]
        Ordered list of selected node identifiers.
    """
    if replicas <= 0:
        return []

    weight_map = rank_nodes(key, nodes)

    sorted_nodes = sorted(
        weight_map.keys(),
        key=lambda node_id: weight_map[node_id],
        reverse=True,
    )

    return sorted_nodes[:replicas]
