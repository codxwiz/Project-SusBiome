from pathlib import Path
import zipfile
import shutil

# ==========================================================
# PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data/bronze/gdelt/raw"
EXTRACT_DIR = PROJECT_ROOT / "data/bronze/gdelt/extracted"
PROCESSED_DIR = PROJECT_ROOT / "data/bronze/gdelt/raw_processed"

EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================================
# CONFIG
# ==========================================================

FILES_PER_RUN = 25

# ==========================================================
# FIND ZIP FILES
# ==========================================================

zip_files = sorted(RAW_DIR.glob("*.zip"))

zip_files = zip_files[:FILES_PER_RUN]

print("=" * 60)
print("GDELT Extraction Batch")
print("=" * 60)
print(f"ZIP files found : {len(zip_files)}")

success = 0
failed = 0

# ==========================================================
# EXTRACT
# ==========================================================

for zip_path in zip_files:

    print(f"\nExtracting: {zip_path.name}")

    try:

        with zipfile.ZipFile(zip_path, "r") as archive:

            archive.extractall(EXTRACT_DIR)

        shutil.move(
            zip_path,
            PROCESSED_DIR / zip_path.name
        )

        success += 1

        print("✓ Extracted")

    except Exception as e:

        failed += 1

        print("✗ Failed")

        print(e)

print()

print("=" * 60)
print("EXTRACTION COMPLETE")
print("=" * 60)

print(f"Success : {success}")
print(f"Failed  : {failed}")

print()
print(f"Extracted files : {len(list(EXTRACT_DIR.glob('*.CSV')))}")