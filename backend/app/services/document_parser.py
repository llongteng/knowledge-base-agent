from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".csv"}


@dataclass
class ParsedSegment:
    content: str
    page_number: Optional[int] = None
    paragraph_index: Optional[int] = None
    title_path: Optional[str] = None
    row_number: Optional[int] = None


def parse_bytes(filename: str, content: bytes, content_type: str | None = None) -> list[ParsedSegment]:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("暂不支持该文件格式，请上传 PDF、TXT、Markdown 或 CSV")

    if len(content) > 10 * 1024 * 1024:
        raise ValueError("文件超过 10MB，请拆分后上传")

    if extension == ".csv":
        return _parse_csv(content)
    if extension in {".md", ".markdown"}:
        return _parse_markdown(_decode_text(content))
    if extension == ".pdf":
        return _parse_pdf(content)
    return _parse_plain_text(_decode_text(content))


def _decode_text(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("文件编码无法识别，请另存为 UTF-8 后重新上传") from exc


def _parse_plain_text(text: str) -> list[ParsedSegment]:
    paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
    return [
        ParsedSegment(content=paragraph, paragraph_index=index)
        for index, paragraph in enumerate(paragraphs, start=1)
    ]


def _parse_markdown(text: str) -> list[ParsedSegment]:
    segments: list[ParsedSegment] = []
    headings: list[str] = []
    paragraph_index = 1
    buffer: list[str] = []

    def flush() -> None:
        nonlocal paragraph_index, buffer
        content = "\n".join(buffer).strip()
        if content:
            segments.append(
                ParsedSegment(
                    content=content,
                    paragraph_index=paragraph_index,
                    title_path=" > ".join(headings) if headings else None,
                )
            )
            paragraph_index += 1
        buffer = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue
        if line.startswith("#"):
            flush()
            level = len(line) - len(line.lstrip("#"))
            title = line[level:].strip()
            headings = headings[: level - 1] + [title]
            continue
        buffer.append(line)
    flush()
    return segments


def _parse_csv(content: bytes) -> list[ParsedSegment]:
    text = _decode_text(content)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV 需要包含表头和至少一行数据")

    segments: list[ParsedSegment] = []
    for row_index, row in enumerate(reader, start=2):
        values = [f"{key}: {value}" for key, value in row.items() if key and value]
        if values:
            segments.append(ParsedSegment(content="; ".join(values), row_number=row_index))

    if not segments:
        raise ValueError("CSV 需要包含表头和至少一行数据")
    return segments


def _parse_pdf(content: bytes) -> list[ParsedSegment]:
    try:
        import pdfplumber  # type: ignore
    except ImportError as exc:
        raise ValueError("当前环境缺少 pdfplumber，请安装后解析 PDF") from exc

    segments: list[ParsedSegment] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for paragraph_index, paragraph in enumerate(
                [part.strip() for part in text.splitlines() if part.strip()],
                start=1,
            ):
                segments.append(
                    ParsedSegment(
                        content=paragraph,
                        page_number=page_index,
                        paragraph_index=paragraph_index,
                    )
                )
    if not segments:
        raise ValueError("暂不支持扫描版 PDF，请上传可复制文本的 PDF")
    return segments
