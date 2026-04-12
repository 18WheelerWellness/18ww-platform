import re
import io
from pathlib import Path

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ===== CONFIG =====
SHEET_ID = "1fnSGKqatQlyl5ZIeHHx66Bsud4SCX4wDa32ma73RsW0"
CLAIMS_PARENT_FOLDER_ID = "1lgG0jgiWiz4ui8Z1CIV04dv9xyCxztaw"
FMS_PARENT_FOLDER_ID = "1VE3CjdXrAH-Ic9v8sHcz5K4BygAD0Z6w"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IO_LAYER_DIR = Path(__file__).resolve().parent

DRIVE_CLIENT_SECRET_PATHS = [
    PROJECT_ROOT / "drive_oauth_client_secret.json",
    PROJECT_ROOT / "client_secret_drive.json",
    IO_LAYER_DIR / "drive_oauth_client_secret.json",
    Path("drive_oauth_client_secret.json").resolve(),
]

DRIVE_TOKEN_PATH = PROJECT_ROOT / "drive_token.json"

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]


def _find_existing_path(paths, label: str) -> str:
    for path in paths:
        if path.exists():
            return str(path)

    searched = "\n".join(str(p) for p in paths)
    raise FileNotFoundError(
        f"{label} was not found.\n"
        f"Checked these locations:\n{searched}"
    )


def _get_drive_client_secret_file():
    return _find_existing_path(
        DRIVE_CLIENT_SECRET_PATHS,
        "Drive OAuth client secret JSON (drive_oauth_client_secret.json)"
    )


def get_client():
    if "gcp_service_account" in st.secrets:
        creds = ServiceAccountCredentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=SHEETS_SCOPES,
        )
        return gspread.authorize(creds)

    local_creds_path = PROJECT_ROOT / "credentials.json"
    if local_creds_path.exists():
        creds = ServiceAccountCredentials.from_service_account_file(
            str(local_creds_path),
            scopes=SHEETS_SCOPES,
        )
        return gspread.authorize(creds)

    raise FileNotFoundError(
        "Google Sheets credentials were not found. "
        "Use Streamlit secrets with [gcp_service_account] in cloud, "
        "or place credentials.json in the project root for local use."
    )


def _get_drive_user_credentials():
    creds = None

    if DRIVE_TOKEN_PATH.exists():
        creds = UserCredentials.from_authorized_user_file(
            str(DRIVE_TOKEN_PATH),
            DRIVE_SCOPES,
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secret_file = _get_drive_client_secret_file()
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_file,
                DRIVE_SCOPES,
            )
            creds = flow.run_local_server(port=0)

        DRIVE_TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return creds


def _drive_service():
    creds = _get_drive_user_credentials()
    return build("drive", "v3", credentials=creds)


def _open_sheet():
    client = get_client()
    return client.open_by_key(SHEET_ID)


def sanitize_tab_name(name: str) -> str:
    name = str(name).strip()
    name = re.sub(r"[\[\]\*\?/\\:]", "_", name)
    if not name:
        name = "Company"
    return name[:90]


def company_tab_name(company_name: str, data_type: str) -> str:
    company = sanitize_tab_name(company_name)
    dtype = sanitize_tab_name(data_type)
    return f"{company}_{dtype}"[:99]


def save_df_to_company_tab(df: pd.DataFrame, company_name: str, data_type: str) -> str:
    spreadsheet = _open_sheet()
    tab_name = company_tab_name(company_name, data_type)

    try:
        ws = spreadsheet.worksheet(tab_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name,
            rows=max(len(df) + 10, 100),
            cols=max(len(df.columns) + 5, 20),
        )

    export_df = df.copy().fillna("")
    values = [export_df.columns.tolist()] + export_df.astype(str).values.tolist()
    ws.update("A1", values)

    return tab_name


def load_df_from_company_tab(company_name: str, data_type: str) -> pd.DataFrame:
    spreadsheet = _open_sheet()
    tab_name = company_tab_name(company_name, data_type)
    ws = spreadsheet.worksheet(tab_name)
    rows = ws.get_all_records()
    return pd.DataFrame(rows)


def load_company_rows_from_shared_tab(company_name, tab_name):
    client = get_client()
    sheet = client.open_by_key(SHEET_ID)

    try:
        worksheet = sheet.worksheet(tab_name)
    except Exception:
        return pd.DataFrame()

    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    if df.empty:
        return df

    company_col = None
    for col in ["company", "company_name"]:
        if col in df.columns:
            company_col = col
            break

    if company_col is None:
        return df

    if str(company_name).strip().upper() == "ALL":
        return df.reset_index(drop=True)

    return df[
        df[company_col].astype(str).str.strip() == str(company_name).strip()
    ].reset_index(drop=True)


