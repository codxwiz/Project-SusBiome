import xarray as xr

ds = xr.open_dataset(
    "data/raw/era5/extracted/data_stream-oper_stepType-instant.nc"
)

print(ds)
print("\nVARIABLES:")
print(ds.variables)