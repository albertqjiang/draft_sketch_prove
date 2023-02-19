import openai
import time
import os
import json
import socket
import random
import subprocess
import re


random.seed(213)
boxed_string = "\\boxed{"
theorem_string = "theorem"
oai_keys = [
    "PUT YOUR OPEN AI KEYS HERE!!!!"
]
informal_starter = "Informal:\n(*"
informal_statement_starter = "### Problem"
informal_proof_starter = "### Solution"
formal_statement_starter = "Formal:"

prompts_path = "/private/home/aqj/autoformalization/data/paper_prompt_examples"
prompts_by_category = {}
for prompt_file in os.listdir(prompts_path):
    if prompt_file.endswith("json"):
        prompt_file_path = os.path.join(prompts_path, prompt_file)
        prompt_json = json.load(open(prompt_file_path))
        tag = prompt_json["tag"]
        category = prompt_json["category"]
        prompt = prompt_json["prompt"]
        
        if category not in prompts_by_category:
            prompts_by_category[category] = {}
            
        prompts_by_category[category][tag] = prompt.strip()

ablation_prompts_path = "/private/home/aqj/autoformalization/data/ablation_prompt_examples_no_comments"
ablation_prompts_by_category = {}
for prompt_file in os.listdir(ablation_prompts_path):
    if prompt_file.endswith("json"):
        prompt_file_path = os.path.join(ablation_prompts_path, prompt_file)
        prompt_json = json.load(open(prompt_file_path))
        tag = prompt_json["tag"]
        category = prompt_json["category"]
        prompt = prompt_json["prompt"]
        
        if category not in ablation_prompts_by_category:
            ablation_prompts_by_category[category] = {}
            
        ablation_prompts_by_category[category][tag] = prompt.strip()

    
ablation_sketch_prompts_path = "/private/home/aqj/autoformalization/data/ablation_prompt_examples_no_hammers"
ablation_sketch_prompts_by_category = {}
for prompt_file in os.listdir(ablation_sketch_prompts_path):
    if prompt_file.endswith("json"):
        prompt_file_path = os.path.join(ablation_sketch_prompts_path, prompt_file)
        prompt_json = json.load(open(prompt_file_path))
        tag = prompt_json["tag"]
        category = prompt_json["category"]
        prompt = prompt_json["prompt"]
        
        if category not in ablation_sketch_prompts_by_category:
            ablation_sketch_prompts_by_category[category] = {}
            
        ablation_sketch_prompts_by_category[category][tag] = prompt.strip()
        

def generate(prompt, n=1, temperature=0.0, max_tokens=1024, failure_limit=50, failure_sleep=5):
    while True:
        import openai
        openai.api_key = os.environ['OPENAI_API_KEY']
        try:
            completion = openai.Completion.create(
                model='code-davinci-002',
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                n=n,
                stop=['\n\n'],
            )
            break
        except Exception as e:
            failure_limit -= 1
            if failure_limit == 0:
                print("too many failures, giving up")
                return ['']
            print(str(e))
            print("Retrying... (%d retries remaining)" % failure_limit)
            time.sleep(failure_sleep)

    texts = [choice['text'] for choice in completion['choices']]
    return texts


def generate_multi(prompt, n=1, temperatures=[0.0], max_tokens=1024, sleep=0):
    texts = []
    settings = [(1, 0.0)] + [(n, temp) for temp in temperatures]
    for (num_samples, temp) in settings:
        if num_samples > 0:
            texts_ = generate(
                prompt=prompt, n=num_samples, temperature=temp, max_tokens=max_tokens
            )
            texts.extend(texts_)
            if sleep > 0:
                time.sleep(sleep)
    return texts


def ad_hoc_generate(prompt, max_tokens=256, stop_sequence='\n\n', temperature=0.0):
    completion = openai.Completion.create(
        model='code-davinci-002',
        prompt=prompt,
        max_tokens=max_tokens,
        stop=[stop_sequence],
        temperature=temperature
    )
    return completion['choices'][0]['text']


def get_info_from_response_path(response_path):
    with open(response_path) as f:
        response = json.load(f)
    return {
        "id": response["id"],
        "theorem": response["problem"]["formal_statement"],
        "proof": response["generation"].strip(),
        "generation_params": response["generation_params"],
    }

def find_available_port():
    SLURM_ARRAY_TASK_ID = os.environ.get("SLURM_ARRAY_TASK_ID", None)
    SLURM_ARRAY_TASK_ID = int(SLURM_ARRAY_TASK_ID)
    assert isinstance(SLURM_ARRAY_TASK_ID, int), SLURM_ARRAY_TASK_ID
    assert SLURM_ARRAY_TASK_ID >= 0
    assert SLURM_ARRAY_TASK_ID <= 10000
    
    available_ports = [8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000, 16000, 17000]
    modulo_residue = SLURM_ARRAY_TASK_ID % len(available_ports)
    # Rotate the available ports so that the first port is different for different jobs
    available_ports = available_ports[modulo_residue:] + available_ports[:modulo_residue]

    for port in available_ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', port))
        if result != 0:
            sock.close()
            return port
    raise AssertionError


