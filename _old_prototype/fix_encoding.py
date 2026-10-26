#!/usr/bin/env python3
"""
Script fix encoding cho TuVi RAG chunks
- Fix text field (bị encoding sai)
- Giữ nguyên display_text (đã đúng)
- Thêm flag để identify source
"""

import json
import unicodedata
from pathlib import Path

def fix_text_encoding(text):
    """Fix encoding issues in text field"""
    if not text:
        return text

    # Try to detect and fix common encoding issues
    try:
        # If text contains garbled Vietnamese, try to fix
        # Common issue: UTF-8 bytes being interpreted as Latin-1
        fixed = text.encode('latin-1').decode('utf-8')
        return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass

    # Try normalize unicode
    fixed = unicodedata.normalize('NFC', text)
    return fixed

def process_jsonl(input_file, output_file):
    """Process JSONL file and fix encoding"""
    fixed_count = 0
    total_count = 0

    with open(input_file, 'r', encoding='utf-8') as f_in:
        with open(output_file, 'w', encoding='utf-8') as f_out:
            for line in f_in:
                total_count += 1
                try:
                    data = json.loads(line)

                    # Fix text field if it exists
                    if 'text' in data:
                        original_text = data['text']
                        fixed_text = fix_text_encoding(original_text)
                        if fixed_text != original_text:
                            data['text'] = fixed_text
                            fixed_count += 1

                    # Add encoding fix flag
                    data['encoding_fixed'] = True

                    f_out.write(json.dumps(data, ensure_ascii=False) + '\n')

                except json.JSONDecodeError:
                    print(f"Warning: Could not parse line {total_count}")
                    continue

    print(f"Processed {total_count} chunks")
    print(f"Fixed {fixed_count} text fields")
    print(f"Output: {output_file}")

if __name__ == "__main__":
    input_file = "TuVi_KMS_3Books_RAG_CHUNKS_v1.0.jsonl"
    output_file = "TuVi_KMS_3Books_RAG_CHUNKS_v1.0_FIXED.jsonl"

    if Path(input_file).exists():
        process_jsonl(input_file, output_file)
    else:
        print(f"Input file not found: {input_file}")
