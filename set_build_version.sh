#!/bin/bash
# Set the timezone to GMT+4
export TZ=Asia/Dubai

BUILD_VERSION=$(date +%Y.%-m.%-d.%H.%M)
echo "Build version generated: $BUILD_VERSION"
echo "{\"BUILD_VERSION\":\"$BUILD_VERSION\"}" > build_version.json
