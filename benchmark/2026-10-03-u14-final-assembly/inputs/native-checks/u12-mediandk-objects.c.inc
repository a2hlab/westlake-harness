struct AMediaDataSource {
    void *userdata;
    AMediaDataSourceReadAt read_at;
    AMediaDataSourceGetSize get_size;
    AMediaDataSourceClose close;
};

struct AMediaExtractor {
    unsigned unconfigured;
};

struct Int32Property {
    char *name;
    int32_t value;
    struct Int32Property *next;
};

struct AMediaFormat {
    struct Int32Property *properties;
};

static media_status_t unsupported_media(const char *function) {
    fprintf(stderr, "[U12-MEDIA-UNSUPPORTED] %s status=%d\n", function, AMEDIA_ERROR_UNSUPPORTED);
    return AMEDIA_ERROR_UNSUPPORTED;
}

AMediaFormat *AMediaFormat_new(void) {
    return calloc(1, sizeof(AMediaFormat));
}

static void delete_format(AMediaFormat *format) {
    if (format == NULL) return;
    struct Int32Property *property = format->properties;
    while (property != NULL) {
        struct Int32Property *next = property->next;
        free(property->name);
        free(property);
        property = next;
    }
    free(format);
}

static void set_int32(AMediaFormat *format, const char *name, int32_t value) {
    if (format == NULL || name == NULL) return;
    struct Int32Property *property = format->properties;
    while (property != NULL) {
        if (strcmp(property->name, name) == 0) {
            property->value = value;
            return;
        }
        property = property->next;
    }
    property = calloc(1, sizeof(*property));
    if (property == NULL) return;
    property->name = strdup(name);
    if (property->name == NULL) {
        free(property);
        return;
    }
    property->value = value;
    property->next = format->properties;
    format->properties = property;
}

static bool get_int32(AMediaFormat *format, const char *name, int32_t *output) {
    if (format == NULL || name == NULL || output == NULL) return false;
    for (struct Int32Property *property = format->properties; property != NULL; property = property->next) {
        if (strcmp(property->name, name) == 0) {
            *output = property->value;
            return true;
        }
    }
    return false;
}
