from casefile.data.taxonomy import (
    OTHER_ISSUE,
    issue_label,
    map_product,
    normalise_issue,
    select_issues,
)


def test_product_mapping_across_renames() -> None:
    assert map_product("Credit reporting or other personal consumer reports", "x") == (
        "credit_reporting"
    )
    assert map_product(
        "Credit reporting, credit repair services, or other personal consumer reports", "x"
    ) == ("credit_reporting")
    assert map_product("Credit card", "anything") == "credit_card"
    assert map_product("Mortgage", "x") is None


def test_prepaid_cards_are_excluded() -> None:
    assert map_product("Credit card or prepaid card", "Store credit card") == "credit_card"
    assert map_product("Credit card or prepaid card", "General-purpose prepaid card") is None


def test_issue_aliases() -> None:
    old = "Problem with a credit reporting company's investigation into an existing problem"
    assert normalise_issue(old) == "Problem with a company's investigation into an existing problem"
    assert normalise_issue("Unchanged issue") == "Unchanged issue"


def test_select_issues_threshold_and_ties() -> None:
    counts = {"a": 500, "b": 300, "c": 190, "d": 5, "e": 5}
    assert select_issues(counts) == ["a", "b", "c"]
    assert issue_label("d", ["a", "b", "c"]) == OTHER_ISSUE
    assert select_issues({}) == []
