#!/usr/bin/env python3
"""Upload Lemieux artifacts (docx, pdf, json, yaml, md, png) to a Google Drive folder.

This is the framework's portable Drive uploader — it does NOT depend on Claude.ai's
Drive integration or any sandbox auth. You bring your own Google OAuth credentials
once; subsequent runs use a cached token.

Quick start (one-time setup, ~5 min):

  1. Go to https://console.cloud.google.com/, create a project (or pick one).
  2. APIs & Services → Library → enable "Google Drive API".
  3. APIs & Services → Credentials → Create Credentials → OAuth client ID.
     Application type: **Desktop app**. Name: anything (e.g. "Lemieux uploader").
     Click "Download JSON" → save the file as `~/.lemieux/google-credentials.json`
     (or set LEMIEUX_GOOGLE_CREDS=/path/to/credentials.json).
  4. Install deps: `pip install google-api-python-client google-auth-oauthlib`
  5. First run will open a browser for consent. After that, the cached token at
     `~/.lemieux/google-token.json` (refreshable) handles auth silently.

Usage:

  # Upload one or more files to a default folder ("Lemieux Hockey Analytics")
  python tools/push_to_drive.py FILE [FILE ...]

  # Or specify the folder explicitly
  python tools/push_to_drive.py --folder "Habs Round 1 2026" examples/habs_round1_2026/*.docx

  # Re-upload (overwrite by name) instead of creating duplicates
  python tools/push_to_drive.py --overwrite path/to/file.docx

  # Dry-run — print what would happen without writing
  python tools/push_to_drive.py --dry-run examples/habs_round1_2026/*.docx

The script creates the folder if it doesn't exist, uploads each file with the
correct MIME type (so docx stays a Word document — not auto-converted to a
Google Doc), and prints the shareable Drive URL for each uploaded file.
"""
from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    sys.stderr.write(
        "Missing Google API client. Install with:\n"
        "    pip install google-api-python-client google-auth-oauthlib\n"
    )
    sys.exit(1)

# Drive scope: write to files this app creates. Sufficient for upload, doesn't
# grant access to the user's existing files outside what we create.
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

DEFAULT_CREDS_PATH = Path.home() / ".lemieux" / "google-credentials.json"
DEFAULT_TOKEN_PATH = Path.home() / ".lemieux" / "google-token.json"
DEFAULT_FOLDER = "Lemieux Hockey Analytics"

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def get_service(creds_path: Path, token_path: Path):
    """Return an authenticated Drive v3 service."""
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                sys.stderr.write(
                    f"\nNo Google OAuth credentials at {creds_path}\n"
                    "Follow the one-time setup at the top of this file (or pass --creds PATH).\n"
                )
                sys.exit(2)
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("drive", "v3", credentials=creds)


