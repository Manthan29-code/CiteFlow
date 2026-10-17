import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 1. Load environment variables from .env
root_dir = Path(__file__).resolve().parent
load_dotenv(root_dir / ".env")

private_key = os.getenv("IMAGEKIT_PRIVATE_KEY")
url_endpoint = os.getenv("IMAGEKIT_URL_ENDPOINT")
base_folder = os.getenv("IMAGEKIT_BASE_FOLDER", "/citegen_test")

print("=" * 60)
print(" ImageKit API Key & Upload / Deletion Test")
print("=" * 60)

if not private_key:
    print("[ERROR] IMAGEKIT_PRIVATE_KEY is missing in your .env file!")
    sys.exit(1)

if not url_endpoint:
    print("[ERROR] IMAGEKIT_URL_ENDPOINT is missing in your .env file!")
    sys.exit(1)

print(f"URL Endpoint: {url_endpoint}")
print(f"Base Folder:  {base_folder}")
print(f"Private Key:  {private_key[:6]}...{private_key[-4:] if len(private_key) > 10 else ''}")
print("-" * 60)

# 2. Initialize ImageKit SDK
try:
    from imagekitio import ImageKit
except ImportError:
    print("[ERROR] 'imagekitio' is not installed. Please run: pip install imagekitio")
    sys.exit(1)

imagekit = ImageKit(private_key=private_key)

# 3. Choose a sample PDF
sample_dir = root_dir / "samples"
sample_files = list(sample_dir.glob("*.pdf"))

if not sample_files:
    print(f"[ERROR] No PDF files found in {sample_dir}")
    sys.exit(1)

# Pick the smallest sample PDF by default for quick upload
sample_pdf = min(sample_files, key=lambda f: f.stat().st_size)
print(f"Selected sample PDF: {sample_pdf.name} ({sample_pdf.stat().st_size / 1024:.1f} KB)")

# 4. Upload to ImageKit
print("\n[1/3] Uploading file to ImageKit...")
try:
    with open(sample_pdf, "rb") as f:
        response = imagekit.files.upload(
            file=f,
            file_name=sample_pdf.name,
            folder=base_folder,
            is_private_file=True,
            use_unique_file_name=True,
        )

    file_id = getattr(response, "file_id", getattr(response, "fileId", None))
    file_path = getattr(response, "file_path", getattr(response, "filePath", None))
    raw_url = getattr(response, "url", None)

    print("\n[SUCCESS] File uploaded successfully!")
    print(f"  - File ID:   {file_id}")
    print(f"  - File Path: {file_path}")
    print(f"  - Raw URL:   {raw_url}")

except Exception as e:
    print(f"\n[UPLOAD FAILED] Error: {e}")
    sys.exit(1)

# 5. Generate Signed URL for private file access
print("\n[2/3] Generating Signed URL (valid for 5 minutes)...")
try:
    signed_url = imagekit.helper.build_url(
        url_endpoint=url_endpoint,
        src=file_path,
        signed=True,
        expires_in=300,
    )
    print("[SUCCESS] Signed URL created:")
    print(f"  {signed_url}")
    print("  (You can open this URL in your browser to verify it displays your PDF)")
except Exception as e:
    print(f"[WARNING] Failed to generate signed URL: {e}")

# 6. Interactive Deletion
print("\n[3/3] Deletion Option")
choice = input(f"Do you want to delete this test file ({file_id}) from ImageKit now? (y/n): ").strip().lower()

if choice in ("y", "yes"):
    try:
        imagekit.files.delete(file_id=file_id)
        print(f"[DELETED] File '{file_id}' successfully removed from ImageKit.")
    except Exception as e:
        print(f"[DELETE FAILED] Error deleting file: {e}")
else:
    print(f"[KEPT] File '{file_id}' remains in your ImageKit media library under '{base_folder}'.")

print("\nDone!")