def save_company_rows_to_shared_tab(df, company_name, tab_name):
    client = get_client()
    sheet = client.open_by_key(SHEET_ID)

    try:
        worksheet = sheet.worksheet(tab_name)
    except Exception:
        worksheet = sheet.add_worksheet(title=tab_name, rows="1000", cols="100")

    existing_data = worksheet.get_all_records()
    existing_df = pd.DataFrame(existing_data)

    df = df.copy()

    company_col = None
    for col in ["company", "company_name"]:
        if col in df.columns:
            company_col = col
            break

    if company_col is None:
        company_col = "company_name"
        df[company_col] = company_name

    if str(company_name).strip().upper() == "ALL":
        combined_df = df.copy()
    else:
        if not existing_df.empty:
            existing_company_col = None
            for col in ["company", "company_name"]:
                if col in existing_df.columns:
                    existing_company_col = col
                    break

            if existing_company_col is not None:
                existing_df = existing_df[
                    existing_df[existing_company_col].astype(str).str.strip()
                    != str(company_name).strip()
                ]

        combined_df = pd.concat([existing_df, df], ignore_index=True)

    worksheet.clear()
    if combined_df.empty:
        worksheet.update([df.columns.tolist()])
    else:
        worksheet.update(
            [combined_df.columns.tolist()] + combined_df.fillna("").astype(str).values.tolist()
        )


def _find_or_create_drive_folder(folder_name: str, parent_folder_id: str) -> str:
    service = _drive_service()

    safe_folder_name = str(folder_name).replace("'", "\\'")
    query = (
        "mimeType='application/vnd.google-apps.folder' "
        "and trashed=false "
        f"and name='{safe_folder_name}' "
        f"and '{parent_folder_id}' in parents"
    )

    results = service.files().list(
        q=query,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    files = results.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id],
    }

    folder = service.files().create(
        body=metadata,
        fields="id",
        supportsAllDrives=True,
    ).execute()

    return folder["id"]


def upload_claim_file(company_name: str, claim_number: str, uploaded_file, doc_type: str):
    service = _drive_service()

    company_folder_id = _find_or_create_drive_folder(
        company_name or "Unknown Company",
        CLAIMS_PARENT_FOLDER_ID,
    )

    claim_folder_name = f"claim_{claim_number}" if claim_number else "claim_unassigned"
    claim_folder_id = _find_or_create_drive_folder(claim_folder_name, company_folder_id)

    file_bytes = uploaded_file.getvalue()
    file_stream = io.BytesIO(file_bytes)

    content_type = getattr(uploaded_file, "type", None) or "application/octet-stream"
    original_name = getattr(uploaded_file, "name", "uploaded_file")
    drive_name = f"{doc_type}_{original_name}"

    file_metadata = {
        "name": drive_name,
        "parents": [claim_folder_id],
    }

    media = MediaIoBaseUpload(
        file_stream,
        mimetype=content_type,
        resumable=False,
    )

    created = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    ).execute()

    file_link = f"https://drive.google.com/file/d/{created['id']}/view"
    folder_link = f"https://drive.google.com/drive/folders/{claim_folder_id}"

    return file_link, folder_link


def upload_fms_image(company_name: str, driver_id: str, driver_name: str, session_tag: str, uploaded_file, view_name: str):
    service = _drive_service()

    company_folder_id = _find_or_create_drive_folder(
        company_name or "Unknown Company",
        FMS_PARENT_FOLDER_ID,
    )

    safe_driver_name = str(driver_name or "UnknownDriver").strip().replace("/", "_")
    safe_driver_id = str(driver_id or "").strip().replace("/", "_")

    if safe_driver_id:
        driver_folder_name = f"{safe_driver_name}_{safe_driver_id}"
    else:
        driver_folder_name = safe_driver_name

    driver_folder_id = _find_or_create_drive_folder(driver_folder_name, company_folder_id)

    safe_session_tag = str(session_tag or "Baseline").strip().replace("/", "_")
    assessment_folder_name = safe_session_tag
    assessment_folder_id = _find_or_create_drive_folder(assessment_folder_name, driver_folder_id)

    file_bytes = uploaded_file.getvalue()
    file_stream = io.BytesIO(file_bytes)

    content_type = getattr(uploaded_file, "type", None) or "application/octet-stream"
    original_name = getattr(uploaded_file, "name", f"{view_name}.jpg")
    drive_name = f"{view_name}_{original_name}"

    file_metadata = {
        "name": drive_name,
        "parents": [assessment_folder_id],
    }

    media = MediaIoBaseUpload(
        file_stream,
        mimetype=content_type,
        resumable=False,
    )

    created = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    ).execute()

    file_link = f"https://drive.google.com/file/d/{created['id']}/view"
    folder_link = f"https://drive.google.com/drive/folders/{assessment_folder_id}"

    return file_link, folder_link
