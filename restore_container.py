import subprocess, utils

build_command = lambda instance_id: f"docker build -t {instance_id.lower()} instances/{instance_id}".split()
run_command = (
    lambda instance_id, memory, core: f"docker run -d --memory={memory} --cpus={core} --name container_{instance_id} {instance_id.lower()}".split()
)


for instance in utils.load_instances():
    if not instance["status"] == "running":
        continue

    build_cmd = build_command(instance_id=instance["instance_id"])
    run_cmd = run_command(
        instance_id=instance["instance_id"],
        memory=instance["ram"].replace(" ", "").replace("GB", "g").replace("MB", "m"),
        core=instance["core"],
    )

    if subprocess.run(build_cmd).returncode == 0:
        run_process = subprocess.run(run_cmd)

        if run_process.returncode == 0:
            continue

    instance_data = utils.get_data_by_id(instance_id=instance["instance_id"])
    instance_data["status"] = "stopped"
    utils.write(
        instance_id=instance["instance_id"],
        data=instance_data,
    )
