import os
import shutil
import json
import signal
import subprocess
import psutil
import time

from autoformalization.utils import get_info_from_response_path


try:
    from PisaFlexibleClient import initialise_env
except:
    print("Set $PISA_PATH to /yourpath/to/Portal-to-ISAbelle/src/main/python")


class Checker(object):
    def __init__(self, working_dir, isa_path, theory_file, port=9000):
        self.working_dir = working_dir
        self.isa_path = isa_path
        self.theory_file = theory_file
        self.port = port

    def _initialize(self):
        print("Initializing environment")
        print("ISA_PATH: %s" % self.isa_path)
        print("THEORY_FILE: %s" % self.theory_file)
        print("WORKING_DIR: %s" % self.working_dir)
        env = initialise_env(
            self.port,
            working_directory=self.working_dir,
            isa_path=self.isa_path,
            theory_file_path=self.theory_file
        )
        print("Start initialising environment")
        env.post('<initialise>')
        return env

    def _exit(self, env):
        try:
            env.post('exit')
        except:
            print("env.post('exit') timed out")
            pass
        os.system("ps aux | grep Isabelle | awk '{print $2}' | xargs kill -9 > /dev/null 2>&1")
        os.system("ps aux | grep poly | awk '{print $2}' | xargs kill -9 > /dev/null 2>&1")

    def _parse_output(self, obs):
        """Parse the sledgehammer output, otherwise return an empty string"""
        if '<hammer>' in obs:
            output = obs.split('<hammer>')[0]
        else:
            output = ''
        return output

    def _run_step(self, step, i, tls_name, env):
        obs, reward, done, metadata = env.step_to_top_level_state(
            action=step,
            tls_name=tls_name,
            new_name='default_%d' % i
        )
        error = None
        if 'error:' in obs or 'Step error' in obs or 'Unknown error' in obs:
            error = obs
        return obs, reward, done, metadata, error

    def _run_sledgehammer(self, step, i, tls_name, env):
        # First try heuristics
        for heuristic in ['by auto', 'by simp', 'by blast', 'by fastforce', 'by force', 'by eval', 'by presburger', 'by sos', 'by arith', 'by linarith', 'by (auto simp: field_simps)']:
        # for heuristic in []:
            step_ = step.replace('sledgehammer', heuristic)
            obs, reward, done, metadata, error = self._run_step(step_, i, tls_name, env)
            if error is None:
                obs = '%s <hammer> %s' % (heuristic, obs)
                return obs, reward, done, metadata, error
        # Try sledgehammer
        return self._run_step(step, i, tls_name, env)

    def check(self, formal):
        # Initialize environment
        env = self._initialize()

        # Wrap and parse theorem
        theory = Checker.minif2f_wrap_theorem(formal)
        steps = Checker.get_parsed(env, theory)

        done = False
        reason = ''
        success = False
        step_results = []
        tls_name = 'default'
        for i, step in enumerate(steps):
            try:
                time0 = time.time()
                if 'sledgehammer' in step:
                    obs, reward, done, metadata, error = self._run_sledgehammer(step, i, tls_name, env)
                else:
                    obs, reward, done, metadata, error = self._run_step(step, i, tls_name, env)
                step_time = time.time() - time0
                step_results.append(dict(index=i, step=step, output=self._parse_output(obs), step_time=step_time))
                if error is not None:
                    reason = error
                    success = False
                    done = False
                    break
            except:
                # Timeout - end the proof attempt
                success = False
                done = False
                reason = 'timeout (%d)' % len(step_results)
                step_results.append(dict(index=i, step=step, output=''))
                break

            # Change when successful
            tls_name = 'default_%d' % i

        if done and reward == 1.0:
            success = True

        result = {
            'success': success,
            'reason': reason,
            'num_steps': len(steps),
            'last_step': len(step_results),
            'step_results': step_results
        }
        # Exit environment
        self._exit(env)
        return result

    @staticmethod
    def minif2f_wrap_theorem(theorem):
        return 'theory Interactive imports HOL.HOL Complex_Main "HOL-Library.Code_Target_Numeral" "HOL-Library.Sum_of_Squares" "Symmetric_Polynomials.Vieta" "HOL-Computational_Algebra.Computational_Algebra" "HOL-Number_Theory.Number_Theory" \n begin\n%s' % theorem

    @staticmethod
    def wrap_theorem(theorem):
        return 'theory Interactive imports Complex_Main \n "HOL-Computational_Algebra.Computational_Algebra" \n "HOL-Number_Theory.Number_Theory" \n begin\n%s' % theorem

    @staticmethod
    def get_parsed(env, theory, tls_name='default'):
        steps = env.post(f"<parse text> ${theory}")
        steps = steps.split('<SEP>')
        steps = [s for s in steps if s.strip() != '']
        # remove weird '$' step and whitespace steps
        steps = [s for s in steps if s != '$' and s.strip() != '']
        return steps


