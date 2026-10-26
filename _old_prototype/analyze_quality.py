#!/usr/bin/env python3
"""
Analyze quality flags trong RAG chunks
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

def analyze_quality_flags(file_path):
    """Analyze quality flags trong dataset"""

    quality_flags = Counter()
    certainty_status = Counter()
    index_status = Counter()
    knowledge_types = Counter()
    taxonomy_codes = Counter()
    book_codes = Counter()

    chunks_with_flags = 0
    total_chunks = 0

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            total_chunks += 1
            data = json.loads(line)
            meta = data.get('metadata', {})

            # Quality flags
            flags = meta.get('Quality_Flags', '')
            if flags:
                chunks_with_flags += 1
                for flag in flags.split(';'):
                    quality_flags[flag.strip()] += 1

            # Certainty status
            certainty = meta.get('Source_Certainty_Status', '')
            if certainty:
                certainty_status[certainty] += 1

            # Index status
            index = meta.get('Index_Status', '')
            if index:
                index_status[index] += 1

            # Knowledge types
            ktypes = meta.get('Knowledge_Types', '')
            if ktypes:
                for kt in ktypes.split(';'):
                    knowledge_types[kt.strip()] += 1

            # Taxonomy codes
            tax = meta.get('Taxonomy_Codes', '')
            if tax:
                for t in tax.split(';'):
                    taxonomy_codes[t.strip()] += 1

            # Book codes
            book = meta.get('Book_Code', '')
            if book:
                book_codes[book] += 1

    # Print results
    print(f"\n{'='*60}")
    print(f"📊 QUALITY ANALYSIS REPORT")
    print(f"{'='*60}")
    print(f"\n📦 Total chunks: {total_chunks}")
    print(f"⚠️  Chunks with flags: {chunks_with_flags} ({100*chunks_with_flags/total_chunks:.1f}%)")

    print(f"\n{'─'*60}")
    print(f"🔴 QUALITY FLAGS:")
    for flag, count in quality_flags.most_common():
        pct = 100 * count / total_chunks
        print(f"   {flag}: {count} ({pct:.1f}%)")

    print(f"\n{'─'*60}")
    print(f"🔵 SOURCE CERTAINTY STATUS:")
    for status, count in certainty_status.most_common():
        print(f"   {status}: {count}")

    print(f"\n{'─'*60}")
    print(f"🟢 INDEX STATUS:")
    for status, count in index_status.most_common():
        print(f"   {status}: {count}")

    print(f"\n{'─'*60}")
    print(f"📚 KNOWLEDGE TYPES:")
    for kt, count in knowledge_types.most_common(10):
        print(f"   {kt}: {count}")

    print(f"\n{'─'*60}")
    print(f"🏷️  BOOKS:")
    for book, count in book_codes.most_common():
        print(f"   {book}: {count}")

    print(f"\n{'─'*60}")
    print(f"🏷️  TOP TAXONOMY CODES:")
    for tax, count in taxonomy_codes.most_common(15):
        print(f"   {tax}: {count}")

if __name__ == "__main__":
    file_path = "TuVi_KMS_3Books_RAG_CHUNKS_v1.0.jsonl"
    if Path(file_path).exists():
        analyze_quality_flags(file_path)
    else:
        print(f"File not found: {file_path}")
