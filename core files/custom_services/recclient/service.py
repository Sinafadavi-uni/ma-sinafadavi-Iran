"""REC Client service for CORE emulator."""

from typing import Any
from core.services.base import CoreService, ServiceMode


class RecClientService(CoreService):
    """REC Client - Submits jobs and queries system."""

    name: str = "RECClient"
    group: str = "REC"
    executables: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ("DTN7GO",)
    dirs: tuple[str, ...] = ()
    files: tuple[str, ...] = ("recclient.sh",)
    startup: tuple[str, ...] = ("bash recclient.sh",)
    validate: tuple[str, ...] = ("pgrep -f 'rec.run_dtn.*client'",)
    shutdown: tuple[str, ...] = ("pkill -9 -f 'rec.run_dtn.*client'",)
    validation_mode: ServiceMode = ServiceMode.BLOCKING
    default_configs: tuple[str, ...] = ()
    modes: dict[str, dict[str, str]] = {}

    @classmethod
    def data(cls) -> dict[str, Any]:
        return {}

    @classmethod
    def get_text_template(cls, name: str) -> str:
        if name == "recclient.sh":
            return """#!/bin/bash
cd "$(dirname "$0")"
CONTEXT="/tmp/rec_client_${node.name}_context.toml"
RESULTS="/tmp/rec_client_${node.name}_results"
mkdir -p "$RESULTS"
echo "Starting REC Client: ${node.name}"

# Set Python path to find REC module and dependencies
export PYTHONPATH="/home/sina/Desktop/Related Work/New-Pr-UCP/ma-sinafadavi:/home/sina/.local/lib/python3.12/site-packages:$PYTHONPATH"

for i in {1..30}; do
    [ -S "/tmp/${node.name}.sock" ] && break
    [ $i -eq 30 ] && echo "ERROR: No DTN socket" && exit 1
    sleep 1
done
python3 -m rec.run_dtn --id "dtn://${node.name}/" --socket "/tmp/${node.name}.sock" client --context_file "$CONTEXT" --results_directory "$RESULTS" > /tmp/rec_client_${node.name}.log 2>&1 &
"""
        return ""
