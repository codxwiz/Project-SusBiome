import requests

from scripts.sources.common.auth import AuthManager

URL = (
    "https://data.gesdisc.earthdata.nasa.gov/data/"
    "GPM_L3/GPM_3IMERGDF.07/2024/07/"
    "3B-DAY.MS.MRG.3IMERG.20240701-"
    "S000000-E235959.V07B.nc4"
)

print("=" * 60)
print("TEST 1")
print("AuthManager Session")
print("=" * 60)

auth = AuthManager()

session = auth.session("NASA")

print(session.headers)

response = session.get(
    URL,
    stream=True,
)

print("Status:", response.status_code)
print("Final URL:", response.url)

print()

print("=" * 60)
print("TEST 2")
print("Remove Authorization Header")
print("=" * 60)

session.headers.pop("Authorization", None)

print(session.headers)

response = session.get(
    URL,
    stream=True,
)

print("Status:", response.status_code)
print("Final URL:", response.url)