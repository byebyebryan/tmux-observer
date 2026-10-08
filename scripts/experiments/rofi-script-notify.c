/* SPDX-License-Identifier: MIT
 * T06 native mode prototype, pinned to installed Rofi 2.0/Mode ABI 7.
 * The installed mode interface delegates row/filter/result semantics to Rofi's
 * script mode. Private factory/view hooks are explicit experiment dependencies.
 * No preload, source/service/lifecycle action or synthesized key is involved.
 */
#include <dlfcn.h>
#include <rofi/mode-private.h>
#include <string.h>
#include <sys/stat.h>

#if ABI_VERSION != 7
#error "This experiment is pinned to Rofi Mode ABI 7."
#endif

typedef struct {
    Mode *script;
    guint timer;
    char *feed;
    struct stat stamp;
    gboolean observed;
} NotifyState;

static Mode *(*script_setup)(const char *);
static void *(*active_view)(void);
static Mode *(*view_mode)(void *);
static int (*completed_view)(void *);
static void (*update_view)(void *);
static void (*trigger_action)(void *, int, unsigned int);
static unsigned int (*action_from_name)(const char *);

static gboolean notify_tick(gpointer context) {
    Mode *sw = context;
    void *view = active_view();
    if (!view || view_mode(view) != sw) {
        return G_SOURCE_CONTINUE;
    }
    if (completed_view(view)) {
        update_view(view);
    }
    view = active_view();
    NotifyState *data = mode_get_private_data(sw);
    if (!data || !view || view_mode(view) != sw) {
        return G_SOURCE_CONTINUE;
    }
    struct stat current;
    if (stat(data->feed, &current) == 0) {
        gboolean changed = data->observed &&
            (current.st_ino != data->stamp.st_ino ||
             current.st_mtim.tv_sec != data->stamp.st_mtim.tv_sec ||
             current.st_mtim.tv_nsec != data->stamp.st_mtim.tv_nsec);
        data->stamp = current;
        data->observed = TRUE;
        if (changed) {
            // SCOPE_GLOBAL is zero in the pinned Rofi 2.0 keyb.h.
            trigger_action(view, 0, action_from_name("kb-custom-19"));
            update_view(view);
        }
    }
    return G_SOURCE_CONTINUE;
}

static int initialize(Mode *sw) {
    const char *command = g_getenv("TMUX_OBSERVER_ROFI_SCRIPT");
    const char *feed = g_getenv("TMUX_OBSERVER_ROFI_FEED");
    if (!command || !feed || strlen(command) > 16384 || strlen(feed) > 4096) {
        return FALSE;
    }
    script_setup = dlsym(RTLD_DEFAULT, "script_mode_parse_setup");
    active_view = dlsym(RTLD_DEFAULT, "rofi_view_get_active");
    view_mode = dlsym(RTLD_DEFAULT, "rofi_view_get_mode");
    completed_view = dlsym(RTLD_DEFAULT, "rofi_view_get_completed");
    update_view = dlsym(RTLD_DEFAULT, "rofi_view_maybe_update");
    trigger_action = dlsym(RTLD_DEFAULT, "rofi_view_trigger_action");
    action_from_name = dlsym(RTLD_DEFAULT, "key_binding_get_action_from_name");
    if (!script_setup || !active_view || !view_mode || !completed_view ||
        !update_view || !trigger_action || !action_from_name) {
        return FALSE;
    }
    NotifyState *data = g_new0(NotifyState, 1);
    data->feed = g_strdup(feed);
    char *specification = g_strconcat("observer-notify-script:", command, NULL);
    data->script = script_setup(specification);
    g_free(specification);
    if (!data->script || !mode_init(data->script)) {
        if (data->script) {
            mode_destroy(data->script);
            mode_free(&data->script);
        }
        g_free(data->feed);
        g_free(data);
        return FALSE;
    }
    mode_set_private_data(sw, data);
    sw->display_name = data->script->display_name;
    data->timer = g_timeout_add(25, notify_tick, sw);
    return TRUE;
}

static void destroy(Mode *sw) {
    NotifyState *data = mode_get_private_data(sw);
    if (data) {
        g_source_remove(data->timer);
        mode_destroy(data->script);
        mode_free(&data->script);
        g_free(data->feed);
        g_free(data);
        mode_set_private_data(sw, NULL);
        sw->display_name = NULL;
    }
}

static unsigned int count(const Mode *sw) {
    NotifyState *data = mode_get_private_data(sw);
    return mode_get_num_entries(data->script);
}

static char *display(const Mode *sw, unsigned int line, int *state, GList **attributes, int get_entry) {
    NotifyState *data = mode_get_private_data(sw);
    return mode_get_display_value(data->script, line, state, attributes, get_entry);
}

static int match(const Mode *sw, rofi_int_matcher **tokens, unsigned int line) {
    NotifyState *data = mode_get_private_data(sw);
    return mode_token_match(data->script, tokens, line);
}

static char *message(const Mode *sw) {
    NotifyState *data = mode_get_private_data(sw);
    return mode_get_message(data->script);
}

static cairo_surface_t *icon(const Mode *sw, unsigned int line, unsigned int height) {
    NotifyState *data = mode_get_private_data(sw);
    return mode_get_icon(data->script, line, height);
}

static ModeMode result(Mode *sw, int action, char **input, unsigned int selected) {
    NotifyState *data = mode_get_private_data(sw);
    ModeMode next = mode_result(data->script, action, input, selected);
    sw->display_name = data->script->display_name;
    return next;
}

G_MODULE_EXPORT Mode mode = {
    .abi_version = ABI_VERSION,
    .name = "observer-probe",
    ._init = initialize,
    ._destroy = destroy,
    ._get_num_entries = count,
    ._get_display_value = display,
    ._token_match = match,
    ._get_message = message,
    ._get_icon = icon,
    ._result = result,
    .type = MODE_TYPE_SWITCHER,
};
