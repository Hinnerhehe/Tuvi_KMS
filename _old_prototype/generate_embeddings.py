#!/usr/bin/env python3
"""
Generate embeddings cho RAG chunks
- Use text-embedding-3-small (OpenAI) hoặc sentence-transformers (local)
- Store with metadata
"""

import json
import os
import math
from pathlib import Path
from tqdm import tqdm

# Try OpenAI first, fallback to sentence-transformers
try:
    from openai import OpenAI
    USE_OPENAI = True
    print("✅ Using OpenAI embeddings")
except ImportError:
    USE_OPENAI = False
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print("✅ Using Sentence-Transformers (local)")
    except ImportError:
        print("❌ Need openai or sentence-transformers")
        exit(1)

def chunk_generator(file_path, batch_size=100):
    """Yield chunks from JSONL file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        batch = []
        for line in f:
            data = json.loads(line)
            # Use display_text for better quality, fallback to text
            text = data.get('display_text') or data.get('text', '')
            batch.append({
                'id': data.get('id'),
                'text': text,
                'metadata': data.get('metadata', {})
            })

            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

def get_embedding(text, client):
    """Get embedding from OpenAI"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def get_embedding_local(text):
    """Get embedding from local model"""
    return model.encode(text).tolist()

def generate_embeddings(input_file, output_file, batch_size=100):
    """Generate embeddings cho all chunks"""

    client = None
    if USE_OPENAI:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY not set")
            return
        client = OpenAI(api_key=api_key)

    total_chunks = 0
    processed = 0

    # Count total chunks first
    with open(input_file, 'r', encoding='utf-8') as f:
        total_chunks = sum(1 for _ in f)

    print(f"📊 Processing {total_chunks} chunks...")

    with open(output_file, 'w', encoding='utf-8') as f_out:
        for batch in tqdm(chunk_generator(input_file, batch_size),
                         total=math.ceil(total_chunks/batch_size),
                         desc="Embedding"):

            texts = [item['text'] for item in batch]

            # Get embeddings
            if USE_OPENAI:
                # Batch request to OpenAI
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts
                )
                embeddings = [item.embedding for item in response.data]
            else:
                embeddings = model.encode(texts).tolist()

            # Write output
            for i, item in enumerate(batch):
                output = {
                    'id': item['id'],
                    'text': item['text'],
                    'embedding': embeddings[i],
                    'metadata': item['metadata']
                }
                f_out.write(json.dumps(output, ensure_ascii=False) + '\n')
                processed += 1

    print(f"✅ Done! Processed {processed} chunks")
    print(f"📁 Output: {output_file}")

if __name__ == "__main__":
    input_file = "TuVi_KMS_3Books_RAG_CHUNKS_v1.0.jsonl"
    output_file = "TuVi_KMS_3Books_EMBEDDINGS.jsonl"

    if Path(input_file).exists():
        generate_embeddings(input_file, output_file)
    else:
        print(f"Input file not found: {input_file}")
