from datetime import datetime

from scripts.sources.nasa.discovery import NASAEarthdataDiscovery
from scripts.sources.nasa.models import Product
from pathlib import Path

from scripts.sources.common.auth import AuthManager
from scripts.sources.common.storage import Storage
from scripts.sources.common.downloader import Downloader

product = Product(
    provider="NASA",
    product="GPM_3IMERGDF",
    version="07",
    description="GPM IMERG Final Run V07",
    file_extension=".nc4",
)

discovery = NASAEarthdataDiscovery()

try:

    granules = discovery.discover(
        product=product,
        start=datetime(2024, 7, 1),
        end=datetime(2024, 7, 2),
    )

    print(f"Granules found: {len(granules)}")

    if granules:
        first = granules[0]

        print(f"Granule ID : {first.granule_id}")
        print(f"Start      : {first.start_time}")
        print(f"End        : {first.end_time}")
        print(f"URL        : {first.url}")
        auth = AuthManager()

    storage = Storage(
        Path("data")
    )

    downloader = Downloader(
        auth=auth,
        storage=storage,
    )

    result = downloader.download(
        provider="NASA",
        url=first.url,
        destination=Path(
            "bronze/nasa/gpm/sample/"
            "3B-DAY.MS.MRG.3IMERG.20240701.V07B.nc4"
        ),
    )

    print("\nDownload Result")
    print("----------------")
    print(result)

finally:

    discovery.close()