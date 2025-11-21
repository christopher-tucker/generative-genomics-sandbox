import numpy as np

# Toy inference: returns deterministic pseudo-random vector based on inputs
def generate_dummy(descriptor):
    seed = hash(str(descriptor)) % (2**32)
    rng = np.random.RandomState(seed)
    genes = [f'GENE{i+1}' for i in range(100)]
    expr = rng.rand(100).tolist()
    return genes, expr
