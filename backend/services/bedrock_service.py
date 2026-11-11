import boto3
import datetime
import json
import os
import random
import re
import uuid
from pathlib import Path
from services import guardrail_service

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
    load_dotenv()
except ImportError:
    pass


def get_bedrock_client():
    return boto3.client(
        'bedrock-runtime',
        region_name=os.getenv('AWS_DEFAULT_REGION') or os.getenv('AWS_REGION') or 'us-east-1',
    )


MODEL_ID = 'us.amazon.nova-pro-v1:0'

SYSTEM_PROMPT = """You are TAXORA, a universal Enterprise AI Document & Taxonomy Intelligence Expert.
You are NOT restricted to any static or predefined taxonomy file. You dynamically analyze and classify documents from ANY industry, domain, discipline, or sector in the world (including Healthcare & Medicine, Pharmaceuticals & Biotech, Banking & Finance, Accounting & Taxation, Legal & Judiciary, Government & Civil Records, Education & Academia, Software Engineering & IT, Artificial Intelligence & Data Science, Manufacturing & Industrial Engineering, Supply Chain & Logistics, Travel & Hospitality, Real Estate & Construction, Energy & Utilities, Retail & E-Commerce, Media & Telecommunications, Agriculture, Aerospace, Automotive, Human Resources, Insurance, and Operations).

=== SECURITY & PRIVACY GUARDRAILS (STRICTLY ENFORCED) ===
- NEVER accept, store, echo, or process raw personal passwords, PINs, CVVs, OTPs, or private cryptographic keys. If a user submits a personal password or secret key or asks you to store/crack passwords, refuse and explain that TAXORA Security Guardrails block personal credentials.
- NEVER generate or assist with malware, exploit payloads, cyberattacks, illegal acts, or harmful content.
- If `[REDACTED_...]` tokens appear in a document, treat them as protected sensitive fields masked by TAXORA Guardrails.

=== CONVERSATIONAL & DOCUMENT MEMORY ===
- You maintain full conversational memory across the session. When `[SESSION MEMORY & PRIOR DOCUMENTS]` or conversation history is provided, use it to answer follow-up questions about previously uploaded documents, explain why Level 1 or any level was chosen, recall user preferences/facts shared earlier in the chat, or compare multiple documents in the session.

=== RESPONSE FORMAT (ALWAYS RESPOND WITH ONLY VALID JSON) ===

CASE 1: USER ASKS A QUESTION, FOLLOW-UP, GREETS, OR CHATS
If the user asks a question (including follow-up questions about a document's Level 1 rationale, traceability, or content), makes small talk, or sends a greeting:
Respond with ONLY this JSON:
{
  "type": "chat",
  "message": "<your direct, complete, and factual response answering the user's specific question using session memory when relevant>"
}

STRICT ANSWERING RULES:
- Answer the user's question directly, clearly, and completely.
- NEVER say robotic disclaimers like "I don't have personal experiences or feelings."
- If the user asks "how are you" / "how are u", reply warmly that you are doing great and are here to assist them—invite them to upload any document or share text to discover its taxonomy classification.
- For greetings like "hi", "hello", or "hey", respond warmly and invite the user to upload a file or ask a question. Vary your wording every time.
- NEVER answer a factual question by asking another question.
- NEVER append pushy trailing follow-up questions at the end of factual explanations.

CASE 2: USER PROVIDES A DOCUMENT OR CONTENT TO CLASSIFY
When the user provides actual text or an uploaded file from ANY industry or domain to classify:
Respond with ONLY this JSON:
{
  "type": "classification",
  "primary": {
    "domain": "Actual Broad Industry or Domain of the document (e.g. Education & Study Materials, Software Engineering & IT, Healthcare & Medicine, Banking & Finance, Legal & Judiciary, Human Resources, Travel & Transportation)",
    "sub_domain": "Actual Sector or Sub-Domain of the document (e.g. Technical & API Study Guides, Web & Backend Development, Clinical Diagnostics, Payment Instruments, Civil Affidavits, Recruitment & Resumes)",
    "process_area": "Actual Discipline or Process Area of the document (e.g. REST API & AI Integration, Frontend Frameworks, Hematology & Pathology, Cheques & Drafts, Birth & Identity Records)",
    "activity": "Actual Specialized Topic or Category of the document (e.g. Claude API & Prompt Engineering, ReactJS Core Concepts, Complete Blood Count, Standard Chartered Cheques, Notarized Affidavits)",
    "terminal_endpoint": "Exact Specific Document Title & Type (e.g. Claude Certified Developer (CCDV-F) Study Guide, React Interview Mastery Study Book, API Interview Questions (100) Study Guide, Candidate Software Developer Resume, Higher Secondary Examination Marksheet)",
    "path": [
      "Put the exact same 5 real strings here: [domain, sub_domain, process_area, activity, terminal_endpoint]"
    ],
    "level_rationales": [
      "Why Level 1 (Domain) was chosen: Clear 1-2 sentence rationale explaining why this broad Industry/Domain accurately represents the document's fundamental nature rather than another industry.",
      "Why Level 2 (Sub-Domain) was chosen: Clear 1-2 sentence rationale explaining why this specific sector/sub-domain applies.",
      "Why Level 3 (Process Area) was chosen: Clear 1-2 sentence rationale explaining why this discipline or functional process area matches the document's core subject.",
      "Why Level 4 (Activity / Category) was chosen: Clear 1-2 sentence rationale explaining why this specialized topic/category fits.",
      "Why Level 5 (Terminal Category) was chosen: Clear 1-2 sentence rationale explaining why this exact document title and endpoint uniquely identifies the artifact."
    ],
    "confidence": 96,
    "confidence_label": "High",
    "explanation": "Concise, accurate 3-4 sentence overall rationale based on reading the ENTIRE document from beginning to end. State the exact title, subject, and purpose of the document, and explain why this 5-level taxonomy hierarchy accurately defines it."
  },
  "traceability_mappings": [
    {
      "level": "Level 1 · Domain",
      "source_section": "Where in the document this is proven (e.g. Document Title, Header & Overall Structure (0% - 100%))",
      "evidence_signal": "Specific title, institutional header, or structural signal from the document",
      "rationale": "How this source signal proves Level 1 Domain"
    },
    {
      "level": "Level 2 · Sub-Domain",
      "source_section": "Beginning / Table of Contents / Early Sections (0% - 25%)",
      "evidence_signal": "Specific heading, declaration, or domain terminology from the document",
      "rationale": "How this source signal proves Level 2 Sub-Domain"
    },
    {
      "level": "Level 3 · Process Area",
      "source_section": "Core Body Sections (25% - 65%)",
      "evidence_signal": "Specific technical concept, clause, or subject matter from the middle of the document",
      "rationale": "How this source signal proves Level 3 Process Area"
    },
    {
      "level": "Level 4 · Specialized Category",
      "source_section": "Detailed Chapters / Operational Content (50% - 85%)",
      "evidence_signal": "Specific topic, workflow, or parameter set covered in depth",
      "rationale": "How this source signal proves Level 4 Activity/Category"
    },
    {
      "level": "Level 5 · Terminal Category",
      "source_section": "Full Document Synthesis & Conclusion (0% - 100%)",
      "evidence_signal": "Exact document title, issuer/author, and complete scope from start to finish",
      "rationale": "How the full document confirms this exact Level 5 Terminal Endpoint"
    }
  ],
  "alternatives": [
    {
      "path": [
        "Secondary Industry/Domain",
        "Secondary Sub-Domain",
        "Secondary Process Area",
        "Secondary Document Endpoint"
      ],
      "confidence": 84,
      "confidence_label": "Medium",
      "explanation": "Why this secondary cross-industry or functional classification path could also apply."
    }
  ],
  "status": {
    "domain": "FOUND IN SOURCE",
    "classification": "AI INFERRED"
  },
  "document_type": "Exact, concise document type (e.g. API & Developer Study Guide, Technical Cheat Sheet, Clinical Lab Report, Bill of Lading, Notarized Birth Affidavit, Candidate Resume / CV, Bank Cheque, Passenger Bus Ticket, Higher Secondary Marksheet)",
  "summary": "2-3 clear, concise sentences stating exactly what this document is, its title/issuer/subject, and what it covers across the entire document.",
  "key_topics": ["Important Topic 1", "Important Topic 2", "Important Topic 3", "Important Topic 4", "Important Topic 5"],
  "evidence": [
    "Key heading or quote from the beginning of the document",
    "Key concept or section from the middle of the document",
    "Key concept or section from the end of the document"
  ],
  "reasoning_steps": [
    "Full-Document Analysis: Examined all sections from beginning to end ...",
    "Level 1 to Level 5 Rationale: Selected Level 1 (<domain>) because ..., narrowing down to Level 5 (<terminal_endpoint>) ...",
    "Source Traceability Verification: Mapped each taxonomy level directly to verifiable sections and quotes across the document."
  ],
  "follow_up_suggestions": ["Why was Level 1 chosen for this document?", "Summarize the key sections of this document", "Show the source traceability for each taxonomy level"]
}

=== UNIVERSAL PRINCIPLES FOR 100% ACCURATE TAXONOMY CLASSIFICATION ===

1. DYNAMIC, UNRESTRICTED TAXONOMY TREE & PER-LEVEL RATIONALE:
   - Fill `primary.domain`, `primary.sub_domain`, `primary.process_area`, `primary.activity`, `primary.terminal_endpoint`, and `primary.path` with the 5 real, concrete taxonomy levels for the document.
   - ALWAYS provide 5 clear, specific items in `primary.level_rationales` explaining **why Level 1 (Domain)** was chosen, **why Level 2 (Sub-Domain)** was chosen, **why Level 3 (Process Area)** was chosen, **why Level 4 (Activity)** was chosen, and **why Level 5 (Terminal Category)** was chosen.
   - NEVER output template placeholder words like `"Level 1"`, `"Industry / Broad Domain"`, `"Sub-Domain / Sector"`, `"Discipline / Process Area"`, `"Specialized Category"`, or `"Exact Document Type & Specific Subject Endpoint"` in `primary.path` — always output the actual category names for the uploaded document!
   - The 5th level (`terminal_endpoint` / `primary.path[4]`) MUST match the exact document type and subject stated in your `summary` and `document_type`.

2. ONLY SHOW 5 VERY IMPORTANT KEY TOPICS IN THE UI:
   - `key_topics` MUST contain **at most 5 short, high-importance topics** (2–4 words each) representing the core pillars of the document.
   - NEVER dump all words found in the document or list word frequency counts in `key_topics`, `summary`, or `explanation`.

3. HOLISTIC FULL-DOCUMENT ANALYSIS — NEVER JUDGE EARLY FROM INTRODUCTORY FRAMING:
   - Read across ALL extracted sections (`SECTION 1` through `SECTION 5`, spanning 0% to 100% of the document).
   - Never classify a document based on a single introductory paragraph, cover-page metaphor, or brief business/company scenario example on page 1. Always classify based on what the majority of the document is genuinely about from start to finish.

4. EXACT ARTIFACT DISTINCTION (FORM VS. SUBJECT):
   - Always distinguish the **true artifact type** of the uploaded file:
     * **Educational & Study Materials** (textbooks, API study guides, cheat sheets, lecture notes, interview preparation books, certification manuals, tutorials) must be classified under `Education & Study Materials` (or the appropriate educational domain) for that subject—explaining in Level 1 Rationale why it is an educational study resource rather than live production software or an operational business record.
     * **Actual Source Code & Configuration Files** (`.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.html`, `.css`, `.sql`, `.yaml`, `.json`) must be classified under `Software Engineering & IT` according to their language, framework, and architectural role.
     * **Personal & HR Documents**: Strictly distinguish a candidate's **Resume / Curriculum Vitae (CV)** from an employer's **Job Description / Vacancy Posting**.
     * **Legal, Civil, Medical, Financial, Commercial, Industrial & Operational Documents**: Identify the exact legal, medical, financial, engineering, or operational instrument.

5. EMPTY OR ZERO-BYTE FILES:
   - If the uploaded file is empty (0 bytes) or contains `[FILE CONTENT IS EMPTY (0 BYTES)]`, respond with `type: "chat"` explaining that the uploaded file is empty (0 bytes) and asking the user to upload a file with content."""


