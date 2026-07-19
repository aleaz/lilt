"""Tests for deterministic AccuracyGate."""

from lilt.llm.critique_parser import CritiqueParser
from lilt.validation.accuracy_gate import AccuracyGate, placeholder_ref

# Residual conflict segment from Gemma Thinking-Off baseline (13ea136e).
_SOURCE_13EA = (
    '\\subsection<group_start id="5"/>Training Details<group_end id="5"/>\n'
    'We train SBERT on the combination of the SNLI <cite id="2"/> and the '
    'Multi-Genre NLI <cite id="1"/> dataset. The SNLI is a collection of '
    "570,000 sentence pairs annotated with the labels "
    '\\textit<group_start id="4"/>contradiction<group_end id="4"/>, '
    '\\textit<group_start id="3"/>eintailment<group_end id="3"/>, and '
    '\\textit<group_start id="2"/>neutral<group_end id="2"/>. MultiNLI contains '
    "430,000 sentence pairs and covers a range of genres of spoken and written "
    "text. We fine-tune SBERT with a 3-way softmax-classifier objective function "
    "for one epoch. We used a batch-size of 16, Adam optimizer with learning "
    'rate <math id="1"/>, and a linear learning rate warm-up over '
    '10<macro id="1"/> of the training data. Our default pooling strategy is '
    '\\texttt<group_start id="1"/>MEAN<group_end id="1"/>.\n\n\n\n\n'
)

_DRAFT_13EA = (
    '\\subsection<group_start id="5"/>Detalles del entrenamiento'
    '<group_end id="5"/>\n'
    "Entrenamos SBERT con la combinación de los conjuntos de datos SNLI "
    '<cite id="2"/> y Multi-Genre NLI <cite id="1"/>. SNLI es una colección de '
    "570,000 pares de oraciones anotados con las etiquetas "
    '\\textit<group_start id="4"/>contradiction<group_end id="4"/>, '
    '\\textit<group_start id="3"/>entailment<group_end id="3"/> y '
    '\\textit<group_start id="2"/>neutral<group_end id="2"/>. MultiNLI contiene '
    "430,000 pares de oraciones y cubre una gama de géneros de texto hablado y "
    "escrito. Realizamos el ajuste fino (fine-tuning) de SBERT con una función "
    "objetivo de clasificador softmax de 3 vías durante una época. Utilizamos "
    "un tamaño de lote (batch-size) de 16, el optimizador Adam con una tasa de "
    'aprendizaje <math id="1"/>, y un calentamiento de la tasa de aprendizaje '
    "(learning rate warm-up) lineal durante el "
    '<math id="1"/>10% de los datos de entrenamiento. Nuestra estrategia de '
    'pooling por defecto es \\texttt<group_start id="1"/>MEAN'
    '<group_end id="1"/>.'
)


def test_placeholder_ref_json_safe():
    assert placeholder_ref('<macro id="1"/>') == "macro#1"
    assert '"' not in placeholder_ref('<math id="2"/>')


def test_accuracy_gate_ok_matching_placeholders():
    source = 'Hello <macro id="1"/> world'
    draft = 'Hola <macro id="1"/> mundo'
    result = AccuracyGate.evaluate(source, draft)
    assert result.ok is True
    assert result.issues == []


def test_accuracy_gate_13ea136e_detects_macro_loss():
    result = AccuracyGate.evaluate(_SOURCE_13EA, _DRAFT_13EA)
    assert result.ok is False
    refs = " ".join(issue.description for issue in result.issues)
    assert "macro#1" in refs
    assert '"' not in refs
    payload = result.to_critique_json()
    assert '"requires_refine": true' in payload or '"requires_refine":true' in payload
    # Synthetic critique must be valid JSON (no raw double-quoted tags).
    parsed = CritiqueParser.try_parse(payload)
    assert parsed is not None
    assert parsed.requires_refine is True
