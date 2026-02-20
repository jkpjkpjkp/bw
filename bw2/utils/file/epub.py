import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import duckdb

from .xml import html_to_txt
from ._utils import is_content_chapter, store_book


def _get_container_rootfile(zf: zipfile.ZipFile) -> str:
    """Get the path to the root OPF file from container.xml."""
    container = zf.read("META-INF/container.xml").decode("utf-8")
    root = ET.fromstring(container)
    ns = {"cont": "urn:oasis:names:tc:opendocument:xmlns:container"}
    rootfile = root.find(".//cont:rootfile", ns)
    if rootfile is None:
        raise ValueError("No rootfile found in container.xml")
    return rootfile.get("full-path", "")


def _parse_opf(zf: zipfile.ZipFile, opf_path: str) -> tuple[str, str, list[tuple[str, str]], str | None]:
    """Parse the OPF file to get metadata and spine items.

    Returns: (title, author, list of (id, href) for spine items, ncx_href)
    """
    opf_content = zf.read(opf_path).decode("utf-8")
    root = ET.fromstring(opf_content)

    # Handle namespaces
    ns = {
        "opf": "http://www.idpf.org/2007/opf",
        "dc": "http://purl.org/dc/elements/1.1/",
    }

    # Get metadata
    title = ""
    author = ""

    title_el = root.find(".//dc:title", ns)
    if title_el is not None and title_el.text:
        title = title_el.text

    creator_el = root.find(".//dc:creator", ns)
    if creator_el is not None and creator_el.text:
        author = creator_el.text

    # Build manifest id->href mapping
    manifest = root.find("opf:manifest", ns) or root.find("manifest")
    id_to_href: dict[str, str] = {}
    ncx_href: str | None = None
    if manifest is not None:
        for item in manifest:
            item_id = item.get("id", "")
            href = item.get("href", "")
            media_type = item.get("media-type", "")
            if "html" in media_type or "xhtml" in media_type:
                id_to_href[item_id] = href
            elif "ncx" in media_type or href.endswith(".ncx"):
                ncx_href = href

    # Get spine items in order
    spine = root.find("opf:spine", ns) or root.find("spine")
    spine_items: list[tuple[str, str]] = []
    if spine is not None:
        for itemref in spine:
            idref = itemref.get("idref", "")
            if idref in id_to_href:
                spine_items.append((idref, id_to_href[idref]))

    return title, author, spine_items, ncx_href


def _parse_ncx(zf: zipfile.ZipFile, ncx_path: str) -> dict[str, str]:
    """Parse NCX file to get href -> title mapping."""
    try:
        ncx_content = zf.read(ncx_path).decode("utf-8")
    except KeyError:
        return {}

    try:
        root = ET.fromstring(ncx_content)
    except ET.ParseError:
        return {}

    ns = {"ncx": "http://www.daisy.org/z3986/2005/ncx/"}
    href_to_title: dict[str, str] = {}

    for navpoint in root.findall(".//ncx:navPoint", ns):
        label = navpoint.find("ncx:navLabel/ncx:text", ns)
        content = navpoint.find("ncx:content", ns)
        if label is not None and content is not None and label.text:
            src = content.get("src", "").split("#")[0]  # Remove fragment
            href_to_title[src] = label.text.strip()

    return href_to_title


def _extract_chapter_title(html: str, fallback: str) -> str:
    """Try to extract chapter title from HTML content."""
    root = None
    try:
        root = ET.fromstring(html)
    except ET.ParseError:
        # Try with a wrapper for malformed HTML
        try:
            root = ET.fromstring(f"<root>{html}</root>")
        except ET.ParseError:
            return fallback

    if root is None:
        return fallback

    # Look for title in h1, h2, h3, or title tags
    for tag in ["title", ".//h1", ".//h2", ".//h3"]:
        el = root.find(tag)
        if el is not None and el.text:
            title = el.text.strip()
            if title and len(title) < 100:
                return title

    return fallback


def load_epub(path: str | Path, con: duckdb.DuckDBPyConnection | None = None) -> str:
    """Load an EPUB file and store it directly in DuckDB.

    Args:
        path: Path to the EPUB file.
        con: Optional DuckDB connection. If None, creates new one.

    Returns:
        The uid_book of the created book.
    """
    path = Path(path)

    with zipfile.ZipFile(path, "r") as zf:
        opf_path = _get_container_rootfile(zf)
        opf_dir = str(Path(opf_path).parent)

        title, author, spine_items, ncx_href = _parse_opf(zf, opf_path)

        # Parse NCX for chapter titles
        ncx_titles: dict[str, str] = {}
        if ncx_href:
            if opf_dir and opf_dir != ".":
                ncx_full_path = f"{opf_dir}/{ncx_href}"
            else:
                ncx_full_path = ncx_href
            ncx_titles = _parse_ncx(zf, ncx_full_path)

        chapters: list[tuple[str, str]] = []
        for i, (item_id, href) in enumerate(spine_items):
            # Resolve href relative to OPF directory
            if opf_dir and opf_dir != ".":
                full_href = f"{opf_dir}/{href}"
            else:
                full_href = href

            # Handle fragment identifiers
            full_href = full_href.split("#")[0]

            try:
                content = zf.read(full_href).decode("utf-8")
            except KeyError:
                continue

            text = html_to_txt(content)
            if not text or len(text) < 500:  # Skip very short/empty chapters
                continue

            # Get title from NCX first, then try HTML, then fallback
            chapter_title = ncx_titles.get(href) or _extract_chapter_title(content, f"Chapter {i + 1}")

            # Skip non-content chapters
            if not is_content_chapter(chapter_title):
                continue

            chapters.append((chapter_title, text))

        return store_book(
            title=title or path.stem,
            author=author,
            chapters=chapters,
            con=con,
        )
