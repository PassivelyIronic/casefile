"""Label taxonomy: map raw CFPB product / issue names to the project's canonical labels.

Decided after profiling the export (see data/README.md and evals/reports/data/):
- 4 products; raw names changed in 2017 and 2023, mapped below.
- "Credit card or prepaid card" (2017-2023) also held prepaid cards; only credit-card
  sub-products are kept.
- Issue names were renamed a few times; aliases unify them. Rare issues are collapsed
  into "other" per product (rule in `issue_label`).
"""

from collections.abc import Mapping
from typing import Final, Literal

Product = Literal["credit_reporting", "debt_collection", "credit_card", "checking_savings"]
PRODUCTS: Final[tuple[Product, ...]] = (
    "credit_reporting",
    "debt_collection",
    "credit_card",
    "checking_savings",
)

DATE_FROM: Final = "2022-01-01"
DATE_TO: Final = "2025-12-31"

PRODUCT_MAP: Final[Mapping[str, Product]] = {
    "Credit reporting or other personal consumer reports": "credit_reporting",
    "Credit reporting, credit repair services, or other personal consumer reports": (
        "credit_reporting"
    ),
    "Debt collection": "debt_collection",
    "Credit card": "credit_card",
    "Credit card or prepaid card": "credit_card",
    "Checking or savings account": "checking_savings",
}

# Sub-products of "Credit card or prepaid card" that are credit cards.
CREDIT_CARD_SUB_PRODUCTS: Final = frozenset(
    {"General-purpose credit card or charge card", "Store credit card"}
)

ISSUE_ALIASES: Final[Mapping[str, str]] = {
    "Problem with a credit reporting company's investigation into an existing problem": (
        "Problem with a company's investigation into an existing problem"
    ),
    "Problem with a company's investigation into an existing issue": (
        "Problem with a company's investigation into an existing problem"
    ),
    "Identity theft protection or other monitoring services": (
        "Credit monitoring or identity theft protection services"
    ),
    "Trouble using the card": "Trouble using your card",
}

OTHER_ISSUE: Final = "other"
MIN_ISSUE_SHARE: Final = 0.02  # issues below 2% of a product's complaints -> "other"
MAX_ISSUES_PER_PRODUCT: Final = 8

MONETARY_RELIEF: Final = "Closed with monetary relief"


def map_product(product_raw: str, sub_product: str) -> Product | None:
    product = PRODUCT_MAP.get(product_raw)
    if product_raw == "Credit card or prepaid card" and sub_product not in CREDIT_CARD_SUB_PRODUCTS:
        return None
    return product


def normalise_issue(issue_raw: str) -> str:
    return ISSUE_ALIASES.get(issue_raw, issue_raw)


def select_issues(counts: Mapping[str, int]) -> list[str]:
    """Issues kept as their own label for one product: share >= MIN_ISSUE_SHARE, top-K."""
    total = sum(counts.values())
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    kept = [k for k, n in ranked if total and n / total >= MIN_ISSUE_SHARE]
    return kept[:MAX_ISSUES_PER_PRODUCT]


def issue_label(issue: str, kept: list[str]) -> str:
    return issue if issue in kept else OTHER_ISSUE
