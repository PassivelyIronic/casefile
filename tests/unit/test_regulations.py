from casefile.data.regulations import SECTIONS, ecfr_xml_to_text, source_url, usc_html_to_text

ECFR_XML = """<?xml version="1.0" encoding="UTF-8"?>
<DIV8 N="1026.13" TYPE="SECTION">
<HEAD>§ 1026.13 Billing error resolution.</HEAD>
<P>(a) <I>Definition of billing error.</I> For purposes of this section:</P>
<P>(1) A reflection   on a periodic statement.</P>
</DIV8>"""

USC_HTML = """<html><body>
<!-- field-start:head -->
<h3>§1681i. Procedure in case of disputed accuracy</h3>
<!-- field-end:head -->
<!-- field-start:statute --><p>(a) Reinvestigations</p><p>(1) Reinvestigation &amp; more</p>
<!-- field-end:statute --><!-- field-start:notes --><p>Editorial notes</p><!-- field-end:notes -->
</body></html>"""


def test_ecfr_parsing() -> None:
    heading, text = ecfr_xml_to_text(ECFR_XML)
    assert heading == "§ 1026.13 Billing error resolution."
    assert text == (
        "(a) Definition of billing error. For purposes of this section:\n\n"
        "(1) A reflection on a periodic statement."
    )


def test_usc_parsing_drops_notes() -> None:
    heading, text = usc_html_to_text(USC_HTML)
    assert heading == "§1681i. Procedure in case of disputed accuracy"
    assert text == "(a) Reinvestigations\n\n(1) Reinvestigation & more"


def test_sections_unique_and_cover_all_products() -> None:
    ids = [s.section_id for s in SECTIONS]
    assert len(ids) == len(set(ids))
    products = {p for s in SECTIONS for p in s.products}
    assert products == {"credit_reporting", "debt_collection", "credit_card", "checking_savings"}


def test_source_urls_are_pinned() -> None:
    for s in SECTIONS:
        url = source_url(s)
        assert ("versioner/v1/full/2026-" in url) or ("year=2024" in url)
