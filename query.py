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

from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule

from rag import answer

console = Console()


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

    console.print(f"\n[bold cyan]Q:[/bold cyan] {question}\n")
    console.print("[dim]Searching documentation...[/dim]\n")

    result = answer(question, n_results=args.top_k)

    console.print(Markdown(result["answer"]))

    console.print(Rule(style="dim"))
    console.print("[bold]Sources:[/bold]")
    for url in result["sources"]:
        console.print(f"  [dim]{url}[/dim]")

    if args.debug:
        console.print(Rule(title="Retrieved Chunks", style="dim"))
        for i, chunk in enumerate(result["chunks"], 1):
            console.print(f"\n[bold][{i}][/bold] score=[green]{chunk['score']}[/green]  [dim]{chunk['url']}[/dim]")
            console.print(chunk["text"][:300] + ("..." if len(chunk["text"]) > 300 else ""))


if __name__ == "__main__":
    main()
