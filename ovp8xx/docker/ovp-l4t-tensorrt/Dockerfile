##########################################
# Docker base image for O3R amd64 builds #
##########################################

ARG O3R_BASE="o3r-l4t-base:r32.4"

FROM nexus03.dev.ifm:18443/${O3R_BASE} as base

FROM base as builder


# Install essential build packages
RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get install -y -qq --no-install-recommends \
    ca-certificates \
    build-essential \
    libnvinfer-samples \
    cuda-libraries-dev-${CUDA} \
    cuda-cudart-dev-${CUDA} \
    cuda-compiler-${CUDA} \
    && rm -rf /var/lib/apt/lists/*

# Build the TensorRT examples
RUN cd /usr/src/tensorrt/samples && CUDA_INSTALL_DIR=/usr/local/cuda-${CUDA}/targets/aarch64-linux \
    TRT_LIB_DIR=/usr/local/cuda-${CUDA}/targets/aarch64-linux/lib \
    CUDNN_INSTALL_DIR=/usr/local/cuda-${CUDA}/targets/aarch64-linux \
    TARGET=aarch64 \
    make BUILD_TYPE="release"

FROM base AS deploy

# The small runtime image to be used
# We do copy the files to our own destination due to the fact the NVIDIA docker runtime does
# overwrite /usr/src/tensorrt in the container with the O3R directory
COPY --from=builder /usr/src/tensorrt/bin/sample_algorithm_selector /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_char_rnn /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_dynamic_reshape /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_fasterRCNN /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_googlenet /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_int8 /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_int8_api /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_mnist /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_mnist_api /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_onnx_mnist /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_ssd /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_uff_faster_rcnn /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_uff_mask_rcnn /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_uff_mnist /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_uff_plugin_v2_ext /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/sample_uff_ssd /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/bin/trtexec /opt/ifm/tensorrt/bin/
COPY --from=builder /usr/src/tensorrt/data /opt/ifm/tensorrt/data