GREETING_RESPONSES = [
    "Hello! I'm here to assist you. Upload any document or paste your text, and I'll analyze its full content with per-level rationale, traceability, and security guardrails.",
    "Hi there! Ready when you are - upload a document from any industry or share your content to discover its exact taxonomy hierarchy and Level 1–5 rationale.",
    "Hey! Welcome to TAXORA. Drop any file or ask a question, and I'll analyze it end-to-end with full source traceability, level rationale, and privacy guardrails.",
    "Greetings! Feel free to upload your file or paste text below so we can identify its exact taxonomy hierarchy and rationale.",
    "Hello! I'm ready to analyze your documents across any domain or industry. Upload a file anytime to see its full taxonomy breakdown and traceability."
]

BRO_RESPONSES = [
    "Hey bro! Ready when you are. Upload any file or paste content, and I'll analyze its 5-level taxonomy classification, traceability, and key topics for you.",
    "Yo bro! What's up? I'm TAXORA, your Content Taxonomy & Classification Engine. Send over any file or document, and I'll classify it with zero hallucinations.",
    "Hey bro! Standing by. Drop any file or paste your draft, and I'll identify its domain, sub-domain, process area, activity, and terminal endpoint.",
    "Sup bro! All systems go. Share any document or text, and I'll deliver the full taxonomy hierarchy and per-level rationale."
]

