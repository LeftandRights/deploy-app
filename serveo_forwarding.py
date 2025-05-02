import subprocess, re, threading
from time import sleep


ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
count = 0


class Serveo(threading.Thread):
    def __init__(self, source_port: int, destination_port: int, port_range: tuple[int, int] | None = None) -> None:
        self.source_port: int = source_port
        self.destination_port = destination_port
        self.port_list = []

        if port_range:
            self.port_list = [
                item for sublist in [f"-R {port}:localhost:{destination_port}".split() for port in range(*port_range)] for item in sublist
            ]

        threading.Thread.__init__(self, daemon=True)

    def run(self) -> None:
        global count

        command = [
            "ssh",
            *(f"-R {self.source_port}:localhost:{self.destination_port}" if not self.port_list else "").split(),
            *self.port_list,
            "serveo.net",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
        ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        for line in process.stdout:
            if not line:
                continue

            if "Forwarding TCP" in (line := ANSI_ESCAPE.sub("", line).strip()):
                count += 1
                print(line, f"({count}/1000)")
                continue


for port in range(59000, 60001, 18):
    Serveo(0, 9050, (port, port + 18)).start()

while True:
    sleep(60)