def find_or_create_folder(service, name: str) -> str:
    """Return the Drive folder ID for `name`, creating it if missing."""
    safe_name = name.replace("'", "\\'")
    q = (
        f"name = '{safe_name}' and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    resp = service.files().list(q=q, spaces="drive", fields="files(id, name)").execute()
    items = resp.get("files", [])
    if items:
        return items[0]["id"]
    body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    folder = service.files().create(body=body, fields="id").execute()
    return folder["id"]


def make_anyone_with_link(service, file_id: str) -> None:
    """Grant 'anyone with the link can view' permission on a file or folder."""
    try:
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()
    except Exception as e:  # noqa: BLE001
        # Permission already exists or domain policy blocks — surface but don't fail.
        sys.stderr.write(f"   (note: could not set anyone-with-link on {file_id}: {e})\n")


def find_file_in_folder(service, folder_id: str, name: str) -> str | None:
    safe_name = name.replace("'", "\\'")
    q = f"name = '{safe_name}' and '{folder_id}' in parents and trashed = false"
    resp = service.files().list(q=q, spaces="drive", fields="files(id, name)").execute()
    items = resp.get("files", [])
    return items[0]["id"] if items else None


def guess_mime(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return DOCX_MIME
    mt, _ = mimetypes.guess_type(str(path))
    return mt or "application/octet-stream"


def upload_file(service, folder_id: str, path: Path, overwrite: bool, dry_run: bool,
                public: bool = False) -> dict:
    name = path.name
    mime = guess_mime(path)
    existing_id = find_file_in_folder(service, folder_id, name)
    if existing_id and not overwrite:
        if public:
            make_anyone_with_link(service, existing_id)
        return {"status": "exists", "name": name, "id": existing_id,
                "webViewLink": f"https://drive.google.com/file/d/{existing_id}/view"}
    if dry_run:
        return {"status": "would_upload", "name": name, "size": path.stat().st_size}
    media = MediaFileUpload(str(path), mimetype=mime, resumable=True)
    # `supportsAllDrives` is harmless and forward-compatible with shared drives.
    # Critically: do NOT pass any conversion flag — the v3 default is no conversion,
    # so docx stays docx in Drive. (This was a bug in v0.1: we were getting
    # auto-converted Google Docs because the legacy default differs.)
    if existing_id and overwrite:
        result = (
            service.files()
            .update(fileId=existing_id, media_body=media,
                    fields="id, name, webViewLink, mimeType",
                    supportsAllDrives=True)
            .execute()
        )
        result["status"] = "updated"
    else:
        body = {"name": name, "parents": [folder_id], "mimeType": mime}
        result = (
            service.files()
            .create(body=body, media_body=media,
                    fields="id, name, webViewLink, mimeType",
                    supportsAllDrives=True)
            .execute()
        )
        result["status"] = "uploaded"
    if public:
        make_anyone_with_link(service, result["id"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Lemieux artifacts to Google Drive.")
    parser.add_argument("files", nargs="+", type=Path,
                        help="One or more files to upload. Globs work via your shell.")
    parser.add_argument("--folder", default=DEFAULT_FOLDER,
                        help=f"Target Drive folder name (created if missing). Default: {DEFAULT_FOLDER!r}")
    parser.add_argument("--creds", type=Path,
                        default=Path(os.environ.get("LEMIEUX_GOOGLE_CREDS") or DEFAULT_CREDS_PATH),
                        help="Path to Google OAuth client_secret JSON.")
    parser.add_argument("--token", type=Path, default=DEFAULT_TOKEN_PATH,
                        help="Path to cache the user token. Default: ~/.lemieux/google-token.json")
    parser.add_argument("--overwrite", action="store_true",
                        help="If a file with the same name exists in the folder, replace it.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without uploading.")
    parser.add_argument("--public", action="store_true",
                        help="After upload, set 'anyone with the link can view' on each file.")
    parser.add_argument("--folder-public", action="store_true",
                        help="Also make the target folder itself publicly browsable (implies --public).")
    args = parser.parse_args()
    if args.folder_public:
        args.public = True

    missing = [p for p in args.files if not p.exists()]
    if missing:
        sys.stderr.write(f"Files not found: {[str(p) for p in missing]}\n")
        return 1

    service = get_service(args.creds, args.token)
    folder_id = find_or_create_folder(service, args.folder)
    if args.folder_public:
        make_anyone_with_link(service, folder_id)
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
    visibility = " · public link enabled" if args.folder_public else ""
    print(f"📁 Drive folder: {args.folder!r}  (id: {folder_id}){visibility}")
    print(f"   {folder_url}")
    print()

    failures = 0
    public_links = []
    for path in args.files:
        try:
            result = upload_file(service, folder_id, path, args.overwrite, args.dry_run, args.public)
            status = result["status"]
            symbol = {"uploaded": "✓", "updated": "↻", "exists": "·",
                      "would_upload": "?"}.get(status, "?")
            link = result.get("webViewLink") or ""
            tag = " 🔓" if args.public and status in {"uploaded", "updated", "exists"} else ""
            print(f"   {symbol} [{status:14}] {path.name:55}{tag} {link}")
            if args.public and link:
                public_links.append((path.name, link))
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"   ✗ [error         ] {path.name}: {e}")

    if args.public and public_links:
        print()
        print("=== PUBLIC LINKS (anyone with the link can view) ===")
        for name, link in public_links:
            print(f"  {name}\n    {link}")
        if args.folder_public:
            print(f"\n  Folder: {folder_url}")

    if failures:
        print(f"\n{failures} file(s) failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