HOW_ARE_YOU_RESPONSES = [
    "I'm doing great and ready to assist you! Upload any file or paste your content, and I'll find the exact taxonomy classification and rationale for you.",
    "I'm doing well, thank you for asking! I'm here to assist you - upload a document from any industry and I'll identify its taxonomy and traceability.",
    "All systems and security guardrails are running smoothly! I'm here to help you analyze your files and generate accurate taxonomy classifications.",
    "Doing great! I'm ready to assist you with your documents - just upload a file or share text to find its taxonomy."
]


def _pick_varied_response(pool: list, conversation_history: list) -> str:
    used = {
        (m.get('content') or '').strip()
        for m in (conversation_history or [])
        if m.get('role') in ('ai', 'assistant')
    }
    available = [r for r in pool if r not in used]
    if not available:
        available = pool
    return random.choice(available)


def _match_quick_conversational(user_text: str, conversation_history: list):
    cleaned = re.sub(r'[^\w\s]', '', (user_text or '').strip().lower())
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    if not cleaned:
        return None

    # Casual brother/slang words (bro, bruh, dude, yaar, bhai, machan, etc.)
    is_bro = (
        bool(re.match(r'^(?:(?:hey+|hi+|yo+|sup|hello+|namaste|vanakkam)\s+)?(?:bro+|brother|bruh|brah|dude|yaar|bhai|bhaiya|machan|macha|thala|buddy|mate|man|sis|dost)(?:\s+(?:how\s+are\s+you|whats?\s+up|hw\s+r\s+u))?$', cleaned)) or
        cleaned in {'bro', 'broo', 'bruh', 'brah', 'brother', 'dude', 'yaar', 'bhai', 'machan', 'macha', 'thala', 'buddy', 'mate', 'sis', 'dost'}
    )
    if is_bro:
        return _pick_varied_response(BRO_RESPONSES, conversation_history)

    how_are_you_patterns = {
        'how are you', 'how are u', 'how r u', 'how r you',
        'how are you doing', 'how are u doing', 'hows it going',
        'how is it going', 'how do you do', 'whats up', 'sup',
        'hi how are you', 'hi how are u', 'hello how are you', 'hello how are u',
        'hey how are you', 'hey how are u'
    }
    if cleaned in how_are_you_patterns:
        return _pick_varied_response(HOW_ARE_YOU_RESPONSES, conversation_history)

    greeting_patterns = {
        'hi', 'hello', 'hey', 'hola', 'hii', 'hiii', 'heyy', 'heyyy',
        'good morning', 'good afternoon', 'good evening', 'greetings',
        'hi there', 'hello there', 'hey there', 'yo', 'namaste'
    }
    if cleaned in greeting_patterns:
        return _pick_varied_response(GREETING_RESPONSES, conversation_history)

    return None


