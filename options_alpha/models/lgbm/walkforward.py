import numpy as np
from typing import List, Dict

# Refined Walk-Forward Splitting
def generate_purged_walk_forward_splits(
    n_rows: int,
    train_size: int,
    val_size: int,
    horizon: int,
    embargo: int
) -> List[dict]:
    splits = []
    cursor = train_size

    while True:
        train_end = cursor
        val_start = train_end + embargo + horizon
        val_end = val_start + val_size

        if val_end > n_rows:
            break

        splits.append({
            "train_idx": np.arange(0, train_end),
            "val_idx": np.arange(val_start, val_end)
        })

        cursor += val_size
    return splits

# Train fold functionality
# Will be implemented using imported training logic
