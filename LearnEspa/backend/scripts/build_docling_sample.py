from __future__ import annotations

import argparse
from pathlib import Path

from pypdf import PdfReader, PdfWriter


SAMPLE_PAGES = (10, 18, 19, 24, 29)


def build_sample(source: Path, output: Path) -> Path:
    reader = PdfReader(source)
    writer = PdfWriter()
    for page_number in SAMPLE_PAGES:
        if page_number > len(reader.pages):
            raise ValueError(f"源 PDF 只有 {len(reader.pages)} 页，无法提取第 {page_number} 页")
        writer.add_page(reader.pages[page_number - 1])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        writer.write(stream)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="构建五页 Docling 本地验证样本")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_sample(args.source, args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
