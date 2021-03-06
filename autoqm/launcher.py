
# connect to registration table

# search entries with status "job_created" 
# check the job input files are indeed there

# launch job, get jobid and update status "job_launched"
import os
import subprocess

import autoqm.utils
from autoqm.connector import saturated_ringcore_table

config = autoqm.utils.read_config()

def select_launch_target(limit=100):
	"""
	This method is to inform job launcher which targets 
	to launch, which need meet two requirements:
	1. status is job_created
	2. job input files located as expected

	Returns a list of targets with necessary meta data
	"""
	top_targets = list(saturated_ringcore_table.find({"status":"job_created"}).sort([('count', -1)]).limit(limit))

	selected_targets = []
	data_path = config['QuantumMechanicJob']['data_path']
	for target in top_targets:
		aug_inchi = str(target['aug_inchi'])
		spec_name = aug_inchi.replace('/', '_slash_')
		spec_path = os.path.join(data_path, spec_name)

		inp_file = os.path.join(spec_path, 'input.inp')
		submission_script_path = os.path.join(spec_path, 'submit.sl')
		if os.path.exists(inp_file) and os.path.exists(submission_script_path):
			selected_targets.append(target)
		else:
			print("Warning: {0} has status job_created, but no input files found.".format(aug_inchi))
			print("If the job input is created by this current worker, it should be fine.")
			print("Otherwise, please check if there's issues with autoQM job creator.")

	print('Selected {0} targets to launch.'.format(len(selected_targets)))

	return selected_targets

def launch_jobs(limit):
	"""
	This method launches job with following steps:
	1. select jobs to launch
	2. go to each job folder
	3. launch them with "sbatch submit.sl"
	4. get job id
	5. update status "job_launched"
	"""
	# 1. select jobs to launch
	targets = select_launch_target(limit)

	# 2. go to each job folder
	data_path = config['QuantumMechanicJob']['data_path']
	for target in targets:
		aug_inchi = str(target['aug_inchi'])
		spec_name = aug_inchi.replace('/', '_slash_')
		spec_path = os.path.join(data_path, spec_name)

		os.chdir(spec_path)

		# 3. launch them with "sbatch submit.sl"
		commands = ['sbatch', 'submit.sl']
		process = subprocess.Popen(commands,
								stdout=subprocess.PIPE,
								stderr=subprocess.PIPE)

		stdout, stderr = process.communicate()

		if stderr:
			print(stderr)
			continue

		# 4. get job id from stdout, e.g., "Submitted batch job 5022607"
		job_id = stdout.replace('Submitted batch job ', '').strip()
		print("Job id for {0} is {1}.".format(aug_inchi, job_id))

		# 5. update status "job_launched"
		query = {"aug_inchi": aug_inchi}
		update_field = {
				'job_id': job_id,
				'status': "job_launched"
		}

		saturated_ringcore_table.update_one(query, {"$set": update_field}, True)

limit = int(config['QuantumMechanicJob']['limit_per_launch'])
launch_jobs(limit)

