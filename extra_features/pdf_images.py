"""Convert PDF pages to image files."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(frozen=True)
class RenderedPage:
    page_number: int
    image_path: Path
    width: int
    height: int


def pdf_to_images(
    pdf_path: Path,
    output_dir: Path,
    *,
    dpi: int = 200,
    image_format: str = "png",
    prefix: str | None = None,
) -> list[RenderedPage]:
    if dpi <= 0:
        raise ValueError("dpi must be greater than 0")

    image_format = image_format.lower().lstrip(".")
    if image_format not in {"png", "jpg", "jpeg"}:
        raise ValueError("image_format must be png, jpg, or jpeg")

    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = prefix or pdf_path.stem
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    rendered: list[RenderedPage] = []

    with fitz.open(pdf_path) as document:
        for index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image_path = output_dir / f"{stem}_page_{index:04d}.{image_format}"
            pixmap.save(image_path)
            rendered.append(
                RenderedPage(
                    page_number=index,
                    image_path=image_path,
                    width=pixmap.width,
                    height=pixmap.height,
                )
            )

    return rendered


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render each PDF page as one image.")
    parser.add_argument("pdf", type=Path, help="PDF file to render.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("pdf_images"),
        help="Directory where page images will be written. Default: pdf_images.",
    )
    parser.add_argument("--dpi", type=int, default=200, help="Render DPI. Default: 200.")
    parser.add_argument(
        "--format",
        default="png",
        choices=["png", "jpg", "jpeg"],
        help="Image format. Default: png.",
    )
    parser.add_argument(
        "--prefix",
        help="Output filename prefix. Default: PDF filename stem.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rendered = pdf_to_images(
        args.pdf,
        args.output_dir,
        dpi=args.dpi,
        image_format=args.format,
        prefix=args.prefix,
    )

    for page in rendered:
        print(
            f"page={page.page_number} path={page.image_path} "
            f"size={page.width}x{page.height}"
        )
    print(f"rendered {len(rendered)} page(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