def sample_prompts(prompts_by_category, category, n=3, avoid_tag=None):
    # Sample n prompts and give their tags
    if category not in prompts_by_category:
        prompts = prompts_by_category["algebra"] | prompts_by_category["number_theory"]
    else:
        prompts = prompts_by_category[category]
    
    tags = list(prompts.keys())
    if isinstance(avoid_tag, str):
        tags = [element for element in tags if element != avoid_tag]
    sampled_tags = random.sample(tags, k=n)

    processed_sampled_prompts = []
    for tag in sampled_tags:
        sampled_prompt = prompts[tag].strip()
        if "*)\n\nFormal:" in sampled_prompt:
            index = sampled_prompt.find("*)\n\nFormal:")
            if sampled_prompt[index-1] == "\n":
                sampled_prompt = sampled_prompt[:index-1] + sampled_prompt[index:]
        elif "\n\nFormal:" in sampled_prompt:
            index = sampled_prompt.find("\n\nFormal:")
            if sampled_prompt[index-1] == "\n":
                sampled_prompt = sampled_prompt[:index-1] + sampled_prompt[index:]
        else:
            pass
        
        processed_sampled_prompts.append(sampled_prompt)
    
    prompt_string = "\n\n".join(processed_sampled_prompts)
    return prompt_string, sampled_tags

def type_conversion(problem_type):
    return {
        "Algebra": "algebra",
        "Number Theory": "number_theory",
    }[problem_type]

def get_the_type(tag):
    if "algebra" in tag:
        return "algebra"
    elif "number_theory" in tag:
        return "number_theory"
    else:
        return "unknown"

def extract_boxed_content_and_indices(proof_string: str):
    starting_index = proof_string.find(boxed_string)
    opening_brackets = 0
    for i in range(starting_index+len(boxed_string), len(proof_string)):
        if proof_string[i] == "}":
            if opening_brackets == 0:
                return proof_string[starting_index+len(boxed_string):i], \
                        (starting_index, i)
            else:
                opening_brackets -= 1
        elif proof_string[i] == "{":
            opening_brackets += 1
        else:
            pass
        
def process_formal_statements(formal_statement):
    if len(formal_statement.split()) == 0:
        pass
    else:
        if not theorem_string in formal_statement.split()[0]:
            print(formal_statement)
    starting_index = formal_statement.find(theorem_string) + len(theorem_string)
    colon_index = formal_statement.find(":")
    return formal_statement[:starting_index] + formal_statement[colon_index+1:]

def process_prompt_examples(
    prompts_by_type, 
    omit_informal_statement=False,
    omit_informal_proof=False,
    omit_formal=False,
):
    if "omission_done" not in prompts_by_type and (omit_informal_statement or omit_informal_proof or omit_formal):
        for category, category_prompt_dict in prompts_by_type.items():
            for tag, prompt in category_prompt_dict.items():
                divided_elements = re.split(f"{informal_statement_starter}|{informal_proof_starter}|{formal_statement_starter}", prompt)
                assert len(divided_elements) == 4, divided_elements
                assert divided_elements[0] == informal_starter, divided_elements[0]

                assembled_string = ""
                if not omit_informal_statement:
                    assembled_string += informal_starter + informal_statement_starter + divided_elements[1]
                if not omit_informal_proof:
                    assembled_string += informal_proof_starter + divided_elements[2]
                if not omit_formal:
                    assembled_string += formal_statement_starter + divided_elements[3]
                prompts_by_type[category][tag] = assembled_string
    prompts_by_type["omission_done"] = True
    return prompts_by_type


