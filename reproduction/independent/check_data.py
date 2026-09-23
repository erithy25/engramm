import os, sys, time, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import hdc
import appendix_a as AA
from hdc import sha256_hex

RESULTS = []


def rec(section, name, got, expected):
    ok = got == expected
    RESULTS.append(dict(section=section, check=name, got=str(got), expected=str(expected), ok=bool(ok)))
    print(("PASS" if ok else "FAIL"), section, name, "| got:", got, "| exp:", expected, flush=True)


t0 = time.time()
W = hdc.load_wili()
print("wili load s", time.time() - t0)
for m, exp, size in (("x_train.txt", "afac7e069450ec7ac2995c7b8203ae9445404a68dbc7a66fedb0f64d3720a12e", 64085137),
                     ("y_train.txt", "bd0d63a9ab19cb15594588d1bb1b43c4b1b39d7f102656a391c259ca862e0753", None),
                     ("x_test.txt", "c06db2b42ae5a29428aca5ab9505c5117cbdeb82538eb1b087f55a6627c45556", 65166417),
                     ("y_test.txt", "2fbc58bc6f34c8cea1587396d82986a2637adf5ecb2b5cbd8f2a20be0f81ad11", None)):
    rec("14.1", f"{m} sha256", sha256_hex(W["member_raw"][m]), exp)
    if size:
        rec("14.1", f"{m} size", len(W["member_raw"][m]), size)
# splitlines vs raw \n split
for m, xs in (("x_train.txt", W["x_train"]), ("x_test.txt", W["x_test"])):
    raw = W["member_raw"][m]
    parts = raw.split(b"\n")
    rec("1.2", f"{m} ends with \\n and splitlines == raw \\n split", parts[-1] == b"" and parts[:-1] == xs, True)
rec("14.1", "line counts", [len(W["x_train"]), len(W["y_train"]), len(W["x_test"]), len(W["y_test"])], [117500] * 4)
rec("14.1", "first five y_train", " ".join(W["y_train_str"][:5]), "est swe mai oci tha")
rec("14.1", "labels", " ".join(W["labels"]), "ace afr als amh ang ara arg arz asm ast ava aym azb aze bak bar bcl be-tarask bel ben bho bjn bod bos bpy bre bul bxr cat cbk cdo ceb ces che chr chv ckb cor cos crh csb cym dan deu diq div dsb dty egl ell eng epo est eus ext fao fas fin fra frp fry fur gag gla gle glg glk glv grn guj hak hat hau hbs heb hif hin hrv hsb hun hye ibo ido ile ilo ina ind isl ita jam jav jbo jpn kaa kab kan kat kaz kbd khm kin kir koi kok kom kor krc ksh kur lad lao lat lav lez lij lim lin lit lmo lrc ltg ltz lug lzh mai mal map-bms mar mdf mhr min mkd mlg mlt mon mri mrj msa mwl mya myv mzn nan nap nav nci nds nds-nl nep new nld nno nob nrm nso oci olo ori orm oss pag pam pan pap pcd pdc pfl pnb pol por pus que roa-tara roh ron rue rup rus sah san scn sco sgs sin slk slv sme sna snd som spa sqi srd srn srp stq sun swa swe szl tam tat tcy tel tet tgk tgl tha ton tsn tuk tur tyv udm uig ukr urd uzb vec vep vie vls vol vro war wln wol wuu xho xmf yid yor zea zh-yue zho")
lens_tr = [len(x) for x in W["x_train"]]; lens_te = [len(x) for x in W["x_test"]]
rec("1.2", "shortest text bytes", min(min(lens_tr), min(lens_te)), 140)
rec("1.2", "longest train text bytes", max(lens_tr), 120424)
rec("1.2", "longest test text bytes / index", (max(lens_te), int(np.argmax(lens_te))), (579350, 24169))
trainset = set(W["x_train"])
dup = np.array([x in trainset for x in W["x_test"]])
rec("1.3", "test_items_in_train", int(dup.sum()), 3147)
np.save(os.path.join(HERE, "out", "wili_test_dup_mask.npy"), dup)
rec("1.3", "class 0 candidates first 5 / count",
    (np.flatnonzero(W["y_train"] == 0)[:5].tolist(), int((W["y_train"] == 0).sum())), ([221, 645, 865, 914, 1063], 500))

