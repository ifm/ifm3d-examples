#%%
import sys

from pathlib import Path
import tqdm

try:
    from ovp_docker_utils.cli import cli_tee
except ImportError:
    from cli import cli_tee

chunk_size = 1024*1024
def cat(fname):
    # rewrite with tqdm but with progress bar
    fsize= Path(fname).stat().st_size
    with open(fname, 'rb') as f:
        with tqdm.tqdm(total=fsize, unit='KB', unit_scale=True,
                      bar_format='{desc:<5.5}{percentage:3.0f}%|{bar:10}{r_bar}' ) as pbar:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                sys.stdout.buffer.write(chunk)
                sys.stdout.flush()
                pbar.update(len(chunk))
                sys.stderr.flush()
parent = Path(__file__).parent
fname = "demo.py"
default_src = (parent/fname).as_posix()
home = "/home/oem"

def ssh_pipe(
        src:str = default_src,
        output_cmd: str = "cat > /dev/null",
        host:str = "192.168.0.69",
        user:str = "oem",
        key:str = "~/.ssh/id_rsa_ovp8xx",
    ):
    assert output_cmd
    python= sys.executable
    cmd = f'{python} {__file__} cat {Path(src).as_posix()} | ssh {user}@{host} -o "StrictHostKeyChecking no" -i {key} "{output_cmd}" '
    cli_tee(cmd,pty=True)
# %%
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'cat':
            cat(sys.argv[2])
        else:
            print(f"transferring {sys.argv[1]}")
            dest = f"{home}/{Path(sys.argv[1]).name}"
            ssh_pipe(sys.argv[1], output_cmd=f"cat > {dest}")
# %%
