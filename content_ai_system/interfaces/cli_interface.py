"""CLI interface for content generation workflows."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from content_ai_system.app import build_system
from content_ai_system.models.types import ExpansionRequest, GenerationRequest, RewriteRequest


def _parse_mix(raw_mix: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for item in raw_mix:
        if ":" not in item:
            continue
        creator, weight = item.split(":", 1)
        out[creator.strip()] = float(weight.strip()) / 100.0
    total = sum(out.values())
    if total > 0:
        return {k: v / total for k, v in out.items()}
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Knowledge Graph Content Intelligence CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", aliases=["/generate"], help="Generate new content")
    gen.add_argument("topic")
    gen.add_argument("--platform", default="LinkedIn")
    gen.add_argument("--audience", default="general")
    gen.add_argument("--goal", default="authority")
    gen.add_argument("--type", default="post", dest="content_type")

    rewrite = sub.add_parser("rewrite", aliases=["/rewrite"], help="Rewrite existing content")
    rewrite.add_argument("content")
    rewrite.add_argument("--platform", default="LinkedIn")
    rewrite.add_argument("--goal", default="clarity")

    expand = sub.add_parser("expand", aliases=["/expand"], help="Expand content to long-form")
    expand.add_argument("content")
    expand.add_argument("--target", default="Blog Article")
    expand.add_argument("--audience", default="general")

    ideas = sub.add_parser("ideas", aliases=["/ideas"], help="Generate 30 content ideas")
    ideas.add_argument("topic")

    style = sub.add_parser("style", aliases=["/style"], help="Retrieve style blueprint")
    style.add_argument("query")

    mix = sub.add_parser("mix", aliases=["/mix"], help="Generate using creator style mix")
    mix.add_argument("topic")
    mix.add_argument("--platform", default="LinkedIn")
    mix.add_argument("--audience", default="general")
    mix.add_argument("--goal", default="authority")
    mix.add_argument("--mix", nargs="+", required=True, help="Creator weights like 'Creator A:70' 'Creator B:30'")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    services = build_system()

    generator = services["generator"]
    rewrite_engine = services["rewrite_engine"]
    expander = services["expander"]
    content_os = services["content_os"]
    retriever = services["retriever"]
    blueprint_builder = services["generator"].blueprint_builder
    style_mixer = services["style_mixer"]

    if args.command in {"generate", "/generate"}:
        req = GenerationRequest(
            topic=args.topic,
            platform=args.platform,
            audience=args.audience,
            goal=args.goal,
            content_type=args.content_type,
        )
        print(generator.generate(req))

    elif args.command in {"rewrite", "/rewrite"}:
        req = RewriteRequest(content=args.content, platform=args.platform, goal=args.goal)
        print(rewrite_engine.rewrite(req))

    elif args.command in {"expand", "/expand"}:
        req = ExpansionRequest(content=args.content, target_format=args.target, audience=args.audience)
        print(expander.expand(req))

    elif args.command in {"ideas", "/ideas"}:
        print("\n".join(content_os.generate_30_content_ideas(args.topic)))

    elif args.command in {"style", "/style"}:
        retrieval = retriever.retrieve(args.query)
        blueprint = blueprint_builder.build(retrieval)
        print(json.dumps(asdict(blueprint), indent=2))

    elif args.command in {"mix", "/mix"}:
        creator_weights = _parse_mix(args.mix)
        req = GenerationRequest(
            topic=args.topic,
            platform=args.platform,
            audience=args.audience,
            goal=args.goal,
            content_type="post",
        )
        print(style_mixer.generate_with_mix(req, creator_weights=creator_weights))


if __name__ == "__main__":
    main()
