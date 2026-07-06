import pytest
import io
from fastapi import HTTPException, UploadFile
from validation import validate_analyze_request


class FakeUploadFile:
    def __init__(self, filename, content, content_type="text/plain"):
        self.filename = filename
        self.file = io.BytesIO(content.encode() if isinstance(content, str) else content)
        self.content_type = content_type
        self.size = len(content) if isinstance(content, bytes) else len(content.encode())

    async def read(self):
        return self.file.getvalue()


@pytest.mark.asyncio
async def test_empty_input_raises():
    with pytest.raises(HTTPException) as exc:
        await validate_analyze_request(None, "", None)
    assert exc.value.status_code == 400
    assert exc.value.detail["error"] == "empty_input"


@pytest.mark.asyncio
async def test_ambiguous_input_raises():
    img = FakeUploadFile("chat.png", b"fakeimage", "image/png")
    with pytest.raises(HTTPException) as exc:
        await validate_analyze_request([img], "also text", None)
    assert exc.value.status_code == 400
    assert exc.value.detail["error"] == "ambiguous_input"


@pytest.mark.asyncio
async def test_text_too_long_raises():
    long_text = "哈" * 20001
    with pytest.raises(HTTPException) as exc:
        await validate_analyze_request(None, long_text, None)
    assert exc.value.status_code == 413
    assert exc.value.detail["error"] == "text_too_long"


@pytest.mark.asyncio
async def test_image_count_too_many_raises():
    imgs = [FakeUploadFile(f"chat{i}.png", b"fake", "image/png") for i in range(6)]
    with pytest.raises(HTTPException) as exc:
        await validate_analyze_request(imgs, "", None)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_unsupported_image_format_raises():
    img = FakeUploadFile("chat.bmp", b"fake", "image/bmp")
    with pytest.raises(HTTPException) as exc:
        await validate_analyze_request([img], "", None)
    assert exc.value.status_code == 415


@pytest.mark.asyncio
async def test_valid_text_returns_parsed():
    input_type, content, locale = await validate_analyze_request(None, "你好，最近怎么样？", None)
    assert input_type == "text"
    assert "你好".encode() in content
    assert locale == "zh-CN"


@pytest.mark.asyncio
async def test_valid_images_return_parsed():
    img = FakeUploadFile("chat.png", b"fakeimage", "image/png")
    input_type, content, locale = await validate_analyze_request([img], "", None)
    assert input_type == "image"
    assert locale == "zh-CN"


@pytest.mark.asyncio
async def test_file_unsupported_format_raises():
    f = FakeUploadFile("chat.pdf", b"pdfcontent", "application/pdf")
    with pytest.raises(HTTPException) as exc:
        await validate_analyze_request(None, "", f)
    assert exc.value.status_code == 415


@pytest.mark.asyncio
async def test_valid_file_returns_parsed():
    f = FakeUploadFile("chat.txt", b"user1: hello\nuser2: hi")
    input_type, content, locale = await validate_analyze_request(None, "", f)
    assert input_type == "file"
