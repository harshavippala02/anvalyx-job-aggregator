from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.ats.resume_parser import parse_resume
from database import save_resume

router = APIRouter()

@router.post("/resume")
async def upload_resume(file: UploadFile = File(...)):
    if file.content_type not in [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain"
    ]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    file_bytes = await file.read()

    try:
        resume_text = parse_resume(file.filename, file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to parse resume")

    save_resume(resume_text)

    return {
        "status": "success",
        "message": "Resume uploaded successfully"
    }
