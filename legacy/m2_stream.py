def evaluate(eng: Engramm, ev) -> dict:
    hit = {"b77": [0, 0], "wili": [0, 0]}
    for b, label in ev:
        src = label.split(":", 1)[0]
        pred, _ = eng.classify(b)
        hit[src][0] += int(pred == label)
        hit[src][1] += 1
    total = sum(v[0] for v in hit.values()) / sum(v[1] for v in hit.values())
    return {"total": total,
            "b77": hit["b77"][0] / hit["b77"][1],
            "wili": hit["wili"][0] / hit["wili"][1]}