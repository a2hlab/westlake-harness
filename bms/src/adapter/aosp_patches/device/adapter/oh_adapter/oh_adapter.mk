#
# Minimal AOSP product for Android-OH Adapter Project
# Only includes App runtime components (no system_server, no system apps)
#

# 64-bit only
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)

PRODUCT_NAME := oh_adapter
PRODUCT_DEVICE := generic_arm64
PRODUCT_BRAND := Android
PRODUCT_MODEL := OH Adapter Runtime
PRODUCT_MANUFACTURER := Adapter

# Minimal product settings
PRODUCT_PROPERTY_OVERRIDES +=     ro.build.display.id=oh_adapter-eng

# Only the App runtime packages we need
PRODUCT_PACKAGES +=     framework-minus-apex     framework-res     libandroid_runtime     dex2oat

# Allow missing dependencies for partial AOSP sync
ALLOW_MISSING_DEPENDENCIES := true

# Disable bazel mode for partial builds
BUILD_BROKEN_DISABLE_BAZEL := true
