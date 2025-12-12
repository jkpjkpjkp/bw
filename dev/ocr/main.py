"""
OCR experimentation module for scanned books.

Tests multiple OCR engines on scanned book PDFs and compares results.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional
import json
import time


# OCR tools to experiment with (ordered by expected quality for scanned books)
OCR_TOOLS = [
    "pytesseract",      # Tesseract - baseline, widely used
    "easyocr",          # EasyOCR - easy to use, good accuracy
    "paddleocr",        # PaddleOCR - excellent for complex layouts
    "doctr",            # docTR - good for scanned documents
    "surya-ocr",        # Surya/Marker - modern, structured output
]


def install_ocr_tools():
    """Install OCR tools using uv."""
    packages = [
        "pytesseract",
        "easyocr",
        "paddleocr",
        "python-doctr[torch]",
        "surya-ocr",
        "pdf2image",  # For converting PDF pages to images
        "Pillow",
    ]
    for pkg in packages:
        print(f"Installing {pkg}...")
        subprocess.run([sys.executable, "-m", "uv", "pip", "install", pkg],
                      capture_output=True)


def pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 300) -> list[Path]:
    """Convert PDF pages to images for OCR processing."""
    from pdf2image import convert_from_path

    output_dir.mkdir(parents=True, exist_ok=True)
    images = convert_from_path(pdf_path, dpi=dpi)

    image_paths = []
    for i, image in enumerate(images):
        img_path = output_dir / f"page_{i:04d}.png"
        image.save(img_path, "PNG")
        image_paths.append(img_path)

    return image_paths


def ocr_tesseract(image_path: Path) -> dict:
    """Run Tesseract OCR on an image."""
    import pytesseract
    from PIL import Image

    start = time.time()
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    elapsed = time.time() - start

    return {
        "tool": "tesseract",
        "text": text,
        "time": elapsed,
        "chars": len(text),
    }


def ocr_easyocr(image_path: Path, reader=None) -> dict:
    """Run EasyOCR on an image."""
    import easyocr

    if reader is None:
        reader = easyocr.Reader(['en'])

    start = time.time()
    results = reader.readtext(str(image_path))
    text = "\n".join([r[1] for r in results])
    elapsed = time.time() - start

    return {
        "tool": "easyocr",
        "text": text,
        "time": elapsed,
        "chars": len(text),
        "confidence": sum(r[2] for r in results) / len(results) if results else 0,
    }


def ocr_paddleocr(image_path: Path, ocr=None) -> dict:
    """Run PaddleOCR on an image."""
    from paddleocr import PaddleOCR

    if ocr is None:
        ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)

    start = time.time()
    results = ocr.ocr(str(image_path), cls=True)

    text_parts = []
    confidences = []
    if results and results[0]:
        for line in results[0]:
            text_parts.append(line[1][0])
            confidences.append(line[1][1])

    text = "\n".join(text_parts)
    elapsed = time.time() - start

    return {
        "tool": "paddleocr",
        "text": text,
        "time": elapsed,
        "chars": len(text),
        "confidence": sum(confidences) / len(confidences) if confidences else 0,
    }


def ocr_doctr(image_path: Path, model=None) -> dict:
    """Run docTR OCR on an image."""
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor

    if model is None:
        model = ocr_predictor(pretrained=True)

    start = time.time()
    doc = DocumentFile.from_images(str(image_path))
    result = model(doc)

    text_parts = []
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                line_text = " ".join(word.value for word in line.words)
                text_parts.append(line_text)

    text = "\n".join(text_parts)
    elapsed = time.time() - start

    return {
        "tool": "doctr",
        "text": text,
        "time": elapsed,
        "chars": len(text),
    }


def ocr_surya(image_path: Path) -> dict:
    """Run Surya OCR on an image."""
    from surya.ocr import run_ocr
    from surya.model.detection.model import load_model as load_det_model
    from surya.model.detection.processor import load_processor as load_det_processor
    from surya.model.recognition.model import load_model as load_rec_model
    from surya.model.recognition.processor import load_processor as load_rec_processor
    from PIL import Image

    # Load models (these should be cached after first load)
    det_model = load_det_model()
    det_processor = load_det_processor()
    rec_model = load_rec_model()
    rec_processor = load_rec_processor()

    start = time.time()
    img = Image.open(image_path)

    results = run_ocr(
        [img],
        [["en"]],
        det_model,
        det_processor,
        rec_model,
        rec_processor,
    )

    text_parts = []
    for page in results:
        for line in page.text_lines:
            text_parts.append(line.text)

    text = "\n".join(text_parts)
    elapsed = time.time() - start

    return {
        "tool": "surya",
        "text": text,
        "time": elapsed,
        "chars": len(text),
    }


def compare_ocr_tools(
    image_path: Path,
    tools: Optional[list[str]] = None,
) -> list[dict]:
    """Run multiple OCR tools on an image and compare results."""
    if tools is None:
        tools = ["tesseract", "easyocr", "paddleocr", "doctr", "surya"]

    results = []

    for tool in tools:
        print(f"Running {tool}...")
        try:
            if tool == "tesseract":
                result = ocr_tesseract(image_path)
            elif tool == "easyocr":
                result = ocr_easyocr(image_path)
            elif tool == "paddleocr":
                result = ocr_paddleocr(image_path)
            elif tool == "doctr":
                result = ocr_doctr(image_path)
            elif tool == "surya":
                result = ocr_surya(image_path)
            else:
                print(f"Unknown tool: {tool}")
                continue

            results.append(result)
            print(f"  {tool}: {result['chars']} chars in {result['time']:.2f}s")

        except Exception as e:
            print(f"  {tool} failed: {e}")
            results.append({
                "tool": tool,
                "error": str(e),
            })

    return results


def run_experiment(
    pdf_path: Path,
    output_dir: Path,
    pages: Optional[list[int]] = None,
    tools: Optional[list[str]] = None,
) -> dict:
    """
    Run OCR experiment on a PDF.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to store results
        pages: List of page numbers to process (0-indexed), or None for all
        tools: List of OCR tools to use, or None for all

    Returns:
        Dictionary with experiment results
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert PDF to images
    print(f"Converting {pdf_path} to images...")
    images_dir = output_dir / "images"
    image_paths = pdf_to_images(pdf_path, images_dir)
    print(f"  Created {len(image_paths)} page images")

    # Select pages to process
    if pages is not None:
        image_paths = [image_paths[i] for i in pages if i < len(image_paths)]

    # Run OCR on each page
    all_results = []
    for i, img_path in enumerate(image_paths):
        print(f"\nProcessing page {i + 1}/{len(image_paths)}...")
        page_results = compare_ocr_tools(img_path, tools)
        all_results.append({
            "page": i,
            "image": str(img_path),
            "results": page_results,
        })

    # Save results
    results_path = output_dir / "results.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\nResults saved to {results_path}")

    # Save individual text outputs
    for tool in (tools or ["tesseract", "easyocr", "paddleocr", "doctr", "surya"]):
        tool_dir = output_dir / tool
        tool_dir.mkdir(exist_ok=True)

        for page_data in all_results:
            for result in page_data["results"]:
                if result.get("tool") == tool and "text" in result:
                    text_path = tool_dir / f"page_{page_data['page']:04d}.txt"
                    with open(text_path, "w") as f:
                        f.write(result["text"])

    return {
        "pdf": str(pdf_path),
        "pages_processed": len(image_paths),
        "output_dir": str(output_dir),
        "results": all_results,
    }


if __name__ == "__main__":
    install_ocr_tools()
    # Default test with the semiconductor book
    pdf_path = Path("/home/ping/h/bw/.ocr/Semiconductor Device Fundamentals -- Robert F_ Pierret -- 2nd, PT, 1996 -- Addison Wesley -- 9780131784598 -- 4f8eb9f7853c7873e8397b450e728004 -- Anna's Archive.pdf")
    output_dir = Path("/home/ping/h/bw/.ocr/experiment")

    # Test on first 3 pages with all tools
    run_experiment(pdf_path, output_dir, pages=[0, 1, 2])
