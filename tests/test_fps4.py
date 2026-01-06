import os

from libvespy import fps4


target = os.path.join("./artifacts/BTL_PACK.DAT")
out_dir = os.path.join("./artifacts/BTL_PACK")
manifest_dir = os.path.join("./artifacts/.manifest", "BTL_PACK.json")

assert os.path.exists(target)

fps4.extract(target, out_dir, manifest_dir)
