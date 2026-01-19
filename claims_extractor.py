#!/usr/bin/env python3
"""
extract_claims_4.py

Reads persona statements from a text file and extracts EXACTLY 4 factual, checkable,
atomic claims per statement using an Ollama model.

Output is JSONL where each line is:
{
  "statement_id": "...",
  "politician": "...",
  "topic": "...",
  "statement": "...",
  "claims": [
    {"claim_text":"...","claim_type":"...","checkability":"...","evidence_hints":[...]},
    ...
  ],
  "model": "...",
  "meta": {...}
}

Requirements:
  pip install requests
Ollama must be running locally (default: http://localhost:11434).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# -----------------------------
# Parsing + validation helpers
# -----------------------------

JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
WS_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)

# Detect block headers like "D-S1", "R-S3"
BLOCK_ID_RE = re.compile(r"^\s*([DR]-S\d+)\s*(?:[\t| ]\s*(.*))?$", re.IGNORECASE)

def normalize_ws(s: str) -> str:
    return WS_RE.sub(" ", s).strip()

def word_count(s: str) -> int:
    return len(WORD_RE.findall(s))

def safe_json_load(text: str) -> Dict[str, Any]:
    """Parse a JSON object even if the model wraps it in ```json fences."""
    t = JSON_FENCE_RE.sub("", text.strip()).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        # try slicing from first { to last }
        start = t.find("{")
        end = t.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(t[start : end + 1])
        raise

def dedup_by_text(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for c in claims:
        txt = normalize_ws(c.get("claim_text", ""))
        key = re.sub(r"\W+", "", txt.lower())
        if not txt or key in seen:
            continue
        seen.add(key)
        c["claim_text"] = txt
        out.append(c)
    return out

# -----------------------------
# Statement loading
# -----------------------------

@dataclass
class Statement:
    statement_id: str
    politician: str = ""
    topic: str = ""
    statement: str = ""

def load_statements(path: Path) -> List[Statement]:
    """
    Supports:
    1) TSV/CSV with header including at least: statement_id, statement.
       Optional: politician, topic
    2) Plain text blocks starting with an ID line "D-S1" or "R-S2"
       and following lines until next ID are the statement.
    3) Fallback: whole file as one statement.
    """
    raw = path.read_text(encoding="utf-8", errors="replace")

    # Try CSV/TSV if it looks tabular (has header line with commas/tabs and "statement")
    first_line = raw.splitlines()[0].strip() if raw.splitlines() else ""
    looks_tabular = ("," in first_line or "\t" in first_line) and ("statement" in first_line.lower())

    if looks_tabular:
        # Sniff delimiter (tab preferred)
        delimiter = "\t" if "\t" in first_line else ","
        reader = csv.DictReader(raw.splitlines(), delimiter=delimiter)
        out: List[Statement] = []
        for row in reader:
            sid = (row.get("statement_id") or row.get("id") or row.get("sid") or "").strip()
            st = (row.get("statement") or row.get("text") or "").strip()
            if not sid:
                # fallback to row number if missing
                sid = f"S{len(out)+1}"
            if not st:
                continue
            out.append(Statement(
                statement_id=sid,
                politician=(row.get("politician") or row.get("party") or "").strip(),
                topic=(row.get("topic") or "").strip(),
                statement=st
            ))
        if out:
            return out

    # Try block format with IDs like D-S1 / R-S2
    lines = raw.splitlines()
    blocks: List[Statement] = []
    current: Optional[Statement] = None
    buf: List[str] = []

    def flush():
        nonlocal current, buf
        if current is not None:
            current.statement = "\n".join(buf).strip()
            if current.statement:
                blocks.append(current)
        current = None
        buf = []

    any_block = False
    for line in lines:
        m = BLOCK_ID_RE.match(line)
        if m:
            any_block = True
            flush()
            sid = m.group(1).strip()
            rest = (m.group(2) or "").strip()

            # Optional: allow "D-S1\tDEM\thealthcare" or "D-S1 | democrat | healthcare"
            pol = ""
            topic = ""
            if rest:
                parts = [p.strip() for p in re.split(r"[\t|]+", rest) if p.strip()]
                if parts:
                    # heuristic: if first part looks like party label
                    if parts[0].lower() in {"dem", "democrat", "republican", "rep", "d", "r"}:
                        pol = parts[0]
                        if len(parts) > 1:
                            topic = parts[1]
                    else:
                        # maybe it's topic directly
                        topic = parts[0]
                        if len(parts) > 1:
                            pol = parts[1]
            current = Statement(statement_id=sid, politician=pol, topic=topic, statement="")
        else:
            if current is None and line.strip() == "":
                continue
            if current is None:
                # If we haven't seen any block header yet, keep accumulating.
                buf.append(line)
            else:
                buf.append(line)

    if any_block:
        flush()
        if blocks:
            return blocks

    # Fallback: whole file is one statement
    return [Statement(statement_id="S1", politician="", topic="", statement=raw.strip())]

# -----------------------------
# Ollama call + prompt
# -----------------------------

PROMPT_TEMPLATE = """You are an information extraction system.

Task:
Extract EXACTLY 4 factual, checkable claims from the text below.

Rules:
- ONLY extract claims explicitly stated in the text. Do NOT add background knowledge.
- Each claim must be atomic (one verifiable fact per claim). Split compound claims.
- Each claim MUST be <= {max_words} words. If longer, split into multiple shorter atomic claims.
- Prefer specific, verifiable claims with dates, numbers, named institutions, laws, or concrete events.
- Ignore opinions, predictions, moral judgments, and vague claims.

Output MUST be valid JSON only. No extra text.

JSON schema:
{{
  "claims": [
    {{
      "claim_text": "...",
      "claim_type": "DATE|NUMBER|LAW|EVENT|ORG|OTHER",
      "checkability": "HIGH|MED|LOW",
      "evidence_hints": ["keyword1","keyword2"]
    }}
  ]
}}


Text:
<<<
{statement}
>>>
"""

def ollama_generate(
    base_url: str,
    model: str,
    prompt: str,
    temperature: float = 0.0,
    num_predict: int = 200,
    timeout_s: int = 1800
) -> str:
    url = base_url.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict
        }
    }
    r = requests.post(url, json=payload)
    r.raise_for_status()
    data = r.json()
    return (data.get("response") or "").strip()

# -----------------------------
# Extraction logic (with guardrails)
# -----------------------------

def extract_4_claims_for_statement(
    st: Statement,
    base_url: str,
    model: str,
    max_words: int = 25,
    retries: int = 2,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns (claims, meta).
    Ensures exactly 4 claims if possible. Uses retries if model under-produces or violates constraints.
    """
    topic = st.topic.strip() or "unknown"
    MAX_INPUT_CHARS = 1500  # try 1200–2000 depending on speed
    statement_for_llm = st.statement[:MAX_INPUT_CHARS]

    prompt = PROMPT_TEMPLATE.format(topic=topic, statement=statement_for_llm, max_words=max_words)

    meta: Dict[str, Any] = {"attempts": []}
    chosen: List[Dict[str, Any]] = []
    banned_texts: List[str] = []

    for attempt in range(1, retries + 2):  # initial + retries
        raw = ollama_generate(base_url, model, prompt)
        meta["attempts"].append({"attempt": attempt, "raw_len": len(raw)})

        try:
            obj = safe_json_load(raw)
        except Exception as e:
            meta["attempts"][-1]["parse_error"] = str(e)
            # tighten prompt and retry
            prompt = prompt + "\nREMINDER: Output JSON only. No markdown. No commentary."
            continue

        claims = obj.get("claims", [])
        if not isinstance(claims, list):
            claims = []

        # Normalize + dedup
        claims = dedup_by_text(claims)

        # Filter by length and novelty
        valid: List[Dict[str, Any]] = []
        for c in claims:
            txt = normalize_ws(c.get("claim_text", ""))
            if not txt:
                continue
            if txt in banned_texts:
                continue
            if word_count(txt) > max_words:
                continue
            valid.append(c)

        # Add until we have 4
        for c in valid:
            if len(chosen) >= 4:
                break
            txt = normalize_ws(c["claim_text"])
            banned_texts.append(txt)
            chosen.append({
                "claim_id": f"C{len(chosen)+1}",
                "claim_text": txt,
                "claim_type": c.get("claim_type", "OTHER"),
                "checkability": c.get("checkability", "MED"),
                "evidence_hints": c.get("evidence_hints", [])
            })

        if len(chosen) >= 4:
            return chosen[:4], meta

        # If we’re missing claims, ask the model for *new* ones not repeating existing.
        missing = 4 - len(chosen)
        already = "\n".join([f"- {c['claim_text']}" for c in chosen]) or "(none)"
        prompt = f"""You are an information extraction system.

We already extracted these claims:
{already}

Now extract {missing} ADDITIONAL claims from the same text.

Rules:
- ONLY claims explicitly stated in the text.
- Atomic: one verifiable fact per claim.
- Each claim <= {max_words} words.
- Do NOT repeat claims already listed above.
- Output JSON only.

JSON schema:
{{
  "claims": [
    {{
      "claim_text": "...",
      "claim_type": "DATE|NUMBER|LAW|EVENT|ORG|OTHER",
      "checkability": "HIGH|MED|LOW",
      "evidence_hints": ["keyword1","keyword2"]
    }}
  ]
}}

Text:
<<<
{statement_for_llm}
>>>
"""

    # If still not enough, pad with placeholders (so UI always has 4),
    # but clearly mark them as LOW checkability.
    while len(chosen) < 4:
        chosen.append({
            "claim_text": "No additional checkable claim found in the statement.",
            "claim_type": "OTHER",
            "checkability": "LOW",
            "evidence_hints": []
        })

    return chosen, meta

# -----------------------------
# CLI main
# -----------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Extract exactly 4 clickable claims per persona statement via Ollama.")
    ap.add_argument("--input", required=True, help="Path to statements.txt (or CSV/TSV/JSONL).")
    ap.add_argument("--output", default="extracted_claims.jsonl", help="Output JSONL path.")
    ap.add_argument("--model", default="HammerAI/mistral-nemo-uncensored:latest", help="Ollama model name.")
    ap.add_argument("--base-url", default="http://localhost:11434", help="Ollama base URL.")
    ap.add_argument("--max-words", type=int, default=25, help="Max words per claim.")
    ap.add_argument("--retries", type=int, default=2, help="Retries if <4 valid claims.")
    ap.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between statements (rate limiting).")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"ERROR: input file not found: {in_path}", file=sys.stderr)
        return 2

    statements = load_statements(in_path)
    if not statements:
        print("ERROR: no statements parsed from input.", file=sys.stderr)
        return 2

    out_path = Path(args.output)
    with out_path.open("w", encoding="utf-8") as f:
        for idx, st in enumerate(statements, start=1):
            claims, meta = extract_4_claims_for_statement(
                st=st,
                base_url=args.base_url,
                model=args.model,
                max_words=args.max_words,
                retries=args.retries
            )

            record = {
                "statement_id": st.statement_id or f"S{idx}",
                "politician": st.politician,
                "topic": st.topic,
                "statement": st.statement,
                "claims": claims,
                "model": args.model,
                "meta": meta
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

            if args.sleep > 0:
                time.sleep(args.sleep)

    print(f"Done. Wrote {len(statements)} rows to: {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
