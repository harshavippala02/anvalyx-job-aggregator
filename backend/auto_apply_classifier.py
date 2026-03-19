from urllib.parse import urlparse


SUPPORTED_AUTO_APPLY_TYPES = {"greenhouse", "lever"}


def detect_apply_type(url: str | None, source: str | None = None) -> str:
    source_value = (source or "").strip().lower()

    if source_value == "linkedin":
        return "linkedin"

    if not url:
        return "missing"

    try:
        parsed = urlparse(url.strip())
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
        full = f"{host}{path}"
    except Exception:
        return "other"

    if "linkedin.com" in host:
        return "linkedin"

    if "greenhouse.io" in full or "boards.greenhouse.io" in full:
        return "greenhouse"

    if "lever.co" in full or "jobs.lever.co" in full:
        return "lever"

    if "myworkdayjobs.com" in full or "workday" in full:
        return "workday"

    if "ashbyhq.com" in full:
        return "ashby"

    if "smartrecruiters.com" in full:
        return "smartrecruiters"

    if "bamboohr.com" in full:
        return "bamboohr"

    if "icims.com" in full:
        return "icims"

    return "other"


def classify_auto_apply_status(source: str | None, url: str | None, current_status: str | None) -> dict:
    source_value = (source or "").strip().lower()
    current = (current_status or "new").strip().lower()
    apply_type = detect_apply_type(url, source_value)

    if source_value == "linkedin":
        return {
            "apply_type": "linkedin",
            "eligible": False,
            "status": current,
            "reason": "linkedin_excluded",
        }

    if not url:
        return {
            "apply_type": "missing",
            "eligible": False,
            "status": "manual_required",
            "reason": "missing_apply_url",
        }

    if apply_type in SUPPORTED_AUTO_APPLY_TYPES:
        return {
            "apply_type": apply_type,
            "eligible": True,
            "status": "auto_ready",
            "reason": f"{apply_type}_supported",
        }

    return {
        "apply_type": apply_type,
        "eligible": False,
        "status": "manual_required",
        "reason": f"{apply_type}_not_supported",
    }