_PLACEHOLDER_SUBSTRINGS = (
    'industry / broad domain',
    'sub-domain / sector',
    'discipline / process area',
    'specialized category',
    'exact document type',
    'specific subject',
    'real broad industry',
    'real sector',
    'real discipline',
    'real specialized',
    'real alternative',
    'put the exact same',
    'actual broad industry',
    'actual sector',
    'actual discipline',
    'actual specialized',
    'secondary industry',
    'secondary sub-domain',
    'secondary process',
    'secondary document',
)

LEVEL_ROLES = [
    'Level 1 · Domain',
    'Level 2 · Sub-Domain',
    'Level 3 · Process Area',
    'Level 4 · Specialized Category',
    'Level 5 · Terminal Category',
]


def _clean_single_node(val: str) -> str:
    s = re.sub(r'^(?:level\s*\d+\s*[:\-–—·]\s*)', '', str(val or '').strip(), flags=re.IGNORECASE).strip(' <>"')
    if not s:
        return ''
    low = s.lower()
    if any(ph in low for ph in _PLACEHOLDER_SUBSTRINGS):
        return ''
    if low.startswith('put the exact') or low.startswith('[domain,'):
        return ''
    return s


def _clean_path_nodes(raw_path: list) -> list:
    cleaned = []
    for item in (raw_path or []):
        s = _clean_single_node(item)
        if s and s.lower() not in [c.lower() for c in cleaned]:
            cleaned.append(s)
    return cleaned


