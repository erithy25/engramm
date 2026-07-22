    accs, learns = np.array(accs), np.array(learns)
    if len(seeds) > 1:
        print(f"\n  {len(seeds)} SEEDS: acc = {accs.mean():.4f} "
              f"± {accs.std(ddof=1):.4f}   Lernzeit = "
              f"{learns.mean() / 60:.1f} ± {learns.std(ddof=1) / 60:.1f} min")
    if full:
        crit = accs.mean() >= 0.94 and learns.max() < 1800
        print(f"  Vorregistriertes M1b-Kriterium (acc>=0.94, Lernzeit<30min CPU): "
              f"{'ERFUELLT' if crit else 'NICHT ERFUELLT'}")
