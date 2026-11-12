# TAXORA & 10 CONTENT INTELLIGENCE AGENTS: COMPREHENSIVE PROJECT MEMORY

> **Purpose**: This persistent memory document records the full architecture, live AWS deployment, enterprise guardrails, and specifications for the 10 Content Intelligence Agents. Any new Antigravity session can read this file to immediately continue with full context.

---

## 1. Live AWS Production Infrastructure (Account: `984625844016`)

- **Live CloudFront Web App URL**: [`https://duwz8hk1atmbr.cloudfront.net`](https://duwz8hk1atmbr.cloudfront.net)
- **Backend API Gateway Endpoint**: `https://yvw8dqk6c2.execute-api.us-east-1.amazonaws.com`
- **CloudFront Distribution ID**: `E22LRLZOTUA1TZ`
- **Amazon S3 Frontend & Document Bucket**: `taxora-ui-984625844016`
- **AWS Lambda Serverless Backend**: `taxora-backend-api` (Python 3.11, 1024 MB, 90s timeout)
- **IAM Role**: `taxora-backend-lambda-role` (Least-privilege S3, Bedrock, Textract, CloudWatch access)
- **AWS Region**: `us-east-1` (N. Virginia)
- **Active User / Identity**: `arn:aws:iam::984625844016:user/ai-admin`
- **Automated Deployment Script**: [`c:/Users/ELCOT/OneDrive/Desktop/Agent/taxora-taxonomy-agent/deploy_aws.py`](file:///c:/Users/ELCOT/OneDrive/Desktop/Agent/taxora-taxonomy-agent/deploy_aws.py)

---

## 2. Core Implemented Capabilities in TAXORA

1. **100% Dynamic Foundation Model Taxonomy**:
   - Zero dependence on static taxonomy files. Dynamically classifies any document from any industry into a verified 5-level hierarchy (`Domain > Sub-Domain > Process Area > Activity > Terminal Category`).
   - Clean taxonomy tree nodes: placeholder labels (`Level 1:`, `Industry / Broad Domain`) are strictly cleaned.

2. **Level 1 to Level 5 Rationales**:
   - Generates distinct, audit-grade rationales for every level in the hierarchy, with explicit focus on **Why Level 1 (Domain)** was chosen over other industries.

3. **End-to-End Source Traceability**:
   - Provides a unique `Trace ID` (e.g. `TXR-20261111-XXXXXX`), words/pages analyzed, and explicit document section mappings (`📍 Source Section` + verbatim evidence signal).
   - Traceability metadata is included in the downloadable `.json` report.

4. **Zero Model Identification**:
   - Model IDs and internal model strings are completely suppressed from the UI, system responses, and metadata exports.

5. **5 Key Topics Highlight Limit**:
   - Caps UI highlights to at most 5 high-importance topics (no raw word frequency dumps).

---

## 3. Enterprise BFSI Guardrails & Fraud Detection (TCS BFSI Standard)

Implemented in [`taxora-taxonomy-agent/backend/services/guardrail_service.py`](file:///c:/Users/ELCOT/OneDrive/Desktop/Agent/taxora-taxonomy-agent/backend/services/guardrail_service.py):

### A. Statement Anomaly & Tampering Detection (`BLOCKED_FRAUD_ANOMALY`)
- **Arithmetic Reconciliation Check**:
  Verifies $\text{Opening Balance} + \text{Total Credits} - \text{Total Debits} = \text{Closing Balance}$. If there is a discrepancy ($> 5.00$), the document is immediately **rejected** with an audit breakdown of calculated vs. stated balance.
- **Impossible Calendar Dates**:
  Detects and rejects non-existent dates (e.g. `February 30`, `April 31`).
- **IFSC / Routing Structural Validation**:
  Validates banking routing codes (e.g. RBI IFSC 5th character rule).
- **Illicit Activity & Forgery Signatures**:
  Blocks documents with counterfeit currency, fake invoice generator, or money laundering markers.

### B. High-Risk Identifier Redaction vs. Non-Harmful Data Preservation
- **Harmful / High-Risk Data (Strictly Blocked or Sanitized)**:
  - Passwords, PINs, OTPs, CVVs, Private Keys $\rightarrow$ Strictly Blocked.
  - Credit/Debit Cards (16-digit) $\rightarrow$ Masked as `[REDACTED_CARD_NUMBER]`.
  - National IDs (Aadhaar, SSN, PAN) $\rightarrow$ Masked as `[REDACTED_AADHAAR]`, `[REDACTED_PAN_ID]`.
  - Bank Account Numbers $\rightarrow$ Sanitized to last 4 digits `[REDACTED_ACCOUNT: XXXX-1234]`.
- **Non-Harmful Context (Preserved for Legitimate Business Workflows)**:
  - Customer Name, City/State, Bank Branch Name, Statement Dates, Transaction Titles are retained so the document can be classified accurately.

---

## 4. The 10 Content Intelligence Agents Specification

The upcoming multi-agent workspace features 10 specialized agents working under a shared Python middleware bus:

1. **CLARIA** (*Customer Communications Redesign*):
   - Reads long, complex customer notices, emails, or letters.
   - Extracts: What this is about (1–3 sentences), What you need to do (most prominent), Important details (deadlines, amounts), Why this matters, and What happens next.
   - Generates a simplified plain-language rewrite without altering facts or inventing actions.
2. **LENS** (*Content Reviewer*):
   - Acts as an intelligent second reviewer for draft communications.
   - Identifies contradictions, missing info, conflicting dates/numbers, and ambiguous instructions.
   - Output format: *Issue $\rightarrow$ Why it matters $\rightarrow$ Suggested fix* (recommends rather than silently rewriting).
3. **INDEX** (*Metadata Tagger*):
   - Dynamically extracts comprehensive metadata for any domain (Basic, Business, Content, Entities, and Important Dates/Amounts) for enterprise search and vector retrieval.
4. **BRIDGE** (*CMS Migrator*):
   - Analyzes source vs. target CMS content models.
   - Recommends field mappings, taxonomy transformations, and highlights missing mandatory fields or migration exceptions.
5. **GRID** (*Content Model Architect*):
   - Designs structured, reusable, and scalable headless CMS content types, components, relationships, validation rules, and channel reuse strategies.
6. **ADAPTA** (*Channel Message Adapter*):
   - Adapts master communications into Email, SMS, Push notifications, Web/App snippets, Call-center scripts, and Formal Letters while keeping critical actions, amounts, and deadlines intact.
7. **GLANCE** (*Interactive Statement Lab*):
   - Transforms dense multi-page bank, insurance, billing, and credit statements into clean summaries ("At a glance", "What changed?", "Important actions").
   - Supports interactive Q&A over statement charges.
8. **SORTIA** (*Content Classifier*):
   - Assigns documents to predefined enterprise categories with confidence scoring and flags ambiguous cases for human review.
9. **ECHO** (*Document Comparator*):
   - Compares Document V1 vs Document V2 to detect semantic changes (deadlines, amounts, customer responsibilities) and explains the practical business impact.
10. **ALLY** (*Web Accessibility Coach*):
    - Reviews web content, forms, buttons, links, and headings against WCAG standards.
    - Output format: *Issue $\rightarrow$ Why it matters $\rightarrow$ How to improve*.

---

## 5. Next Planned Phase
- Implement the unified multi-agent UI/UX once designs are provided.
- Build the shared router and 10 agent handlers on the Python backend.
- Maintain dual-boundary guardrails, session memory, and traceability across all 10 agents.