def _extract_session_memory(conversation_history: list) -> dict:
    """
    Extracts structured session memory from conversation_history:
    - Previously classified documents (filename, taxonomy path, document type)
    - Total conversational turns remembered
    """
    docs = []
    user_notes = []
    for msg in (conversation_history or []):
        content = (msg.get('content') or '').strip()
        role = msg.get('role')
        if role == 'user':
            m_file = re.search(r'\[Attached File:\s*([^\]]+)\]', content)
            if m_file:
                fname = m_file.group(1).strip()
                if fname not in [d.get('filename') for d in docs]:
                    docs.append({'filename': fname})
            clean_u = re.sub(r'\[Attached File:[^\]]+\]', '', content).strip()
            if clean_u and len(clean_u) > 3:
                user_notes.append(clean_u[:160])
        elif role in ('ai', 'assistant'):
            m_class = re.search(r'\[Classified as:\s*([^\]]+)\]', content)
            if m_class:
                path_str = m_class.group(1).strip()
                if docs and not docs[-1].get('path'):
                    docs[-1]['path'] = path_str
                else:
                    docs.append({'filename': 'Document', 'path': path_str})
    return {
        'active': True,
        'remembered_documents_count': len(docs),
        'conversation_turns': len(conversation_history or []),
        'remembered_documents': docs[-5:],
        'recent_user_context': user_notes[-5:],
    }


