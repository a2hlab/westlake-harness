static jobject ReturnParcelFileDescriptor(JNIEnv* env, std::unique_ptr<Asset> asset,
                                          jlongArray out_offsets) {
  off64_t start_offset, length;
  int fd = asset->openFileDescriptor(&start_offset, &length);
  asset.reset();

  if (fd < 0) {
    jniThrowException(env, "java/io/FileNotFoundException",
                      "This file can not be opened as a file descriptor; it is probably "
                      "compressed");
    return nullptr;
  }

  jlong* offsets = reinterpret_cast<jlong*>(env->GetPrimitiveArrayCritical(out_offsets, 0));
  if (offsets == nullptr) {
    close(fd);
    return nullptr;
  }

  offsets[0] = start_offset;
  offsets[1] = length;

  env->ReleasePrimitiveArrayCritical(out_offsets, offsets, 0);

  jobject file_desc = jniCreateFileDescriptor(env, fd);
  if (file_desc == nullptr) {
    close(fd);
    return nullptr;
  }

  // This is the implementation of android::newParcelFileDescriptor used by
  // AOSP android_util_Binder.cpp: construct the local Java owner directly.
  // No Binder transaction or native Parcel operation is involved.
  jclass pfd_class = env->FindClass("android/os/ParcelFileDescriptor");
  if (pfd_class == nullptr) {
    close(fd);
    return nullptr;
  }
  jmethodID constructor = env->GetMethodID(
      pfd_class, "<init>", "(Ljava/io/FileDescriptor;)V");
  if (constructor == nullptr) {
    close(fd);
    env->DeleteLocalRef(pfd_class);
    return nullptr;
  }
  jobject parcel_fd = env->NewObject(pfd_class, constructor, file_desc);
  env->DeleteLocalRef(pfd_class);
  env->DeleteLocalRef(file_desc);
  if (parcel_fd == nullptr) {
    close(fd);
    return nullptr;
  }
  // Ownership of fd has transferred to ParcelFileDescriptor.
  return parcel_fd;
}

