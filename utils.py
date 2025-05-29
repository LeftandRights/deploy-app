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


def create_instances(instance_name: str, ram: int, core: int, username: str, password: str) -> None:
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
    port = data["http_forward_port"]
    # workspace_dir = os.path.join(instance_dir, "workspace")

    curl_cmd = (
        """curl -X POST -H "Content-Type: application/json" -d "$(printf '{"authorization": "passwd", "instance_id": "ins_id", "redirect_url": "%s", "unique_id": """.replace(
            "passwd", os.getenv("PYANY_PASSWD", "a")
        ).replace(
            "ins_id", instance_id
        )
        + '"'
        + data["http_forward_id"]
        + '"'
        + r"""}' "$(head -n 1 /workspace/.webaddr | tr -d '\r\n')")" """
        + "https://goto-tau.vercel.app/shorten"
    )
    serveo_script = (
        r"""#!/bin/bash

CLOUDFLARED_LAUNCH_LOG="/tmp/cloudflared_launch_attempt.log"
URL_OUTPUT_FILE="/workspace/.webaddr"

rm -f "$CLOUDFLARED_LAUNCH_LOG"

cloudflared tunnel --url http://localhost:%s --no-autoupdate > "$CLOUDFLARED_LAUNCH_LOG" 2>&1 &
CLOUDFLARED_PID=$!

if [[ -z "$CLOUDFLARED_PID" ]]; then
  exit 1
fi

public_url=""
SECONDS_WAITED=0
MAX_WAIT=30

while [[ -z "$public_url" && $SECONDS_WAITED -lt $MAX_WAIT ]]; do
  if ! kill -0 "$CLOUDFLARED_PID" 2>/dev/null; then
    exit 1
  fi

  if [[ -f "$CLOUDFLARED_LAUNCH_LOG" ]]; then
    _match=$(grep -oE 'https?://[-A-Za-z0-9_.]+trycloudflare\.com' "$CLOUDFLARED_LAUNCH_LOG" | head -n 1)
    if [[ -n "$_match" ]]; then
      public_url="$_match"
      break
    fi
  fi

  sleep 1
  SECONDS_WAITED=$((SECONDS_WAITED + 1))
done

if ! kill -0 "$CLOUDFLARED_PID" 2>/dev/null; then
  exit 1
fi

if [[ -n "$public_url" ]]; then
  echo "$public_url" > "$URL_OUTPUT_FILE"
  disown "$CLOUDFLARED_PID"
  exit 0
else
  kill "$CLOUDFLARED_PID"
  wait "$CLOUDFLARED_PID" 2>/dev/null
  exit 1
fi
"""
        % port
    )

    open(os.path.join(instance_dir, "tunnel.sh"), "w").write(serveo_script)

    with open(os.path.join(instance_dir, "entrypoint.sh"), "w") as file:
        file.write(
            f"""#!/bin/bash

/tunnel.sh && rm -f /tunnel.sh > /dev/null 2>&1
{curl_cmd}

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
%s
RUN wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared
COPY workspace/ .
COPY entrypoint.sh /
COPY tunnel.sh /

RUN chmod +x /entrypoint.sh
RUN chmod +x /tunnel.sh
RUN chmod +x cloudflared
RUN mv cloudflared /usr/local/bin/

ENTRYPOINT ["/entrypoint.sh"]"""
            % ("RUN apt update -y && apt upgrade -y && apt-get install curl wget -y" if "ubuntu" in docker_image else "")
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
