    acc = correct / len(xte)
    meta = {"task": task, "system": "engramm", "shots": shots,
            "n_classes": n_classes, "n_test": len(xte), "acc": acc,
            "learn_ms_per_class": round(learn_ms_cls, 3),
            "query_ms_mean": round(float(np.mean(qs)), 4),
            "query_ms_p99": round(float(np.percentile(qs, 99)), 4),
            "energy_note": "27.4 mJ/query (M0-Referenz Apple M4)",
            "config": "t2_local=True"}
    with open(f"logs/m5_engramm_{task}_meta.json", "w") as f:
        json.dump(meta, f, indent=2)