#pragma once
#include <cstddef>
#include <cstdint>
#include <cstdio>
typedef int boolean;
typedef int J_COLOR_SPACE;
typedef int J_DCT_METHOD;
typedef unsigned int JDIMENSION;
typedef unsigned char JSAMPLE;
typedef JSAMPLE* JSAMPROW;
typedef JSAMPROW* JSAMPARRAY;
struct jpeg_error_mgr { int msg_code; };
struct jpeg_compress_struct {
    struct jpeg_error_mgr* err;
    JDIMENSION image_width, image_height;
    int input_components;
    J_COLOR_SPACE in_color_space;
};
struct jpeg_decompress_struct {
    struct jpeg_error_mgr* err;
    JDIMENSION image_width, image_height;
    JDIMENSION output_width, output_height;
    int output_components;
};
typedef struct jpeg_compress_struct* j_compress_ptr;
typedef struct jpeg_decompress_struct* j_decompress_ptr;
inline jpeg_error_mgr* jpeg_std_error(jpeg_error_mgr* e) { return e; }
inline void jpeg_create_compress(j_compress_ptr) {}
inline void jpeg_destroy_compress(j_compress_ptr) {}
inline void jpeg_set_defaults(j_compress_ptr) {}
inline void jpeg_set_quality(j_compress_ptr, int, boolean) {}
inline void jpeg_start_compress(j_compress_ptr, boolean) {}
inline void jpeg_finish_compress(j_compress_ptr) {}
inline JDIMENSION jpeg_write_scanlines(j_compress_ptr, JSAMPARRAY, JDIMENSION) { return 0; }
