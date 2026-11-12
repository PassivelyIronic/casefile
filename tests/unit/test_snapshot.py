import pandas as pd
import pytest

from casefile.data import snapshot as snap
from casefile.data.taxonomy import MONETARY_RELIEF


def row(
    cid: int, product: str = "Debt collection", narrative: str = "text", **kw: str
) -> dict[str, str]:
    base = {
        "complaint_id": str(cid),
        "date_received": "2023-05-01",
        "product_raw": product,
        "sub_product": "x",
        "issue_raw": "Communication tactics",
        "narrative": narrative,
        "company_response": "Closed with explanation",
    }
    return {**base, **kw}


def test_eligible_filters_narrative_window_and_product() -> None:
    df = pd.DataFrame(
        [
            row(1),
            row(2, narrative="   "),
            row(3, date_received="2021-12-31"),
            row(4, date_received="2025-12-31T10:00:00"),
            row(5, product="Mortgage"),
            row(6, product="Credit card or prepaid card", sub_product="Gift card"),
        ]
    )
    assert list(snap.eligible(df)["complaint_id"]) == ["1", "4"]


def test_dedupe_keeps_lowest_id_ignoring_case_and_whitespace() -> None:
    df = pd.DataFrame([row(9, narrative="Same  TEXT"), row(3, narrative="same text"), row(5)])
    idx = snap.dedupe(snap.build_index([df], seed=1))
    assert sorted(idx["complaint_id"]) == ["3", "5"]


def test_select_pool_is_order_independent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(snap, "N_UNIFORM_PER_PRODUCT", 5)
    monkeypatch.setattr(snap, "N_MONETARY_EXTRA_PER_PRODUCT", 2)
    rows = [row(i, narrative=f"n{i}") for i in range(1, 40)]
    rows += [row(i, narrative=f"n{i}", company_response=MONETARY_RELIEF) for i in range(40, 50)]
    df = pd.DataFrame(rows)
    a = snap.select_pool(snap.dedupe(snap.build_index([df], seed=7)))
    b = snap.select_pool(snap.dedupe(snap.build_index([df.iloc[::-1]], seed=7)))
    assert a == b
    assert list(a.values()).count("uniform") == 5
    assert list(a.values()).count("monetary_extra") == 2