selected, draws = hdc.select_shots(W["y_train"], 235, 10, 42)
rec("14.2", "choice class 0 (returned order)", draws[0].tolist(), [12688, 91494, 12915, 80191, 51818, 51210, 84232, 13622, 26676, 99986])
rec("14.2", "choice class 1 (returned order)", draws[1].tolist(), [95435, 48250, 42647, 79867, 100763, 20138, 54773, 62581, 69173, 110892])
rec("14.2", "selected first 16", selected[:16].tolist(), [87, 90, 135, 172, 222, 312, 352, 360, 366, 392, 438, 439, 460, 551, 602, 653])
rec("14.2", "selected last 4", selected[-4:].tolist(), [117281, 117359, 117363, 117404])
rec("14.2", "selected count / distinct", (len(selected), len(set(selected.tolist()))), (2350, 2350))
rec("14.2", "selected sha256 (u64be)", hashlib.sha256(b"".join(int(i).to_bytes(8, "big") for i in selected)).hexdigest(), "3694426073025dbb04a285b339e3319e5071c83f7950e3ffb9af5d1a3c652891")
rec("14.2", "labels of first five selected", " ".join(W["labels"][W["y_train"][i]] for i in selected[:5]), "jbo por kor ina mdf")
# Appendix A choice cross-check (all 235 classes)
g = AA.PCG64(42)
ok = True
for c in range(235):
    cand = np.flatnonzero(W["y_train"] == c).tolist()
    if AA.choice_noreplace(g, cand, 10) != draws[c].tolist():
        ok = False; break
rec("A", "appendix choice == numpy choice for all 235 classes", ok, True)
np.save(os.path.join(HERE, "out", "wili_selected.npy"), selected)

# ---------------------------------------------------------------- MNIST
t0 = time.time()
M = hdc.load_mnist()
print("mnist load s", time.time() - t0)
r = M["raw"]
rec("14.1", "train images header", r["xtr_raw"][:16].hex(), "00000803" "0000ea60" "0000001c" "0000001c")
rec("14.1", "test images header", r["xte_raw"][:16].hex(), "00000803" "00002710" "0000001c" "0000001c")
import struct
rec("14.1", "train labels magic/count", struct.unpack(">II", r["ytr_raw"][:8]), (2049, 60000))
rec("14.1", "test labels magic/count", struct.unpack(">II", r["yte_raw"][:8]), (2049, 10000))
rec("1.4", "decompressed sizes", [len(r[k]) for k in ("xtr_raw", "ytr_raw", "xte_raw", "yte_raw")], [47040016, 60008, 7840016, 10008])
rec("14.1", "y_train[0:10]", M["y_train"][:10].tolist(), [5, 0, 4, 1, 9, 2, 1, 3, 1, 4])
rec("14.1", "y_test[0:10]", M["y_test"][:10].tolist(), [7, 2, 1, 0, 4, 1, 4, 9, 5, 9])
rec("14.1", "train class counts", np.bincount(M["y_train"], minlength=10).tolist(), [5923, 6742, 5958, 6131, 5842, 5421, 5918, 6265, 5851, 5949])
rec("14.1", "train pixels sha256", sha256_hex(np.ascontiguousarray(M["x_train"]).tobytes()), "741c988805d008ac6e4c904b69001ba184c24b2c540a4ef403f4c71b676cf757")
rec("14.1", "test pixels sha256", sha256_hex(np.ascontiguousarray(M["x_test"]).tobytes()), "6d87418db22cc8025d05968bec9bd5c3932904b23485740db143a061a2c9d161")

with open(os.path.join(HERE, "out", "checks_data.json"), "w") as f:
    json.dump(RESULTS, f, indent=1)
print("n_fail", sum(not r["ok"] for r in RESULTS))
