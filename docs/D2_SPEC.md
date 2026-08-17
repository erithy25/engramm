             rot1(V[seq[i+1]]) XOR            if ĉ ≠ c:
             V[seq[i+2]]                        A[c] += 2x−1;  A[ĉ] −= 2x−1
        acc += (2t − 1)        # int-SIMD       clip_or_halve; rebinarize both
      return [acc > 0] tiebreak V_tie         for e in topk:
                                                e.util += (e.val==c ? +1 : −1)
    QUERY(q):
      C := HNSW_search(q, ef=64, k=32)      CONSOLIDATE():               # T3
      if rand < ε: C ∪= sample(L1, 4)         for e in L0_episodes:
      for e in C:                               p := proto(e.val)
        w[e] := û(e.util) *                     if sim(e,p) > 0.12 ∧ e.util < 2:
                max(0, sim(q,e.key) − θ₀)          A[p] += 2e.key−1; e → L2
      s[c] := λe·Σ w[e|val=c]                 evict lowest decile(util,age) → L2
            + λp·sim(q, P[c])                 # Lauf ≤ 10 s; NIE Vollindex
      return argmax softmax(s/T), C

## §6 Speicherbudget

| Komponente | C-M1 (K=235, N≈2,4·10³) | C-Ziel (K=10³, N=10⁷) |
|---|---|---|
| Item-Memory inkl. ρ-Kopien | 0,96 MB | 0,96–13 MB |
| Prototypen (int16 + binär) | 5,0 MB | 22 MB |
| Episoden inkl. Index | 3,8 MB | 16.000 MB |