"""
Datastore mapping layer.

This module connects the membership component with
the HRW algorithm to select appropriate datastore nodes.

Responsibilities:
- Retrieve active nodes from membership
- Delegate ranking to HRW
- Remain free of low-level hashing logic
"""

from typing import List

from rec.dtn.placement.hrw import hrw_select
from rec.dtn.placement.membership import Membership


class DatastoreMapper:
    """
    Map named data to datastore nodes using HRW.

    This class deliberately separates system state
    (membership) from hashing logic (HRW).
    """

    def __init__(self, membership: Membership):
        """
        Initialize the mapper.

        Parameters
        ----------
        membership : Membership
            Membership manager instance.
        """
        self._membership = membership

    def select_datastores(
        self,
        named_data: str,
        replica_count: int = 1,
    ) -> List[str]:
        """
        Select datastore nodes for the given data identifier.

        Parameters
        ----------
        named_data : str
            Unique data name.
        replica_count : int
            Number of desired replicas.

        Returns
        -------
        List[str]
            Ordered list of selected datastores.
        """
        active_nodes = self._membership.active_nodes()

        if not active_nodes:
            return []

        return hrw_select(
            key=named_data,
            nodes=active_nodes,
            replicas=replica_count,
        )
