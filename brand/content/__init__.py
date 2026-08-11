"""
brand/content

The content layer: a project's information, held independently of any document.

This is the object the architecture proposal
(``docs/proposals/ADOS-Creative-Layer.md`` §A) identified as the one genuinely
missing piece. Before it, a template received an untyped ``**context`` dict and
every caller invented its own keys, which meant "the same project data becomes
a report, a portfolio spread or a case study" had no subject: there was no
*data*, only a set of arguments shaped like whichever document was being built.
"""

from brand.content.model import (
    BlockRole,
    BlockType,
    ContentBlock,
    ContentModel,
)

__all__ = ["BlockRole", "BlockType", "ContentBlock", "ContentModel"]
