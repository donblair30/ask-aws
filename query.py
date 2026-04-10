"""
CLI entry point for ask-aws.

Usage:
    python query.py "How do I control access to S3 buckets?"
    python query.py --top-k 8 "What IAM policies does ECS need?"
    python query.py --service s3 "How does S3 versioning work?"
    python query.py --debug "What is an EC2 placement group?"
"""

import argparse
import sys

from rag import answer


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ask-aws",
        description="Ask natural-language questions about AWS documentation.",
    )
    parser.add_argument("question", nargs="+", help="Your question")
    parser.add_argument(
        "--top-k", type=int, default=None,
        help="Number of chunks to retrieve (default: from config)"
    )
    parser.add_argument(
        "--service", choices=["s3", "ec2", "iam"], default=None,
        help="Restrict retrieval to one AWS service"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Print retrieved chunks and similarity scores"
    )

    args = parser.parse_args()
    question = " ".join(args.question)

    print(f"\nQ: {question}\n")
    print("Searching documentation...\n")

    result = answer(question, n_results=args.top_k)

    print(result["answer"])

    print("\nSources:")
    for url in result["sources"]:
        print(f"  {url}")

    if args.debug:
        print("\n--- Retrieved chunks ---")
        for i, chunk in enumerate(result["chunks"], 1):
            print(f"\n[{i}] score={chunk['score']}  {chunk['url']}")
            print(chunk["text"][:300] + ("..." if len(chunk["text"]) > 300 else ""))


if __name__ == "__main__":
    main()
