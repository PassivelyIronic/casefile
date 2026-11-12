"""Fetch the regulations corpus (public domain US federal law) into `corpora/regulations/`.

CFR sections come from the eCFR versioner API at a fixed date; US Code sections from
govinfo's annual edition. Each section is stored as Markdown; `manifest.json` records
source URL, retrieval date and sha256 of the stored text.
"""

import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

ECFR_DATE = "2026-11-04"
USC_EDITION = "2024"


@dataclass(frozen=True)
class Section:
    section_id: str  # e.g. "12-CFR-1026.13", "15-USC-1681i"
    source: str  # "ecfr" | "usc"
    title: int
    section: str
    part: str | None
    products: tuple[str, ...]
    law: str


SECTIONS: tuple[Section, ...] = (
    # Credit reporting: FCRA (statute) + Regulation V
    Section("15-USC-1681b", "usc", 15, "1681b", None, ("credit_reporting",), "FCRA"),
    Section("15-USC-1681c-2", "usc", 15, "1681c-2", None, ("credit_reporting",), "FCRA"),
    Section("15-USC-1681g", "usc", 15, "1681g", None, ("credit_reporting",), "FCRA"),
    Section("15-USC-1681i", "usc", 15, "1681i", None, ("credit_reporting",), "FCRA"),
    Section("15-USC-1681s-2", "usc", 15, "1681s-2", None, ("credit_reporting",), "FCRA"),
    Section("12-CFR-1022.43", "ecfr", 12, "1022.43", "1022", ("credit_reporting",), "Reg V"),
    # Debt collection: Regulation F (implements FDCPA)
    Section("12-CFR-1006.6", "ecfr", 12, "1006.6", "1006", ("debt_collection",), "Reg F"),
    Section("12-CFR-1006.14", "ecfr", 12, "1006.14", "1006", ("debt_collection",), "Reg F"),
    Section("12-CFR-1006.18", "ecfr", 12, "1006.18", "1006", ("debt_collection",), "Reg F"),
    Section("12-CFR-1006.22", "ecfr", 12, "1006.22", "1006", ("debt_collection",), "Reg F"),
    Section("12-CFR-1006.30", "ecfr", 12, "1006.30", "1006", ("debt_collection",), "Reg F"),
    Section("12-CFR-1006.34", "ecfr", 12, "1006.34", "1006", ("debt_collection",), "Reg F"),
    Section("12-CFR-1006.38", "ecfr", 12, "1006.38", "1006", ("debt_collection",), "Reg F"),
    # Credit card: Regulation Z
    Section("12-CFR-1026.9", "ecfr", 12, "1026.9", "1026", ("credit_card",), "Reg Z"),
    Section("12-CFR-1026.12", "ecfr", 12, "1026.12", "1026", ("credit_card",), "Reg Z"),
    Section("12-CFR-1026.13", "ecfr", 12, "1026.13", "1026", ("credit_card",), "Reg Z"),
    Section("12-CFR-1026.52", "ecfr", 12, "1026.52", "1026", ("credit_card",), "Reg Z"),
    Section("12-CFR-1026.55", "ecfr", 12, "1026.55", "1026", ("credit_card",), "Reg Z"),
    # Checking / savings: Regulation E + Regulation DD
    Section("12-CFR-1005.6", "ecfr", 12, "1005.6", "1005", ("checking_savings",), "Reg E"),
    Section("12-CFR-1005.11", "ecfr", 12, "1005.11", "1005", ("checking_savings",), "Reg E"),
    Section("12-CFR-1005.17", "ecfr", 12, "1005.17", "1005", ("checking_savings",), "Reg E"),
    Section("12-CFR-1030.4", "ecfr", 12, "1030.4", "1030", ("checking_savings",), "Reg DD"),
    Section("12-CFR-1030.5", "ecfr", 12, "1030.5", "1030", ("checking_savings",), "Reg DD"),
)


@dataclass(frozen=True)
class ManifestEntry:
    section_id: str
    heading: str
    law: str
    products: list[str]
    url: str
    retrieved_at: str
    sha256: str
    file: str


def source_url(s: Section) -> str:
    if s.source == "ecfr":
        return (
            f"https://www.ecfr.gov/api/versioner/v1/full/{ECFR_DATE}/title-{s.title}.xml"
            f"?part={s.part}&section={s.section}"
        )
    return (
        f"https://www.govinfo.gov/link/uscode/{s.title}/{s.section}"
        f"?year={USC_EDITION}&link-type=html"
    )


def ecfr_xml_to_text(xml: str) -> tuple[str, str]:
    root = ET.fromstring(xml)  # noqa: S314  (trusted government source, fixed URL)
    heading = "".join(root.findtext("HEAD") or "").strip()
    paras = [" ".join("".join(p.itertext()).split()) for p in root.iter("P")]
    return heading, "\n\n".join(p for p in paras if p)


def _field(page: str, name: str) -> list[str]:
    body = page.split(f"<!-- field-start:{name} -->", 1)[-1]
    body = body.split(f"<!-- field-end:{name} -->", 1)[0]
    body = re.sub(r"(?i)</?(p|h\d|div|br)[^>]*>", "\n", body)
    text = html.unescape(re.sub(r"<[^>]+>", "", body))
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return [line for line in lines if line]


def usc_html_to_text(page: str) -> tuple[str, str]:
    head = _field(page, "head")
    heading = head[-1] if head else ""
    return heading, "\n\n".join(_field(page, "statute"))


def fetch_section(client: httpx.Client, s: Section) -> tuple[str, str, str]:
    url = source_url(s)
    r = client.get(url)
    r.raise_for_status()
    if s.source == "ecfr":
        heading, text = ecfr_xml_to_text(r.text)
    else:
        heading, text = usc_html_to_text(r.text)
    if len(text) < 200:
        raise ValueError(f"{s.section_id}: suspiciously short text ({len(text)} chars)")
    return url, heading, text


def build_corpus(out_dir: Path) -> list[ManifestEntry]:
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[ManifestEntry] = []
    headers = {"Accept-Encoding": "gzip", "User-Agent": "casefile-corpus-builder"}
    with httpx.Client(timeout=60.0, follow_redirects=True, headers=headers) as client:
        for s in SECTIONS:
            url, heading, text = fetch_section(client, s)
            doc = f"# {heading}\n\n{text}\n"
            path = out_dir / f"{s.section_id}.md"
            path.write_text(doc, encoding="utf-8", newline="\n")
            entries.append(
                ManifestEntry(
                    section_id=s.section_id,
                    heading=heading,
                    law=s.law,
                    products=list(s.products),
                    url=url,
                    retrieved_at=datetime.now(UTC).date().isoformat(),
                    sha256=hashlib.sha256(doc.encode("utf-8")).hexdigest(),
                    file=path.name,
                )
            )
    manifest = {
        "ecfr_date": ECFR_DATE,
        "usc_edition": USC_EDITION,
        "license": "US federal law, public domain (17 U.S.C. 105)",
        "sections": [asdict(e) for e in entries],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return entries


if __name__ == "__main__":
    out = Path("corpora/regulations")
    for e in build_corpus(out):
        size = len((out / e.file).read_text(encoding="utf-8"))
        print(f"{e.section_id:18} {size:>7}  {e.heading}")
