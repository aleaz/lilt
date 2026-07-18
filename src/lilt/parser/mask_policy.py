"""Declarative macro argument masking policies."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pylatexenc.latexwalker import LatexMacroNode

    from lilt.parser.ast_parser import OpacityMask
    from lilt.parser.environment_stack import EnvironmentStack


MacroArgAction = Literal["skip", "opaque", "transparent"]


@dataclass(frozen=True)
class MacroArgSlot:
    """Maps a fixed pylatexenc argument index to a masking action."""

    index: int
    action: MacroArgAction


TraverseCallback = Callable[
    [object, str, "OpacityMask", list, "EnvironmentStack"], None
]


MACRO_POLICIES: dict[str, list[MacroArgSlot]] = {
    "textcolor": [
        MacroArgSlot(0, "skip"),
        MacroArgSlot(1, "opaque"),
        MacroArgSlot(2, "transparent"),
    ],
    "href": [
        MacroArgSlot(0, "skip"),
        MacroArgSlot(1, "opaque"),
        MacroArgSlot(2, "transparent"),
    ],
}


def apply_macro_policy(
    mac: str,
    node: "LatexMacroNode",
    text: str,
    mask: "OpacityMask",
    boundaries: list,
    env_stack: "EnvironmentStack",
    traverse_cb: TraverseCallback,
) -> bool:
    """Apply a registered macro policy. Returns True if handled."""
    slots = MACRO_POLICIES.get(mac)
    if slots is None or not node.nodeargd or not node.nodeargd.argnlist:
        return False

    args = list(node.nodeargd.argnlist)
    for slot in slots:
        if slot.index >= len(args):
            continue
        arg = args[slot.index]
        if slot.action == "skip" or arg is None:
            continue
        if slot.action == "opaque":
            mask.add_opaque(arg.pos, arg.pos + arg.len, "ARG")
        elif slot.action == "transparent":
            traverse_cb(arg, text, mask, boundaries, env_stack)
    return True
