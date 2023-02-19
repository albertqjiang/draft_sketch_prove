import json
import argparse
from tqdm import tqdm
import openai
import os
from autoformalization import prompts
from autoformalization import utils
from autoformalization.checker import Checker

openai.api_key = os.environ['OPENAI_API_KEY']


def _load_data(args):
    data = json.load(open(args.datapath))
    data = data[args.split]
    _adjust_end_index(len(data), args)
    data = data[args.start_index:args.end_index]
    return data


def _adjust_end_index(data_len, args):
    if args.end_index == -1:
        args.end_index = data_len
    if args.end_index > data_len:
        args.end_index = data_len
    return args


def _save(output, args, log=True):
    os.makedirs(args.outdir, exist_ok=True)
    if args.sledgehammer_only_baseline:
        tag = 'sledgehammer_only__'
    else:
        tag = ''
    name = os.path.join(
        args.outdir,
        f'{tag}verified__minif2f_autoformalized__{args.split}__{args.start_index}_{args.end_index}.json'
    )
    json.dump(output, open(name, 'w'))
    if log:
        print(name)


def _format(formal_statement, proof):
    return ('%s\nproof -%s' % (formal_statement, proof))


def generate_proofs(prompt, args, include_sledgehammer_only):
    formal = []
    if include_sledgehammer_only:
        formal.append('\nshow ?thesis sledgehammer\nqed')
    if not args.sledgehammer_only_baseline:
        formal.extend(utils.generate_multi(prompt, n=args.num_samples, temperatures=args.temperatures))
    return formal


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # Autoformalization
    parser.add_argument('--datapath', type=str, default='./data/miniF2F/aligned/aligned_mathd_minif2f.json')
    parser.add_argument('--outdir', type=str, default='./eval')
    parser.add_argument('--split', choices=['valid', 'test'], default='valid')

    # inference
    parser.add_argument('--prompt-dir', type=str, default='./autoformalization/prompt_examples')
    parser.add_argument('--temperatures', type=float, default=[0.3], nargs='+')
    parser.add_argument('--num-samples', type=int, default=4, help='number of samples per temperature setting')
    parser.add_argument('--num-prompts', type=int, default=3, help='number of times we sample a prompt per proof')
    parser.add_argument('--num-examples-per-prompt', type=int, default=2)

    parser.add_argument('--sledgehammer-only-baseline', action='store_true')

    parser.add_argument('--start-index', type=int, default=0)
    parser.add_argument(
        '--end-index', type=int, default=-1,
        help="-1 will set the end index to the end of the list"
    )

    # Verification
    parser.add_argument('--isa-path', default='/home/seanw/Isabelle2021')
    parser.add_argument('--working-dir', default='/home/seanw/Isabelle2021/src/HOL/Examples')
    parser.add_argument('--theory-file', default='/home/seanw/Isabelle2021/src/HOL/Examples/Interactive.thy')

    args = parser.parse_args()

    examples = _load_data(args)
    print("Generating with %d examples" % len(examples))

    # Setup verifier
    checker = Checker(
        working_dir=args.working_dir,
        isa_path=args.isa_path,
        theory_file=args.theory_file,
        port=9000
    )

    prompter = prompts.Prompter(args.prompt_dir)

    output = []
    for i, example in enumerate(tqdm(examples, total=len(examples))):
        # Generate
        proofs = []
        for j in range(args.num_prompts):
            prompt = prompter.get_prompt(
                informal_problem_and_proof=prompts.MATH_example_template(example),
                formal_statement=example['formal_statement'],
                n=args.num_examples_per_prompt
            )

            proofs_ = generate_proofs(
                prompt, args,
                include_sledgehammer_only=j == 0  # try sledgehammer-only once
            )
            proofs.extend(proofs_)

        item = {
            'example': example,
            'formal': [_format(example['formal_statement'], proof) for proof in proofs]
        }

        # Verify
        results = []
        for formal in item['formal']:
            result = checker.check(formal)
            results.append(result)
            if result['success']:
                break

        any_success = any([result['success'] for result in results])
        sledgehammer_only = results[0]['success']
        print("%s\t%s\tsledgehammer_only: %s\n" % (item['example']['tag'], any_success, sledgehammer_only))
        output.append({
            'result': results,
            'example': item['example'],
            'formal': item['formal'],
        })

        _save(output, args, log=(i == 0))  # log the output filepath on the first step

    _save(output, args, log=True)

