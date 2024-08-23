#---
# name: ifm_oem
# group: ifm3d
# notes: set permissions for the oem user

#---

    
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
# FROM ${BASE_IMAGE} AS stage
# FROM nvcr.io/nvidia/l4t-base:r32.7.1


# RUN chown -f -R ${uid}:${gid} /


ARG user=oem
ARG group=oem
ARG uid=442
ARG gid=442
RUN groupadd -g ${gid} ${group} \
&& useradd -u ${uid} -g ${gid} -s /bin/bash -m  ${user}
RUN apt-get update \
&& apt-get install -y sudo \
    && echo $user ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$user \
    && chmod 0440 /etc/sudoers.d/$user
COPY --from=stage --chown=oem:oem / /
RUN for dir in /root/ /home/ /etc/ /var/ /usr/ /bin/ /sbin/ /lib/ /opt/ /mnt/ /media/ /srv/ /tmp/ /var/ /run/ /dev/ /proc/ /dev/ dst/ ; do \
        if [ -d "$dir" ]; then \
            chown -R ${uid}:${gid} "$dir"; \
        fi; \
    done
# RUN find / -path /proc -prune -o -path /sys -prune -o -path /dev -prune -o -exec chown -f -R ${uid}:${gid} {} +
# # RUN for dir in /start_jupyter ; do \
# #         if [ -d "$dir" ]; then \
# #             chown ${uid}:${gid} "$dir"; \
# #         fi; \
# #     done

# # for dir in / chown Recursively but don't break on error
# RUN for dir in 