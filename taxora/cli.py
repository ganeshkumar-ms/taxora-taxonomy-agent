"""Command-line interface for TAXORA (`taxora`)."""

from __future__ import annotations

import argparse
import json
import sys

from .client import DEFAULT_API_URL, TaxoraClient, TaxoraError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taxora", description="TAXORA Document Taxonomy CLI")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"TAXORA API base URL (default: {DEFAULT_API_URL})")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health", help="Check live TAXORA API health")

    p_file = sub.add_parser("classify-file", help="Upload and classify a document")
    p_file.add_argument("path", help="Local path to document (PDF, DOCX, XLSX, CSV, TXT, HTML, image, ZIP)")
    p_file.add_argument("--prompt", default="", help="Optional classification guidance or context note")

    p_text = sub.add_parser("classify-text", help="Classify text or ask TAXORA a question")
    p_text.add_argument("text", help="Text content or question to send to TAXORA")

    args = parser.parse_args(argv)
    client = TaxoraClient(api_url=args.api_url)

    try:
        if args.command == "health":
            res = client.health()
        elif args.command == "classify-file":
            res = client.classify_file(args.path, prompt=args.prompt)
        else:
            res = client.classify_text(args.text)
    except (TaxoraError, FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
