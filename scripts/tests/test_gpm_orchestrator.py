"""
============================================================
Test GPM Daily Orchestrator
============================================================
"""

from datetime import datetime
from pathlib import Path

from scripts.sources.common.auth import AuthManager
from scripts.sources.common.downloader import Downloader
from scripts.sources.common.manifest import ManifestCatalog
from scripts.sources.common.storage import Storage

from scripts.sources.nasa.client import NASAClient
from scripts.sources.nasa.discovery import NASAEarthdataDiscovery
from scripts.sources.nasa.gpm.ingest_gpm import GPMIngestor
from scripts.sources.nasa.gpm.orchestrator import GPMDailyOrchestrator
from scripts.sources.nasa.models import Product


storage = Storage(
    root=Path("data")
)

manifest = ManifestCatalog(
    manifest_path=Path("data/manifest.parquet")
)

auth = AuthManager()

client = NASAClient(
    auth=auth
)

discovery = NASAEarthdataDiscovery(
    client=client
)

downloader = Downloader(
    auth=auth,
    storage=storage,
)

ingestor = GPMIngestor(
    discovery=discovery,
    downloader=downloader,
    storage=storage,
    manifest=manifest,
)

orchestrator = GPMDailyOrchestrator(
    ingestor=ingestor,
)

product = Product(
    provider="NASA",
    product="GPM_3IMERGDF",
    version="07",
    description="GPM IMERG Daily Final",
    file_extension=".nc4",
)

print()
print("=" * 60)
print("STARTING GPM DAILY ORCHESTRATION TEST")
print("=" * 60)
print()

with orchestrator:

    orchestrator.run(

        product=product,

        start_date=datetime(
            2024,
            7,
            1,
        ),

        end_date=datetime(
            2024,
            7,
            1,
        ),

    )

print()
print("=" * 60)
print("ORCHESTRATOR TEST COMPLETE")
print("=" * 60)
print()

client.close()