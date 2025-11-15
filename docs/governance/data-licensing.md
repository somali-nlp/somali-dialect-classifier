# Data Licensing and Usage Rights

**Version:** 1.0
**Last Updated:** 2025-11-15
**Status:** Active

## Table of Contents

- [Overview](#overview)
- [License Summary by Source](#license-summary-by-source)
- [Usage Guidelines](#usage-guidelines)
- [Compliance Requirements](#compliance-requirements)
- [Attribution](#attribution)

---

## Overview

This document summarizes the licensing terms and usage rights for all data sources in the Somali NLP project. All users must comply with these terms to ensure legal and ethical use of the data.

### Principles

1. **Transparency:** All licenses are documented and tracked in silver layer
2. **Compliance:** Strict adherence to source-specific terms
3. **Attribution:** Proper credit given to all data sources
4. **Ethical Use:** Research and educational purposes prioritized

---

## License Summary by Source

### Wikipedia (Somali)

| Property | Value |
|----------|-------|
| **License** | CC-BY-SA 3.0 |
| **Source URL** | https://so.wikipedia.org |
| **Research Use** | ✓ Permitted |
| **Commercial Use** | ✓ Permitted (with attribution + share-alike) |
| **Redistribution** | ✓ Permitted (same license + attribution) |
| **Modifications** | ✓ Permitted (must share under same license) |
| **Attribution Required** | ✓ Yes |

**Terms:**
- Must provide attribution to Wikipedia and original authors
- Derivative works must be licensed under CC-BY-SA 3.0 or compatible
- Must indicate if changes were made
- Cannot suggest endorsement by Wikipedia

**Attribution Example:**
```
This dataset contains text from Wikipedia (so.wikipedia.org),
licensed under CC-BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0/).
```

**Records in Dataset:** ~9,960 articles
**Coverage:** Encyclopedic content, formal register

---

### BBC Somali

| Property | Value |
|----------|-------|
| **License** | Custom Terms of Service |
| **Source URL** | https://www.bbc.com/somali |
| **Research Use** | ✓ Permitted (fair use doctrine) |
| **Commercial Use** | ✗ Not permitted without permission |
| **Redistribution** | ✗ Not permitted |
| **Modifications** | ⚠ Limited (fair use) |
| **Attribution Required** | ✓ Yes |

**Terms:**
- Research and educational use only
- No commercial applications without BBC permission
- Cannot redistribute raw BBC content
- Can publish derived statistics and analyses
- Must respect robots.txt (350 articles/day limit)

**Fair Use Justification:**
- Academic research purpose
- Limited corpus size (350/day quota)
- Transformative use (NLP training data)
- No market harm to BBC

**Attribution Example:**
```
This research uses text from BBC Somali (bbc.com/somali) under fair use
for academic purposes. BBC content is not redistributed.
```

**Records in Dataset:** ~3 articles (test data)
**Coverage:** News content, standard journalistic Somali

**Restrictions:**
- DO NOT redistribute BBC text publicly
- DO NOT use in commercial products
- DO NOT exceed 350 articles/day (ethical limit)
- CAN publish aggregated metrics and model outputs
- CAN use for academic research and papers

---

### HuggingFace Datasets (MC4 Somali)

| Property | Value |
|----------|-------|
| **License** | Varies by dataset (check metadata) |
| **Source URL** | https://huggingface.co/datasets |
| **Research Use** | ✓ Generally permitted |
| **Commercial Use** | ⚠ Check per dataset |
| **Redistribution** | ⚠ Check per dataset |
| **Modifications** | ⚠ Check per dataset |
| **Attribution Required** | ✓ Yes |

**Common Licenses:**
- ODC-BY (Open Data Commons Attribution)
- CC-BY 4.0
- Apache 2.0
- Custom (check dataset card)

**MC4 Somali Specific:**
- License: ODC-BY (most permissive)
- Web-scraped Common Crawl data
- Research and commercial use permitted
- Attribution to Common Crawl required

**Attribution Example:**
```
This dataset includes text from MC4 (Multilingual C4), created from
Common Crawl data and available on HuggingFace. Licensed under ODC-BY.
```

**Important:**
- Always check individual dataset license on HuggingFace
- License field in silver layer records source-specific terms
- Some datasets may have more restrictive terms

**Records in Dataset:** Target 10,000/day (variable quality)
**Coverage:** Web-scraped text, mixed registers

---

### Språkbanken (Swedish Language Bank)

| Property | Value |
|----------|-------|
| **License** | CC-BY 4.0 (most corpora) |
| **Source URL** | https://spraakbanken.gu.se/ |
| **Research Use** | ✓ Permitted |
| **Commercial Use** | ✓ Permitted (with attribution) |
| **Redistribution** | ✓ Permitted (with attribution) |
| **Modifications** | ✓ Permitted |
| **Attribution Required** | ✓ Yes |

**Terms:**
- Must attribute Språkbanken and corpus creators
- License applies to individual corpora (verify per corpus)
- Some corpora may have additional restrictions
- Academic/non-profit use encouraged

**Attribution Example:**
```
This dataset includes corpora from Språkbanken (Swedish Language Bank),
licensed under CC-BY 4.0. See https://spraakbanken.gu.se/ for details.
```

**Note:** 23 different Somali corpora available, each may have specific terms.
Always verify license metadata for each corpus.

**Records in Dataset:** Variable (10 corpora/day quota)
**Coverage:** Academic corpora, diverse text types

---

### TikTok (via Apify)

| Property | Value |
|----------|-------|
| **License** | TikTok Terms of Service + Apify Terms |
| **Source URL** | https://www.tiktok.com |
| **Research Use** | ✓ Limited (fair use) |
| **Commercial Use** | ✗ Not permitted |
| **Redistribution** | ✗ Not permitted |
| **Modifications** | ⚠ Limited (aggregation OK) |
| **Attribution Required** | ✓ Yes |

**Terms:**
- Research use only under fair use doctrine
- No commercial applications
- Cannot redistribute TikTok content
- Must comply with TikTok Community Guidelines
- Apify terms also apply (check actor license)

**Privacy Considerations:**
- Public comments only (no private data)
- PII redaction required before analysis
- User anonymization mandatory
- No user profiling or targeting

**Attribution Example:**
```
This research uses public TikTok comments collected via Apify for
academic purposes. TikTok content is not redistributed. User privacy
is protected through anonymization.
```

**Records in Dataset:** Target 30,000 comments (manual approval)
**Coverage:** Social media text, informal Somali

**Ethical Requirements:**
- Manual cost approval for each run
- PII scanning mandatory
- User anonymization required
- No user re-identification allowed

---

## Usage Guidelines

### For Academic Research

**Permitted:**
- Analysis and statistical aggregation
- Training machine learning models
- Publishing research papers with findings
- Sharing derived metrics and model outputs
- Creating derivative datasets (with proper licensing)

**Required:**
- Attribution to all sources
- Respect license restrictions per source
- Document data sources in publications
- Follow ethical guidelines (below)

**Not Permitted:**
- Redistributing BBC or TikTok raw text
- Commercial use of BBC or TikTok data
- User re-identification from TikTok data

---

### For Production/Commercial Use

**Permitted Sources:**
- Wikipedia (CC-BY-SA 3.0) - with share-alike
- Språkbanken (CC-BY 4.0) - with attribution
- HuggingFace datasets (verify per dataset)

**Restricted Sources:**
- BBC Somali - Research only
- TikTok - Research only

**Requirements:**
- Derivative models must respect most restrictive license
- If training on BBC/TikTok, model for research use only
- If production model needed, train only on permissive sources
- Always provide attribution

**Example Compliant Production Model:**
```
Model trained on:
- Wikipedia Somali (CC-BY-SA 3.0)
- Språkbanken corpora (CC-BY 4.0)
- HuggingFace MC4 Somali (ODC-BY)

Model excludes BBC and TikTok data to enable commercial use.
Model is licensed under CC-BY-SA 3.0 (most restrictive source license).
```

---

### For Redistribution

**Can Redistribute:**
- Wikipedia text (with CC-BY-SA 3.0 license)
- Språkbanken text (with CC-BY 4.0 license)
- HuggingFace data (check per dataset, usually permissive)

**Cannot Redistribute:**
- BBC Somali raw text
- TikTok comments or user data
- Any PII-containing records

**Best Practice:**
- Create a "research-only" and "permissive" split
- Clearly label license restrictions
- Provide license metadata with each record
- Document exclusions in dataset card

**Example Dataset Card:**
```markdown
# Somali NLP Dataset

## License Breakdown
- 60% Wikipedia (CC-BY-SA 3.0) - Redistributable
- 30% Språkbanken (CC-BY 4.0) - Redistributable
- 10% BBC + TikTok (Research only) - NOT INCLUDED IN PUBLIC RELEASE

Public release contains only permissively licensed data (Wikipedia + Språkbanken).
Full dataset (including research-only sources) available on request for academic use.
```

---

## Compliance Requirements

### License Field in Silver Layer

Every record in the silver layer MUST have a `license` field:

```python
{
    "id": "...",
    "text": "...",
    "source": "Wikipedia-Somali",
    "license": "CC-BY-SA-3.0",  # Required field
    # ... other fields
}
```

**Validation:**
- Pre-flight check verified 100% license field coverage
- Schema validation enforces license field presence
- Null or missing license = record rejected

---

### Attribution in Publications

All publications using this data must include:

```markdown
## Data Sources

This research uses the Somali NLP Dataset, which includes text from:

- **Wikipedia (Somali):** Licensed under CC-BY-SA 3.0
  (https://creativecommons.org/licenses/by-sa/3.0/)

- **BBC Somali:** Used under fair use for academic research
  (bbc.com/somali)

- **HuggingFace MC4 Somali:** Licensed under ODC-BY
  (https://huggingface.co/datasets/mc4)

- **Språkbanken Corpora:** Licensed under CC-BY 4.0
  (https://spraakbanken.gu.se/)

- **TikTok Public Comments:** Used under fair use for academic research,
  with user anonymization (tiktok.com)
```

---

### Legal Compliance

**Requirements:**
- All data collection respects robots.txt
- Rate limiting prevents server overload
- No circumvention of access controls
- Public data only (no authentication bypass)

**Documentation:**
- Ledger tracks all data provenance
- Metrics record data volumes
- Pipeline runs are auditable
- License tracking enables compliance audits

---

## Attribution

### How to Attribute This Dataset

When using the Somali NLP Dataset, include:

```
This work uses the Somali NLP Dataset, which contains text from
Wikipedia (CC-BY-SA 3.0), Språkbanken (CC-BY 4.0), HuggingFace
datasets (various licenses), BBC Somali (fair use), and TikTok
(fair use). See full license information at [repository URL].
```

### How to Attribute Derived Models

Models trained on this data should include:

```
This model was trained on the Somali NLP Dataset. The dataset includes
text from multiple sources with varying licenses. See [repository URL]
for full license compliance information.

For commercial use, this model should be retrained on permissively
licensed sources only (Wikipedia, Språkbanken, HuggingFace).
```

---

## Review and Updates

**Frequency:** Quarterly review of license compliance
**Responsibility:** Data governance team
**Process:**
1. Verify no license term changes from sources
2. Audit silver layer license field coverage
3. Review new sources for license compatibility
4. Update this document with any changes

**Version History:**
- 1.0 (2025-11-15): Initial version for Stage 0.6 validation

---

**For questions about licensing, contact:** [Define contact]

**Last Reviewed:** 2025-11-15

---

## Appendix: License Compatibility Matrix

| Use Case | Wikipedia | BBC | HuggingFace | Språkbanken | TikTok |
|----------|-----------|-----|-------------|-------------|--------|
| Research | ✓ | ✓ | ✓ | ✓ | ✓ |
| Commercial | ✓* | ✗ | ⚠ | ✓ | ✗ |
| Redistribution | ✓* | ✗ | ⚠ | ✓ | ✗ |
| Model Training (Research) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Model Training (Commercial) | ✓* | ✗ | ⚠ | ✓ | ✗ |

*Must comply with share-alike (Wikipedia) or attribution (Språkbanken) requirements
⚠ Check specific dataset license
✓ Permitted
✗ Not permitted

---

**End of Document**
