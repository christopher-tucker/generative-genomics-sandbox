from ..inference import generate_dummy
def test_generate_shape():
    genes, expr = generate_dummy({'cell_type':'A','treatment':'X','dose':1,'timepoint':1})
    assert len(genes) == 100
    assert len(expr) == 100
