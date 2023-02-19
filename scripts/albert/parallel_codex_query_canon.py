import os
import json
import submitit
import argparse

from tqdm import tqdm

from autoformalization.utils import get_the_type, get_a_single_sample, a_list_of_jobs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--aligned_path", type=str, default="/large_experiments/theorem/aqj/abs_fixed/aligned_problems/new_complete_mini.jsonl")
    parser.add_argument("--dump_path", type=str, default="/large_experiments/theorem/aqj/dumped/experiment_09_07/responses_with_human_proofs_3_examples")
    parser.add_argument("--log_path", type=str, default="/large_experiments/theorem/aqj/dumped/experiment_09_07/logs")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--n_examples", type=int, default=3)
    parser.add_argument("--prompts_type", type=str, default="default")
    parser.add_argument("--n_attempts", type=int, default=50)
    parser.add_argument("--chunk_size", type=int, default=50)
    parser.add_argument("--progress_path", type=str, required=True)
    parser.add_argument("--omit_informal_statement", action="store_true", default=False)
    parser.add_argument("--omit_informal_proof", action="store_true", default=False)
    parser.add_argument("--omit_formal", action="store_true", default=False)
    parser.add_argument("--codex_generation", action="store_true", default=False)
    args = parser.parse_args()
    # minerva_path = ""
    # minerva_dump_path = ""
    algined_path = args.aligned_path
    dump_path = args.dump_path
    log_path = args.log_path
    prompts_type = args.prompts_type

    name_to_info = {}
    with open(algined_path) as f:
        for line in f.readlines():
            line = json.loads(line.strip())
            problem_name = line["problem_name"]
            informal_statement = line["informal_statement"]
            informal_proof = line["informal_proof"]
            if isinstance(informal_proof, float):
                informal_proof = "We attempt this problem"

            formal_statement = line["formal_statement"]
            
            informal_statement = informal_statement if not args.omit_informal_statement else ""
            informal_proof = informal_proof if not args.omit_informal_proof else ""
            if args.codex_generation:
                informal_proof = ""
            formal_statement = formal_statement if not args.omit_formal else ""
            name_to_info[problem_name] = {
                "informal_statement": informal_statement,
                "informal_proof": informal_proof,
                "formal_statement": formal_statement,
            }

    print(len(name_to_info))
    # assert len(name_to_info) == 488

    if not os.path.isdir(dump_path):
        os.mkdir(dump_path)
    
    index = 0
    temperature_schedule = [args.temperature] * args.n_attempts
    queries_per_tag = len(temperature_schedule)
    existing_queries = dict()
    for file in os.listdir(dump_path):
        if file.endswith(".json") and not file.startswith("param"):
            tag = "_".join(file.split("_")[:-1])
            existing_queries[tag] = existing_queries.get(tag, 0) + 1

    for tag, count in existing_queries.items():
        if count == queries_per_tag:
            del name_to_info[tag]
        else:
            print(f"{dump_path}/{tag}_*.json")
            os.system(f"rm {dump_path}/{tag}_*.json")

    print(f"Number of remaining problems: {len(name_to_info)}")
    executor = submitit.AutoExecutor(folder=log_path)
    executor.update_parameters(
        slurm_array_parallelism=30, 
        mem_gb=4,
        cpus_per_task=2,
        timeout_min=10*args.chunk_size,
        slurm_partition="Theorem_Proving,learnaccel",
        gpus_per_node=0,
    )

    number_of_queries = {}
    parameters = []
    for i, (problem_name, info) in tqdm(enumerate(name_to_info.items())):
        for k in range(queries_per_tag):
            problem_name_index = number_of_queries.get(problem_name, 0)
            temperature = temperature_schedule[problem_name_index]
            number_of_queries[problem_name] = problem_name_index + 1
            
            hashed_id = hash(f"{problem_name}-{problem_name_index}")
            prompt_sample, sampled_problem_names = get_a_single_sample(
                info["informal_statement"], 
                info["informal_proof"], 
                info["formal_statement"],
                get_the_type(problem_name), 
                problem_name,
                prompts_type=prompts_type,
                n=args.n_examples,
                omit_informal_statement=args.omit_informal_statement,
                omit_informal_proof=args.omit_informal_proof,
                omit_formal=args.omit_formal,
                codex_generation=args.codex_generation,
            )
            print(hashed_id)
            # print(prompt_sample)
            # print("="*100)
            # continue
            prompt_examples = sampled_problem_names
            generation_params = {
                "temperature": temperature,
                "model": "code-davinci-002",
                "max_tokens": 2048,
                "stop": "Informal"
            }
            problem = {
                "tag": problem_name,
                "informal_statement": info["informal_statement"],
                "informal_proof": info["informal_proof"],
                "formal_statement": info["formal_statement"],
            }
            parameters.append(
                (
                    problem_name,
                    prompt_sample, 
                    generation_params, 
                    hashed_id, 
                    prompt_examples, 
                    problem, 
                    dump_path
                )
            )
    print(f"Number of queries: {len(parameters)}")

    # arg.chunk_size attempts per array job
    all_sub_lists = []
    for i in range(0, len(parameters), args.chunk_size):
        sub_list = parameters[i:i+args.chunk_size]
        all_sub_lists.append(sub_list)
    assert len(all_sub_lists) < 500, len(all_sub_lists)

    executor.map_array(a_list_of_jobs, all_sub_lists, [args.progress_path]*len(all_sub_lists))
