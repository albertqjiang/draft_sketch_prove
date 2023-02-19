import argparse
import os
import submitit
import subprocess
import json
import time

from autoformalization.checker import evaluate_one_problem

def evaluate_a_list_of_problems(
    list_of_parameters
):
    SLURM_ARRAY_JOB_ID = os.environ.get("SLURM_ARRAY_JOB_ID", None)
    SLURM_ARRAY_TASK_ID = os.environ.get("SLURM_ARRAY_TASK_ID", None)
    SLURM_ARRAY_TASK_ID = int(SLURM_ARRAY_TASK_ID)
    isa_residue = SLURM_ARRAY_TASK_ID % 50

    progress_file_path = os.path.join(
        "/large_experiments/theorem/aqj/dumped/rerun/progress",
        f"eval_progress_{SLURM_ARRAY_JOB_ID}-{SLURM_ARRAY_TASK_ID}.txt",
    )

    good_count = 0
    for datapath, dump_path, isa_path, pisa_path, afp_path, python_file_to_execute in list_of_parameters:
        print(f"datapath: {datapath}")
        print(f"dump_path: {dump_path}")
        print(f"isa_path: {isa_path}")
        print(f"pisa_path: {pisa_path}")
        print(f"afp_path: {afp_path}")
        print(f"python_file_to_execute: {python_file_to_execute}")
        print(f"progress_file_path: {progress_file_path}")


        hashed_id = hash(datapath)

        true_isa_path = os.path.join(isa_path, f"isabelle_copy_{isa_residue}/main_isa/Isabelle2021")
        
        param_json_path = os.path.join(dump_path, f"eval_param_{hashed_id}.json")
        with open(param_json_path, "w") as f:
            json.dump(
                {
                    "datapath": datapath,
                    "dump_path": dump_path,
                    "isa_path": true_isa_path,
                    "pisa_path": pisa_path,
                    "afp_path": afp_path,
                }, f
            )
        
        dump_file_path = os.path.join(dump_path, f"{datapath.split('/')[-1].rstrip('.json')}_eval.json")
        while True:
            process = subprocess.Popen(
                ["python", python_file_to_execute, "--json-path", param_json_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            process.wait()
            if os.path.exists(dump_file_path):
                good_count += 1
                with open(progress_file_path, "w") as f:
                    f.write(f"good_count: {good_count}\n")
                break
        time.sleep(10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Autoformalization evaluation")
    parser.add_argument("--exp_name", type=str, default="eval autoformalization")
    parser.add_argument("--response-path", type=str, default="/private/home/aqj/workdir/hongwu_AUTOF_MINIF2F/2022_08_19_07_47_41/data/responses")
    parser.add_argument("--dump-path", type=str, default="/private/home/aqj/workdir/hongwu_AUTOF_MINIF2F/2022_08_19_07_47_41/data/evaluation")
    parser.add_argument("--log-folder", type=str, default="/private/home/aqj/workdir/hongwu_AUTOF_MINIF2F/2022_08_19_07_47_41/data/logs")
    parser.add_argument("--chunk-size", type=int, default=50)
    parser.add_argument("--isa-path", type=str, default="/checkpoint/aqj/isabelle_setup_copies")
    parser.add_argument("--pisa-path", type=str, default="/large_experiments/theorem/aqj/third_party_software/pisa_jars")
    parser.add_argument("--afp-path", type=str, default="/private/home/aqj/afp-2021-10-22")
    parser.add_argument("--python-file-to-execute", type=str, default="/private/home/aqj/autoformalization/autoformalization/eval_and_store.py")
    args = parser.parse_args()

    datapaths = []
    for file in os.listdir(args.response_path):
        if file.endswith(".json") and not file.startswith("param") and not os.path.isfile(os.path.join(args.dump_path, file.rstrip(".json") + "_eval.json")):
            datapaths.append(os.path.join(args.response_path, file))

    print(f"{len(datapaths)} problems to evaluate")

    executor = submitit.AutoExecutor(folder=args.log_folder)
    executor.update_parameters(
        slurm_array_parallelism=200, 
        mem_gb=50,
        cpus_per_task=10,
        timeout_min=15*100, 
        slurm_partition="Theorem_Proving,learnaccel"
    )

    # Construct sublists of parameters to execute
    chunk_size = args.chunk_size
    list_of_list_of_parameters = []
    for i in range(0, len(datapaths), chunk_size):
        list_of_parameters = []
        for datapath in datapaths[i:i+chunk_size]:
            list_of_parameters.append(
                [
                    datapath, args.dump_path, args.isa_path, args.pisa_path, args.afp_path, args.python_file_to_execute
                ]
            )
        list_of_list_of_parameters.append(list_of_parameters)

    assert len(list_of_list_of_parameters) < 1000, len(list_of_list_of_parameters)
    print(len(list_of_list_of_parameters))
    jobs = executor.map_array(evaluate_a_list_of_problems, list_of_list_of_parameters)