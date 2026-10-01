/*
 * Copyright (c) 2022 Huawei Device Co., Ltd.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "dynlink_rand.h"

/* Source excerpt: original lines 85-139. */
            }
            __libc_free(node);
            return;
        } else {
            pre_node = node;
            node = node->next;
        }
    }
}

static void *gen_handle(void)
{
    uintptr_t handle = saved_handle;
    do {
        if (getrandom(&handle, sizeof handle, GRND_RANDOM | GRND_NONBLOCK) == -1) {
            handle += HANDLE_INCREASE;
            saved_handle = handle;
        }
    } while (find_dso_by_handle((void *)handle) || handle == 0);
    return (void *)handle;
}

void *assign_valid_handle(struct dso *p)
{
    void *handle = find_handle_by_dso(p);
    if (handle == 0) {
        handle = gen_handle();
        if (!add_handle_node(handle, p)) {
            handle = 0;
        }
    }
    return handle;
}

struct loadtasks *create_loadtasks(void)
{
    struct loadtasks *tasks = __libc_malloc(sizeof(struct loadtasks));
    if (tasks) {
        tasks->array = NULL;
        tasks->capacity = 0;
        tasks->length = 0;
        return tasks;
    }
    return NULL;
}

bool append_loadtasks(struct loadtasks *tasks, struct loadtask *item)
{
    if (tasks->length + 1 > tasks->capacity) {
        size_t new_cap = 0;
        new_cap = tasks->capacity + TASK_BASE_CAPACITY;
        void *realloced = NULL;
        if (tasks->array) {
            realloced = __libc_realloc(tasks->array, new_cap * sizeof(struct loadtask *));
        } else {
