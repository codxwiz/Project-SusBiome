from netCDF4 import Dataset

file = Dataset("data/raw/era5/test_era5.nc")

print(file)
print(file.variables.keys())