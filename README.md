# Autoformalization of Proofs
Authors: Sean Welleck, Albert Q. Jiang, Jin Peng Zhou

Implementation for the ICLR 2023 (Oral) paper: [Draft, Sketch, and Prove: Guiding Formal Theorem Provers with Informal Proofs](https://openreview.net/forum?id=SMa9EAovKMC).

## Results
In the results folder are the names of theorems that can be solved by
- Hmmaer + heuristics
- Human informal proofs x 100 autoformalizations
- Minerva informal proofs x 100 autoformalizations
- Minerva informal proofs x 200 autoformalizations.

It also contains the proofs found with human informal proofs x 100 autoformalizations. Sledgehammer-generated steps are labelled with a \<ATP\> \</ATP\> tag.

### Setup
```bash
python setup.py develop
```

## OpenAI keys
First of all, you should go to autoformalization/utils.py to put your openai keys there.

## Querying for autoformalizations
We use a slurm/submitit system to execute multiple queries concurrently. Take a loot at scripts/albert/parallel_codex_query_canon.py to see how it's done. Make sure to change the partition names to fit your system.

## Evaluating the queried results
Evaluating the outputs requires a [Portal-to-ISAbelle](https://github.com/albertqjiang/Portal-to-ISAbelle) to exist. Please take extra caution to verify your installation, or it could fail in surprising ways.

Then, take a look at scripts/albert/eval_script.py to see how mass evaluation is done, also with a slurm/submitit system. Adjust paths, partitions, and specifications where appropriate.

### (Warning) Working with Isabelle is not easy. Please be patient with the installations and the setting up. It will pay off.

## Citation
> @inproceedings{<br>
  jiang2023draft,<br>
  title={{Draft}, {Sketch}, and {Prove}: {Guiding} Formal Theorem Provers with Informal Proofs},<br>
  author={Albert Qiaochu Jiang and Sean Welleck and Jin Peng Zhou and Wenda Li and Jiacheng Liu and Mateja Jamnik and Timoth{\'{e}}e Lacroix and Yuhuai Wu and Guillaume Lample},<br>
  booktitle={International Conference on Learning Representations},<br>
  year={2023},<br>
  url={https://doi.org/10.48550/arXiv.2210.12283}<br>
}