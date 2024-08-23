#%%
import sys
try:
    from ovp_docker_utils.cli import cli_tee
except ImportError:
    from cli import cli_tee
from pathlib import Path
import tqdm

chunk_size = 1024
def cat(fname):
    # with open(fname, 'rb') as f:
    #     while(True):
    #         chunk = f.read(chunk_size)
    #         if not chunk:
    #             break
    #         sys.stdout.buffer.write(chunk)
    #         sys.stdout.flush()

    # rewrite with tqdm
    with open(fname, 'rb') as f:
        for chunk in tqdm.tqdm(iter(lambda: f.read(chunk_size), b''), unit='KB', unit_scale=True):
            sys.stdout.buffer.write(chunk)
            sys.stdout.flush()


parent = Path(__file__).parent
fname = "demo.py"
default_src = (parent/fname).as_posix()
home = "/home/oem"

def transfer(
        src:str = default_src,
        output_cmd: str = "cat > /dev/null",
        host:str = "192.168.0.69",
        user:str = "oem",
        key:str = "~/.ssh/id_rsa_ovp8xx",
    ):
    assert output_cmd
    python= sys.executable
    cmd = f'{python} {__file__} cat {Path(src).as_posix()} | ssh {user}@{host} -o "StrictHostKeyChecking no" -i {key} "{output_cmd}" '
    cli_tee(cmd,verbose=True,pty=True)
# %%
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'cat':
            cat(sys.argv[2])
        else:
            print(f"transferring {sys.argv[1]}")
            dest = f"{home}/{Path(sys.argv[1]).name}"
            transfer(sys.argv[1], output_cmd=f"cat > {dest}")
# %%