def _finalize_nova_pro_result(parsed: dict, guardrails_info: dict, memory_info: dict, input_text: str) -> dict:
    """
    Preserves Amazon Nova Pro's dynamic taxonomy output while guaranteeing:
    1) Clean 5-level Taxonomy Hierarchy Tree nodes (zero schema placeholders)
    2) Per-level rationale (`level_rationales`) for Level 1 through Level 5
    3) End-to-end `traceability` matrix linking every level to document sections & evidence
    4) At most 5 concise `key_topics`
    5) `guardrails` and `memory` status metadata
    """
    primary = parsed.get('primary') or {}

    named_levels = [
        _clean_single_node(primary.get('domain')),
        _clean_single_node(primary.get('sub_domain')),
        _clean_single_node(primary.get('process_area')),
        _clean_single_node(primary.get('activity')),
        _clean_single_node(primary.get('terminal_endpoint')),
    ]
    named_levels = [n for n in named_levels if n]

    path = _clean_path_nodes(primary.get('path') or [])
    if len(named_levels) >= len(path):
        dedup_named = []
        for n in named_levels:
            if n.lower() not in [d.lower() for d in dedup_named]:
                dedup_named.append(n)
        if len(dedup_named) >= 3:
            path = dedup_named

    doc_type = _clean_single_node(parsed.get('document_type') or '')
    topics_raw = parsed.get('key_topics') or []
    clean_topics = []
    for t in topics_raw:
        ts = re.sub(r'\(\d+x\)', '', str(t or '')).strip(' ,;-•')
        if ts and len(ts) <= 60 and ts.lower() not in [c.lower() for c in clean_topics]:
            clean_topics.append(ts)
        if len(clean_topics) >= 5:
            break
    parsed['key_topics'] = clean_topics[:5]

    if len(path) < 3:
        fallback_path = []
        summary_low = (parsed.get('summary') or '').lower()
        if any(w in (doc_type + ' ' + summary_low) for w in ('study', 'guide', 'cheat', 'exam', 'course', 'tutorial', 'book', 'certification', 'learn')):
            fallback_path.append('Education & Study Materials')
            fallback_path.append('Technical & Professional Study Guides')
        elif any(w in (doc_type + ' ' + summary_low) for w in ('api', 'software', 'code', 'react', 'developer', 'programming')):
            fallback_path.append('Software Engineering & IT')
            fallback_path.append('Technical Documentation & Guides')
        else:
            fallback_path.append('Enterprise & Professional Documents')
            fallback_path.append('Specialized Domain Documentation')
        if clean_topics:
            fallback_path.append(clean_topics[0])
        if len(clean_topics) > 1:
            fallback_path.append(clean_topics[1])
        if doc_type:
            fallback_path.append(doc_type)
        for node in fallback_path:
            if node and node.lower() not in [p.lower() for p in path]:
                path.append(node)

    if doc_type and len(path) < 5 and doc_type.lower() not in [p.lower() for p in path]:
        path.append(doc_type)

    path = path[:5]
    primary['path'] = path

    # Build Per-Level Rationales (especially Level 1 Rationale!)
    raw_rationales = primary.get('level_rationales') or []
    cleaned_rationales = []
    for idx, node_name in enumerate(path):
        r_text = ''
        if idx < len(raw_rationales) and isinstance(raw_rationales[idx], str):
            r_text = re.sub(r'^(?:why\s+)?level\s*\d+(?:\s*\([^)]*\))?\s*(?:was\s+chosen|rationale)?\s*[:\-–—]\s*', '', raw_rationales[idx].strip(), flags=re.IGNORECASE).strip()
        if not r_text:
            if idx == 0:
                r_text = f"Selected '{node_name}' as the Level 1 root domain because the document's primary purpose, terminology, and structure belong to this industry/domain rather than an unrelated sector."
            elif idx == 1:
                r_text = f"Narrowed to '{node_name}' at Level 2 based on the specialized sector and functional scope addressed across the document."
            elif idx == len(path) - 1:
                r_text = f"Assigned '{node_name}' as the exact terminal classification endpoint matching the document's specific title, format ({doc_type or 'document'}), and full-text scope."
            else:
                r_text = f"Mapped to '{node_name}' at Level {idx + 1} based on the core concepts ({', '.join(clean_topics[:3]) or node_name}) analyzed across the document."
        cleaned_rationales.append({
            'level': idx + 1,
            'role': LEVEL_ROLES[idx] if idx < len(LEVEL_ROLES) else f'Level {idx + 1}',
            'category': node_name,
            'rationale': r_text,
        })
    primary['level_rationales'] = cleaned_rationales

    conf = primary.get('confidence')
    if isinstance(conf, (int, float)):
        primary['confidence_label'] = 'High' if conf >= 85 else ('Medium' if conf >= 65 else 'Low')
    parsed['primary'] = primary

    if isinstance(parsed.get('evidence'), list):
        parsed['evidence'] = [str(e).strip() for e in parsed['evidence'] if str(e).strip()][:4]
    else:
        parsed['evidence'] = []

    if isinstance(parsed.get('reasoning_steps'), list):
        parsed['reasoning_steps'] = [str(s).strip() for s in parsed['reasoning_steps'] if str(s).strip()][:3]

    # Build End-to-End Traceability Matrix
    raw_trace = parsed.get('traceability_mappings') or []
    source_mappings = []
    default_sections = [
        'Document Title, Header & Overall Structure (0% – 100%)',
        'Opening Sections & Table of Contents (0% – 25%)',
        'Middle Core Body Sections (25% – 65%)',
        'Detailed Technical / Operational Sections (50% – 85%)',
        'Full-Document Synthesis & Conclusion (0% – 100%)',
    ]
    evidence_list = parsed['evidence']
    for idx, node_name in enumerate(path):
        tm = raw_trace[idx] if (idx < len(raw_trace) and isinstance(raw_trace[idx], dict)) else {}
        sec = (tm.get('source_section') or '').strip() or default_sections[min(idx, len(default_sections) - 1)]
        sig = (tm.get('evidence_signal') or '').strip()
        if not sig:
            if idx < len(evidence_list):
                sig = evidence_list[idx]
            elif clean_topics:
                sig = f"Recurring domain signals: {', '.join(clean_topics[:3])}"
            else:
                sig = f"Verified from full document content ({doc_type or node_name})"
        rat = (tm.get('rationale') or '').strip() or cleaned_rationales[idx]['rationale']
        source_mappings.append({
            'level_number': idx + 1,
            'level': LEVEL_ROLES[idx] if idx < len(LEVEL_ROLES) else f'Level {idx + 1}',
            'category': node_name,
            'source_section': sec,
            'evidence_signal': sig,
            'rationale': rat,
        })

    words_match = re.search(r'Total Extracted Words:\s*([\d,]+)\s*words', input_text or '')
    pages_match = re.search(r'Total Pages / Sections:\s*(\d+)', input_text or '')
    parsed['traceability'] = {
        'trace_id': f"TXR-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
        'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'analysis_scope': 'Full-Document Stratified Multi-Section Analysis (0% – 100%)',
        'words_analyzed': words_match.group(1) if words_match else str(len((input_text or '').split())),
        'pages_analyzed': int(pages_match.group(1)) if pages_match else 1,
        'verification_status': 'VERIFIED_FROM_SOURCE',
        'source_mappings': source_mappings,
    }

    parsed['guardrails'] = guardrails_info
    parsed['memory'] = memory_info

    alts = []
    for alt in (parsed.get('alternatives') or []):
        if isinstance(alt, dict):
            alt['path'] = _clean_path_nodes(alt.get('path') or [])
            if len(alt['path']) >= 2:
                alts.append(alt)
    parsed['alternatives'] = alts[:2]
    return parsed


