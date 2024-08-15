#%%

# use regex to filter out files

exclude_patterns = [
    "/tmp/",
    "/.git/",
    "/logs/",
    "/__pycache__/",
    "jetson-containers",
] # middle of path
exclude_file_extensions = [
    ".h5",
    "sh",
    ".tar",
    ".zip",
] # end of path

files = [
    "ovp8xx/docker/ovp_docker_utils/docker_build.py",
    "ovp8xx/docker/ovp_docker_utils/docker_build.h5",
    "ovp8xx/docker/.git/ovp_docker_utils/docker_build.py",
    "ovp8xx/docker/ovp_docker_utils/docker_build.sh",
    "ovp8xx/docker/.git/docker_build.py",
]

# convert the exclude patterns to regex
import re
exclude_regex = '|'.join([
                pattern for pattern in exclude_patterns]+[
                f".*{ext}$" for ext in exclude_file_extensions])
# filter out files
filtered_files = []
for file in files:
    print( re.search(exclude_regex, file))
    if not re.search(exclude_regex, file):
        filtered_files.append(file)
#%%
print(exclude_regex)

# %%
filtered_files
# %%
