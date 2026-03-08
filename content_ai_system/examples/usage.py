"""Example usage of the Content Intelligence System."""

from __future__ import annotations

from content_ai_system.app import build_system
from content_ai_system.models.types import ExpansionRequest, GenerationRequest, RewriteRequest


def run_examples() -> None:
    system = build_system()

    generator = system["generator"]
    rewrite_engine = system["rewrite_engine"]
    expander = system["expander"]
    content_os = system["content_os"]
    style_mixer = system["style_mixer"]

    print("\n=== generate_linkedin_post(topic) ===")
    post = generator.generate(
        GenerationRequest(
            topic="AI consulting for startups",
            platform="LinkedIn",
            audience="founders",
            goal="authority",
            content_type="post",
        )
    )
    print(post)

    print("\n=== rewrite_post(content) ===")
    rewritten = rewrite_engine.rewrite(
        RewriteRequest(
            content="AI is important for companies. You should use it.",
            platform="LinkedIn",
            goal="engagement",
        )
    )
    print(rewritten)

    print("\n=== expand_to_blog(content) ===")
    expanded = expander.expand(
        ExpansionRequest(
            content="Most AI teams fail because they start with tools, not workflow bottlenecks.",
            target_format="Blog Article",
            audience="startup operators",
        )
    )
    print(expanded)

    print("\n=== generate_30_content_ideas(topic) ===")
    ideas = content_os.generate_30_content_ideas("AI GTM strategy")
    print("\n".join(ideas[:5]))

    print("\n=== style mix ===")
    mixed = style_mixer.generate_with_mix(
        GenerationRequest(
            topic="AI strategy",
            platform="LinkedIn",
            audience="B2B founders",
            goal="authority",
            content_type="post",
        ),
        creator_weights={"Creator A": 0.7, "Creator B": 0.3},
    )
    print(mixed)


if __name__ == "__main__":
    run_examples()
