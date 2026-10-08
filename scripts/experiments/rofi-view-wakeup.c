/* SPDX-License-Identifier: MIT
 * Owned T06 experiment only; private Rofi 2.0 symbols are not a deployment API.
 * Process only a completed view whose theme action is otherwise pending input.
 * No synthesized keys, source reads, model mutation or installed Rofi changes.
 */
#include <dlfcn.h>
#include <glib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void *(*active_view)(void);
static int (*completed_view)(void *);
static void (*update_view)(void *);
static void (*trigger_action)(void *, int, unsigned int);
static unsigned int (*action_from_name)(const char *);
static const char *feed_path;
static struct stat previous_feed;
static gboolean saw_feed;

static gboolean wake_completed(gpointer unused) {
    (void)unused;
    void *view = active_view();
    if (view && completed_view(view)) {
        update_view(view);
    }
    if (feed_path) {
        struct stat current;
        if (stat(feed_path, &current) == 0) {
            gboolean changed = saw_feed &&
                (current.st_ino != previous_feed.st_ino ||
                 current.st_mtim.tv_sec != previous_feed.st_mtim.tv_sec ||
                 current.st_mtim.tv_nsec != previous_feed.st_mtim.tv_nsec);
            previous_feed = current;
            saw_feed = TRUE;
            view = active_view();
            if (changed && view) {
                // SCOPE_GLOBAL is zero in the pinned Rofi 2.0 keyb.h. This
                // fixed read-only fixture callback is independent of typing.
                trigger_action(view, 0, action_from_name("kb-custom-19"));
                update_view(view);
            }
        }
    }
    return G_SOURCE_CONTINUE;
}

__attribute__((constructor)) static void initialize(void) {
    char executable[4096];
    ssize_t size = readlink("/proc/self/exe", executable, sizeof(executable) - 1);
    if (size <= 0 || size >= (ssize_t)sizeof(executable) - 1) {
        return;
    }
    executable[size] = '\0';
    const char *name = strrchr(executable, '/');
    // Rofi's callback children inherit the experiment environment. They must
    // not install a GLib timer or attempt to call Rofi functions.
    if (!name || strcmp(name + 1, "rofi") != 0) {
        return;
    }
    active_view = dlsym(RTLD_DEFAULT, "rofi_view_get_active");
    completed_view = dlsym(RTLD_DEFAULT, "rofi_view_get_completed");
    update_view = dlsym(RTLD_DEFAULT, "rofi_view_maybe_update");
    feed_path = g_getenv("TMUX_OBSERVER_ROFI_WAKEUP_FEED");
    trigger_action = dlsym(RTLD_DEFAULT, "rofi_view_trigger_action");
    action_from_name = dlsym(RTLD_DEFAULT, "key_binding_get_action_from_name");
    if (feed_path && (!trigger_action || !action_from_name)) {
        return;
    }
    if (active_view && completed_view && update_view) {
        g_timeout_add(25, wake_completed, NULL);
    }
}
