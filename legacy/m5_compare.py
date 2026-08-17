    all_ok = c1 and c2 and c3 and c4
    catastrophe = gap > 15
    if all_ok and not catastrophe:
        out = "(1) VOLLER SIEG"
    elif c2 and c3 and 5 <= gap <= 15:
        out = "(2) TEILERFOLG — Effizienz-Nische, Genauigkeitslücke quantifiziert"
    elif all_ok and catastrophe:
        out = "(2) TEILERFOLG — Kriterien erfüllt, aber >15 pp Lücke auf dieser Aufgabe"
    else:
        out = "(3) NIEDERLAGE — B1 dominiert Genauigkeit bei zu kleinem Effizienzabstand"
    print(f"\n  VORREGISTRIERTER AUSGANG: {out}")