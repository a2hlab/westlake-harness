#pragma once
typedef struct GifFileType GifFileType;
typedef int GifByteType;
typedef int ColorMapObject;
typedef int SavedImage;
typedef int GifRecordType;
inline GifFileType* DGifOpen(void*, void*, int*) { return nullptr; }
inline int DGifSlurp(GifFileType*) { return 0; }
inline int DGifCloseFile(GifFileType*, int*) { return 0; }
