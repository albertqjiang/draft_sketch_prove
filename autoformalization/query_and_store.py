import argparse
import json

from autoformalization.utils import a_single_job


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-path", type=str, required=True)
    args = parser.parse_args()

    with open(args.json_path) as f:
        json_obj = json.load(f)
        tag = json_obj["tag"]
        prompt_sample = json_obj["prompt_sample"]
        generation_params = json_obj["generation_params"]
        hashed_id = json_obj["hashed_id"]
        prompt_examples = json_obj["prompt_examples"]
        problem = json_obj["problem"]
        dump_path = json_obj["dump_path"]
        a_single_job(
            tag,
            prompt_sample,
            generation_params,
            hashed_id,
            prompt_examples,
            problem,
            dump_path,
        )
