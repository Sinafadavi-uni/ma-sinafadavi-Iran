"""
Membership management module.

This module is responsible for tracking active nodes in the system
using a lightweight heartbeat mechanism.

Design assumptions:
- The system is currently single-threaded.
- Membership is the single source of truth for node liveness.
- Failure detection is time-based and conservative.
"""

import time
from typing import Dict, List, Optional


class Membership:
    """
    Track node liveness based on heartbeat timestamps.

    Each node is identified by a unique node_id (string).
    Nodes are considered active if their last heartbeat
    is within a predefined timeout window.
    """

    def __init__(self, timeout: float = 10.0):
        """
        Initialize the membership manager.

        time.time() -> float
        Returns the current time in seconds since the Unix epoch
        as a floating point number.
        Output: 1766139128.1120422
        This value is a Unix timestamp (number of seconds since January 1, 1970)
        with subsecond precision (decimal digits).


        Using float makes the data type compatible with Python's time
        API and provides flexibility for sub-second timeouts if needed.


        # In rec/dtn/broker.py
        ANNOUNCEMENT_INTERVAL_SECONDS = 10

        # In rec/dtn/node.py
        BUNDLE_POLL_INTERVAL_SECONDS = 10

        Parameters
        ----------
        timeout : float
            Maximum allowed heartbeat silence (in seconds)
            before a node is considered inactive.
        """
        self._timeout: float = timeout
        self._last_seen: Dict[str, float] = {}

    def heartbeat(self, node_id: str) -> None:
        """
        Record a heartbeat from a node.

        This updates the last-seen timestamp for the node.
        If the node is new, it will be added automatically.

        Parameters
        ----------
        node_id : str
            Unique identifier of the node.
        """
        self._last_seen[node_id] = time.time()

    def is_active(self, node_id: str) -> bool:
        """
        Check whether a node is currently considered active.

        Parameters
        ----------
        node_id : str
            Node identifier.

        Returns
        -------
        bool
            True if the node is active, False otherwise.
        """
        last_seen: Optional[float] = self._last_seen.get(node_id)
        if last_seen is None:
            return False

        return (time.time() - last_seen) <= self._timeout

    def active_nodes(self) -> List[str]:
        """
        Get the list of currently active nodes.

        Returns
        -------
        List[str]
            List of node identifiers considered alive.
        """
        now = time.time()
        active: List[str] = []

        for node_id, last_seen in self._last_seen.items():
            if now - last_seen <= self._timeout:
                active.append(node_id)

        return active

    def remove_node(self, node_id: str) -> None:
        """
        Explicitly remove a node from membership.

        This can be useful for graceful shutdowns
        or administrative operations.

        Parameters
        ----------
        node_id : str
            Node identifier to remove.
        """
        self._last_seen.pop(node_id, None)

    def size(self) -> int:
        """
        Return the number of known nodes
        (active + inactive).

        Returns
        -------
        int
            Total number of nodes tracked.
        """
        return len(self._last_seen)
