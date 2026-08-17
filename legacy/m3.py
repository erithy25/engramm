def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")
    p = sub.add_parser("run")
    p.add_argument("--authors", type=int, default=1000)
    p.add_argument("--tranches", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-t2", action="store_true")
    p.add_argument("--log-l2", action="store_true", default=True)
    p.add_argument("--no-log", dest="log_l2", action="store_false")
    q = sub.add_parser("orderinv")
    q.add_argument("--authors", type=int, default=1000)
    q.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    if a.cmd == "prepare":
        cmd_prepare()
    elif a.cmd == "orderinv":
        cmd_orderinv(a.authors, a.seed)
    else:
        cmd_run(a.authors, a.tranches, a.seed, a.no_t2, a.log_l2)
