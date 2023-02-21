All problems are from the miniF2F benchmark.

The miniF2F benchmark has a significantly updated version with many errors fixed [here](https://github.com/facebookresearch/miniF2F).
But for the files in this repository/paper, we experimented with its older version [here](https://github.com/openai/miniF2F), such that the results are
comparable with other works.

Contents of each file:
- hammer_heuristics_success.txt: names of 95 theorems solved by Sledgehammer + heuristics (paper Section 4.2)
- human_100_success.txt: names of 200 theorems solved by DSP with human informal proofs (1 proof x 100 autoformalization attempts) (paper Section 4.4)
  - human_100_proofs.jsonl: formal proofs of the 200 theorems solved by DSP with human informal proofs
- minerva_100_success.txt: names of 199 theorems solved by DSP with Minerva informal proofs (100 proofs x 1 autoformalization attempt) (paper Section 4.4)
- minerva_200_success.txt: names of 209 theorems solved by DSP with Minerva informal proofs (100 proofs x 2 autoformalization attempts) (paper Section 5.2)