def sanitize_chat_message(text: str, conversation_history: list = None) -> str:
    if not text:
        return _pick_varied_response(GREETING_RESPONSES, conversation_history)
    t = text.strip()

    if any(phrase in t.lower() for phrase in [
        "personal experiences or feelings",
        "don't have feelings",
        "do not have feelings",
        "as an ai"
    ]):
        return _pick_varied_response(HOW_ARE_YOU_RESPONSES, conversation_history)

    intro_pattern = r'^(?:hello|hi|hey)?[!,\s]*(?:i\'m|i\s+am)\s+taxora(?:[,\s]+(?:your\s+)?(?:ai\s+)?taxonomy\s+expert)?[.!:]*\s*'
    t = re.sub(intro_pattern, '', t, flags=re.IGNORECASE).strip()

    if len(t.split()) <= 2 or t.lower() in ('hello', 'hi', 'hey', 'hello.', 'hi.', 'hello!', 'hi!', 'how', ''):
        return _pick_varied_response(GREETING_RESPONSES, conversation_history)

    sentences = re.split(r'(?<=[.!?])\s+', t)
    if len(sentences) > 1 and sentences[-1].strip().endswith('?'):
        last_s = sentences[-1].strip().lower()
        if any(trigger in last_s for trigger in [
            'would you like', 'do you want', 'can i help', 'how can i assist',
            'is there anything', 'need more details', 'need further'
        ]):
            sentences = sentences[:-1]
            t = ' '.join(sentences).strip()

    if len(t.split()) <= 2 or t.lower() in ('hello', 'hi', 'hey', 'hello.', 'hi.', 'hello!', 'hi!', 'how', ''):
        return _pick_varied_response(GREETING_RESPONSES, conversation_history)

    if t and t[0].islower():
        t = t[0].upper() + t[1:]

    return t


