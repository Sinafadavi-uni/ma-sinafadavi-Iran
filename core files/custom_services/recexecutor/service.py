"""REC Executor service for CORE emulator."""

from typing import Any
from core.services.base import CoreService, ServiceMode


class RecExecutorService(CoreService):
    """REC Executor - Executes WASM jobs."""

    name: str = "RECExecutor"
    group: str = "REC"
    executables: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ("DTN7GO",)
    dirs: tuple[str, ...] = ()
    files: tuple[str, ...] = ("recexecutor.sh",)
    startup: tuple[str, ...] = ("bash recexecutor.sh",)
    validate: tuple[str, ...] = ("pgrep -f 'rec.run_dtn.*executor'",)
    shutdown: tuple[str, ...] = ("pkill -9 -f 'rec.run_dtn.*executor'",)
    validation_mode: ServiceMode = ServiceMode.BLOCKING
    default_configs: tuple[str, ...] = ()
    modes: dict[str, dict[str, str]] = {}

    @classmethod
    def data(cls) -> dict[str, Any]:
        return {}

    @classmethod
    def get_text_template(cls, name: str) -> str:
        if name == "recexecutor.sh":
            return """#!/bin/bash
cd "$(dirname "$0")"
STORAGE="/tmp/rec_executor_${node.name}"
mkdir -p "$STORAGE"
echo "Starting REC Executor: ${node.name}"

# Set Python path to find REC module and dependencies
export PYTHONPATH="/home/sina/Desktop/Related Work/New-Pr-UCP/ma-sinafadavi:/home/sina/.local/lib/python3.12/site-packages:$PYTHONPATH"

for i in {1..30}; do
    [ -S "/tmp/${node.name}.sock" ] && break
    [ $i -eq 30 ] && echo "ERROR: No DTN socket" && exit 1
    sleep 1
done
python3 -m rec.run_dtn --id "dtn://${node.name}/" --socket "/tmp/${node.name}.sock" executor "$STORAGE" > /tmp/rec_executor_${node.name}.log 2>&1 &
"""
        return ""
