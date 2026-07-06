import hashlib
from fastapi import HTTPException, UploadFile

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_FILE_EXTS = {".txt", ".json"}
MAX_IMAGES = 5
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_FILE_SIZE = 5 * 1024 * 1024    # 5 MB
MAX_TEXT_LENGTH = 20000
VALID_LOCALES = {"zh-CN", "zh-TW", "en"}


async def validate_analyze_request(
    images: list[UploadFile] | None,
    text: str | None,
    file: UploadFile | None,
    locale: str = "zh-CN",
) -> tuple[str, bytes, str]:
    provided = sum(1 for x in [
        images is not None and len(images) > 0,
        text is not None and text.strip() != "",
        file is not None,
    ] if x)

    if provided == 0:
        raise HTTPException(400, detail={"error": "empty_input", "detail": "请提供聊天截图、文本或文件"})
    if provided > 1:
        raise HTTPException(400, detail={"error": "ambiguous_input", "detail": "请只选择一种输入方式"})

    if locale not in VALID_LOCALES:
        locale = "zh-CN"

    if images is not None and len(images) > 0:
        if len(images) > MAX_IMAGES:
            raise HTTPException(400, detail={"error": "too_many_images", "detail": f"最多上传 {MAX_IMAGES} 张图片"})
        contents = []
        for img in images:
            if img.content_type not in ALLOWED_IMAGE_TYPES:
                raise HTTPException(415, detail={"error": "unsupported_format", "detail": f"不支持的图片格式: {img.content_type}"})
            data = await img.read()
            if len(data) > MAX_IMAGE_SIZE:
                raise HTTPException(413, detail={"error": "file_too_large", "detail": "单张图片不超过 10MB"})
            contents.append(data)
        return ("image", b"||IMG_SEP||".join(contents), locale)

    if text is not None and text.strip():
        if len(text) > MAX_TEXT_LENGTH:
            raise HTTPException(413, detail={"error": "text_too_long", "detail": f"文本不超过 {MAX_TEXT_LENGTH} 字符"})
        return ("text", text.encode("utf-8"), locale)

    if file is not None:
        filename = file.filename or ""
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_FILE_EXTS:
            raise HTTPException(415, detail={"error": "unsupported_format", "detail": f"不支持的文件格式: {ext}"})
        data = await file.read()
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(413, detail={"error": "file_too_large", "detail": "文件不超过 5MB"})
        return ("file", data, locale)

    raise HTTPException(400, detail={"error": "empty_input", "detail": "请提供有效的聊天内容"})


def hash_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
