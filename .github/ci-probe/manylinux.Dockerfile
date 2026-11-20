# CI probe: stands in for Kokoro's linux-tink-py-manylinux{,-arm64} images
# (kokoro/testutils/py_test_container_images.sh), which are private.
# tools/distribution/create_bdist_linux.sh expects the image to provide the
# build tools. BASE_IMAGE is the quay.io/pypa/manylinux_2_28 image that the
# bdist scripts pinned until 16f8000 ("Use prebuilt manylinux images for
# bdist"); this adds what tools/distribution/build_linux_binary_wheels.sh,
# which 16f8000 removed, installed into it: bazelisk 1.30.0 and protoc 29.5
# (same URLs and SHA-256 sums), and LD_LIBRARY_PATH=/usr/local/lib.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

RUN set -eux; \
    case "$(uname -m)" in \
      x86_64) \
        bazelisk_arch="amd64"; \
        bazelisk_sha256="a248ae2b2b62b5baebb748f6fba7203bff1a27e5d01b55399a8406744cb539e8"; \
        protoc_arch="x86_64"; \
        protoc_sha256="a3f094363cd205c6f7af0d1b9305cb4c8517043f265cdb188f098cae93e8b217"; \
        ;; \
      aarch64) \
        bazelisk_arch="arm64"; \
        bazelisk_sha256="b2bcc040c213b44586b121bda6d983c35df121b917c3a7a66fb16f2fa0df1a4f"; \
        protoc_arch="aarch_64"; \
        protoc_sha256="25eb0848ff13a90a0b2d2a3b4a9d2babc7fbfe158f596c00d8c26a21028dd6f5"; \
        ;; \
      *) \
        echo "Unsupported architecture $(uname -m)" >&2; \
        exit 1; \
        ;; \
    esac; \
    curl -LsS -o /usr/local/bin/bazelisk \
      "https://github.com/bazelbuild/bazelisk/releases/download/v1.30.0/bazelisk-linux-${bazelisk_arch}"; \
    echo "${bazelisk_sha256} /usr/local/bin/bazelisk" | sha256sum -c -; \
    chmod +x /usr/local/bin/bazelisk; \
    curl -LsS -o /tmp/protoc.zip \
      "https://github.com/protocolbuffers/protobuf/releases/download/v29.5/protoc-29.5-linux-${protoc_arch}.zip"; \
    echo "${protoc_sha256} /tmp/protoc.zip" | sha256sum -c -; \
    unzip -o /tmp/protoc.zip -d /usr/local bin/protoc; \
    rm /tmp/protoc.zip

# build_linux_binary_wheels.sh: "Required to fix
# https://github.com/pypa/manylinux/issues/357."
ENV LD_LIBRARY_PATH=/usr/local/lib
