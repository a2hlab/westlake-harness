# Shared strict input check for the manifest JNI bridge closure.
# Source after setting ADAPTER_ROOT and OH; overrides are used by standalone builds.
MINIZIP_DIR="${BRIDGE_MINIZIP_DIR:-$OH/out/rk3568/obj/third_party/zlib/contrib/minizip/shared_libz}"
LIBZ_A="${BRIDGE_LIBZ_A:-$OH/out/rk3568/obj/third_party/zlib/libz.a}"
for required in \
 "$ADAPTER_ROOT/framework/package-manager/jni/apk_manifest_jni.cpp" \
 "$ADAPTER_ROOT/framework/package-manager/jni/apk_manifest_parser.cpp" \
 "$ADAPTER_ROOT/framework/package-manager/jni/axml_parser.cpp" \
 "$ADAPTER_ROOT/framework/package-manager/jni/arsc_resolver.cpp" \
 "$MINIZIP_DIR/unzip.o" "$MINIZIP_DIR/ioapi.o" "$LIBZ_A"; do
 if [ ! -f "$required" ]; then
  echo "ERROR: required manifest bridge input missing: $required" >&2
  exit 1
 fi
done
