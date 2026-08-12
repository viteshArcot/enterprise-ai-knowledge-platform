import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from app.config.settings import settings
from app.database.session import async_session_factory
from app.models.document import Document
from app.providers.embedding.factory import create_embedding_gateway
from app.providers.reranker.factory import create_reranker_gateway
from app.repositories.chunk import ChunkRepository


def calculate_metrics_for_question(expected_pages: set[int], retrieved_chunks: list[dict]):
    hit_at_5 = False
    hit_at_10 = False
    hit_at_20 = False
    first_relevant_rank = 0
    found_expected_pages = set()
    retrieved_pages_ordered = []

    for item in retrieved_chunks:
        rank = item["rank"]
        page_num = item["page_number"]
        if page_num is not None:
            retrieved_pages_ordered.append(page_num)
        
        is_hit = False
        if page_num in expected_pages:
            is_hit = True
            found_expected_pages.add(page_num)
        
        if is_hit:
            if first_relevant_rank == 0:
                first_relevant_rank = rank
            if rank <= 5:
                hit_at_5 = True
            if rank <= 10:
                hit_at_10 = True
            if rank <= 20:
                hit_at_20 = True

    is_complete = len(found_expected_pages) == len(expected_pages) if expected_pages else False
    rr = 1.0 / first_relevant_rank if first_relevant_rank > 0 else 0.0

    return {
        "hit_at_5": hit_at_5,
        "hit_at_10": hit_at_10,
        "hit_at_20": hit_at_20,
        "first_relevant_rank": first_relevant_rank,
        "found_expected_pages": found_expected_pages,
        "retrieved_pages_ordered": retrieved_pages_ordered,
        "is_complete": is_complete,
        "rr": rr
    }

