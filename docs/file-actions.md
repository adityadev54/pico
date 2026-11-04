# File actions

Pico works within the folders you approve on your computer. The phone sends the request; the companion performs the local action. Basic file actions do not call Muse, though delivery still needs the relay and a connected companion.

## Supported actions

- Find files by name, inspect supported content and transfer a selected file to the phone.
- Create or revise files in a write folder.
- Convert images to PDF, PNG, JPEG or WebP; extract PDF text into TXT or DOCX; convert DOCX to PDF.
- Merge PDFs, extract selected pages, rotate pages and add a text watermark.
- Create ZIP archives or extract a ZIP into an approved workspace.
- Move files to Pico trash and restore them. Trash access and permanent clearing require explicit permission and confirmation.
- Save a reviewed camera photo from the phone into a write folder.

These are supported operations, not arbitrary application automation or conversion between every format.

## Requirements

Choose read access for finding and inspecting files; choose write access for creating results. Destructive actions need their separate permission. Keep the computer awake and its companion connected. Complete the scoped review when prompted.

**LibreOffice is required only for DOCX → PDF.** On Mac, install LibreOffice.app in Applications or your user Applications folder. On Windows, use the standard LibreOffice installation under Program Files. An installation exposing `soffice` on PATH is also supported.

Source development environments additionally need Pillow for image conversion, pypdf for PDF operations and python-docx for DOCX output; use the project’s companion dependencies. Installing LibreOffice does not enable unsupported Office formats.

## Try it

1. Put a small sample file in an approved write folder.
2. Ask from the phone: “Convert lecture.docx to PDF”, “Convert photo.png to WebP”, or “Convert notes.pdf to TXT”. Use your actual filename.
3. Select the workspace if asked and approve the action.
4. Open the result beside the original and check its contents. Existing conversion outputs receive a numbered filename.

PDF → DOCX extracts text; it does not recreate the original page layout. Scanned PDFs need OCR, which is not included. Conversion inputs and outputs are capped at 1 MB; images at 16 megapixels; PDF operations at 100 pages. Locked PDFs are refused. Conversion leaves the source unchanged.

If an action fails, check the connection, folder access, file size and required converter. A missing converter or failed request does not mean the result was created.
