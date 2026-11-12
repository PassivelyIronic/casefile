from casefile.data.injection import ATTACKS, build_cases, insert_attack

NARR = "First sentence here. Second sentence follows. Third one ends it."


def test_positions() -> None:
    assert insert_attack(NARR, "ATTACK", "prefix").startswith("ATTACK\n\n")
    assert insert_attack(NARR, "ATTACK", "suffix").endswith("\n\nATTACK")
    mid = insert_attack(NARR, "ATTACK", "middle")
    assert mid == "First sentence here. ATTACK Second sentence follows. Third one ends it."


def test_middle_without_sentence_boundary() -> None:
    assert insert_attack("abcdef", "X", "middle") == "abc X def"


def test_build_cases_cycles_attacks_and_labels_synthetic() -> None:
    src = {
        "complaint_id": "1",
        "product": "credit_card",
        "issue": "Fees or interest",
        "company": "ACME",
        "date_received": "2024-01-01",
        "narrative": NARR,
    }
    cases = build_cases([{**src, "complaint_id": str(i)} for i in range(16)])
    assert [c["attack_id"] for c in cases[:8]] == [a.attack_id for a in ATTACKS]
    assert all(c["synthetic"] and c["expected"]["must_escalate"] for c in cases)
    assert all(c["attack_text"] in c["narrative"] for c in cases)
    assert len({c["case_id"] for c in cases}) == 16