def evaluate_one_problem(
    datapath, 
    dump_path="/private/home/aqj/workdir/hongwu_AUTOF_MINIF2F/2022_08_19_07_47_41/data/evaluation", 
    isa_path="/private/home/aqj/Isabelle2021", 
    pisa_path="/large_experiments/theorem/aqj/third_party_software/pisa_jars", 
    afp_path="/private/home/aqj/afp-2021-10-22"
):
    file_info = get_info_from_response_path(datapath)

    job_id = os.environ.get("SLURM_JOB_ID", None)
    if os.path.exists("/scratch/slurm_tmpdir/") and job_id is not None:
        tmp_dir = f"/scratch/slurm_tmpdir/{job_id}"
        if not os.path.exists(tmp_dir):
            print(
                f"/scratch/slurm_tmpdir/{job_id} not found! not setting TMPDIR"
            )
            return
        print(f"Setting TMPDIR to {tmp_dir}")
        os.environ["TMPDIR"] = tmp_dir
    else:
        raise AssertionError("Not setting TMPDIR")

    SLURM_ARRAY_TASK_ID = os.environ.get("SLURM_ARRAY_TASK_ID", None)
    SLURM_ARRAY_TASK_ID = int(SLURM_ARRAY_TASK_ID)

    residue = SLURM_ARRAY_TASK_ID % 200
    port = residue + 8000
    jar_path = os.path.join(pisa_path, f"pisa_copy{residue}.jar")

    # Copy over the Isabelle directory
    copied_isa_path = os.path.join(tmp_dir, f"Isabelle2021_{SLURM_ARRAY_TASK_ID}")
    if not os.path.exists(copied_isa_path):
        shutil.copytree(isa_path, copied_isa_path, symlinks=True)

    # Copy over the AFP directory
    copied_afp_path = os.path.join(tmp_dir, f"afp_copy_{SLURM_ARRAY_TASK_ID}")
    if not os.path.exists(copied_afp_path):
        shutil.copytree(afp_path, copied_afp_path, symlinks=True)
    minif2f_working_directory = os.path.join(copied_afp_path, "thys", "Symmetric_Polynomials")
    minif2f_theory_filepath = os.path.join(minif2f_working_directory, "Interactive.thy")

    print("port:", port)
    sub = subprocess.Popen(["java", "-cp", jar_path, f"pisa.server.PisaOneStageServer{port}"]).pid
    print(f"Server started with pid {sub}")
    time.sleep(10)

    checker = Checker(
        working_dir=minif2f_working_directory,
        isa_path=copied_isa_path,
        theory_file=minif2f_theory_filepath,
        port=port,
    )

    result = checker.check(file_info["theorem"] + "\n" + file_info["proof"])
    dump_file_path = os.path.join(dump_path, f"{datapath.split('/')[-1].rstrip('.json')}_eval.json")
    json.dump(
        {
            "id": file_info["id"],
            "generation_params": file_info["generation_params"],
            "success": result["success"],
            "result": result,
        }, open(dump_file_path, "w")
    )

    try:
        parent = psutil.Process(sub)
        children = parent.children(recursive=True)
        for process in children:
            process.send_signal(signal.SIGTERM)
        parent.send_signal(signal.SIGTERM)
    except psutil.NoSuchProcess:
        pass