def get_a_single_sample(
    informal_statement, informal_proof, 
    formal_statement, problem_type, tag, 
    n=3, 
    delete_comments=False,
    prompts_type="default",
    omit_informal_statement=False,
    omit_informal_proof=False,
    omit_formal=False,
    codex_generation=False,
):
    prompts_by_type = {
        "default": prompts_by_category,
        "ablation": ablation_prompts_by_category,
        "ablation_sketch": ablation_sketch_prompts_by_category,
    }[prompts_type]
    prompts_by_type = process_prompt_examples(
        prompts_by_type,
        omit_informal_statement=omit_informal_statement,
        omit_informal_proof=omit_informal_proof,
        omit_formal=omit_formal,
    )
    proper_prefix = False

    if len(informal_proof) > 5000:
        informal_proof = informal_proof[:5000]
    while not proper_prefix:
        prompt_prefix, sampled_tags = sample_prompts(prompts_by_type, problem_type, n=n, avoid_tag=tag)
        if len(prompt_prefix) + len(informal_statement) + len(informal_proof) <= 10000:
            proper_prefix = True
    
    if delete_comments:
        prompt_prefix_lines = [line.strip() for line in prompt_prefix.split("\n")]
        lines_to_delete = []
        to_delete = False
        for i, line in enumerate(prompt_prefix_lines):
            
            if line.startswith("(*"):
                assert not to_delete
                to_delete = True
            
            if to_delete:
                lines_to_delete.append(i)

            if line.endswith("*)"):
                assert to_delete
                to_delete = False
        assert not to_delete
        prompt_prefix_lines = [line for i, line in enumerate(prompt_prefix_lines) if i not in lines_to_delete]
        prompt_prefix = "\n".join(prompt_prefix_lines)

    if boxed_string in informal_proof:
        result = extract_boxed_content_and_indices(informal_proof)
        if result is None:
            pass
        else:
            content, (si, ei) = result
            content = content.strip()
            if "Show that it is" not in informal_statement:
                informal_statement = f"{informal_statement.strip()} Show that it is {content}."
            informal_proof = informal_proof[:si] + content + informal_proof[ei+1:]
    
    formal_statement = process_formal_statements(formal_statement)
    if not codex_generation:
        total_prompt = f"{prompt_prefix}\n\n" + \
            f"Informal:\n(*" + \
            ("" if omit_informal_statement else f"{informal_statement_starter}\n\n{informal_statement}\n\n") + \
            ("" if omit_informal_proof else f"{informal_proof_starter}\n\n{informal_proof}*)\n\n") + \
            ("" if omit_formal else f"{formal_statement_starter}\n{formal_statement}")
    else:
        total_prompt = f"{prompt_prefix}\n\n" + \
            f"Informal:\n(*" + \
            ("" if omit_informal_statement else f"{informal_statement_starter}\n\n{informal_statement}\n\n") + \
            ("" if omit_informal_proof else f"{informal_proof_starter}")
    return total_prompt, sampled_tags

def a_single_job(
    tag,
    prompt_sample, 
    generation_params, 
    hashed_id, 
    prompt_examples, 
    problem, 
    dump_path
):
    index = 0
    success = False
    while (not success):
        try:
            key = oai_keys[index]
            import openai
            openai.api_key = key
            json_obj = json.loads(
                str(
                    openai.Completion.create(
                        prompt=prompt_sample.strip(),
                        **generation_params
                    )
                )
            )
            response = json_obj["choices"][0]["text"]
            success = True
        except Exception as e:
            index = (index + 1) % len(oai_keys)
            time.sleep(15)

    json.dump(
        {
            "id": hashed_id,
            "prompt_examples": prompt_examples,
            "generation_params": generation_params,
            "problem": problem,
            "generation": response
        },
        open(os.path.join(dump_path, f"{tag}_{hashed_id}.json"), "w")
    )


def a_list_of_jobs(
    list_of_parameters,
    progress_path="/large_experiments/theorem/aqj/dumped/experiment_09_07/progress",
    python_file_to_execute="/private/home/aqj/autoformalization/autoformalization/query_and_store.py"
):
    SLURM_ARRAY_TASK_ID = os.environ.get("SLURM_ARRAY_TASK_ID", None)
    SLURM_ARRAY_TASK_ID = int(SLURM_ARRAY_TASK_ID)

    progress_file_path = os.path.join(
        progress_path,
        f"progress_{SLURM_ARRAY_TASK_ID}.txt",
    )

    good_count = 0
    for tag, prompt_sample, generation_params, hashed_id, prompt_examples, problem, dump_path in list_of_parameters:
        param_json_path = os.path.join(dump_path, f"param_{tag}_{hashed_id}.json")
        with open(param_json_path, "w") as f:
            json.dump(
                {
                    "tag": tag,
                    "prompt_sample": prompt_sample,
                    "generation_params": generation_params,
                    "hashed_id": hashed_id,
                    "prompt_examples": prompt_examples,
                    "problem": problem,
                    "dump_path": dump_path
                },
                f
            )
        eval_path = os.path.join(dump_path, f"{tag}_{hashed_id}.json")

        while True:
            process = subprocess.Popen(["python", python_file_to_execute, "--json-path", param_json_path], stdout=subprocess.PIPE)
            process.wait()
            if os.path.exists(eval_path):
                good_count += 1
                with open(progress_file_path, "w") as f:
                    f.write(f"{good_count}\n")
                break
        time.sleep(10)
