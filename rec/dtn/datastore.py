import asyncio
from pathlib import Path
from typing import Any, Dict, List, Tuple, override

from rec.dtn.eid import EID
from rec.dtn.messages import BundleData, BundleType, NodeType
from rec.dtn.node import Node
from rec.dtn.storage import NameTakenError, Storage
from rec.util.log import LOG

HEARTBEAT_INTERVAL_SECONDS = 10

# --- Helper Cache Class for Optimization ---
# This class provides an asynchronous, thread-safe, size-limited cache
# to store frequently accessed data in memory, avoiding repeated disk/database I/O.


class DataCache:
    """A simple asynchronous, size-limited, LRU-like cache."""

    def __init__(self, size_limit: int = 1000) -> None:
        # Dictionary to store cached data: {named_data: List[Tuple[str, bytes]]}
        self._cache: Dict[str, List[Tuple[str, bytes]]] = {}
        self._lock = asyncio.Lock()
        self._size_limit = size_limit

    async def get(self, key: str) -> List[Tuple[str, bytes]] | None:
        """Retrieve data from the cache."""
        async with self._lock:
            # Using .get() for safe access
            return self._cache.get(key)

    async def put(self, key: str, value: List[Tuple[str, bytes]]) -> None:
        """Store data in the cache, with eviction if limit is reached."""
        async with self._lock:
            if key not in self._cache and len(self._cache) >= self._size_limit:
                # Simple LRU-like eviction: remove the oldest item (first item in dict)
                try:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                except StopIteration:
                    pass
            self._cache[key] = value

    async def invalidate(self, key: str) -> None:
        """Remove an item from the cache (used after a successful PUT/UPDATE)."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]


# --- End of Helper Cache Class ---


class Datastore(Node):
    _storage: Storage
    _cache: DataCache
    CACHE_SIZE_LIMIT = 1000  # Max number of data items to keep in cache

    def __init__(
        self, node_id: EID, dtn_agent_socket: Path, root_directory: Path
    ) -> None:
        super().__init__(
            _node_id=node_id,
            _dtn_agent_socket=dtn_agent_socket,
            _node_type=NodeType.DATASTORE,
        )

        root_directory.mkdir(parents=True, exist_ok=True)

        db_path = root_directory / "database.db"
        blob_directory = root_directory / "blobs"
        self._storage = Storage(db_path, blob_directory)

        # Initialize the high-performance cache
        self._cache = DataCache(size_limit=self.CACHE_SIZE_LIMIT)

    @override
    async def run(self) -> None:
        LOG.info("Starting datastore (Optimized with In-Memory Cache)")
        await super().run()

        # Cancel the receive task created by super() since we manage it in TaskGroup
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._send_periodic_heartbeat())
            tg.create_task(self._receive_loop())

        await self.stop()

    @override
    async def _handle_bundle(self, bundle: BundleData) -> list[BundleData]:
        replies: list[BundleData] = []

        if BundleType.NDATA_PUT <= bundle.type <= BundleType.NDATA_DEL:
            replies = await self._handle_data(bundle=bundle)
        elif BundleType.BROKER_ANNOUNCE <= bundle.type <= BundleType.BROKER_ACK:
            replies = await self._handle_discovery(bundle=bundle)
        else:
            LOG.warning(f"Won't handle bundle of type: {bundle.type}")

        return replies

    async def _handle_data(self, bundle: BundleData) -> list[BundleData]:
        LOG.debug("Named data bundle")

        if not bundle.named_data:
            LOG.error(
                "Received NDATA bundle with no name set. "
                "This indicates a malformed bundle from the sender. "
                "Ignoring."
            )
            return []

        bundles: list[BundleData] = []

        match bundle.type:
            case BundleType.NDATA_PUT:
                LOG.debug("Data action is PUT")

                success = True
                error = ""
                try:
                    await self._storage.store_data(
                        name=bundle.named_data, data=bundle.payload
                    )
                    # Optimization: Invalidate cache after successful store
                    await self._cache.invalidate(bundle.named_data)
                    LOG.debug(
                        f"Invalidated cache for {bundle.named_data} to ensure freshness."
                    )

                except NameTakenError as err:
                    success = False
                    error = str(err)

                response = BundleData(
                    type=BundleType.NDATA_PUT,
                    source=self._node_id,
                    destination=bundle.source,
                    named_data=bundle.named_data,
                    success=success,
                    error=error,
                )
                bundles.append(response)

            case BundleType.NDATA_GET:
                LOG.debug("Data action is GET (Checking Cache first)")

                # High-performance check: Try to retrieve from cache first
                loaded = await self._cache.get(bundle.named_data)

                if loaded is not None:
                    LOG.debug(
                        f"Cache HIT for {bundle.named_data}. Serving from memory."
                    )
                else:
                    # Cache Miss: Load from the underlying storage (disk/database)
                    LOG.debug(
                        f"Cache MISS for {bundle.named_data}. Loading from storage."
                    )
                    loaded = await self._storage.load_data(name=bundle.named_data)

                    # Store the loaded data in the cache for future requests
                    if loaded:
                        await self._cache.put(bundle.named_data, loaded)

                LOG.debug(f"Loaded data count: {len(loaded)}")
                for l_name, l_data in loaded:
                    response = BundleData(
                        type=BundleType.NDATA_GET,
                        source=self._node_id,
                        destination=bundle.source,
                        payload=l_data,
                        named_data=l_name,
                    )
                    bundles.append(response)

            case _:
                LOG.error(f"Received bundle of type {bundle.type}, ignoring")

        return bundles

    async def _send_periodic_heartbeat(self) -> None:
        """
        Periodically send heartbeat to broker to maintain registration.

        This method runs in the background while the node is active.
        It sends BROKER_REQUEST messages at regular intervals to prove
        liveness to the broker.
        """
        LOG.info("Starting periodic heartbeat to broker")

        while self._running:
            await self._interruptible_sleep(HEARTBEAT_INTERVAL_SECONDS)

            async with self._state_mutex.reader_lock:
                broker = self._broker

            if broker:
                heartbeat = BundleData(
                    type=BundleType.BROKER_REQUEST,
                    source=self._node_id,
                    destination=broker,
                    node_type=self._node_type,
                )

                await self._send_and_check(bundles=[heartbeat])
                LOG.debug(f"Sent heartbeat to broker {broker}")
            else:
                LOG.debug("No broker associated yet, skipping heartbeat")

        LOG.info("Periodic heartbeat stopped")
