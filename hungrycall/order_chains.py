"""Order wish chains: config parsing, call instructions and result evaluation.

The approved blueprint deliberately has one source of truth. ``OrderChain`` is
rendered as cells in the browser, serialized as config, translated into the
voice-agent task here, and used again to judge the structured answer.
"""

from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional, Tuple, Union

from hungrycall.call_language import call_language
from hungrycall.models import (
    CriterionKind,
    CriterionReaction,
    NothingAvailableRule,
    OrderCell,
    OrderChain,
    OrderCriterion,
)


@dataclass
class OrderSelection:
    position_index: int
    cell_index: int
    cell: OrderCell
    tags: List[str]
    criterion_results: Dict[int, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class OrderChainEvaluation:
    success: bool
    aborted: bool = False
    accepted: List[OrderSelection] = field(default_factory=list)
    skipped_positions: List[int] = field(default_factory=list)
    reason: Optional[str] = None


def parse_order_chain(raw: Union[str, Dict[str, Any], OrderChain, None]) -> Optional[OrderChain]:
    """Parse the JSON config carried by the web form.

    ``None`` and an empty string preserve compatibility with table bookings
    and with the earlier food form. Invalid supplied config is never ignored.
    """
    if raw in (None, ""):
        return None
    if isinstance(raw, OrderChain):
        return raw
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("order_chain_json is not valid JSON") from exc
    return OrderChain.from_dict(raw)


def order_chain_json(chain: OrderChain) -> str:
    return json.dumps(chain.to_dict(), ensure_ascii=False, separators=(",", ":"))


def default_order_chain() -> OrderChain:
    return OrderChain.from_dict({
        "version": 1,
        "posten": [{
            "zellen": [{
                "menge": 1,
                "produkt": "Burger",
                "art": "essen",
                "kriterien": [],
            }],
            "tags": [],
            "wenn_nichts_verfuegbar": "posten_weglassen",
        }],
    })


def _reaction_instruction(reaction: CriterionReaction) -> str:
    if reaction is CriterionReaction.ACCEPT:
        return "accept the criterion and continue with this cell"
    if reaction is CriterionReaction.NEXT_REPLACEMENT:
        return "discard this cell and try the next replacement cell"
    return "reject this position immediately and apply the position end rule"


def _criterion_instruction(criterion: OrderCriterion, index: int) -> str:
    prefix = f"Criterion {index} ({criterion.kind.value})"
    yes = _reaction_instruction(criterion.on_yes)
    no = _reaction_instruction(criterion.on_no)
    if criterion.kind is CriterionKind.MAX_PRICE:
        return (
            f"{prefix}: ask for the exact unit price. At or below "
            f"{float(criterion.value):.2f} EUR: {yes}; above it, vague, or missing: {no}."
        )
    if criterion.kind is CriterionKind.SPECIAL_REQUEST:
        return (
            f"{prefix}: ask whether '{criterion.value}' can be fulfilled and wait for "
            f"confirmation. Confirmed: {yes}; not confirmed: {no}."
        )
    return (
        f"{prefix}: ask exactly \"{criterion.value}\". "
        f"Yes: {yes}; no: {no}."
    )


def _cell_availability_question(locale: str, product: str) -> str:
    """The VERBATIM-quoted availability question, in the call's language.

    Field-trial feedback 2026-08-11: availability first and in general
    terms, price second, quantity only once the price holds. The question
    is quoted with ``ask exactly "..."`` and therefore spoken verbatim
    (AGENTS.md), so it must already be in the call's own language.
    """
    if locale == "en":
        return f"Do you have {product}?"
    return f"Haben Sie {product}?"


def _order_chain_style_example(locale: str) -> List[str]:
    """The worked dialogue example, in the call's language (verbatim-quoted)."""
    if locale == "en":
        return [
            "Example of the expected conversational style (English; adapt to the actual items):",
            '  You: "The pizza is too expensive for my client. Do you have Pasta Napoli instead?"',
            '  Restaurant: "Yes." - You: "What does that cost?" - Restaurant: "9 euros."',
            '  You: "That is an acceptable price, then we will take two of those."',
            "And when a hard limit fails at the end, announce the abort the same way:",
            '  You: "That puts the total order over my client\'s budget. '
            'Then we will not order anything today. Thank you very much, goodbye!"',
        ]
    return [
        "Example of the expected conversational style (German; adapt to the actual items):",
        '  Sie: "Die Pizza ist meinem Auftraggeber leider zu teuer. Haben Sie stattdessen Pasta Napoli?"',
        '  Restaurant: "Ja." - Sie: "Was kostet die?" - Restaurant: "9 Euro."',
        '  Sie: "Das ist ein akzeptabler Preis, dann nehmen wir zwei davon."',
        "And when a hard limit fails at the end, announce the abort the same way:",
        '  Sie: "Damit liegt die Bestellung insgesamt über dem Budget meines Auftraggebers. '
        'Dann bestellen wir heute leider nichts. Vielen Dank, auf Wiederhören!"',
    ]


def build_order_chain_instruction(chain: OrderChain, locale: Optional[str] = None) -> str:
    """Translate section 3 of BLUEPRINT-BESTELLKETTEN.md into the call task.

    ``locale`` selects the language of the VERBATIM-quoted fragments (the
    availability question and the worked dialogue example). Everything else
    here is meta-instruction and stays English regardless of locale, because
    CALL-E rephrases unquoted instructions into the call's own language
    (field trial 2026-08-11). Defaults to ``call_language().locale`` —
    ``call_language.py`` is the single seam that also sets the CALL-E
    recipient's region/locale, so an unset ``HUNGRYCALL_CALL_LOCALE`` keeps
    this function's output byte-identical to before locale support existed.
    """
    locale = locale or call_language().locale
    lines = [
        "Work through the order wish chain in position order. Do not reorder positions or replacements.",
        "For each position, try its cells in order. Never order more than one cell from one position.",
    ]
    for position_index, position in enumerate(chain.positions, start=1):
        # Coverage-map finding #20 (CONVERSATION-TREE.md §4 row 20): tags
        # used to be printed here as "(tags: X)", but nothing ever told the
        # agent what to do with them -- they exist solely for the result
        # screen's grouping (render_tag_summary, populated straight from
        # position.tags via evaluate_order_chain's OrderSelection, never
        # from this text). Text in the prompt nobody needs is noise for the
        # voice agent; dropped rather than paired with an instruction that
        # would have had to invent a purpose the tags do not actually have.
        lines.append(f"Position {position_index}:")
        for cell_index, cell in enumerate(position.cells, start=1):
            question = _cell_availability_question(locale, cell.product)
            lines.append(
                f"  Cell {cell_index}: ask exactly \"{question}\" — availability "
                "only, do not mention any quantity yet. If not available, try the next cell. "
                "If available, check the following criteria in order."
            )
            if cell.criteria:
                for criterion_index, criterion in enumerate(cell.criteria, start=1):
                    lines.append("    " + _criterion_instruction(criterion, criterion_index))
            else:
                lines.append("    There are no additional criteria; accept this cell.")
            lines.append(
                f"    Only after every applicable criterion is accepted, state the quantity now: "
                f"order {cell.quantity} x {cell.product} for this position, "
                "then continue with the next position."
            )
            # Field-trial finding 2026-08-11: the agent stated the quantity
            # here correctly but silently placed and confirmed a smaller
            # amount later in the same call. The commitment must be repeated
            # at the point where it is actually placed, not stated once and
            # assumed to carry through the rest of the conversation.
            lines.append(
                f"    When you later place and summarize the order, place and confirm exactly "
                f"{cell.quantity} x {cell.product} for this position — never a smaller or "
                "different amount, even if the conversation drifted."
            )
        if position.if_nothing_available is NothingAvailableRule.SKIP_ITEM:
            lines.append(
                "  If no cell carries, say briefly that this item is dropped, record this "
                "position as skipped and continue with the next position."
            )
        else:
            lines.append(
                "  If no cell carries, the whole order is off: say clearly that you will "
                "not order anything, thank them and end the conversation politely. Do NOT "
                "move on to any later position and do NOT ask for any total price."
            )
    lines.extend([
        "Announce every decision aloud as you go: which item you are taking, which you are "
        "dropping, and at the end whether you are placing an order at all.",
        *_order_chain_style_example(locale),
        "Never ask for a total price when nothing has been settled for the order.",
        "Return evidence for every attempted cell in order_chain_results; never infer a price or "
        "answer. For every cell you took (available and every criterion passed), report the "
        "quantity you actually placed in menge_bestellt — it must equal the quantity stated for "
        "that cell above. Omit menge_bestellt entirely for a cell you did not take.",
        "Place the order only after all positions have resolved under these rules.",
    ])
    return "\n".join(lines)


def _criterion_reaction(
    criterion: OrderCriterion,
    result: Dict[str, Any],
) -> Tuple[Optional[CriterionReaction], Optional[str]]:
    if criterion.kind is CriterionKind.MAX_PRICE:
        price = result.get("preis_eur")
        if result.get("preis_bekannt") is not True or not isinstance(price, (int, float)):
            return criterion.on_no, None
        return (criterion.on_yes if float(price) <= float(criterion.value) else criterion.on_no), None
    if criterion.kind is CriterionKind.SPECIAL_REQUEST:
        confirmed = result.get("bestaetigt")
        if not isinstance(confirmed, bool):
            return None, "sonderwunsch result must contain boolean bestaetigt"
        return (criterion.on_yes if confirmed else criterion.on_no), None
    answer = result.get("antwort_ja")
    if not isinstance(answer, bool):
        return None, "rueckfrage result must contain boolean antwort_ja"
    return (criterion.on_yes if answer else criterion.on_no), None


def _apply_position_end_rule(
    chain: OrderChain,
    position_index: int,
    evaluation: OrderChainEvaluation,
) -> Optional[OrderChainEvaluation]:
    position = chain.positions[position_index]
    if position.if_nothing_available is NothingAvailableRule.SKIP_ITEM:
        evaluation.skipped_positions.append(position_index)
        return None
    evaluation.success = False
    evaluation.aborted = True
    evaluation.reason = f"position {position_index + 1} failed and requires bestellung_abbrechen"
    return evaluation


def evaluate_order_chain(
    chain: OrderChain,
    structured_result: Dict[str, Any],
) -> OrderChainEvaluation:
    """Recompute the chain decision from raw structured evidence.

    Reported outcome labels are intentionally ignored. The evaluator follows
    the configured reactions itself, so an agent cannot turn a hard criterion
    into a soft one merely by returning ``outcome=accepted``.
    """
    raw_positions = structured_result.get("order_chain_results")
    if not isinstance(raw_positions, list):
        return OrderChainEvaluation(False, reason="order_chain_results is missing")

    position_results = {
        item.get("posten_index"): item
        for item in raw_positions
        if isinstance(item, dict) and isinstance(item.get("posten_index"), int)
    }
    evaluation = OrderChainEvaluation(success=True)

    for position_index, position in enumerate(chain.positions):
        position_result = position_results.get(position_index)
        if not isinstance(position_result, dict):
            return OrderChainEvaluation(
                False, accepted=evaluation.accepted,
                skipped_positions=evaluation.skipped_positions,
                reason=f"result for position {position_index + 1} is missing",
            )
        raw_cells = position_result.get("zellen")
        if not isinstance(raw_cells, list):
            return OrderChainEvaluation(False, reason=f"cell results for position {position_index + 1} are missing")
        cell_results = {
            item.get("zelle_index"): item
            for item in raw_cells
            if isinstance(item, dict) and isinstance(item.get("zelle_index"), int)
        }
        selected = False
        hard_failure = False

        for cell_index, cell in enumerate(position.cells):
            cell_result = cell_results.get(cell_index)
            if not isinstance(cell_result, dict):
                return OrderChainEvaluation(
                    False, accepted=evaluation.accepted,
                    skipped_positions=evaluation.skipped_positions,
                    reason=f"result for position {position_index + 1}, cell {cell_index + 1} is missing",
                )
            available = cell_result.get("verfuegbar")
            if not isinstance(available, bool):
                return OrderChainEvaluation(False, reason="verfuegbar must be boolean")
            if not available:
                continue

            raw_criteria = cell_result.get("kriterien", [])
            if not isinstance(raw_criteria, list):
                return OrderChainEvaluation(False, reason="kriterien result must be a list")
            criterion_results = {
                item.get("kriterium_index"): item
                for item in raw_criteria
                if isinstance(item, dict) and isinstance(item.get("kriterium_index"), int)
            }
            try_next = False
            for criterion_index, criterion in enumerate(cell.criteria):
                criterion_result = criterion_results.get(criterion_index)
                if not isinstance(criterion_result, dict):
                    return OrderChainEvaluation(
                        False, accepted=evaluation.accepted,
                        skipped_positions=evaluation.skipped_positions,
                        reason=(
                            f"result for position {position_index + 1}, cell {cell_index + 1}, "
                            f"criterion {criterion_index + 1} is missing"
                        ),
                    )
                reaction, error = _criterion_reaction(criterion, criterion_result)
                if error:
                    return OrderChainEvaluation(False, reason=error)
                if reaction is CriterionReaction.NEXT_REPLACEMENT:
                    try_next = True
                    break
                if reaction is CriterionReaction.REJECT:
                    hard_failure = True
                    break
            if hard_failure:
                break
            if try_next:
                continue

            # Field-trial finding 2026-08-11: everything above this point checks
            # WHICH cell was taken, never HOW MANY were actually ordered. A cell
            # that is available and passes every criterion still is not this
            # position's answer unless the ordered quantity matches what the
            # goal told the agent to order (build_order_chain_instruction:
            # "order {cell.quantity} x {cell.product}"). Prompt coverage is not
            # result coverage — see CONVERSATION-TREE.md's Verification column.
            ordered_quantity = cell_result.get("menge_bestellt")
            if not isinstance(ordered_quantity, int):
                return OrderChainEvaluation(
                    False, accepted=evaluation.accepted,
                    skipped_positions=evaluation.skipped_positions,
                    reason=(
                        f"result for position {position_index + 1}, cell {cell_index + 1} is "
                        "missing the ordered quantity (menge_bestellt)"
                    ),
                )
            if ordered_quantity != cell.quantity:
                return OrderChainEvaluation(
                    False, accepted=evaluation.accepted,
                    skipped_positions=evaluation.skipped_positions,
                    reason=(
                        f"Ordered quantity {ordered_quantity} does not match the configured "
                        f"{cell.quantity} x {cell.product}"
                    ),
                )

            evaluation.accepted.append(OrderSelection(
                position_index=position_index,
                cell_index=cell_index,
                cell=cell,
                tags=list(position.tags),
                criterion_results=criterion_results,
            ))
            selected = True
            break

        if not selected:
            ended = _apply_position_end_rule(chain, position_index, evaluation)
            if ended:
                return ended

    if not evaluation.accepted:
        evaluation.success = False
        evaluation.reason = "all positions were skipped; an empty order must not be placed"
    return evaluation


def simulate_order_chain_result(
    chain: OrderChain,
    structured_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Create complete local fixture evidence without network access.

    This is used only by ``DryRunCallClient``. Live results must supply their
    own evidence according to the generated recipient schema.
    """
    total = structured_result.get("total_price_eur")
    price_slots = sum(
        1 for position in chain.positions for cell in position.cells[:1]
        for criterion in cell.criteria if criterion.kind is CriterionKind.MAX_PRICE
    ) or 1
    share = float(total) / price_slots if isinstance(total, (int, float)) else 0.0
    positions: List[Dict[str, Any]] = []
    for position_index, position in enumerate(chain.positions):
        cell = position.cells[0]
        criteria: List[Dict[str, Any]] = []
        for criterion_index, criterion in enumerate(cell.criteria):
            result: Dict[str, Any] = {"kriterium_index": criterion_index}
            if criterion.kind is CriterionKind.MAX_PRICE:
                result.update({
                    "preis_bekannt": True,
                    "preis_eur": min(share, float(criterion.value)),
                })
            elif criterion.kind is CriterionKind.SPECIAL_REQUEST:
                result["bestaetigt"] = criterion.on_yes is CriterionReaction.ACCEPT
            else:
                result["antwort_ja"] = criterion.on_yes is CriterionReaction.ACCEPT
            criteria.append(result)
        positions.append({
            "posten_index": position_index,
            "zellen": [{
                "zelle_index": 0,
                "verfuegbar": True,
                "menge_bestellt": cell.quantity,
                "kriterien": criteria,
            }],
        })
    return positions


def selections_by_tag(evaluation: OrderChainEvaluation) -> Dict[str, List[OrderSelection]]:
    grouped: Dict[str, List[OrderSelection]] = {}
    for selection in evaluation.accepted:
        tags = selection.tags or [""]
        for tag in tags:
            grouped.setdefault(tag, []).append(selection)
    return grouped


ORDER_CHAIN_RESULT_SCHEMA: Dict[str, Any] = {
    "type": "array",
    "description": "Evidence for every order position and every attempted replacement cell, using zero-based indexes.",
    "items": {
        "type": "object",
        "required": ["posten_index", "zellen"],
        "properties": {
            "posten_index": {"type": "integer"},
            "zellen": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["zelle_index", "verfuegbar", "kriterien"],
                    "properties": {
                        "zelle_index": {"type": "integer"},
                        "verfuegbar": {"type": "boolean"},
                        # Field-trial finding 2026-08-11: the chain instruction told the
                        # agent to order 2 x Pasta Napoli; it placed 1 x, and the app
                        # accepted the result because nothing here ever asked what
                        # quantity was actually ordered. Deliberately NOT in this cell's
                        # "required" list and NOT a nullable type (the API rejects
                        # nullable union types, upstream issue #120) -- its absence is
                        # how a cell that was never taken (unavailable or rejected by a
                        # criterion) is represented. evaluate_order_chain() enforces it
                        # as mandatory for a cell that WAS taken; the schema alone cannot
                        # express "required only when verfuegbar is true and every
                        # criterion passed" for every CALL-E-accepted schema shape.
                        "menge_bestellt": {
                            "type": "integer",
                            "description": (
                                "The quantity actually ordered for THIS cell, if and only "
                                "if it was taken (available and every criterion passed). "
                                "Omit entirely for a cell that was not taken."
                            ),
                        },
                        "kriterien": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["kriterium_index"],
                                "properties": {
                                    "kriterium_index": {"type": "integer"},
                                    "preis_bekannt": {"type": "boolean"},
                                    "preis_eur": {"type": "number"},
                                    "bestaetigt": {"type": "boolean"},
                                    "antwort_ja": {"type": "boolean"},
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}