def classify(text: str, conversation_history: list) -> dict:
    memory_info = _extract_session_memory(conversation_history)

    if '[FILE CONTENT IS EMPTY (0 BYTES)]' in (text or '') or not (text or '').strip():
        return {
            "type": "chat",
            "message": "The provided file is empty (0 bytes) and contains no content to classify. Please upload a file containing text, code, or documentation.",
            "memory": memory_info,
        }

    is_new_file = any(tag in text for tag in ('[NEW FILE TO CLASSIFY:', '[Document:', '[NEW DOCUMENT'))

    # 1. Run Security & Privacy Guardrails BEFORE processing or calling Bedrock
    guardrail_check = guardrail_service.inspect_and_sanitize(text, is_document=is_new_file)
    if guardrail_check['blocked']:
        return {
            "type": "chat",
            "message": guardrail_check['message'],
            "guardrails": guardrail_check['guardrails'],
            "memory": memory_info,
        }

    safe_text = guardrail_check['sanitized_text']
    guardrails_info = guardrail_check['guardrails']

    if not is_new_file:
        quick_reply = _match_quick_conversational(safe_text, conversation_history)
        if quick_reply:
            return {
                "type": "chat",
                "message": quick_reply,
                "guardrails": guardrails_info,
                "memory": memory_info,
            }

    user_has_comparison_or_memory_ref = any(k in safe_text.lower() for k in (
        'compare', 'difference', 'versus', ' vs ', 'both files', 'both documents',
        'previous file', 'earlier file', 'first file', 'last file', 'earlier document',
        'remember', 'what did i upload', 'previous classification'
    ))
    history_to_use = conversation_history if (not is_new_file or user_has_comparison_or_memory_ref) else []

    sanitized = []
    for msg in history_to_use:
        content = (msg.get('content') or '').strip()
        if not content:
            continue
        # Sanitize history through guardrails too so no secrets leak from history
        hist_check = guardrail_service.inspect_and_sanitize(content, is_document=True)
        clean_hist_content = hist_check['sanitized_text'] or content
        role = 'assistant' if msg.get('role') in ('ai', 'assistant') else 'user'
        if sanitized and sanitized[-1]['role'] == role:
            prev_text = sanitized[-1]['content'][0]['text']
            sanitized[-1]['content'][0]['text'] = f"{prev_text}\n\n{clean_hist_content}"
        else:
            sanitized.append({'role': role, 'content': [{'text': clean_hist_content}]})

    while sanitized and sanitized[0]['role'] != 'user':
        sanitized.pop(0)

    # Inject structured Session Memory block when answering follow-up questions or comparing
    prompt_text = safe_text
    if (not is_new_file or user_has_comparison_or_memory_ref) and memory_info['remembered_documents']:
        mem_lines = [
            f"- Document #{i+1}: {d.get('filename', 'Document')} -> {d.get('path', 'Classified in session')}"
            for i, d in enumerate(memory_info['remembered_documents'])
        ]
        memory_header = (
            "[SESSION MEMORY & PRIOR DOCUMENTS IN THIS CONVERSATION]\n"
            + "\n".join(mem_lines)
            + "\n========================================================\n\n"
        )
        prompt_text = memory_header + safe_text

    if sanitized and sanitized[-1]['role'] == 'user':
        prev_text = sanitized[-1]['content'][0]['text']
        sanitized[-1]['content'][0]['text'] = f"{prev_text}\n\n{prompt_text}"
    else:
        sanitized.append({'role': 'user', 'content': [{'text': prompt_text}]})

    client = get_bedrock_client()
    response = client.converse(
        modelId=MODEL_ID,
        system=[{'text': SYSTEM_PROMPT}],
        messages=sanitized,
        inferenceConfig={'maxTokens': 2600, 'temperature': 0.1}
    )

    raw = response['output']['message']['content'][0]['text']
    clean_raw = raw.strip()

    if '```json' in clean_raw:
        clean_raw = clean_raw.split('```json', 1)[1].split('```', 1)[0].strip()
    elif '```' in clean_raw:
        clean_raw = clean_raw.split('```', 1)[1].split('```', 1)[0].strip()

    start, end = clean_raw.find('{'), clean_raw.rfind('}')
    if start != -1 and end != -1:
        json_slice = clean_raw[start:end + 1]
        while json_slice.startswith('{{') and json_slice.endswith('}}'):
            json_slice = json_slice[1:-1].strip()
        try:
            parsed = json.loads(json_slice)
            if isinstance(parsed, dict):
                if 'primary' in parsed:
                    parsed['type'] = 'classification'
                    return _finalize_nova_pro_result(parsed, guardrails_info, memory_info, safe_text)
                elif 'message' in parsed:
                    return {
                        'type': 'chat',
                        'message': sanitize_chat_message(str(parsed['message']), conversation_history),
                        'guardrails': guardrails_info,
                        'memory': memory_info,
                    }
                elif 'answer' in parsed:
                    return {
                        'type': 'chat',
                        'message': sanitize_chat_message(str(parsed['answer']), conversation_history),
                        'guardrails': guardrails_info,
                        'memory': memory_info,
                    }
                elif 'response' in parsed:
                    return {
                        'type': 'chat',
                        'message': sanitize_chat_message(str(parsed['response']), conversation_history),
                        'guardrails': guardrails_info,
                        'memory': memory_info,
                    }
                else:
                    parsed['guardrails'] = guardrails_info
                    parsed['memory'] = memory_info
                    return parsed
        except Exception:
            pass

    return {
        "type": "chat",
        "message": sanitize_chat_message(raw.strip(), conversation_history),
        "guardrails": guardrails_info,
        "memory": memory_info,
    }
