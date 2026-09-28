#pragma once
#include <cstdint>
namespace ultrahdr {
struct jpegr_uncompressed_struct { void* data; size_t length; };
struct jpegr_compressed_struct { void* data; size_t length; };
typedef int status_t;
}
