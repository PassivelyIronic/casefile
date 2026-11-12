# Data report: label distributions

- Date window: 2022-01-01 .. 2025-12-31
- Source archive sha256: `35d4c0954b1ea59e72c563319424cf99cbd9d3f9fe7311df956ce01057bed751`
- Verification vs official export: `{"pool_size": 33600, "found_in_official": 33593, "found_rate": 0.9998, "field_match_rate": {"product_raw": 1.0, "issue_raw": 1.0, "company": 0.9966, "company_response": 0.9999, "timely": 1.0, "date_received": 1.0}}`
- `company_response` is what the company did, not the correct resolution (weak label).

## Split sizes

| split | rows |
|---|---|
| golden | 200 |
| train | 10000 |
| history | 20000 |

## Monetary relief rate: population vs golden (oversampled)

| product | population | golden |
|---|---|---|
| credit_reporting | 0.16% | 30.00% |
| debt_collection | 0.50% | 30.00% |
| credit_card | 18.79% | 30.00% |
| checking_savings | 13.61% | 30.00% |

## Issue taxonomy (kept issues per product; the rest -> `other`)

- **credit_reporting**: Incorrect information on your report; Improper use of your report; Problem with a company's investigation into an existing problem
- **debt_collection**: Attempts to collect debt not owed; Written notification about debt; False statements or representation; Took or threatened to take negative or legal action; Communication tactics
- **credit_card**: Problem with a purchase shown on your statement; Getting a credit card; Other features, terms, or problems; Fees or interest; Closing your account; Problem when making payments; Advertising and marketing, including promotional offers; Trouble using your card
- **checking_savings**: Managing an account; Closing an account; Problem with a lender or other company charging your account; Problem caused by your funds being low; Opening an account

## credit_reporting (population after dedupe: 1,015,464, before: 2,125,969)

| company_response | population | golden |
|---|---|---|
| Closed with explanation | 588,819 | 21 |
| Closed with non-monetary relief | 423,807 | 14 |
| Closed with monetary relief | 1,599 | 15 |
| Untimely response | 1,219 | 0 |
| In progress | 16 | 0 |
| (empty) | 4 | 0 |

| issue (normalised) | population |
|---|---|
| Incorrect information on your report | 472,412 |
| Improper use of your report | 295,278 |
| Problem with a company's investigation into an existing problem | 223,528 |
| Unable to get your credit report or credit score | 9,396 |
| Credit monitoring or identity theft protection services | 7,289 |
| Problem with fraud alerts or security freezes | 6,244 |
| Fraud or scam | 447 |
| Confusing or misleading advertising or marketing | 230 |
| Confusing or missing disclosures | 205 |
| Problem with customer service | 186 |
| Unexpected or other fees | 171 |
| Excessive fees | 61 |
| Getting a loan | 3 |
| Getting a loan or lease | 2 |
| Trouble during payment process | 2 |
| Other features, terms, or problems | 2 |
| Problem with a purchase shown on your statement | 2 |
| Trouble using your card | 1 |
| Getting a credit card | 1 |
| Struggling to pay your loan | 1 |
| Advertising and marketing, including promotional offers | 1 |
| Dealing with your lender or servicer | 1 |
| Struggling to repay your loan | 1 |

## debt_collection (population after dedupe: 185,396, before: 237,590)

| company_response | population | golden |
|---|---|---|
| Closed with explanation | 149,621 | 29 |
| Closed with non-monetary relief | 33,450 | 6 |
| Untimely response | 1,392 | 0 |
| Closed with monetary relief | 929 | 15 |
| In progress | 4 | 0 |

| issue (normalised) | population |
|---|---|
| Attempts to collect debt not owed | 85,885 |
| Written notification about debt | 34,353 |
| False statements or representation | 25,314 |
| Took or threatened to take negative or legal action | 19,377 |
| Communication tactics | 13,548 |
| Electronic communications | 3,503 |
| Threatened to contact someone or share information improperly | 3,416 |

## credit_card (population after dedupe: 115,897, before: 128,968)

| company_response | population | golden |
|---|---|---|
| Closed with explanation | 78,753 | 29 |
| Closed with monetary relief | 21,776 | 15 |
| Closed with non-monetary relief | 15,291 | 6 |
| Untimely response | 76 | 0 |
| In progress | 1 | 0 |

| issue (normalised) | population |
|---|---|
| Problem with a purchase shown on your statement | 32,113 |
| Getting a credit card | 14,785 |
| Other features, terms, or problems | 14,708 |
| Fees or interest | 13,415 |
| Closing your account | 9,393 |
| Problem when making payments | 8,344 |
| Advertising and marketing, including promotional offers | 6,096 |
| Trouble using your card | 5,383 |
| Incorrect information on your report | 4,873 |
| Problem with a company's investigation into an existing problem | 3,632 |
| Struggling to pay your bill | 1,556 |
| Improper use of your report | 1,136 |
| Credit monitoring or identity theft protection services | 278 |
| Problem with fraud alerts or security freezes | 122 |
| Unable to get your credit report or credit score | 63 |

## checking_savings (population after dedupe: 122,449, before: 126,901)

| company_response | population | golden |
|---|---|---|
| Closed with explanation | 98,313 | 33 |
| Closed with monetary relief | 16,662 | 15 |
| Closed with non-monetary relief | 7,384 | 2 |
| Untimely response | 90 | 0 |

| issue (normalised) | population |
|---|---|
| Managing an account | 67,567 |
| Closing an account | 17,320 |
| Problem with a lender or other company charging your account | 15,616 |
| Problem caused by your funds being low | 11,063 |
| Opening an account | 10,257 |
| Incorrect information on your report | 194 |
| Problem with a company's investigation into an existing problem | 190 |
| Improper use of your report | 96 |
| Problem with fraud alerts or security freezes | 81 |
| Credit monitoring or identity theft protection services | 57 |
| Unable to get your credit report or credit score | 8 |
