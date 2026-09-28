# Minimal board config for OH Adapter
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_VARIANT := generic
TARGET_CPU_ABI := arm64-v8a

# No 32-bit support needed
TARGET_SUPPORTS_32_BIT_APPS := false
TARGET_SUPPORTS_64_BIT_APPS := true

# Minimal partition sizes
BOARD_SYSTEMIMAGE_PARTITION_SIZE := 2147483648
BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := ext4

# No vendor image
BOARD_VENDORIMAGE_PARTITION_SIZE := 0

# Use generic kernel (not actually needed for our build)
TARGET_NO_KERNEL := true
TARGET_NO_BOOTLOADER := true
TARGET_NO_RECOVERY := true

# No SELinux policy needed (OH handles security)
BOARD_SEPOLICY_DIRS :=
