import requests, os, json, random, shutil
from secrets import token_urlsafe

INSTANCE_DIR: str = os.path.join(os.getcwd(), "instances")


def fetch_docker_image(name: str) -> dict:
    res = requests.get(f"https://hub.docker.com/v2/search/repositories/?query={name}&page_size=10")

    if res.status_code == 200:
        results = [repo for repo in res.json()["results"] if repo["repo_name"] == name]
        return results


def load_instances() -> list[dict]:
    collections = []

    os.makedirs(INSTANCE_DIR, exist_ok=True)

    for instance_id in os.listdir(INSTANCE_DIR):
        instance_path = os.path.join(INSTANCE_DIR, instance_id)

        if not os.path.isdir(instance_path):
            continue

        with open(os.path.join(instance_path, "config.json"), "r") as file:
            collections.append(json.loads(file.read()))

    return collections


def create_instances(instance_name: str, ram: int, core: int, username: str, password: int) -> None:
    instance_id = "".join([random.choice("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(35)])
    instance_dir = os.path.join(INSTANCE_DIR, instance_id)

    os.mkdir(instance_dir)
    os.mkdir(os.path.join(instance_dir, "workspace"))

    with open(os.path.join(instance_dir, "config.json"), "w") as file:
        json.dump(
            {
                "instance_id": instance_id,
                "instance_name": instance_name,
                "status": "stopped",
                "ram": ram,
                "core": core,
                "uptime": "0",
                "instance_config": {
                    "docker_image": "",
                    "install_command": "",
                    "run_command": "",
                },
                "instance_user": username,
                "instance_password": password,
                "http_forward_server": "https://goto00%s.pythonanywhere.com" % random.randint(1, 3),
                "http_forward_id": instance_id,
                "http_forward_port": 5000,
            },
            file,
            indent=2,
        )


def get_data_by_id(instance_id: str) -> dict:
    instance_dir = os.path.join(INSTANCE_DIR, instance_id)

    if not os.path.exists(instance_dir) or not os.path.isdir(instance_dir):
        return

    with open(os.path.join(instance_dir, "config.json")) as file:
        return json.load(file)


def write(instance_id: str, data: dict) -> None:
    instance_dir = os.path.join(INSTANCE_DIR, instance_id)

    if not os.path.exists(instance_dir) or not os.path.isdir(instance_dir):
        return

    with open(os.path.join(instance_dir, "config.json"), "w") as file:
        json.dump(data, file, indent=2)


def create_docker_file(instance_id: str) -> None:
    instance_dir = os.path.join(INSTANCE_DIR, instance_id)
    data = json.load(open(os.path.join(instance_dir, "config.json")))

    docker_image = data["instance_config"]["docker_image"]
    install_command = data["instance_config"]["install_command"]
    run_command = data["instance_config"]["run_command"]
    # workspace_dir = os.path.join(instance_dir, "workspace")

    curl_cmd = (
        """curl -X POST -H "Content-Type: application/json" -d "$(printf '{"api_key": "passwd", "destination_url": "%s", "unique_id": """.replace(
            "passwd", os.getenv("PYANY_PASSWD", "a")
        )
        + '"'
        + data["http_forward_id"]
        + '"'
        + r"""}' "$(head -n 1 /workspace/.webaddr | tr -d '\r\n')")" """
        + data["http_forward_server"]
        + "/create"
    )
    serveo_script = (
        r"""coproc SSH_TUNNEL { cloudflared tunnel --url http://localhost:5000 --no-autoupdate 2>&1; }

while IFS= read -r line <&${SSH_TUNNEL[0]}; do
  if [[ "$line" == *"trycloudflare.com"* ]]; then
    _match=$(echo "$line" | grep -oE 'https?://[^ ]+')
    if [[ -n "$_match" ]]; then
      public_url="$_match"
      echo $public_url > /workspace/.webaddr
      break
    fi
  fi
done

"""
        + curl_cmd
        + " > /dev/null 2>&1"
    )

    open(os.path.join(instance_dir, "tunnel.sh"), "w").write(serveo_script)

    with open(os.path.join(instance_dir, "entrypoint.sh"), "w") as file:
        file.write(
            f"""#!/bin/bash

nohup bash /tunnel.sh && rm -f /tunnel.sh > /dev/null 2>&1

{'echo "\x1b[1m\x1b[34m===== 🔧  Installing dependencies... =====\x1b[0m\n"' if install_command else ""}
{install_command}

echo "\n\x1b[1m\x1b[34m===== 🚀  Starting application... =====\x1b[0m\n"
{run_command}
tail -f /dev/null"""
        )

    with open(os.path.join(instance_dir, "Dockerfile"), "w") as file:
        file.write(
            f"FROM {docker_image}"
            + r"""
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /workspace
RUN wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared
COPY workspace/ .
COPY entrypoint.sh /
COPY tunnel.sh /

RUN chmod +x /entrypoint.sh
RUN chmod +x /tunnel.sh
RUN chmod +x cloudflared
RUN mv cloudflared /usr/local/bin/

ENTRYPOINT ["/entrypoint.sh"]"""
        )


def format_time(seconds: int) -> str:
    if not isinstance(seconds, int):
        return

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if secs or not parts:
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")

    return ", ".join(parts)
