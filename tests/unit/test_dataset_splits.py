import pandas as pd
import pytest

from casefile.data import dataset as ds
from casefile.data.taxonomy import MONETARY_RELIEF, PRODUCTS


@pytest.fixture
def pool(monkeypatch: pytest.MonkeyPatch) -> pd.DataFrame:
    monkeypatch.setattr(ds, "TRAIN_PER_PRODUCT", 100)
    monkeypatch.setattr(ds, "HISTORY_PER_PRODUCT", 200)
    rows = []
    cid = 0
    for product in PRODUCTS:
        for i in range(400):
            cid += 1
            resp = (
                MONETARY_RELIEF
                if i % 20 == 0
                else ("Closed with explanation", "Closed with non-monetary relief")[i % 2]
            )
            rows.append((str(cid), product, resp, "uniform"))
        for _ in range(30):
            cid += 1
            rows.append((str(cid), product, MONETARY_RELIEF, "monetary_extra"))
    df = pd.DataFrame(rows, columns=["complaint_id", "product", "company_response", "pool_stratum"])
    for col in ds.RECORD_FIELDS:
        if col not in df:
            df[col] = "x"
    return df


def test_allocate_largest_remainder() -> None:
    assert ds.allocate({"a": 50, "b": 30, "c": 20}, 7) == {"a": 4, "b": 2, "c": 1}
    assert sum(ds.allocate({"a": 1, "b": 1, "c": 1}, 2).values()) == 2
    assert ds.allocate({"a": 0}, 3) == {"a": 0}


def test_splits_sizes_disjoint_and_oversampled(pool: pd.DataFrame) -> None:
    s = ds.make_splits(pool)
    g = s["golden"]
    assert len(g) == ds.GOLDEN_PER_PRODUCT * len(PRODUCTS)
    for product in PRODUCTS:
        gp = g[g["product"] == product]
        assert (gp["company_response"] == MONETARY_RELIEF).sum() == ds.GOLDEN_MONETARY_PER_PRODUCT
        assert gp["in_human_subset"].sum() == ds.HUMAN_PER_PRODUCT
        human = gp[gp["in_human_subset"]]
        assert (human["company_response"] == MONETARY_RELIEF).sum() == ds.HUMAN_MONETARY_PER_PRODUCT
    ids = [set(s[k]["complaint_id"]) for k in ("golden", "train", "history", "injection_source")]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            assert not ids[i] & ids[j]
    assert len(s["train"]) == 100 * len(PRODUCTS)
    assert len(s["history"]) == 200 * len(PRODUCTS)
    assert set(s["train"]["pool_stratum"]) == {"uniform"}


def test_splits_are_deterministic_and_order_independent(pool: pd.DataFrame) -> None:
    a = ds.make_splits(pool)
    b = ds.make_splits(pool.sample(frac=1, random_state=7))
    for k in ("golden", "train", "history"):
        assert list(a[k]["complaint_id"]) == list(b[k]["complaint_id"])
