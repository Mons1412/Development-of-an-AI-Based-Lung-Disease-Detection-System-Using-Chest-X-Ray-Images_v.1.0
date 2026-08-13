# TASK 06 — Manual PDF Visual Checklist

## Preconditions

- Start the local FastAPI application and open `/demo` in a current desktop browser.
- Allow browser popups for the local application.
- Use a valid local JPG, JPEG or PNG; do not use patient-identifying images for this check.

## Checks

| # | Action | Expected result |
| --- | --- | --- |
| 1 | Open `/demo` before selecting and analyzing an image. | `Xuất report PDF` is not visible or actionable. |
| 2 | Analyze one valid image successfully. | The export button appears beside the result actions only after the result is visible. |
| 3 | Click `Xuất report PDF`. | A report preview opens in a new browser window/tab; no download file is created by the server. |
| 4 | Inspect the preview at 100% zoom. | Vietnamese characters render correctly; NTTU branding, project title, analysis time, sanitized filename, Vietnamese/API class labels, three probabilities, model version and processing time are readable. |
| 5 | Inspect the reference section. | It displays `Nội dung chuyên môn đang chờ duyệt`, source IDs and disclaimer; it does not contain medicine, dosage or treatment advice. |
| 6 | Inspect the report image area. | It states that the original image is not attached. No selected image preview or base64 image is present. |
| 7 | Click `In / Lưu dưới dạng PDF`, select the browser's Save as PDF destination, and inspect the generated user-selected file. | The printed PDF has no blue preview background or print button, has no clipped table/footer, and retains Vietnamese text/logo. The browser/user chooses the save location. |
| 8 | Close preview, click export again for the same result. | A fresh, independent preview opens and still contains the same current result. |
| 9 | Select a different image or click reset before exporting. | The export action disappears; an older result cannot be exported. |
| 10 | Cause a failed prediction (for example stop the local model service) after a previously successful result. | Error state is shown and export is unavailable. |
| 11 | Block popups temporarily, then click export. | The demo explains that a popup must be allowed; no partial report stays open. |

## Manual approval record

- Browser/version: ______________________________
- Windows printer/Save as PDF used: ______________________________
- Desktop/tablet/mobile visual review: PASS / FAIL
- Print-layout review: PASS / FAIL
- Reviewer/date: ______________________________
- Notes: ______________________________
