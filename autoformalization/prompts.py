import glob
import random
import os


class Prompter(object):
    def __init__(self, prompt_dir):
        prompts = []
        for dirname in glob.glob(os.path.join(prompt_dir, '*.txt')):
            prompts.append(open(dirname).read())
        self.prompts = prompts
        print("Loaded %d prompts" % len(self.prompts))

    def _get_examples(self, n, method):
        if method == 'random':
            examples = random.sample(self.prompts, n)
        else:
            raise NotImplementedError(method)
        return examples

    def get_prompt(self, informal_problem_and_proof, formal_statement, n, method='random'):
        examples = self._get_examples(n, method)
        prompt = '\n\n'.join(examples)
        prompt += ('%s\n\nFormal:\n%s\nproof -' % (informal_problem_and_proof, formal_statement))
        return prompt


def MATH_example_template(example):
    template_ = f"""### Problem
{example['problem']}

### Solution
{example['solution']}"""
    return template_


