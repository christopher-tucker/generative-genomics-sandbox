import numpy as np
import pytest

from .. import inference
from ..inference import generate_expression, _build_cond_row, _ensure_loaded


def test_build_cond_row_shape_and_dtype():
    _ensure_loaded()
    descriptor = {
        "celltype": "CD4 T cells",
        "diseasestatus": "healthy",
        "gender": "female",
        "smoker": "no",
        "age": "45",
    }
    cond_row = _build_cond_row(descriptor)

    # Use the fitted encoder to determine expected width
    dummy_row = inference._meta_df[inference._cond_fields].astype(str).iloc[[0]]
    expected_dim = inference._design_encoder.transform(dummy_row.values.astype(str)).shape[1]

    assert cond_row.shape == (1, expected_dim)
    assert cond_row.dtype == np.float32


def test_generate_expression_seeded_is_deterministic():
    descriptor = {
        "celltype": "CD4 T cells",
        "diseasestatus": "healthy",
        "gender": "female",
        "smoker": "no",
        "age": "45",
    }
    genes1, expr1, ver1 = generate_expression(descriptor, seed=42)
    genes2, expr2, ver2 = generate_expression(descriptor, seed=42)

    assert ver1 == ver2 == inference.MODEL_VERSION
    assert genes1 == genes2
    assert len(genes1) == len(expr1) == 500
    assert len(expr2) == 500

    # First few values should be stable for a fixed seed
    assert expr1[:5] == pytest.approx(
        [4.7647948265, 5.9913253784, 3.7196888924, 3.3839278221, 2.6532149315],
        rel=1e-4,
    )
    assert expr1[:5] == pytest.approx(expr2[:5], rel=1e-6)


def test_artifacts_load_and_gene_count():
    _ensure_loaded()
    assert inference._genes is not None
    assert len(inference._genes) == 500
    assert inference._model is not None
    assert inference._meta_df is not None and not inference._meta_df.empty