async def run_evaluation(mode: str):
    print("============================================================")
    print(f"RAG EVALUATION: MODE = {mode.upper()}")
    print("============================================================")

    # 1. Load ground truth
    ground_truth_path = Path(__file__).parent / "ground_truth.json"
    if not ground_truth_path.exists():
        print(f"Error: Could not find ground truth dataset at {ground_truth_path}")
        sys.exit(1)

    with open(ground_truth_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    # 2. Setup dependencies
    gateway = create_embedding_gateway(settings)
    reranker_gateway = None
    if mode == "reranked":
        settings.RERANKER_ENABLED = True
        reranker_gateway = create_reranker_gateway(settings)

    async with async_session_factory() as session:
        # 3. Resolve target document
        target_doc_title = "Building Effective AI Agents"
        stmt = select(Document).where(Document.title.ilike(f"%{target_doc_title}%"))
        result = await session.execute(stmt)
        docs = result.scalars().all()

        if not docs:
            print(f"Error: Target document '{target_doc_title}' not found in the database.")
            sys.exit(1)
        
        target_doc = docs[0]

        print(f"\nDocument:\n{target_doc.title}\n")
        print(f"Questions: {len(dataset)}\n")

        chunk_repo = ChunkRepository(session)

        results = []
        metrics = {
            "overall": {"r5": 0, "r10": 0, "r20": 0, "rr": 0.0, "total": 0},
            "categories": defaultdict(lambda: {"r5": 0, "r10": 0, "r20": 0, "rr": 0.0, "total": 0, "complete": 0})
        }
        
        failures = []

        # 4. Evaluate each question
        for idx, record in enumerate(dataset, 1):
            qid = record["id"]
            category = record["category"]
            question = record["question"]
            expected_pages = set(record.get("expected_pages", []))
            
            # Embed question
            embeddings = await gateway.embed([question])
            if not embeddings:
                print(f"Failed to embed question: {qid}")
                continue
            query_embedding = embeddings[0]

            # Run existing retrieval (Top 20 or candidate limit) with page constraint if detected
            from app.services.query_analyzer import analyze_query
            analysis = analyze_query(question)
            
            similar_chunks = await chunk_repo.find_similar(
                query_embedding, 
                limit=settings.RERANK_CANDIDATE_LIMIT if mode == "reranked" else 20,
                page_number=analysis.page_number
            )
            
            if mode == "reranked":
                from app.providers.reranker.base import RerankResult
                reranked_results = await reranker_gateway.rerank(
                    query=question,
                    candidates=similar_chunks,
                    top_k=20
                )
                final_chunks = [(r.chunk, 1.0 - r.vector_similarity) for r in reranked_results]
            else:
                final_chunks = similar_chunks
            
            retrieved_items = []
            hit_at_5 = False
            hit_at_10 = False
            hit_at_20 = False
            first_relevant_rank = 0
            
            # For tracking complete vs partial evidence
            found_expected_pages = set()
            retrieved_pages_ordered = []

            for rank, (chunk, distance) in enumerate(final_chunks, 1):
                # Filter strictly by target document
                if str(chunk.document_id) != str(target_doc.id):
                    continue

                page_num = chunk.page_number
                source_type = chunk.metadata_.get("source_type", "unknown")
                similarity = 1.0 - (distance if distance is not None else 1.0)
                
                retrieved_items.append({
                    "rank": len(retrieved_items) + 1,
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "page_number": page_num,
                    "chunk_index": chunk.chunk_index,
                    "similarity": similarity,
                    "source_type": source_type
                })

            metrics_result = calculate_metrics_for_question(expected_pages, retrieved_items)
            hit_at_5 = metrics_result["hit_at_5"]
            hit_at_10 = metrics_result["hit_at_10"]
            hit_at_20 = metrics_result["hit_at_20"]
            rr = metrics_result["rr"]
            is_complete = metrics_result["is_complete"]
            first_relevant_rank = metrics_result["first_relevant_rank"]
            found_expected_pages = metrics_result["found_expected_pages"]
            retrieved_pages_ordered = metrics_result["retrieved_pages_ordered"]

            # Metrics calculation
            metrics["overall"]["total"] += 1
            metrics["overall"]["r5"] += 1 if hit_at_5 else 0
            metrics["overall"]["r10"] += 1 if hit_at_10 else 0
            metrics["overall"]["r20"] += 1 if hit_at_20 else 0
            metrics["overall"]["rr"] += rr

            metrics["categories"][category]["total"] += 1
            metrics["categories"][category]["r5"] += 1 if hit_at_5 else 0
            metrics["categories"][category]["r10"] += 1 if hit_at_10 else 0
            metrics["categories"][category]["r20"] += 1 if hit_at_20 else 0
            metrics["categories"][category]["rr"] += rr
            if is_complete:
                metrics["categories"][category]["complete"] += 1

            results.append({
                "id": qid,
                "hit_at_5": hit_at_5,
                "hit_at_10": hit_at_10,
                "hit_at_20": hit_at_20,
                "rr": rr,
                "is_complete": is_complete,
                "retrieved_items": retrieved_items
            })

            if not hit_at_5 or not is_complete:
                failures.append({
                    "id": qid,
                    "category": category,
                    "question": question,
                    "expected_pages": sorted(list(expected_pages)),
                    "found_expected_pages": sorted(list(found_expected_pages)),
                    "retrieved_pages_top_10": retrieved_pages_ordered[:10],
                    "hit_at_5": hit_at_5,
                    "hit_at_10": hit_at_10,
                    "hit_at_20": hit_at_20,
                    "first_relevant_rank": first_relevant_rank,
                    "retrieved_source_types": [item["source_type"] for item in retrieved_items[:5]]
                })

        # Print overall metrics
        total = metrics["overall"]["total"]
        if total > 0:
            print("Overall:")
            print(f"Recall@5:  {metrics['overall']['r5'] / total * 100:.1f}%")
            print(f"Recall@10: {metrics['overall']['r10'] / total * 100:.1f}%")
            print(f"Recall@20: {metrics['overall']['r20'] / total * 100:.1f}%")
            print(f"MRR:       {metrics['overall']['rr'] / total:.3f}")
        
        print("\n------------------------------------------------------------")
        print("BY CATEGORY")
        print("------------------------------------------------------------")
        print(f"{'Category':<20} {'N':<5} {'R@5':<7} {'R@10':<7} {'R@20':<7} {'MRR':<7} {'Complete%':<10}")
        for cat, m in metrics["categories"].items():
            t = m["total"]
            r5 = f"{m['r5']/t*100:.1f}%"
            r10 = f"{m['r10']/t*100:.1f}%"
            r20 = f"{m['r20']/t*100:.1f}%"
            rr = f"{m['rr']/t:.3f}"
            comp = f"{m['complete']/t*100:.1f}%"
            print(f"{cat:<20} {t:<5} {r5:<7} {r10:<7} {r20:<7} {rr:<7} {comp:<10}")

        print("\n------------------------------------------------------------")
        print("FAILURES (Did not hit all expected pages in Top 5)")
        print("------------------------------------------------------------")
        for fail in failures:
            print(f"\nID: {fail['id']}")
            print(f"Category: {fail['category']}")
            print(f"Question:\n\"{fail['question']}\"")
            print(f"\nExpected pages:\n{fail['expected_pages']}")
            print(f"Retrieved top 10 pages:\n{fail['retrieved_pages_top_10']}")
            print(f"Found required pages:\n{fail['found_expected_pages']}")
            if fail['category'] == 'visual':
                print(f"Retrieved source_types (Top 5):\n{fail['retrieved_source_types']}")
            
            print(f"\nHit@5:  {'PASS' if fail['hit_at_5'] else 'FAIL'}")
            print(f"Hit@10: {'PASS' if fail['hit_at_10'] else 'FAIL'}")
            print(f"Hit@20: {'PASS' if fail['hit_at_20'] else 'FAIL'}")
            print(f"Relevant rank: {fail['first_relevant_rank'] if fail['first_relevant_rank'] > 0 else 'None'}")
            print("------------------------------------------------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RAG Pipeline")
    parser.add_argument("--mode", type=str, choices=["baseline", "reranked"], required=True,
                        help="Mode to run the evaluation in: baseline or reranked")
    args = parser.parse_args()
    
    asyncio.run(run_evaluation(args.mode))
