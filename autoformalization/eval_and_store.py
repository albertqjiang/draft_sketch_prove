import argparse
import json

from autoformalization.checker import evaluate_one_problem


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-path", type=str, required=True)
    args = parser.parse_args()

    with open(args.json_path) as f:
        json_obj = json.load(f)
        
        datapath = json_obj["datapath"]
        dump_path = json_obj["dump_path"]
        isa_path = json_obj["isa_path"]
        pisa_path = json_obj["pisa_path"]
        afp_path = json_obj["afp_path"]
        evaluate_one_problem(
            datapath,
            dump_path,
            isa_path,
            pisa_path,
            afp_path
        )
